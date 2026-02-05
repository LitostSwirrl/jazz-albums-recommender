import { useMemo } from 'react';
import { MarkerType } from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import type { Artist, Era, Album } from '../../../types';

export interface GraphNode extends Node {
  data: {
    artist: Artist;
    era: Era | undefined;
    influenceCount: number;
    size: 'sm' | 'md' | 'lg' | 'xl';
  };
}

export interface GraphData {
  nodes: GraphNode[];
  edges: Edge[];
  artistMap: Map<string, Artist>;
}

export const eraColors: Record<string, string> = {
  'early-jazz': '#f59e0b',
  'swing': '#eab308',
  'bebop': '#84cc16',
  'cool-jazz': '#22d3ee',
  'hard-bop': '#3b82f6',
  'free-jazz': '#a855f7',
  'fusion': '#ec4899',
  'contemporary': '#f43f5e',
};

function getNodeSize(influenceCount: number): 'sm' | 'md' | 'lg' | 'xl' {
  if (influenceCount >= 10) return 'xl';
  if (influenceCount >= 6) return 'lg';
  if (influenceCount >= 3) return 'md';
  return 'sm';
}

export function useInfluenceGraph(
  artists: Artist[],
  eras: Era[],
  albums: Album[],
  filter?: { focusArtistId?: string; depth?: number; eraFilter?: string; genreFilter?: string }
): GraphData {
  return useMemo(() => {
    const artistMap = new Map(artists.map((a) => [a.id, a]));
    const eraMap = new Map(eras.map((e) => [e.id, e]));

    // Build artist-to-genres map from albums
    const artistGenres = new Map<string, Set<string>>();
    albums.forEach((album) => {
      const genres = artistGenres.get(album.artistId) || new Set();
      album.genres.forEach((g) => genres.add(g.toLowerCase()));
      artistGenres.set(album.artistId, genres);
    });

    // Filter to artists with connections
    let relevantArtists = artists.filter(
      (a) => a.influences.length > 0 || a.influencedBy.length > 0
    );

    // Apply era filter
    if (filter?.eraFilter) {
      relevantArtists = relevantArtists.filter((a) =>
        a.eras.includes(filter.eraFilter as Artist['eras'][number])
      );
    }

    // Apply genre filter
    if (filter?.genreFilter) {
      relevantArtists = relevantArtists.filter((a) => {
        const genres = artistGenres.get(a.id);
        return genres?.has(filter.genreFilter!.toLowerCase());
      });
    }

    // Apply focus filter (N-hop neighborhood)
    if (filter?.focusArtistId && filter?.depth !== undefined) {
      const focusSet = getNeighborhood(
        filter.focusArtistId,
        filter.depth,
        artistMap
      );
      relevantArtists = relevantArtists.filter((a) => focusSet.has(a.id));
    }

    // Calculate influence counts
    const influenceCounts = new Map<string, number>();
    relevantArtists.forEach((artist) => {
      const count = artist.influences.length + artist.influencedBy.length;
      influenceCounts.set(artist.id, count);
    });

    // Create nodes
    const nodes: GraphNode[] = relevantArtists.map((artist) => {
      const influenceCount = influenceCounts.get(artist.id) || 0;
      const era = eraMap.get(artist.eras[0]);

      return {
        id: artist.id,
        type: 'artist',
        position: { x: 0, y: 0 }, // Will be set by layout
        data: {
          artist,
          era,
          influenceCount,
          size: getNodeSize(influenceCount),
        },
      };
    });

    // Create node ID set for validation
    const nodeIds = new Set(nodes.map((n) => n.id));

    // Create edges
    const edges: Edge[] = [];
    const edgeSet = new Set<string>();

    relevantArtists.forEach((artist) => {
      // Edges from influencers to this artist
      artist.influencedBy.forEach((influencerId) => {
        if (nodeIds.has(influencerId)) {
          const edgeId = `${influencerId}->${artist.id}`;
          if (!edgeSet.has(edgeId)) {
            edgeSet.add(edgeId);
            edges.push({
              id: edgeId,
              source: influencerId,
              target: artist.id,
              type: 'smoothstep',
              animated: false,
              style: { stroke: '#f59e0b', strokeWidth: 2 },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: '#f59e0b',
                width: 20,
                height: 20,
              },
            });
          }
        }
      });

      // Edges from this artist to influenced
      artist.influences.forEach((influencedId) => {
        if (nodeIds.has(influencedId)) {
          const edgeId = `${artist.id}->${influencedId}`;
          const reverseId = `${influencedId}->${artist.id}`;
          if (!edgeSet.has(edgeId) && !edgeSet.has(reverseId)) {
            edgeSet.add(edgeId);
            edges.push({
              id: edgeId,
              source: artist.id,
              target: influencedId,
              type: 'smoothstep',
              animated: false,
              style: { stroke: '#f59e0b', strokeWidth: 2 },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: '#f59e0b',
                width: 20,
                height: 20,
              },
            });
          }
        }
      });
    });

    return { nodes, edges, artistMap };
  }, [artists, eras, albums, filter?.focusArtistId, filter?.depth, filter?.eraFilter, filter?.genreFilter]);
}

// Get N-hop neighborhood around a focus artist
function getNeighborhood(
  focusId: string,
  depth: number,
  artistMap: Map<string, Artist>
): Set<string> {
  const visited = new Set<string>([focusId]);
  let frontier = [focusId];

  for (let i = 0; i < depth; i++) {
    const nextFrontier: string[] = [];

    frontier.forEach((id) => {
      const artist = artistMap.get(id);
      if (!artist) return;

      [...artist.influences, ...artist.influencedBy].forEach((neighborId) => {
        if (!visited.has(neighborId) && artistMap.has(neighborId)) {
          visited.add(neighborId);
          nextFrontier.push(neighborId);
        }
      });
    });

    frontier = nextFrontier;
  }

  return visited;
}

// Find shortest path between two artists using BFS
export function findShortestPath(
  startId: string,
  endId: string,
  artistMap: Map<string, Artist>
): string[] | null {
  if (startId === endId) return [startId];
  if (!artistMap.has(startId) || !artistMap.has(endId)) return null;

  const visited = new Set<string>([startId]);
  const queue: { id: string; path: string[] }[] = [{ id: startId, path: [startId] }];

  while (queue.length > 0) {
    const { id, path } = queue.shift()!;
    const artist = artistMap.get(id);
    if (!artist) continue;

    const neighbors = [...artist.influences, ...artist.influencedBy];

    for (const neighborId of neighbors) {
      if (neighborId === endId) {
        return [...path, neighborId];
      }

      if (!visited.has(neighborId) && artistMap.has(neighborId)) {
        visited.add(neighborId);
        queue.push({ id: neighborId, path: [...path, neighborId] });
      }
    }
  }

  return null; // No path found
}

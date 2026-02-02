import { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  ConnectionMode,
} from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Link } from 'react-router-dom';
import artistsData from '../data/artists.json';
import erasData from '../data/eras.json';
import type { Artist, Era } from '../types';

const artists = artistsData as Artist[];
const eras = erasData as Era[];

const eraColors: Record<string, string> = {
  'early-jazz': '#f59e0b',
  'swing': '#eab308',
  'bebop': '#84cc16',
  'cool-jazz': '#22d3ee',
  'hard-bop': '#3b82f6',
  'free-jazz': '#a855f7',
  'fusion': '#ec4899',
  'contemporary': '#f43f5e',
};

function ArtistNode({ data }: { data: { artist: Artist; era: Era | undefined } }) {
  const { artist, era } = data;
  const borderColor = era ? eraColors[era.id] || '#71717a' : '#71717a';

  return (
    <Link
      to={`/artist/${artist.id}`}
      className="block p-3 rounded-lg bg-zinc-900 border-2 hover:scale-105 transition-transform min-w-[120px] text-center"
      style={{ borderColor }}
    >
      <div className="text-sm font-semibold text-white truncate">{artist.name}</div>
      <div className="text-xs text-zinc-500">
        {artist.instruments.slice(0, 2).join(', ')}
      </div>
      {era && (
        <div
          className="text-xs mt-1 px-2 py-0.5 rounded inline-block"
          style={{ backgroundColor: borderColor + '30', color: borderColor }}
        >
          {era.name.split(' ')[0]}
        </div>
      )}
    </Link>
  );
}

const nodeTypes = {
  artist: ArtistNode,
};

export function InfluenceGraph() {
  // Create nodes from artists who have influence connections
  const { initialNodes, initialEdges } = useMemo(() => {
    const relevantArtists = artists.filter(
      (a) => a.influences.length > 0 || a.influencedBy.length > 0
    );

    // Create a map for quick lookup
    const artistMap = new Map(artists.map((a) => [a.id, a]));

    // Group artists by era for positioning
    const eraGroups: Record<string, Artist[]> = {};
    relevantArtists.forEach((artist) => {
      const primaryEra = artist.eras[0] || 'contemporary';
      if (!eraGroups[primaryEra]) eraGroups[primaryEra] = [];
      eraGroups[primaryEra].push(artist);
    });

    // Position nodes by era (vertical) and within era (horizontal)
    const eraOrder = ['early-jazz', 'swing', 'bebop', 'cool-jazz', 'hard-bop', 'free-jazz', 'fusion', 'contemporary'];
    const nodes: Node[] = [];

    eraOrder.forEach((eraId, eraIndex) => {
      const eraArtists = eraGroups[eraId] || [];
      const era = eras.find((e) => e.id === eraId);

      eraArtists.forEach((artist, artistIndex) => {
        const xOffset = (artistIndex - (eraArtists.length - 1) / 2) * 180;
        nodes.push({
          id: artist.id,
          type: 'artist',
          position: { x: 400 + xOffset, y: eraIndex * 150 },
          data: { artist, era },
        });
      });
    });

    // Create edges for influences
    const edges: Edge[] = [];
    relevantArtists.forEach((artist) => {
      // influencedBy: arrow from influencer TO this artist
      artist.influencedBy.forEach((influencerId) => {
        if (artistMap.has(influencerId) && nodes.find((n) => n.id === influencerId)) {
          edges.push({
            id: `${influencerId}-${artist.id}`,
            source: influencerId,
            target: artist.id,
            animated: true,
            style: { stroke: '#f59e0b', strokeWidth: 2 },
          });
        }
      });

      // influences: arrow FROM this artist to influenced
      artist.influences.forEach((influencedId) => {
        if (artistMap.has(influencedId) && nodes.find((n) => n.id === influencedId)) {
          // Avoid duplicates if already added from the other direction
          const existingEdge = edges.find(
            (e) => e.id === `${artist.id}-${influencedId}` || e.id === `${influencedId}-${artist.id}`
          );
          if (!existingEdge) {
            edges.push({
              id: `${artist.id}-${influencedId}`,
              source: artist.id,
              target: influencedId,
              animated: true,
              style: { stroke: '#f59e0b', strokeWidth: 2 },
            });
          }
        }
      });
    });

    return { initialNodes: nodes, initialEdges: edges };
  }, []);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    // Highlight connected edges
    setEdges((eds) =>
      eds.map((edge) => ({
        ...edge,
        style: {
          ...edge.style,
          stroke: edge.source === node.id || edge.target === node.id ? '#22d3ee' : '#f59e0b',
          strokeWidth: edge.source === node.id || edge.target === node.id ? 3 : 2,
        },
      }))
    );
  }, [setEdges]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-4xl font-bold mb-2">Artist Influence Network</h1>
        <p className="text-zinc-400">
          Explore how jazz musicians influenced each other across generations.
          Click on an artist to highlight their connections. Arrows show the direction of influence.
        </p>
      </div>

      {/* Era Legend */}
      <div className="flex flex-wrap gap-3 mb-6">
        {eras.map((era) => (
          <div key={era.id} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: eraColors[era.id] }}
            />
            <span className="text-sm text-zinc-400">{era.name}</span>
          </div>
        ))}
      </div>

      {/* Graph Container */}
      <div className="h-[600px] rounded-lg border border-zinc-800 overflow-hidden bg-zinc-950">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          connectionMode={ConnectionMode.Loose}
          fitView
          minZoom={0.3}
          maxZoom={2}
          defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
        >
          <Background color="#27272a" gap={20} />
          <Controls className="bg-zinc-900 border-zinc-700" />
          <MiniMap
            nodeColor={(node) => {
              const era = (node.data as { era?: Era }).era;
              return era ? eraColors[era.id] || '#71717a' : '#71717a';
            }}
            maskColor="rgba(0, 0, 0, 0.8)"
            className="bg-zinc-900 border-zinc-700"
          />
        </ReactFlow>
      </div>

      {/* Instructions */}
      <div className="mt-6 p-4 rounded-lg bg-zinc-900 border border-zinc-800">
        <h3 className="font-semibold text-amber-400 mb-2">How to Use</h3>
        <ul className="text-sm text-zinc-400 space-y-1">
          <li>• <strong>Drag</strong> to pan around the graph</li>
          <li>• <strong>Scroll</strong> to zoom in and out</li>
          <li>• <strong>Click</strong> an artist to highlight their connections</li>
          <li>• <strong>Click artist name</strong> to view their full profile</li>
          <li>• Arrows flow from <em>influencer</em> → <em>influenced</em></li>
        </ul>
      </div>
    </div>
  );
}

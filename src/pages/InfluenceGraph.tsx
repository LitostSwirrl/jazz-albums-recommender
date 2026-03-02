import { useCallback, useState, useMemo, useEffect, useRef } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
} from '@xyflow/react';
import type { Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import artistsData from '../data/artists.json';
import albumsData from '../data/albums.json';
import erasData from '../data/eras.json';
import { SEO } from '../components/SEO';
import type { Artist, Era, Album } from '../types';
import { getVerificationStats } from '../utils/connections';
import { ArtistPhoto } from '../components/ArtistPhoto';
import {
  ArtistNode,
  ConnectionEdge,
  useInfluenceGraph,
  useGraphLayout,
  findShortestPath,
  eraColors,
} from '../components/graph';
import { ArtistDropdown } from '../components/graph/controls/ArtistDropdown';
import type { ArtistDropdownHandle } from '../components/graph/controls/ArtistDropdown';

const artists = artistsData as Artist[];
const albums = albumsData as Album[];
const eras = erasData as Era[];

const nodeTypes = {
  artist: ArtistNode,
};

const edgeTypes = {
  connection: ConnectionEdge,
};

// Popular path presets
const POPULAR_PATHS: { fromId: string; toId: string; label: string }[] = [
  { fromId: 'miles-davis', toId: 'john-coltrane', label: 'Miles Davis \u2192 John Coltrane' },
  { fromId: 'charlie-parker', toId: 'sonny-rollins', label: 'Charlie Parker \u2192 Sonny Rollins' },
  { fromId: 'duke-ellington', toId: 'count-basie', label: 'Duke Ellington \u2192 Count Basie' },
  { fromId: 'art-blakey', toId: 'wynton-marsalis', label: 'Art Blakey \u2192 Wynton Marsalis' },
];

function VerificationBadge() {
  const stats = getVerificationStats();
  if (stats.total === 0) return null;

  return (
    <span className="flex items-center gap-2">
      <span className="text-emerald-400">
        <svg className="w-3.5 h-3.5 inline" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        </svg>
      </span>
      {stats.total} connections sourced ({stats.wikiCount} Wikipedia, {stats.total - stats.wikiCount} editorial)
    </span>
  );
}

function PathResult({ path, artistMap }: { path: string[]; artistMap: Map<string, Artist> }) {
  return (
    <div className="mt-4 p-4 bg-surface border border-coral/30 rounded-lg">
      <div className="text-sm text-coral mb-3 font-mono">
        Connected in {path.length - 1} degree{path.length > 2 ? 's' : ''} of separation
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {path.map((id, index) => {
          const artist = artistMap.get(id);
          if (!artist) return null;
          return (
            <span key={id} className="flex items-center gap-2">
              <ArtistPhoto imageUrl={artist.imageUrl} name={artist.name} size="sm" />
              <span className="text-charcoal font-medium text-sm">{artist.name}</span>
              {index < path.length - 1 && (
                <svg className="w-4 h-4 text-coral mx-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              )}
            </span>
          );
        })}
      </div>
    </div>
  );
}

function InfluenceGraphInner() {
  const { fitView } = useReactFlow();

  const [fromArtist, setFromArtist] = useState<Artist | null>(null);
  const [toArtist, setToArtist] = useState<Artist | null>(null);
  const toDropdownRef = useRef<ArtistDropdownHandle>(null);

  const artistMap = useMemo(() => new Map(artists.map((a) => [a.id, a])), []);

  // Auto-find path when both artists are selected
  const currentPath = useMemo(() => {
    if (!fromArtist || !toArtist) return null;
    if (fromArtist.id === toArtist.id) return null;
    return findShortestPath(fromArtist.id, toArtist.id, artistMap);
  }, [fromArtist, toArtist, artistMap]);

  // Graph filter: path mode or default bebop
  const filter = useMemo(() => {
    if (currentPath && currentPath.length >= 2) {
      return { pathArtistIds: currentPath };
    }
    return { eraFilter: 'bebop' };
  }, [currentPath]);

  const { nodes: graphNodes, edges: graphEdges } = useInfluenceGraph(artists, eras, albums, filter);
  const { nodes: layoutedNodes, edges: layoutedEdges } = useGraphLayout(graphNodes, graphEdges);

  // Apply path highlighting
  const pathSet = useMemo(() => {
    if (!currentPath || currentPath.length < 2) return new Set<string>();
    const set = new Set<string>();
    for (let i = 0; i < currentPath.length - 1; i++) {
      set.add(`${currentPath[i]}->${currentPath[i + 1]}`);
      set.add(`${currentPath[i + 1]}->${currentPath[i]}`);
    }
    return set;
  }, [currentPath]);

  const enhancedNodes = useMemo(() => {
    if (!currentPath) return layoutedNodes;
    const pathNodeSet = new Set(currentPath);
    return layoutedNodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        isPathNode: pathNodeSet.has(node.id),
        dimmed: currentPath.length > 0 && !pathNodeSet.has(node.id),
      },
    }));
  }, [layoutedNodes, currentPath]);

  const enhancedEdges = useMemo(() => {
    return layoutedEdges.map((edge) => {
      const isPathEdge = pathSet.has(edge.id) || pathSet.has(`${edge.target}->${edge.source}`);
      return {
        ...edge,
        style: {
          stroke: isPathEdge ? '#D4A843' : '#E63946',
          strokeWidth: isPathEdge ? 4 : 2,
          strokeDasharray: isPathEdge ? undefined : edge.style?.strokeDasharray,
          opacity: 1,
        },
        animated: false,
        markerEnd: edge.markerEnd,
      };
    });
  }, [layoutedEdges, pathSet]);

  const [nodes, setNodes, onNodesChange] = useNodesState(enhancedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(enhancedEdges);

  useEffect(() => {
    setNodes(enhancedNodes);
    setEdges(enhancedEdges);
  }, [enhancedNodes, enhancedEdges, setNodes, setEdges]);

  // Auto-fit when path changes
  useEffect(() => {
    if (currentPath && currentPath.length >= 2) {
      setTimeout(() => fitView({ duration: 800, padding: 0.3 }), 200);
    }
  }, [currentPath, fitView]);

  // Auto-focus "To" dropdown after selecting "From"
  const handleFromSelect = useCallback((artist: Artist | null) => {
    setFromArtist(artist);
    if (artist && !toArtist) {
      setTimeout(() => toDropdownRef.current?.focus(), 100);
    }
  }, [toArtist]);

  // Handle node click
  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setEdges((eds) =>
      eds.map((edge) => {
        const isConnected = edge.source === node.id || edge.target === node.id;
        const isPathEdge = pathSet.has(edge.id);
        return {
          ...edge,
          style: {
            ...edge.style,
            stroke: isPathEdge ? '#D4A843' : isConnected ? '#A8DADC' : '#E63946',
            strokeWidth: isPathEdge ? 4 : isConnected ? 3 : 2,
          },
          markerEnd: edge.markerEnd,
        };
      })
    );
  }, [setEdges, pathSet]);

  // Handle popular path preset click
  const handlePresetClick = useCallback((fromId: string, toId: string) => {
    const from = artistMap.get(fromId);
    const to = artistMap.get(toId);
    if (from && to) {
      setFromArtist(from);
      setToArtist(to);
    }
  }, [artistMap]);

  const showPresets = !fromArtist && !toArtist;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 page-enter">
      <SEO
        title="Connection Finder"
        description="Trace influence paths between jazz musicians. Discover how artists shaped each other across generations."
      />

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-4xl font-bold mb-2 font-display text-charcoal">Connection Finder</h1>
        <p className="text-warm-gray">
          Select two artists to trace their influence path.
        </p>
      </div>

      {/* Popular paths showcase */}
      {showPresets && (
        <div className="mb-6">
          <p className="text-xs text-warm-gray uppercase tracking-widest mb-3 font-mono">Try these paths</p>
          <div className="flex flex-wrap gap-2">
            {POPULAR_PATHS.map((preset) => (
              <button
                key={`${preset.fromId}-${preset.toId}`}
                onClick={() => handlePresetClick(preset.fromId, preset.toId)}
                className="px-4 py-2 rounded-lg bg-surface border border-border text-charcoal text-sm hover:border-coral hover:text-coral transition-colors"
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Two dropdowns */}
      <div className="mb-6">
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-4 items-start">
          <div>
            <label className="block text-xs text-warm-gray uppercase tracking-widest mb-2 font-mono">From Artist</label>
            <ArtistDropdown
              artists={artists}
              selectedArtist={fromArtist}
              onSelect={handleFromSelect}
              placeholder="Search by name or instrument..."
              excludeArtistId={toArtist?.id}
            />
          </div>

          {/* Arrow connector */}
          <div className="hidden md:flex items-center pt-7">
            <svg className="w-8 h-8 text-coral" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </div>

          <div>
            <label className="block text-xs text-warm-gray uppercase tracking-widest mb-2 font-mono">To Artist</label>
            <ArtistDropdown
              ref={toDropdownRef}
              artists={artists}
              selectedArtist={toArtist}
              onSelect={setToArtist}
              placeholder="Search by name or instrument..."
              excludeArtistId={fromArtist?.id}
            />
          </div>
        </div>

        {/* Path result */}
        {fromArtist && toArtist && currentPath && (
          <PathResult path={currentPath} artistMap={artistMap} />
        )}
        {fromArtist && toArtist && !currentPath && (
          <div className="mt-4 p-4 bg-surface border border-border rounded-lg">
            <p className="text-warm-gray text-sm">
              No documented influence path between <span className="text-charcoal font-medium">{fromArtist.name}</span> and <span className="text-charcoal font-medium">{toArtist.name}</span>.
              They may be from unrelated jazz traditions.
            </p>
          </div>
        )}
      </div>

      {/* Era Legend */}
      <div className="flex flex-wrap gap-3 mb-4">
        {eras.map((era) => (
          <div key={era.id} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: eraColors[era.id] }}
            />
            <span className="text-xs text-warm-gray">{era.name}</span>
          </div>
        ))}
      </div>

      {/* Graph Container */}
      <div className="h-[600px] rounded-lg border border-border overflow-hidden bg-navy">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          defaultEdgeOptions={{
            type: 'connection',
            style: { stroke: '#E63946', strokeWidth: 2 },
            animated: false,
          }}
          fitView
          minZoom={0.2}
          maxZoom={2}
          edgesReconnectable={false}
          elevateEdgesOnSelect
        >
          <Background color="#1A1A2E" gap={20} />
          <Controls className="bg-surface border-border" />
          <MiniMap
            nodeColor={(node) => {
              const era = (node.data as { era?: Era }).era;
              return era ? eraColors[era.id] || '#4A4A5A' : '#4A4A5A';
            }}
            maskColor="rgba(0, 0, 0, 0.8)"
            className="bg-navy border-border"
          />
        </ReactFlow>
      </div>

      {/* Stats */}
      <div className="mt-4 flex items-center gap-6 text-sm text-warm-gray">
        <span>Showing {nodes.length} artists</span>
        <span>{edges.length} connections</span>
        <VerificationBadge />
      </div>
    </div>
  );
}

export function InfluenceGraph() {
  return (
    <ReactFlowProvider>
      <InfluenceGraphInner />
    </ReactFlowProvider>
  );
}

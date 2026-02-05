import { useCallback, useState, useMemo, useEffect } from 'react';
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
import type { Artist, Era, Album } from '../types';
import {
  ArtistNode,
  SearchPanel,
  PathFinder,
  FocusControls,
  useInfluenceGraph,
  useGraphLayout,
  findShortestPath,
  eraColors,
} from '../components/graph';

const artists = artistsData as Artist[];
const albums = albumsData as Album[];
const eras = erasData as Era[];

const nodeTypes = {
  artist: ArtistNode,
};

function InfluenceGraphInner() {
  const { fitView, setCenter } = useReactFlow();

  // Focus state
  const [focusArtist, setFocusArtist] = useState<Artist | null>(null);
  const [focusDepth, setFocusDepth] = useState(2);

  // Path finding state
  const [currentPath, setCurrentPath] = useState<string[] | null>(undefined as unknown as string[] | null);
  const [pathSearched, setPathSearched] = useState(false);

  // Era filter state - default to bebop for a focused starting view
  const [eraFilter, setEraFilter] = useState<string | null>('bebop');

  // Genre filter state
  const [genreFilter, setGenreFilter] = useState<string | null>(null);

  // Instructions visibility
  const [showInstructions, setShowInstructions] = useState(true);

  // Get graph data with filters
  const filter = useMemo(() => ({
    focusArtistId: focusArtist?.id,
    depth: focusArtist ? focusDepth : undefined,
    eraFilter: eraFilter || undefined,
    genreFilter: genreFilter || undefined,
  }), [focusArtist, focusDepth, eraFilter, genreFilter]);

  const { nodes: graphNodes, edges: graphEdges, artistMap } = useInfluenceGraph(artists, eras, albums, filter);

  // Apply dagre layout
  const { nodes: layoutedNodes, edges: layoutedEdges } = useGraphLayout(graphNodes, graphEdges);

  // Apply path highlighting to edges
  const pathSet = useMemo(() => {
    if (!currentPath || currentPath.length < 2) return new Set<string>();
    const set = new Set<string>();
    for (let i = 0; i < currentPath.length - 1; i++) {
      set.add(`${currentPath[i]}->${currentPath[i + 1]}`);
      set.add(`${currentPath[i + 1]}->${currentPath[i]}`);
    }
    return set;
  }, [currentPath]);

  // Enhanced nodes with path highlighting
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

  // Enhanced edges with path highlighting - preserve markerEnd for arrows
  const enhancedEdges = useMemo(() => {
    return layoutedEdges.map((edge) => {
      const isPathEdge = pathSet.has(edge.id) || pathSet.has(`${edge.target}->${edge.source}`);
      return {
        ...edge,
        style: {
          stroke: isPathEdge ? '#fbbf24' : '#f59e0b',
          strokeWidth: isPathEdge ? 4 : 2,
          opacity: 1,
        },
        animated: isPathEdge,
        markerEnd: edge.markerEnd, // Explicitly preserve arrow markers
      };
    });
  }, [layoutedEdges, pathSet]);

  const [nodes, setNodes, onNodesChange] = useNodesState(enhancedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(enhancedEdges);

  // Update nodes/edges when data changes
  useEffect(() => {
    setNodes(enhancedNodes);
    setEdges(enhancedEdges);
  }, [enhancedNodes, enhancedEdges, setNodes, setEdges]);

  // Handle node click - highlight connections and preserve arrows
  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setEdges((eds) =>
      eds.map((edge) => {
        const isConnected = edge.source === node.id || edge.target === node.id;
        const isPathEdge = pathSet.has(edge.id);
        return {
          ...edge,
          style: {
            ...edge.style,
            stroke: isPathEdge ? '#fbbf24' : isConnected ? '#22d3ee' : '#f59e0b',
            strokeWidth: isPathEdge ? 4 : isConnected ? 3 : 2,
          },
          markerEnd: edge.markerEnd, // Preserve arrow markers
        };
      })
    );
  }, [setEdges, pathSet]);

  // Handle search selection - center on artist
  const handleSearchSelect = useCallback((artist: Artist) => {
    const node = nodes.find((n) => n.id === artist.id);
    if (node) {
      setCenter(node.position.x + 80, node.position.y + 40, { zoom: 1.2, duration: 800 });
    }
  }, [nodes, setCenter]);

  // Handle focus on artist
  const handleFocusArtist = useCallback((artist: Artist) => {
    setFocusArtist(artist);
    setCurrentPath(null);
    setPathSearched(false);
    setTimeout(() => fitView({ duration: 800 }), 100);
  }, [fitView]);

  // Handle path finding
  const handleFindPath = useCallback((startId: string, endId: string) => {
    const path = findShortestPath(startId, endId, artistMap);
    setCurrentPath(path);
    setPathSearched(true);
    if (path) {
      setTimeout(() => fitView({ duration: 800, padding: 0.2 }), 100);
    }
  }, [artistMap, fitView]);

  const handleClearPath = useCallback(() => {
    setCurrentPath(null);
    setPathSearched(false);
  }, []);

  const handleClearFocus = useCallback(() => {
    setFocusArtist(null);
    setTimeout(() => fitView({ duration: 800 }), 100);
  }, [fitView]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-4xl font-bold mb-2">Artist Influence Network</h1>
        <p className="text-zinc-400 mb-4">
          Explore how jazz musicians influenced each other across generations.
          Search for an artist, find connections between two musicians, or click to explore.
        </p>

        {/* Getting Started Panel - prominent instructions */}
        {showInstructions && (
          <div className="mb-4 p-4 rounded-lg bg-gradient-to-r from-amber-900/20 to-zinc-900 border border-amber-500/30">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-amber-400">Getting Started</h3>
              <button
                onClick={() => setShowInstructions(false)}
                className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                Hide
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-amber-500/20 flex items-center justify-center shrink-0">
                  <span className="text-amber-400 font-bold text-sm">1</span>
                </div>
                <div>
                  <p className="text-white font-medium text-sm">Choose an Era</p>
                  <p className="text-xs text-zinc-400">Filter by jazz period (starts with Bebop)</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-amber-500/20 flex items-center justify-center shrink-0">
                  <span className="text-amber-400 font-bold text-sm">2</span>
                </div>
                <div>
                  <p className="text-white font-medium text-sm">Click Any Artist</p>
                  <p className="text-xs text-zinc-400">Highlight their connections</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-amber-500/20 flex items-center justify-center shrink-0">
                  <span className="text-amber-400 font-bold text-sm">3</span>
                </div>
                <div>
                  <p className="text-white font-medium text-sm">Find Connections</p>
                  <p className="text-xs text-zinc-400">Trace paths between two musicians</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-amber-500/20 flex items-center justify-center shrink-0">
                  <span className="text-amber-400 font-bold text-sm">4</span>
                </div>
                <div>
                  <p className="text-white font-medium text-sm">Explore Freely</p>
                  <p className="text-xs text-zinc-400">Drag to pan, scroll to zoom</p>
                </div>
              </div>
            </div>
            <p className="mt-3 text-xs text-zinc-500">
              Tip: Arrows flow from <em>influencer</em> → <em>influenced</em>. Click "All Eras" to see the full network.
            </p>
          </div>
        )}
        {!showInstructions && (
          <button
            onClick={() => setShowInstructions(true)}
            className="mb-4 text-sm text-amber-500 hover:text-amber-400 transition-colors"
          >
            Show instructions
          </button>
        )}
      </div>

      {/* Controls Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* Search Panel */}
        <div>
          <label className="block text-sm text-zinc-400 mb-2">Search & Center</label>
          <SearchPanel
            artists={artists}
            onSelect={handleSearchSelect}
            placeholder="Search artist to center view..."
          />
        </div>

        {/* Era Filter */}
        <div>
          <label className="block text-sm text-zinc-400 mb-2">Filter by Era</label>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setEraFilter(null)}
              className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                !eraFilter
                  ? 'bg-amber-600 text-white'
                  : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
              }`}
            >
              All Eras
            </button>
            {eras.map((era) => (
              <button
                key={era.id}
                onClick={() => setEraFilter(eraFilter === era.id ? null : era.id)}
                className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                  eraFilter === era.id
                    ? 'text-white'
                    : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                }`}
                style={eraFilter === era.id ? { backgroundColor: eraColors[era.id] } : {}}
              >
                {era.name.split(' ')[0]}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Genre/Style Filter */}
      <div className="mb-6">
        <label className="block text-sm text-zinc-400 mb-2">Filter by Style</label>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setGenreFilter(null)}
            className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
              !genreFilter
                ? 'bg-amber-600 text-white'
                : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
            }`}
          >
            All Styles
          </button>
          {['modal jazz', 'hard bop', 'bebop', 'free jazz', 'fusion', 'cool jazz', 'soul jazz', 'post-bop', 'avant-garde'].map((genre) => (
            <button
              key={genre}
              onClick={() => setGenreFilter(genreFilter === genre ? null : genre)}
              className={`px-3 py-1.5 rounded-full text-sm transition-colors capitalize ${
                genreFilter === genre
                  ? 'bg-amber-600 text-white'
                  : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
              }`}
            >
              {genre}
            </button>
          ))}
        </div>
      </div>

      {/* Focus Controls */}
      <div className="mb-4">
        <FocusControls
          focusArtist={focusArtist}
          depth={focusDepth}
          onDepthChange={setFocusDepth}
          onClearFocus={handleClearFocus}
        />
      </div>

      {/* Path Finder */}
      <div className="mb-6">
        <PathFinder
          artists={artists}
          onFindPath={handleFindPath}
          onClear={handleClearPath}
          currentPath={pathSearched ? currentPath : undefined as unknown as string[] | null}
          artistMap={artistMap}
        />
      </div>

      {/* Era Legend */}
      <div className="flex flex-wrap gap-3 mb-4">
        {eras.map((era) => (
          <button
            key={era.id}
            onClick={() => handleFocusArtist(artists.find((a) => a.eras[0] === era.id)!)}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          >
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: eraColors[era.id] }}
            />
            <span className="text-sm text-zinc-400">{era.name}</span>
          </button>
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
          defaultEdgeOptions={{
            type: 'smoothstep',
            style: { stroke: '#f59e0b', strokeWidth: 2 },
            animated: false,
          }}
          fitView
          minZoom={0.2}
          maxZoom={2}
          edgesReconnectable={false}
          elevateEdgesOnSelect
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

      {/* Stats */}
      <div className="mt-4 flex items-center gap-6 text-sm text-zinc-500">
        <span>Showing {nodes.length} artists</span>
        <span>{edges.length} connections</span>
        {focusArtist && <span>Focused on {focusArtist.name}</span>}
      </div>

      {/* Instructions */}
      <div className="mt-6 p-4 rounded-lg bg-zinc-900 border border-zinc-800">
        <h3 className="font-semibold text-amber-400 mb-2">How to Explore</h3>
        <ul className="text-sm text-zinc-400 space-y-1">
          <li><strong>Search</strong> - Find an artist and center the view on them</li>
          <li><strong>Find Connection</strong> - Discover how two artists are linked</li>
          <li><strong>Click artist</strong> - Highlight their direct connections</li>
          <li><strong>Click artist name</strong> - Visit their full profile</li>
          <li><strong>Drag/Scroll</strong> - Pan and zoom the graph</li>
          <li>Arrows flow from <em>influencer</em> to <em>influenced</em></li>
        </ul>
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

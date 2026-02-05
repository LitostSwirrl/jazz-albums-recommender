import { useMemo } from 'react';
import {
  ReactFlow,
  Background,
  ReactFlowProvider,
  Handle,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Link } from 'react-router-dom';
import type { Artist, Era } from '../../types';
import { eraColors } from './hooks/useInfluenceGraph';

interface MiniInfluenceNetworkProps {
  artist: Artist;
  allArtists: Artist[];
  eras: Era[];
}

interface MiniNodeData {
  artist: Artist;
  era: Era | undefined;
  isCenter: boolean;
}

function MiniArtistNode({ data }: { data: MiniNodeData }) {
  const { artist, era, isCenter } = data;
  const borderColor = era ? eraColors[era.id] || '#71717a' : '#71717a';

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-0 !w-0 !h-0" />
      <Link
        to={`/artist/${artist.id}`}
        className={`block px-2 py-1 rounded text-center transition-all duration-200 hover:scale-105 ${
          isCenter ? 'bg-zinc-800 border-2' : 'bg-zinc-900 border'
        }`}
        style={{ borderColor }}
      >
        <div className={`text-xs font-medium text-white truncate max-w-[80px] ${isCenter ? 'text-sm' : ''}`}>
          {artist.name}
        </div>
      </Link>
      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-0 !w-0 !h-0" />
    </>
  );
}

const nodeTypes = {
  miniArtist: MiniArtistNode,
};

function MiniInfluenceNetworkInner({ artist, allArtists, eras }: MiniInfluenceNetworkProps) {
  const artistMap = useMemo(() => new Map(allArtists.map((a) => [a.id, a])), [allArtists]);
  const eraMap = useMemo(() => new Map(eras.map((e) => [e.id, e])), [eras]);

  const { nodes, edges } = useMemo(() => {
    // Get influencers (who influenced this artist)
    const influencers = artist.influencedBy
      .map((id) => artistMap.get(id))
      .filter((a): a is Artist => !!a)
      .slice(0, 5);

    // Get influenced (who this artist influenced)
    const influenced = artist.influences
      .map((id) => artistMap.get(id))
      .filter((a): a is Artist => !!a)
      .slice(0, 5);

    // Center node
    const centerX = 150;
    const centerY = 100;

    const nodes = [
      {
        id: artist.id,
        type: 'miniArtist',
        position: { x: centerX, y: centerY },
        data: {
          artist,
          era: eraMap.get(artist.eras[0]),
          isCenter: true,
        },
      },
    ];

    // Position influencers above
    influencers.forEach((inf, i) => {
      const offset = (i - (influencers.length - 1) / 2) * 90;
      nodes.push({
        id: inf.id,
        type: 'miniArtist',
        position: { x: centerX + offset, y: 20 },
        data: {
          artist: inf,
          era: eraMap.get(inf.eras[0]),
          isCenter: false,
        },
      });
    });

    // Position influenced below
    influenced.forEach((inf, i) => {
      const offset = (i - (influenced.length - 1) / 2) * 90;
      nodes.push({
        id: inf.id,
        type: 'miniArtist',
        position: { x: centerX + offset, y: 180 },
        data: {
          artist: inf,
          era: eraMap.get(inf.eras[0]),
          isCenter: false,
        },
      });
    });

    // Create edges
    const edges = [
      ...influencers.map((inf) => ({
        id: `${inf.id}->${artist.id}`,
        source: inf.id,
        target: artist.id,
        type: 'smoothstep',
        style: { stroke: '#f59e0b', strokeWidth: 2 },
        animated: true,
      })),
      ...influenced.map((inf) => ({
        id: `${artist.id}->${inf.id}`,
        source: artist.id,
        target: inf.id,
        type: 'smoothstep',
        style: { stroke: '#f59e0b', strokeWidth: 2 },
        animated: true,
      })),
    ];

    return { nodes, edges };
  }, [artist, artistMap, eraMap]);

  const hasConnections = artist.influences.length > 0 || artist.influencedBy.length > 0;

  if (!hasConnections) {
    return (
      <div className="text-center text-zinc-500 py-8">
        No documented influence connections for this artist.
      </div>
    );
  }

  return (
    <div className="h-[250px] rounded-lg border border-zinc-800 overflow-hidden bg-zinc-950">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={{
          type: 'smoothstep',
          style: { stroke: '#f59e0b', strokeWidth: 2 },
        }}
        fitView
        panOnDrag={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        preventScrolling={false}
      >
        <Background color="#27272a" gap={20} />
      </ReactFlow>
    </div>
  );
}

export function MiniInfluenceNetwork(props: MiniInfluenceNetworkProps) {
  return (
    <ReactFlowProvider>
      <MiniInfluenceNetworkInner {...props} />
    </ReactFlowProvider>
  );
}

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Link } from 'react-router-dom';
import type { Artist, Era } from '../../../types';
import { eraColors } from '../hooks/useInfluenceGraph';

interface ArtistNodeData {
  artist: Artist;
  era: Era | undefined;
  influenceCount: number;
  size: 'sm' | 'md' | 'lg' | 'xl';
  highlighted?: boolean;
  dimmed?: boolean;
  isPathNode?: boolean;
}

interface ArtistNodeProps {
  data: ArtistNodeData;
  selected?: boolean;
}

const sizeClasses = {
  sm: 'min-w-[120px] p-2',
  md: 'min-w-[140px] p-3',
  lg: 'min-w-[160px] p-3',
  xl: 'min-w-[180px] p-4',
};

const textSizeClasses = {
  sm: 'text-xs',
  md: 'text-sm',
  lg: 'text-base',
  xl: 'text-lg',
};

function ArtistNodeComponent({ data, selected }: ArtistNodeProps) {
  const { artist, era, influenceCount, size, highlighted, dimmed, isPathNode } = data;
  const borderColor = era ? eraColors[era.id] || '#4A4A5A' : '#4A4A5A';

  const baseClasses = `
    block rounded-lg bg-surface border-2 text-center transition-all duration-200
    ${sizeClasses[size]}
    ${dimmed ? 'opacity-30' : 'opacity-100'}
    ${highlighted || selected ? 'ring-2 ring-teal ring-offset-2 ring-offset-cream' : ''}
    ${isPathNode ? 'ring-2 ring-coral ring-offset-2 ring-offset-cream' : ''}
    hover:scale-105
  `;

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-warm-gray !w-2 !h-2" />
      <Link
        to={`/artist/${artist.id}`}
        className={baseClasses}
        style={{ borderColor }}
      >
        <div className={`font-semibold text-charcoal truncate ${textSizeClasses[size]}`}>
          {artist.name}
        </div>
        <div className="text-xs text-warm-gray truncate">
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
        {influenceCount > 0 && (
          <div className="text-xs text-warm-gray/50 mt-1">
            {influenceCount} connections
          </div>
        )}
      </Link>
      <Handle type="source" position={Position.Bottom} className="!bg-warm-gray !w-2 !h-2" />
    </>
  );
}

export const ArtistNode = memo(ArtistNodeComponent);

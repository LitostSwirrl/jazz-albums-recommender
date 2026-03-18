import { Link } from 'react-router-dom';
import { AlbumCover } from '../AlbumCover';
import type { Album } from '../../types';

interface AlbumCardProps {
  album: Album;
  size?: 'sm' | 'md' | 'lg';
  showYear?: boolean;
  showEraTag?: boolean;
  className?: string;
}

const sizeWidths: Record<string, string> = {
  sm: 'w-36',
  md: 'w-44',
  lg: 'w-56',
};

export function AlbumCard({ album, size = 'md', showYear = false, showEraTag = false, className = '' }: AlbumCardProps) {
  return (
    <Link
      to={`/album/${album.id}`}
      className={`flex-shrink-0 ${sizeWidths[size]} group ${className}`}
    >
      <div className="relative rounded-sm overflow-hidden mb-2 shadow-card group-hover:shadow-card-hover transition-all duration-300 group-hover:scale-[1.03]">
        <AlbumCover coverUrl={album.coverUrl} title={album.title} size="sm" />
        {showEraTag && (
          <div className="absolute bottom-0 left-0 right-0 px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-center bg-black/60 text-white">
            {album.era.replaceAll('-', ' ')}
          </div>
        )}
      </div>
      <h3 className="font-semibold text-charcoal text-sm group-hover:text-coral transition-colors truncate">
        {album.title}
      </h3>
      <p className="text-warm-gray text-xs truncate">
        {album.artist}{showYear ? ` \u00B7 ${album.year}` : ''}
      </p>
    </Link>
  );
}

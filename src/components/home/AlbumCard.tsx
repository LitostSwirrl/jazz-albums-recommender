import { Link } from 'react-router-dom';
import { AlbumCover } from '../AlbumCover';
import { track, type AlbumClickSource } from '../../utils/analytics';
import type { Album } from '../../types';

interface AlbumCardProps {
  album: Album;
  size?: 'sm' | 'md' | 'lg';
  showYear?: boolean;
  showEraTag?: boolean;
  priority?: boolean;
  trackSource?: AlbumClickSource;
  className?: string;
}

const sizeWidths: Record<string, string> = {
  sm: 'w-36',
  md: 'w-44',
  lg: 'w-56',
};

// Optimized pixel widths for carousel cards (matched to actual rendered size on 2x retina)
const pixelWidths: Record<string, number> = {
  sm: 288,   // w-36 = 144px * 2x
  md: 352,   // w-44 = 176px * 2x
  lg: 448,   // w-56 = 224px * 2x
};

export function AlbumCard({ album, size = 'md', showYear = false, showEraTag = false, priority = false, trackSource, className = '' }: AlbumCardProps) {
  const handleClick = () => {
    if (!trackSource) return;
    track('album_click', { album_id: album.id, source: trackSource });
    if (trackSource === 'todays_pick') {
      track('todays_pick_click', { album_id: album.id });
    }
  };

  return (
    <Link
      to={`/album/${album.id}`}
      onClick={handleClick}
      className={`block flex-shrink-0 ${sizeWidths[size]} group ${className}`}
    >
      <div className="relative rounded-sm overflow-hidden mb-2 shadow-card group-hover:shadow-card-hover transition-all duration-300 group-hover:scale-[1.03] aspect-square">
        <div className="absolute inset-0">
          <AlbumCover
            coverUrl={album.coverUrl}
            title={album.title}
            size="sm"
            pixelWidth={pixelWidths[size]}
            priority={priority}
          />
        </div>
        {showEraTag && (
          <div className="absolute bottom-0 left-0 right-0 px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-center bg-black/60 text-white z-10">
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

import { Link } from 'react-router-dom';
import type { Album } from '../../types';
import { AlbumCover } from '../AlbumCover';

interface JazzMilestoneCardProps {
  album: Album;
}

export function JazzMilestoneCard({ album }: JazzMilestoneCardProps) {
  return (
    <Link
      to={`/album/${album.id}`}
      className="flex items-center gap-3 p-3 rounded-lg bg-surface border border-border hover:border-coral/50 shadow-card transition-all group"
    >
      <div className="w-12 h-12 flex-shrink-0">
        <AlbumCover coverUrl={album.coverUrl} title={album.title} size="sm" pixelWidth={120} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-charcoal group-hover:text-coral truncate transition-colors">
          {album.title}
        </div>
        <div className="text-xs text-warm-gray truncate">
          {album.artist} · {album.year}
        </div>
      </div>
    </Link>
  );
}

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
      className="flex items-center gap-3 p-3 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-amber-500/50 transition-all group"
    >
      <div className="w-12 h-12 flex-shrink-0">
        <AlbumCover coverUrl={album.coverUrl} title={album.title} size="sm" pixelWidth={120} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-white group-hover:text-amber-400 truncate transition-colors">
          {album.title}
        </div>
        <div className="text-xs text-zinc-500 truncate">
          {album.artist} · {album.year}
        </div>
      </div>
    </Link>
  );
}

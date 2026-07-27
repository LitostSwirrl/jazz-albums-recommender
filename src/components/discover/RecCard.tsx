import { Link } from 'react-router-dom';
import { AlbumCover } from '../AlbumCover';
import { track } from '../../utils/analytics';
import type { RecAlbum } from '../../types';

interface RecCardProps {
  album: RecAlbum;
  coverUrl?: string;
  size?: 'md' | 'lg';
  showReasons?: boolean;
  priority?: boolean;
}

const widths = { md: 'w-44', lg: 'w-56' };
const pixels = { md: 352, lg: 448 };

export function RecCard({ album, coverUrl, size = 'md', showReasons = false, priority = false }: RecCardProps) {
  const cover = coverUrl ?? album.coverUrl;
  const reasons = showReasons ? album.reasons.slice(0, 2) : [];

  const body = (
    <>
      <AlbumCover
        coverUrl={cover}
        title={album.title}
        size={size === 'lg' ? 'md' : 'sm'}
        pixelWidth={pixels[size]}
        priority={priority}
      />
      <h3 className="mt-2 text-sm font-heading text-charcoal leading-snug line-clamp-2">
        {album.title}
      </h3>
      <p className="text-xs text-warm-gray line-clamp-1">{album.artist}</p>
      {reasons.length > 0 && (
        <ul className="mt-1.5 space-y-0.5">
          {reasons.map((r) => (
            <li key={`${r.type}-${r.ref}`} className="text-[11px] leading-snug text-warm-gray/80">
              {r.detail}
            </li>
          ))}
        </ul>
      )}
    </>
  );

  const className = `${widths[size]} flex-shrink-0 group`;

  if (album.inCatalog && album.catalogId) {
    return (
      <Link
        to={`/album/${album.catalogId}`}
        className={className}
        onClick={() => track('album_click', { album_id: album.id, source: 'discover' })}
      >
        {body}
      </Link>
    );
  }

  if (!album.spotifyUrl) return <div className={className}>{body}</div>;

  return (
    <a
      href={album.spotifyUrl}
      target="_blank"
      rel="noopener noreferrer"
      className={className}
      onClick={() => track('album_click', { album_id: album.id, source: 'discover_spotify' })}
    >
      {body}
    </a>
  );
}

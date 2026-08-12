import { Link } from 'react-router-dom';
import { AlbumCover } from '../AlbumCover';
import { track } from '../../utils/analytics';
import type { RecAlbum } from '../../types';

interface RecCardProps {
  album: RecAlbum;
  coverUrl?: string;
  size?: 'md' | 'lg';
  showReasons?: boolean;
}

// md is the fixed carousel width the shelves scroll horizontally. lg sits in the
// Tonight grid instead, so it fills its track and caps at the same 224px rather
// than forcing a fixed width into a track that may be narrower than it.
const widths = { md: 'w-44', lg: 'w-full max-w-56 mx-auto' };
const pixels = { md: 352, lg: 448 };

export function RecCard({ album, coverUrl, size = 'md', showReasons = false }: RecCardProps) {
  const cover = coverUrl ?? album.coverUrl ?? undefined;
  const reasons = showReasons ? album.reasons.slice(0, 2) : [];

  const body = (
    <>
      <div className="relative rounded-sm overflow-hidden shadow-card group-hover:shadow-card-hover transition-all duration-300 group-hover:scale-[1.03] aspect-square">
        <div className="absolute inset-0">
          <AlbumCover
            coverUrl={cover}
            title={album.title}
            size={size === 'lg' ? 'md' : 'sm'}
            pixelWidth={pixels[size]}
          />
        </div>
      </div>
      <h3 className="mt-2 text-sm font-heading text-charcoal leading-snug line-clamp-2 group-hover:text-coral transition-colors">
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

  // `block` is required, not cosmetic: as an inline box the anchor would ignore
  // its own width entirely and draw a separate focus outline per line box.
  const className = `block ${widths[size]} flex-shrink-0 group`;

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

  return (
    <a
      href={album.spotifyUrl}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${album.title} by ${album.artist}, opens on Spotify in a new tab`}
      className={className}
      onClick={() => track('album_click', { album_id: album.id, source: 'discover_spotify' })}
    >
      {body}
    </a>
  );
}

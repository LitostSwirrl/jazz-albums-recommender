import { Link } from 'react-router-dom';
import { AlbumCover } from '../AlbumCover';
import type { Album } from '../../types';

interface PlaylistAlbumRowProps {
  album: Album;
  trackName: string;
  index: number;
  eraColor?: string;
  isEmbedOpen: boolean;
  onToggleEmbed: () => void;
}

function getSpotifyAlbumId(spotifyUrl: string): string | null {
  const match = spotifyUrl.match(/album\/([A-Za-z0-9]+)/);
  return match ? match[1] : null;
}

export function PlaylistAlbumRow({
  album,
  trackName,
  index,
  eraColor,
  isEmbedOpen,
  onToggleEmbed,
}: PlaylistAlbumRowProps) {
  const spotifyAlbumId = album.spotifyUrl ? getSpotifyAlbumId(album.spotifyUrl) : null;

  return (
    <div className="rounded-lg border border-border bg-surface overflow-hidden">
      <div className="flex items-center gap-4 p-3 group">
        {/* Track number */}
        <span className="w-7 text-center text-sm font-mono text-warm-gray/60 shrink-0">
          {index + 1}
        </span>

        {/* Cover */}
        <div className="w-12 h-12 shrink-0 rounded-sm overflow-hidden">
          <AlbumCover
            coverUrl={album.coverUrl}
            title={album.title}
            size="sm"
            eraColor={eraColor}
          />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <span className="block text-sm font-medium text-charcoal truncate">
            {trackName}
          </span>
          <div className="flex items-center gap-1.5 text-xs text-warm-gray truncate">
            <Link
              to={`/artist/${album.artistId}`}
              className="hover:text-coral transition-colors"
            >
              {album.artist}
            </Link>
            <span>&middot;</span>
            <Link
              to={`/album/${album.id}`}
              className="hover:text-coral transition-colors truncate"
            >
              {album.title}
            </Link>
          </div>
        </div>

        {/* Year */}
        <span className="text-xs font-mono text-warm-gray/60 shrink-0 hidden sm:block">
          {album.year ?? '—'}
        </span>

        {/* Era badge */}
        {eraColor && (
          <span
            className="hidden md:block w-1.5 h-1.5 rounded-full shrink-0"
            style={{ backgroundColor: eraColor }}
          />
        )}

        {/* Spotify embed toggle */}
        {spotifyAlbumId && (
          <button
            onClick={onToggleEmbed}
            aria-label={isEmbedOpen ? 'Close Spotify player' : 'Open Spotify player'}
            className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              isEmbedOpen
                ? 'bg-[#1DB954] text-white'
                : 'bg-border/50 text-warm-gray hover:bg-[#1DB954]/10 hover:text-[#1DB954]'
            }`}
          >
            <svg className="w-3 h-3" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
            </svg>
            {isEmbedOpen ? 'Close' : 'Play'}
          </button>
        )}
      </div>

      {/* Spotify embed (lazy) */}
      {isEmbedOpen && spotifyAlbumId && (
        <div className="border-t border-border">
          <iframe
            src={`https://open.spotify.com/embed/album/${spotifyAlbumId}?utm_source=generator&theme=0`}
            width="100%"
            height="352"
            frameBorder="0"
            allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
            loading="lazy"
            title={`${album.title} on Spotify`}
          />
        </div>
      )}
    </div>
  );
}

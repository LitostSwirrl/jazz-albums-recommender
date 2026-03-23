import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import playlistsData from '../data/playlists.json';
import albumsData from '../data/albums.json';
import erasData from '../data/eras.json';
import { AlbumCover } from '../components/AlbumCover';
import { PlaylistAlbumRow } from '../components/playlist/PlaylistAlbumRow';
import { SpotifyIcon } from '../components/icons';
import { SEO } from '../components/SEO';
import type { CuratedPlaylist, Album, Era } from '../types';

const playlists = playlistsData as CuratedPlaylist[];
const albums = albumsData as Album[];
const eras = erasData as Era[];

const MOOD_LABELS: Record<string, string> = {
  morning: 'Morning',
  afternoon: 'Afternoon',
  evening: 'Evening',
  night: 'Late Night',
  gateway: 'Essential',
  cerebral: 'Deep Listen',
  melancholy: 'Melancholy',
  joyful: 'Joyful',
  urban: 'NYC',
  european: 'European',
  spiritual: 'Spiritual',
  fusion: 'Electric',
};

export function Playlist() {
  const { id } = useParams<{ id: string }>();
  const playlist = playlists.find((p) => p.id === id);
  const [openEmbedId, setOpenEmbedId] = useState<string | null>(null);

  if (!playlist) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12 text-center">
        <h1 className="text-2xl font-bold text-coral">Playlist not found</h1>
        <Link to="/playlists" className="text-coral hover:underline mt-4 inline-block">
          &larr; Back to Playlists
        </Link>
      </div>
    );
  }

  const playlistTracks = playlist.tracks
    .map((t) => {
      const album = albums.find((a) => a.id === t.albumId);
      return album ? { album, trackName: t.track } : null;
    })
    .filter((t): t is { album: Album; trackName: string } => !!t);

  const coverAlbum = albums.find((a) => a.id === playlist.coverAlbumId);

  function getEraColor(album: Album): string | undefined {
    return eras.find((e) => e.id === album.era)?.color;
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-12 page-enter">
      <SEO
        title={`${playlist.name} — Jazz Playlist`}
        description={playlist.description}
        image={coverAlbum?.coverUrl}
      />

      {/* Breadcrumb */}
      <div className="mb-6">
        <Link to="/playlists" className="text-warm-gray hover:text-coral transition-colors">
          Playlists
        </Link>
        <span className="text-border mx-2">/</span>
        <span className="text-charcoal">{playlist.name}</span>
      </div>

      {/* Hero */}
      <div className="flex flex-col sm:flex-row gap-6 mb-10">
        {coverAlbum && (
          <div className="w-40 h-40 shrink-0 rounded-lg overflow-hidden shadow-elevated">
            <AlbumCover
              coverUrl={coverAlbum.coverUrl}
              title={coverAlbum.title}
              size="lg"
              priority
            />
          </div>
        )}
        <div className="flex-1">
          <span className="inline-block px-2.5 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-coral/15 text-coral mb-2">
            {MOOD_LABELS[playlist.mood] ?? playlist.mood}
          </span>
          <h1 className="text-3xl font-display text-charcoal mb-3">{playlist.name}</h1>
          <p className="text-warm-gray leading-relaxed mb-4">{playlist.description}</p>
          <div className="flex flex-wrap gap-1.5 mb-4">
            {playlist.tags.map((tag) => (
              <Link
                key={tag}
                to={`/playlists?tag=${encodeURIComponent(tag)}`}
                className="px-3 py-1 rounded-full text-xs bg-border/50 text-warm-gray hover:bg-coral/10 hover:text-coral transition-colors"
              >
                {tag}
              </Link>
            ))}
            <span className="px-3 py-1 text-xs font-mono text-warm-gray/60">
              {playlistTracks.length} tracks
            </span>
          </div>
          {playlist.spotifyUrl && (
            <a
              href={playlist.spotifyUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#1DB954] text-white font-medium hover:bg-[#1ed760] transition-colors"
            >
              <SpotifyIcon className="w-5 h-5" />
              Open in Spotify
            </a>
          )}
        </div>
      </div>

      {/* Track list */}
      <div className="space-y-2">
        {playlistTracks.length === 0 ? (
          <p className="text-warm-gray text-center py-8">No tracks loaded for this playlist.</p>
        ) : (
          playlistTracks.map(({ album, trackName }, i) => (
            <PlaylistAlbumRow
              key={`${album.id}-${trackName}`}
              album={album}
              trackName={trackName}
              index={i}
              eraColor={getEraColor(album)}
              isEmbedOpen={openEmbedId === album.id}
              onToggleEmbed={() =>
                setOpenEmbedId(openEmbedId === album.id ? null : album.id)
              }
            />
          ))
        )}
      </div>

      {/* Other playlists */}
      {playlists.length > 1 && (
        <section className="mt-12">
          <Link
            to="/playlists"
            className="text-xl font-heading text-charcoal hover:text-coral transition-colors mb-4 inline-block"
          >
            More Playlists &rarr;
          </Link>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
            {playlists
              .filter((p) => p.id !== playlist.id)
              .slice(0, 4)
              .map((p) => {
                const cover = albums.find((a) => a.id === p.coverAlbumId);
                return (
                  <Link
                    key={p.id}
                    to={`/playlists/${p.id}`}
                    className="flex items-center gap-3 p-3 rounded-lg bg-surface border border-border hover:border-coral hover:shadow-card transition-all group"
                  >
                    {cover && (
                      <div className="w-10 h-10 rounded overflow-hidden shrink-0">
                        <AlbumCover coverUrl={cover.coverUrl} title={cover.title} size="sm" />
                      </div>
                    )}
                    <div className="min-w-0">
                      <span className="block text-sm font-medium text-charcoal group-hover:text-coral transition-colors truncate">
                        {p.name}
                      </span>
                      <span className="block text-xs text-warm-gray truncate">
                        {p.tracks.length} tracks
                      </span>
                    </div>
                  </Link>
                );
              })}
          </div>
        </section>
      )}
    </div>
  );
}

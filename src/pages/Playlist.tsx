import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import playlistsData from '../data/playlists.json';
import albumsData from '../data/albums.json';
import erasData from '../data/eras.json';
import { AlbumCover } from '../components/AlbumCover';
import { PlaylistAlbumRow } from '../components/playlist/PlaylistAlbumRow';
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
          <div className="flex flex-wrap gap-1.5">
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

      {/* Related playlists by tag */}
      {playlist.tags.length > 0 && (
        <section className="mt-12">
          <h2 className="text-xl font-heading text-charcoal mb-4">More Playlists</h2>
          <div className="flex flex-wrap gap-2">
            {playlists
              .filter(
                (p) =>
                  p.id !== playlist.id &&
                  p.tags.some((t) => playlist.tags.includes(t))
              )
              .slice(0, 4)
              .map((p) => (
                <Link
                  key={p.id}
                  to={`/playlists/${p.id}`}
                  className="px-4 py-2 rounded-lg bg-surface border border-border text-sm text-charcoal hover:text-coral hover:border-coral transition-colors"
                >
                  {p.name}
                </Link>
              ))}
          </div>
        </section>
      )}
    </div>
  );
}

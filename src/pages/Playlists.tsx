import { useState, useMemo } from 'react';
import playlistsData from '../data/playlists.json';
import albumsData from '../data/albums.json';
import { PlaylistCard } from '../components/playlist/PlaylistCard';
import { SEO } from '../components/SEO';
import type { CuratedPlaylist, Album } from '../types';

const playlists = playlistsData as CuratedPlaylist[];
const albums = albumsData as Album[];

// Collect all unique tags across playlists
const allTags = Array.from(new Set(playlists.flatMap((p) => p.tags))).sort();

export function Playlists() {
  const [activeTag, setActiveTag] = useState<string | null>(null);

  const filtered = useMemo(() => {
    if (!activeTag) return playlists;
    return playlists.filter((p) => p.tags.includes(activeTag));
  }, [activeTag]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 page-enter">
      <SEO
        title="Jazz Playlists"
        description="AI-curated jazz playlists for every mood and moment — from bright morning sessions to late-night explorations."
      />

      <h1 className="text-4xl mb-2 font-display text-charcoal">Playlists</h1>
      <p className="text-warm-gray mb-8">
        Curated listening journeys drawn from {albums.length.toLocaleString()} albums.
      </p>

      {/* Tag filter */}
      <div className="flex flex-wrap gap-2 mb-10">
        <button
          onClick={() => setActiveTag(null)}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
            !activeTag
              ? 'bg-coral text-white'
              : 'bg-border/50 text-warm-gray hover:bg-border hover:text-charcoal'
          }`}
        >
          All
        </button>
        {allTags.map((tag) => (
          <button
            key={tag}
            onClick={() => setActiveTag(activeTag === tag ? null : tag)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              activeTag === tag
                ? 'bg-coral text-white'
                : 'bg-border/50 text-warm-gray hover:bg-border hover:text-charcoal'
            }`}
          >
            {tag}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="text-warm-gray text-center py-12">No playlists match this tag.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((playlist) => (
            <PlaylistCard key={playlist.id} playlist={playlist} albums={albums} />
          ))}
        </div>
      )}
    </div>
  );
}

import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { ArtistPhoto } from '../ArtistPhoto';
import { AlbumCarousel } from './AlbumCarousel';
import { seededPick } from '../../utils/random';
import type { Album, Artist } from '../../types';

interface ArtistSpotlightProps {
  artists: Artist[];
  albums: Album[];
}

export function ArtistSpotlight({ artists, albums }: ArtistSpotlightProps) {
  const spotlight = useMemo(() => {
    // Pick artists with 3+ albums that have covers
    const candidates = artists.filter((artist) => {
      const artistAlbums = albums.filter((a) => a.artistId === artist.id && a.coverUrl);
      return artistAlbums.length >= 3;
    });

    if (candidates.length === 0) return null;

    const daySeed = Math.floor(Date.now() / 86400000);
    const artist = seededPick(candidates, daySeed + 42);
    if (!artist) return null;
    const artistAlbums = albums
      .filter((a) => a.artistId === artist.id && a.coverUrl)
      .sort((a, b) => a.year - b.year);

    return { artist, albums: artistAlbums };
  }, [artists, albums]);

  if (!spotlight) return null;

  const { artist, albums: artistAlbums } = spotlight;

  return (
    <section className="mb-10 rounded-xl bg-surface border border-border p-6 md:p-8">
      <div className="flex items-center gap-4 mb-6">
        <ArtistPhoto imageUrl={artist.imageUrl} name={artist.name} size="lg" />
        <div>
          <span className="text-[10px] font-mono uppercase tracking-widest text-warm-gray">
            Artist Spotlight
          </span>
          <h2 className="text-xl font-heading text-charcoal">
            <Link to={`/artist/${artist.id}`} className="hover:text-coral transition-colors">
              {artist.name}
            </Link>
          </h2>
          <p className="text-sm text-warm-gray">
            {artist.instruments.join(', ')} &middot; {artistAlbums.length} albums
          </p>
        </div>
      </div>
      <AlbumCarousel albums={artistAlbums} cardSize="sm" showYear />
    </section>
  );
}

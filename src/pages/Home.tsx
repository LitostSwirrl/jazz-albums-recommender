import { useMemo } from 'react';
import erasData from '../data/eras.json';
import albumsData from '../data/albums.json';
import artistsData from '../data/artists.json';
import { SEO } from '../components/SEO';
import { HeroFeature } from '../components/home/HeroFeature';
import { TodaysPick } from '../components/home/TodaysPick';
import { RandomAlbumPicker } from '../components/home/RandomAlbumPicker';
import { CarouselSection } from '../components/home/CarouselSection';
import { AlbumCarousel } from '../components/home/AlbumCarousel';
import { GenreRows } from '../components/home/GenreRow';
import { ArtistSpotlight } from '../components/home/ArtistSpotlight';
import { QuickLinksGrid } from '../components/home/QuickLinksGrid';
import { seededShuffle } from '../utils/random';
import type { Era, Album, Artist } from '../types';

const eras = erasData as Era[];
const albums = albumsData as Album[];
const artists = artistsData as Artist[];

export function Home() {
  // Build era album carousels (shuffled daily, different seed per era)
  const eraCarousels = useMemo(() => {
    const daySeed = Math.floor(Date.now() / 86400000);
    return eras.map((era, idx) => {
      const eraAlbums = albums.filter((a) => a.era === era.id && a.coverUrl);
      const shuffled = seededShuffle(eraAlbums, daySeed + idx + 100);
      return { era, albums: shuffled.slice(0, 20) };
    }).filter((c) => c.albums.length > 0);
  }, []); // eras and albums are module-level constants

  return (
    <div className="page-enter">
      <SEO
        title="Your Jazz Library"
        description={`A curated guide to ${albums.length} jazz albums from New Orleans to today. Explore jazz history, discover ${artists.length} artists, and understand how they shaped each other.`}
      />

      <div className="max-w-7xl mx-auto px-4">
        {/* Hero: Featured Album */}
        <HeroFeature albums={albums} eras={eras} />

        {/* Today's Pick: Weather-mood-matched albums */}
        <TodaysPick albums={albums} />

        {/* Random Album Picker: Vinyl Reveal */}
        <RandomAlbumPicker albums={albums} eras={eras} />

        {/* Era Carousels */}
        {eraCarousels.map(({ era, albums: eraAlbums }) => (
          <CarouselSection
            key={era.id}
            title={era.name}
            linkTo={`/era/${era.id}`}
          >
            <AlbumCarousel
              albums={eraAlbums}
              cardSize="sm"
              showYear
              showEraTag={false}
            />
          </CarouselSection>
        ))}

        {/* Genre Collections */}
        <GenreRows albums={albums} />

        {/* Artist Spotlight */}
        <ArtistSpotlight artists={artists} albums={albums} />

        {/* Quick Links */}
        <QuickLinksGrid />
      </div>
    </div>
  );
}

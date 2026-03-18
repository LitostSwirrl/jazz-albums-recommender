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
import { LazySection } from '../components/home/LazySection';
import { GenreRows } from '../components/home/GenreRow';
import { ArtistSpotlight } from '../components/home/ArtistSpotlight';
import { QuickLinksGrid } from '../components/home/QuickLinksGrid';
import { seededShuffle } from '../utils/random';
import type { Era, Album, Artist } from '../types';

const eras = erasData as Era[];
const albums = albumsData as Album[];
const artists = artistsData as Artist[];

export function Home() {
  const eraCarousels = useMemo(() => {
    const daySeed = Math.floor(Date.now() / 86400000);
    return eras.map((era, idx) => {
      const eraAlbums = albums.filter((a) => a.era === era.id && a.coverUrl);
      const shuffled = seededShuffle(eraAlbums, daySeed + idx + 100);
      return { era, albums: shuffled.slice(0, 20) };
    }).filter((c) => c.albums.length > 0);
  }, []);

  return (
    <div className="page-enter">
      <SEO
        title="Your Jazz Library"
        description={`A curated guide to ${albums.length} jazz albums from New Orleans to today. Explore jazz history, discover ${artists.length} artists, and understand how they shaped each other.`}
      />

      <div className="max-w-7xl mx-auto px-4">
        {/* Above the fold: eager-load images */}
        <HeroFeature albums={albums} eras={eras} />

        <TodaysPick albums={albums} />

        {/* Below the fold: lazy-load sections as they approach viewport */}
        <LazySection>
          <RandomAlbumPicker albums={albums} eras={eras} />
        </LazySection>

        {eraCarousels.map(({ era, albums: eraAlbums }, idx) => (
          <LazySection key={era.id}>
            <CarouselSection
              title={era.name}
              linkTo={`/era/${era.id}`}
            >
              <AlbumCarousel
                albums={eraAlbums}
                cardSize="sm"
                showYear
                eagerCount={idx === 0 ? 5 : 0}
              />
            </CarouselSection>
          </LazySection>
        ))}

        <LazySection>
          <GenreRows albums={albums} />
        </LazySection>

        <LazySection>
          <ArtistSpotlight artists={artists} albums={albums} />
        </LazySection>

        <LazySection>
          <QuickLinksGrid />
        </LazySection>
      </div>
    </div>
  );
}

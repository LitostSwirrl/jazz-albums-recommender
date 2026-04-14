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
import { seededShuffle, seededPick } from '../utils/random';
import { getTodaysPicks } from '../utils/weatherMood';
import { usePreloadImages } from '../hooks/usePreloadImages';
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
      const seen = new Set<string>();
      const unique = shuffled.filter((a) => {
        if (seen.has(a.title)) return false;
        seen.add(a.title);
        return true;
      });
      return { era, albums: unique.slice(0, 20) };
    }).filter((c) => c.albums.length > 0);
  }, []);

  // Compute above-the-fold cover URLs for preloading
  const preloadUrls = useMemo(() => {
    const urls: (string | undefined)[] = [];

    // Hero album
    const heroAlbum = seededPick(
      albums.filter((a) => a.coverUrl && a.albumDNA.length > 100),
      Math.floor(Date.now() / 86400000)
    );
    if (heroAlbum) urls.push(heroAlbum.coverUrl);

    // Today's Pick (first 5)
    const todaysPicks = getTodaysPicks(albums, null);
    for (const pick of todaysPicks.slice(0, 5)) {
      urls.push(pick.coverUrl);
    }

    // Initial random album for the picker
    const withCovers = albums.filter((a) => a.coverUrl);
    if (withCovers.length > 0) {
      urls.push(withCovers[Math.floor(Math.random() * withCovers.length)].coverUrl);
    }

    return urls;
  }, []);

  // Inject <link rel="preload"> into <head> immediately
  usePreloadImages(preloadUrls, 500);

  return (
    <div className="page-enter">
      <SEO
        title="Your Jazz Library"
        description="1000 jazz albums, 275 artists, 8 eras."
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

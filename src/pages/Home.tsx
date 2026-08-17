import { lazy, Suspense, useMemo } from 'react';
import erasData from '@site/data/eras.json';
import albumsData from '@site/data/albums.json';
import { siteConfig } from '@site/config';
import { SEO } from '../components/SEO';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { HeroFeature } from '../components/home/HeroFeature';
import { TodaysPick } from '../components/home/TodaysPick';
import { RandomAlbumPicker } from '../components/home/RandomAlbumPicker';
import { LazySection } from '../components/home/LazySection';
import { seededPick, DAY_SEED } from '../utils/random';
import { getDailyPicks } from '../utils/discovery';
import { usePreloadImages } from '../hooks/usePreloadImages';
import type { Era, Album } from '../types';

const eras = erasData as Era[];
const albums = albumsData as Album[];

// Own chunk: DiscoverSection is the sole importer of the ~300KB
// recommendations JSON, which must stay out of the initial bundle.
const DiscoverSection = lazy(() =>
  import('../components/home/DiscoverSection').then((m) => ({ default: m.DiscoverSection }))
);

export function Home() {
  // Compute above-the-fold cover URLs for preloading
  const preloadUrls = useMemo(() => {
    const urls: (string | undefined)[] = [];

    // Hero album
    const heroAlbum = seededPick(
      albums.filter((a) => a.coverUrl && a.albumDNA.length > 100),
      DAY_SEED
    );
    if (heroAlbum) urls.push(heroAlbum.coverUrl);

    // Today's Pick (first 5)
    const todaysPicks = getDailyPicks(albums);
    for (const pick of todaysPicks.slice(0, 5)) {
      urls.push(pick.coverUrl);
    }

    // Initial random album for the picker
    const withCovers = albums.filter((a) => a.coverUrl);
    const randomCover = seededPick(withCovers, DAY_SEED + 7);
    if (randomCover?.coverUrl) urls.push(randomCover.coverUrl);

    return urls;
  }, []);

  // Inject <link rel="preload"> into <head> immediately
  usePreloadImages(preloadUrls, 500);

  return (
    <div className="page-enter">
      <SEO
        title={siteConfig.copy.homeTitle}
        description={siteConfig.copy.homeDescription}
      />

      <div className="max-w-7xl mx-auto px-4">
        {/* Above the fold: eager-load images */}
        <HeroFeature albums={albums} eras={eras} />

        <TodaysPick albums={albums} />

        {/* Below the fold: lazy-load sections as they approach viewport */}
        <LazySection>
          <RandomAlbumPicker albums={albums} eras={eras} />
        </LazySection>

        <LazySection>
          {/* A failed chunk load (stale index.html after a deploy) rejects the
              lazy import; without this boundary the root one would blank the
              whole landing page. fallback must be truthy — null falls through. */}
          <ErrorBoundary fallback={<div />}>
            <Suspense fallback={<div className="h-48" />}>
              <DiscoverSection />
            </Suspense>
          </ErrorBoundary>
        </LazySection>
      </div>
    </div>
  );
}

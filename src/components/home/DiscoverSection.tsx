import recsData from '@site/data/recommendations.json';
import coverManifest from '@site/data/recCoverManifest.json';
import { CarouselSection } from './CarouselSection';
import { RecCard } from '../discover/RecCard';
import type { RecommendationsData, RecAlbum } from '../../types';

const data = recsData as unknown as RecommendationsData;
const covers: Record<string, string> = coverManifest;

function pick(ids: string[]): RecAlbum[] {
  return ids.map((id) => data.albums[id]).filter(Boolean);
}

export function DiscoverSection() {
  const topPicks = pick(data.topPicks);
  // Resolve before filtering. Filtering on s.items.length would keep a shelf
  // whose ids no longer resolve, rendering a title and blurb over an empty row.
  const shelves = data.shelves
    .map((shelf) => ({ ...shelf, albums: pick(shelf.items) }))
    .filter((shelf) => shelf.albums.length > 0);

  if (topPicks.length === 0 && shelves.length === 0) return null;

  return (
    <>
      {topPicks.length > 0 && (
        <section className="mb-10">
          <div className="mb-4">
            <p className="text-xs font-mono uppercase tracking-widest text-coral mb-1">For you</p>
            <h2 className="text-xl font-heading text-charcoal">Tonight</h2>
            <p className="text-warm-gray text-sm mt-0.5">
              Records drawn from what you already play, each one carrying the reason it turned up.
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-x-5 gap-y-8">
            {topPicks.map((album) => (
              <RecCard
                key={album.id}
                album={album}
                coverUrl={covers[album.id]}
                size="lg"
                showReasons
              />
            ))}
          </div>
        </section>
      )}

      {shelves.map((shelf) => (
        <CarouselSection key={shelf.id} title={shelf.title} subtitle={shelf.blurb}>
          <div className="flex gap-4 overflow-x-auto pb-2 -mx-4 px-4">
            {shelf.albums.map((album) => (
              <RecCard key={album.id} album={album} coverUrl={covers[album.id]} />
            ))}
          </div>
        </CarouselSection>
      ))}
    </>
  );
}

import recsData from '../data/recommendations.json';
import coverManifest from '../data/recCoverManifest.json';
import { SEO } from '../components/SEO';
import { CarouselSection } from '../components/home/CarouselSection';
import { RecCard } from '../components/discover/RecCard';
import type { RecommendationsData, RecAlbum } from '../types';

const data = recsData as unknown as RecommendationsData;
const covers: Record<string, string> = coverManifest;

function pick(ids: string[]): RecAlbum[] {
  return ids.map((id) => data.albums[id]).filter(Boolean);
}

export function Discover() {
  const topPicks = pick(data.topPicks);
  const shelves = data.shelves.filter((s) => s.items.length > 0);

  if (topPicks.length === 0 && shelves.length === 0) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12">
        <h1 className="text-3xl font-display uppercase tracking-wide text-charcoal mb-3">Discover</h1>
        <p className="text-warm-gray">No recommendations yet.</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 page-enter">
      <SEO
        title="Discover"
        description="Records picked from what you already listen to, with the reason for each one."
      />

      <header className="mb-10 max-w-2xl">
        <p className="text-xs font-mono uppercase tracking-widest text-coral mb-3">For you</p>
        <h1 className="text-4xl md:text-5xl font-display uppercase tracking-wide text-charcoal mb-4">
          Discover
        </h1>
        <p className="text-lg text-charcoal/80 leading-relaxed">
          Records drawn from what you already play, each one carrying the reason it turned up.
        </p>
      </header>

      {topPicks.length > 0 && (
        <section className="mb-14">
          <h2 className="text-xl font-heading text-charcoal mb-4">Tonight</h2>
          {/* The wrapper div is load-bearing: it keeps RecCard's fixed carousel
              width (w-56) from being blockified into a grid track narrower than
              itself, which would push the page into horizontal scroll below
              1010px. The shelves below depend on that fixed width, so the grid
              adapts rather than the shared component. */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-x-5 gap-y-8">
            {topPicks.map((album, i) => (
              <div key={album.id} className="justify-self-center">
                <RecCard
                  album={album}
                  coverUrl={covers[album.id]}
                  size="lg"
                  showReasons
                  priority={i < 4}
                />
              </div>
            ))}
          </div>
        </section>
      )}

      {shelves.map((shelf) => (
        <CarouselSection key={shelf.id} title={shelf.title} subtitle={shelf.blurb}>
          <div className="flex gap-4 overflow-x-auto pb-2 -mx-4 px-4">
            {pick(shelf.items).map((album) => (
              <RecCard key={album.id} album={album} coverUrl={covers[album.id]} />
            ))}
          </div>
        </CarouselSection>
      ))}
    </div>
  );
}

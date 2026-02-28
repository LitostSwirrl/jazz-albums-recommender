import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import erasData from '../data/eras.json';
import artistsData from '../data/artists.json';
import { SEO } from '../components/SEO';
import { AlbumCover } from '../components/AlbumCover';
import { CategoryBadge, CategoryFilter } from '../components/context';
import {
  EVENT_CATEGORIES,
  formatEventYear,
} from '../utils/historicalContext';
import {
  getEnrichedEventsByCategories,
  getEnrichedEvents,
  getTotalUniqueAlbumCount,
} from '../utils/eventAlbumMatcher';
import type { Era, Artist, HistoricalEventCategory } from '../types';
import type { EnrichedEvent } from '../utils/eventAlbumMatcher';

const eras = erasData as Era[];
const artists = artistsData as Artist[];

interface TimelineEntry {
  type: 'event' | 'era-start';
  year: number;
  event?: EnrichedEvent;
  era?: Era;
}

export function ParallelTimeline() {
  const [activeCategories, setActiveCategories] = useState<HistoricalEventCategory[]>([]);

  const handleToggle = (category: HistoricalEventCategory) => {
    setActiveCategories((prev) => {
      if (prev.includes(category)) {
        return prev.filter((c) => c !== category);
      }
      return [...prev, category];
    });
  };

  const filteredEvents = useMemo(
    () => getEnrichedEventsByCategories(activeCategories),
    [activeCategories],
  );

  const timelineEntries = useMemo(() => {
    const entries: TimelineEntry[] = [];

    eras.forEach((era) => {
      entries.push({ type: 'era-start', year: era.years[0], era });
    });

    filteredEvents.forEach((event) => {
      entries.push({ type: 'event', year: event.year, event });
    });

    return entries.sort((a, b) => a.year - b.year);
  }, [filteredEvents]);

  const allEvents = useMemo(() => getEnrichedEvents(), []);
  const totalAlbums = useMemo(() => getTotalUniqueAlbumCount(), []);
  const eventCount = filteredEvents.length;

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 page-enter">
      <SEO
        title="Jazz & Society"
        description="Explore the interweaving of jazz music with civil rights, politics, economics, technology, and globalization. A parallel timeline of music and history."
      />

      {/* Header */}
      <header className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-3 font-display bg-gradient-to-r from-amber-400 via-red-400 to-purple-400 bg-clip-text text-transparent">
          Jazz & Society
        </h1>
        <p className="text-xl text-zinc-400 max-w-2xl mx-auto mb-2">
          Jazz never existed in a vacuum. Explore how racial justice, economics, politics,
          technology, and globalization shaped — and were shaped by — the music.
        </p>
        <p className="text-sm text-zinc-500">
          {allEvents.length} events · {totalAlbums} albums in context
        </p>
      </header>

      {/* Category Filter */}
      <div className="mb-8 flex flex-col items-center gap-3">
        <p className="text-sm text-zinc-500">Filter by category</p>
        <CategoryFilter activeCategories={activeCategories} onToggle={handleToggle} />
        {activeCategories.length > 0 && (
          <button
            onClick={() => setActiveCategories([])}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            Clear filters ({eventCount} of {allEvents.length} events shown)
          </button>
        )}
      </div>

      {/* Category Legend */}
      <div className="mb-10 p-4 rounded-xl bg-zinc-900 border border-zinc-800">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {(Object.entries(EVENT_CATEGORIES) as [HistoricalEventCategory, typeof EVENT_CATEGORIES[HistoricalEventCategory]][]).map(
            ([key, config]) => (
              <div key={key} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: config.color }}
                />
                <span className="text-sm text-zinc-400">{config.label}</span>
              </div>
            ),
          )}
        </div>
      </div>

      {/* Parallel Timeline */}
      <div className="relative">
        {/* Center line - desktop only */}
        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-zinc-700 -translate-x-1/2 hidden lg:block" />

        {timelineEntries.map((entry, index) => {
          if (entry.type === 'era-start' && entry.era) {
            return (
              <EraMarker key={`era-${entry.era.id}`} era={entry.era} />
            );
          }

          if (entry.type === 'event' && entry.event) {
            const isLeft = index % 2 === 0;
            return (
              <EventRow key={entry.event.id} event={entry.event} isLeft={isLeft} />
            );
          }

          return null;
        })}
      </div>

      {/* Bottom CTA */}
      <div className="mt-16 text-center">
        <p className="text-zinc-400 mb-6">
          Want to dive deeper into any era?
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Link
            to="/timeline"
            className="px-6 py-3 rounded-xl bg-amber-500 text-black font-semibold hover:bg-amber-400 transition-colors"
          >
            Musical Timeline
          </Link>
          <Link
            to="/eras"
            className="px-6 py-3 rounded-xl border border-zinc-700 text-zinc-300 hover:border-zinc-500 transition-colors"
          >
            Browse All Eras
          </Link>
        </div>
      </div>
    </div>
  );
}

function EraMarker({ era }: { era: Era }) {
  return (
    <div className="relative my-8">
      <div className="hidden lg:flex items-center justify-center">
        <div
          className="absolute left-1/2 -translate-x-1/2 w-5 h-5 rounded-full border-4 border-zinc-950 z-10"
          style={{ backgroundColor: era.color }}
        />
      </div>
      <div
        className="py-3 px-6 rounded-xl text-center mx-auto max-w-md"
        style={{ backgroundColor: era.color + '15', border: `1px solid ${era.color}40` }}
      >
        <Link
          to={`/era/${era.id}`}
          className="text-lg font-bold hover:underline"
          style={{ color: era.color }}
        >
          {era.name}
        </Link>
        <div className="text-sm text-zinc-500 font-mono">{era.period}</div>
      </div>
    </div>
  );
}

function EventRow({ event, isLeft }: { event: EnrichedEvent; isLeft: boolean }) {
  const config = EVENT_CATEGORIES[event.category];
  const relatedArtists = artists.filter((a) => event.relatedArtistIds?.includes(a.id));

  return (
    <div className="relative mb-6">
      {/* Desktop dot */}
      <div
        className="hidden lg:block absolute left-1/2 top-6 w-3 h-3 rounded-full -translate-x-1/2 z-10"
        style={{ backgroundColor: config.color }}
      />

      {/* Desktop layout */}
      <div
        className={`hidden lg:block ${
          isLeft ? 'pr-[52%]' : 'pl-[52%]'
        }`}
      >
        <EventCard event={event} config={config} relatedArtists={relatedArtists} />
      </div>

      {/* Mobile layout */}
      <div className="lg:hidden">
        <EventCard event={event} config={config} relatedArtists={relatedArtists} />
      </div>
    </div>
  );
}

interface EventCardProps {
  event: EnrichedEvent;
  config: { color: string; label: string };
  relatedArtists: Artist[];
}

function EventCard({ event, config, relatedArtists }: EventCardProps) {
  return (
    <div
      className="p-4 rounded-xl bg-zinc-900 border border-zinc-800 transition-all hover:border-zinc-700"
      style={{ borderLeftWidth: '3px', borderLeftColor: config.color }}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <CategoryBadge category={event.category} />
        <span className="text-xs text-zinc-500 font-mono">
          {formatEventYear(event)}
        </span>
      </div>
      <h3 className="font-semibold text-white text-sm mb-1">{event.title}</h3>
      <p className="text-zinc-400 text-xs leading-relaxed mb-2">{event.description}</p>
      <div
        className="p-2 rounded-lg bg-zinc-800/50 border-l-2 mb-3"
        style={{ borderLeftColor: config.color + '60' }}
      >
        <p className="text-zinc-300 text-xs leading-relaxed">{event.jazzConnection}</p>
      </div>

      {/* Related artist chips */}
      {relatedArtists.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {relatedArtists.map((artist) => (
            <Link
              key={artist.id}
              to={`/artist/${artist.id}`}
              className="px-1.5 py-0.5 text-[10px] rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition-colors"
            >
              {artist.name}
            </Link>
          ))}
        </div>
      )}

      {/* Album strip */}
      {event.matchedAlbums.length > 0 && (
        <AlbumStrip matchedAlbums={event.matchedAlbums} />
      )}
    </div>
  );
}

interface AlbumStripProps {
  matchedAlbums: EnrichedEvent['matchedAlbums'];
}

function AlbumStrip({ matchedAlbums }: AlbumStripProps) {
  return (
    <div className="mt-2 pt-2 border-t border-zinc-800">
      <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-1.5">
        Music of the moment
      </p>
      <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-thin">
        {matchedAlbums.map(({ album, matchType }) => (
          <Link
            key={album.id}
            to={`/album/${album.id}`}
            className="flex-shrink-0 group/album relative"
            title={`${album.title} — ${album.artist} (${album.year})`}
          >
            <div
              className={`w-14 h-14 rounded-lg overflow-hidden transition-transform duration-200 group-hover/album:scale-110 ${
                matchType === 'explicit'
                  ? 'ring-1 ring-amber-500/50'
                  : ''
              }`}
            >
              <AlbumCover
                coverUrl={album.coverUrl}
                title={album.title}
                size="sm"
                pixelWidth={120}
              />
            </div>
            <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 bg-zinc-800 text-[9px] text-zinc-300 px-1.5 py-0.5 rounded whitespace-nowrap opacity-0 group-hover/album:opacity-100 transition-opacity pointer-events-none z-20">
              {album.title.length > 20 ? album.title.slice(0, 20) + '...' : album.title}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

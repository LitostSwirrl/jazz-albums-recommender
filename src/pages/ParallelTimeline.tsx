import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import erasData from '../data/eras.json';
import albumsData from '../data/albums.json';
import artistsData from '../data/artists.json';
import { SEO } from '../components/SEO';
import { CategoryBadge, CategoryFilter, HistoricalEventCard, JazzMilestoneCard } from '../components/context';
import {
  getAllEvents,
  getEventsByCategories,
  EVENT_CATEGORIES,
  formatEventYear,
} from '../utils/historicalContext';
import type { Era, Album, Artist, HistoricalEventCategory, HistoricalEvent } from '../types';

const eras = erasData as Era[];
const albums = albumsData as Album[];
const artists = artistsData as Artist[];

interface TimelineEntry {
  type: 'event' | 'era-start' | 'album';
  year: number;
  event?: HistoricalEvent;
  era?: Era;
  album?: Album;
}

function getLandmarkAlbums(): Album[] {
  const landmarkIds = [
    'hot-fives-sevens',
    'kind-of-blue',
    'a-love-supreme',
    'mingus-ah-um',
    'the-shape-of-jazz-to-come',
    'bitches-brew',
    'head-hunters',
    'black-radio',
    'the-epic',
    'we-insist',
    'out-to-lunch',
    'time-out',
  ];
  return albums.filter((a) => landmarkIds.includes(a.id));
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
    () => getEventsByCategories(activeCategories),
    [activeCategories],
  );

  const landmarkAlbums = useMemo(() => getLandmarkAlbums(), []);

  const timelineEntries = useMemo(() => {
    const entries: TimelineEntry[] = [];

    eras.forEach((era) => {
      entries.push({ type: 'era-start', year: era.years[0], era });
    });

    filteredEvents.forEach((event) => {
      entries.push({ type: 'event', year: event.year, event });
    });

    landmarkAlbums.forEach((album) => {
      entries.push({ type: 'album', year: album.year, album });
    });

    return entries.sort((a, b) => a.year - b.year);
  }, [filteredEvents, landmarkAlbums]);

  const eventCount = filteredEvents.length;
  const allEvents = getAllEvents();

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <SEO
        title="Jazz & Society"
        description="Explore the interweaving of jazz music with civil rights, politics, economics, technology, and globalization. A parallel timeline of music and history."
      />

      {/* Header */}
      <header className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-3 bg-gradient-to-r from-amber-400 via-red-400 to-purple-400 bg-clip-text text-transparent">
          Jazz & Society
        </h1>
        <p className="text-xl text-zinc-400 max-w-2xl mx-auto mb-2">
          Jazz never existed in a vacuum. Explore how racial justice, economics, politics,
          technology, and globalization shaped — and were shaped by — the music.
        </p>
        <p className="text-sm text-zinc-500">
          {allEvents.length} historical events across {eras.length} eras
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
      <div className="mb-10 p-4 rounded-lg bg-zinc-900 border border-zinc-800">
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

          if (entry.type === 'album' && entry.album) {
            const isLeft = index % 2 === 0;
            return (
              <AlbumRow key={entry.album.id} album={entry.album} isLeft={!isLeft} />
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
            className="px-6 py-3 rounded-lg bg-amber-500 text-black font-semibold hover:bg-amber-400 transition-colors"
          >
            Musical Timeline
          </Link>
          <Link
            to="/eras"
            className="px-6 py-3 rounded-lg border border-zinc-700 text-zinc-300 hover:border-zinc-500 transition-colors"
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
      {/* Desktop center marker */}
      <div className="hidden lg:flex items-center justify-center">
        <div
          className="absolute left-1/2 -translate-x-1/2 w-5 h-5 rounded-full border-4 border-zinc-950 z-10"
          style={{ backgroundColor: era.color }}
        />
      </div>
      <div
        className="py-3 px-6 rounded-lg text-center mx-auto max-w-md"
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

function EventRow({ event, isLeft }: { event: HistoricalEvent; isLeft: boolean }) {
  const config = EVENT_CATEGORIES[event.category];

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
        <div
          className="p-4 rounded-lg bg-zinc-900 border border-zinc-800"
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
          <p className="text-zinc-300 text-xs leading-relaxed italic">{event.jazzConnection}</p>
          {(event.relatedAlbumIds?.length || event.relatedArtistIds?.length) && (
            <RelatedChips event={event} />
          )}
        </div>
      </div>

      {/* Mobile layout */}
      <div className="lg:hidden">
        <HistoricalEventCard event={event} compact />
      </div>
    </div>
  );
}

function AlbumRow({ album, isLeft }: { album: Album; isLeft: boolean }) {
  return (
    <div className="relative mb-6">
      {/* Desktop dot */}
      <div className="hidden lg:block absolute left-1/2 top-5 w-3 h-3 rounded-full -translate-x-1/2 z-10 bg-amber-500" />

      {/* Desktop layout */}
      <div
        className={`hidden lg:block ${
          isLeft ? 'pr-[52%]' : 'pl-[52%]'
        }`}
      >
        <JazzMilestoneCard album={album} />
      </div>

      {/* Mobile layout */}
      <div className="lg:hidden">
        <JazzMilestoneCard album={album} />
      </div>
    </div>
  );
}

function RelatedChips({ event }: { event: HistoricalEvent }) {
  const relatedAlbums = albums.filter((a) => event.relatedAlbumIds?.includes(a.id));
  const relatedArtists = artists.filter((a) => event.relatedArtistIds?.includes(a.id));

  if (relatedAlbums.length === 0 && relatedArtists.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1 mt-2">
      {relatedArtists.map((artist) => (
        <Link
          key={artist.id}
          to={`/artist/${artist.id}`}
          className="px-1.5 py-0.5 text-[10px] rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition-colors"
        >
          {artist.name}
        </Link>
      ))}
      {relatedAlbums.map((album) => (
        <Link
          key={album.id}
          to={`/album/${album.id}`}
          className="px-1.5 py-0.5 text-[10px] rounded bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 transition-colors"
        >
          {album.title}
        </Link>
      ))}
    </div>
  );
}

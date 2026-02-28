import type { HistoricalEvent, HistoricalEventCategory, Album } from '../types';
import albumsData from '../data/albums.json';
import { getAllEvents } from './historicalContext';

const albums = albumsData as Album[];

const MAX_ALBUMS_PER_EVENT = 6;
const DEDUP_WINDOW = 3;

interface MatchedAlbum {
  album: Album;
  matchType: 'explicit' | 'artist-era' | 'era-proximity';
}

export interface EnrichedEvent extends HistoricalEvent {
  matchedAlbums: MatchedAlbum[];
}

// Pre-build lookup maps
const albumById = new Map(albums.map((a) => [a.id, a]));
const albumsByArtistId = new Map<string, Album[]>();
albums.forEach((a) => {
  const existing = albumsByArtistId.get(a.artistId) ?? [];
  existing.push(a);
  albumsByArtistId.set(a.artistId, existing);
});
const albumsByEra = new Map<string, Album[]>();
albums.forEach((a) => {
  const existing = albumsByEra.get(a.era) ?? [];
  existing.push(a);
  albumsByEra.set(a.era, existing);
});

function matchAlbumsToEvent(
  event: HistoricalEvent,
  recentlyShown?: Set<string>,
): MatchedAlbum[] {
  const seen = new Set<string>();
  const matched: MatchedAlbum[] = [];

  const eventYear = event.year;
  const eventEndYear = event.endYear ?? event.year;

  // Layer 1: Explicit — always show editorial picks
  if (event.relatedAlbumIds) {
    for (const id of event.relatedAlbumIds) {
      const album = albumById.get(id);
      if (album && !seen.has(album.id)) {
        seen.add(album.id);
        matched.push({ album, matchType: 'explicit' });
      }
    }
  }

  if (matched.length >= MAX_ALBUMS_PER_EVENT) {
    return matched.slice(0, MAX_ALBUMS_PER_EVENT);
  }

  // Layer 2: Artist-era — albums by relatedArtistIds within ±3 years
  // Prefer albums not recently shown in nearby events
  if (event.relatedArtistIds) {
    const artistAlbums: MatchedAlbum[] = [];
    for (const artistId of event.relatedArtistIds) {
      const artAlbums = albumsByArtistId.get(artistId) ?? [];
      for (const album of artAlbums) {
        if (
          !seen.has(album.id) &&
          album.year >= eventYear - 3 &&
          album.year <= eventEndYear + 3
        ) {
          seen.add(album.id);
          artistAlbums.push({ album, matchType: 'artist-era' });
        }
      }
    }
    // Sort: unseen albums first, then by year proximity
    artistAlbums.sort((a, b) => {
      const aRecent = recentlyShown?.has(a.album.id) ? 1 : 0;
      const bRecent = recentlyShown?.has(b.album.id) ? 1 : 0;
      if (aRecent !== bRecent) return aRecent - bRecent;
      return (
        Math.abs(a.album.year - eventYear) - Math.abs(b.album.year - eventYear)
      );
    });
    matched.push(...artistAlbums);
  }

  if (matched.length >= MAX_ALBUMS_PER_EVENT) {
    return matched.slice(0, MAX_ALBUMS_PER_EVENT);
  }

  // Layer 3: Era-proximity — albums from same era within ±2 years
  // Skip albums recently shown unless no alternatives exist
  const eraAlbums = albumsByEra.get(event.era) ?? [];
  const freshMatches: MatchedAlbum[] = [];
  const recentMatches: MatchedAlbum[] = [];
  for (const album of eraAlbums) {
    if (
      !seen.has(album.id) &&
      album.year >= eventYear - 2 &&
      album.year <= eventEndYear + 2 &&
      album.coverUrl
    ) {
      seen.add(album.id);
      const match: MatchedAlbum = { album, matchType: 'era-proximity' };
      if (recentlyShown?.has(album.id)) {
        recentMatches.push(match);
      } else {
        freshMatches.push(match);
      }
    }
  }
  const sortByProximity = (a: MatchedAlbum, b: MatchedAlbum) =>
    Math.abs(a.album.year - eventYear) - Math.abs(b.album.year - eventYear);
  freshMatches.sort(sortByProximity);
  recentMatches.sort(sortByProximity);
  // Add fresh albums first, fall back to recent if needed
  matched.push(...freshMatches, ...recentMatches);

  return matched.slice(0, MAX_ALBUMS_PER_EVENT);
}

/**
 * Enrich events with matched albums, using a sliding window to reduce
 * album repetition across nearby events.
 */
function enrichEventsWithDedup(events: HistoricalEvent[]): EnrichedEvent[] {
  const sorted = [...events].sort((a, b) => a.year - b.year);
  const result: EnrichedEvent[] = [];
  const recentAlbumIds: string[][] = [];

  for (const event of sorted) {
    // Build the "recently shown" set from last DEDUP_WINDOW events
    const recentlyShown = new Set<string>();
    const windowStart = Math.max(0, recentAlbumIds.length - DEDUP_WINDOW);
    for (let i = windowStart; i < recentAlbumIds.length; i++) {
      recentAlbumIds[i].forEach((id) => recentlyShown.add(id));
    }

    const matched = matchAlbumsToEvent(event, recentlyShown);
    result.push({ ...event, matchedAlbums: matched });
    recentAlbumIds.push(matched.map((m) => m.album.id));
  }

  return result;
}

let _cachedEnrichedEvents: EnrichedEvent[] | null = null;

export function getEnrichedEvents(): EnrichedEvent[] {
  if (_cachedEnrichedEvents) return _cachedEnrichedEvents;

  const allEvents = getAllEvents();
  _cachedEnrichedEvents = enrichEventsWithDedup(allEvents);

  return _cachedEnrichedEvents;
}

export function getEnrichedEventsByCategories(
  categories: HistoricalEventCategory[],
): EnrichedEvent[] {
  const all = getEnrichedEvents();
  if (categories.length === 0) return all.sort((a, b) => a.year - b.year);
  return all
    .filter((e) => categories.includes(e.category))
    .sort((a, b) => a.year - b.year);
}

export function getTotalUniqueAlbumCount(): number {
  const all = getEnrichedEvents();
  const ids = new Set<string>();
  all.forEach((e) => e.matchedAlbums.forEach((m) => ids.add(m.album.id)));
  return ids.size;
}

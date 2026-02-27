import type { HistoricalEvent, HistoricalEventCategory, Album } from '../types';
import albumsData from '../data/albums.json';
import { getAllEvents } from './historicalContext';

const albums = albumsData as Album[];

const MAX_ALBUMS_PER_EVENT = 6;

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

function matchAlbumsToEvent(event: HistoricalEvent): MatchedAlbum[] {
  const seen = new Set<string>();
  const matched: MatchedAlbum[] = [];

  const eventYear = event.year;
  const eventEndYear = event.endYear ?? event.year;

  // Layer 1: Explicit — existing relatedAlbumIds
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
    // Sort by proximity to event year
    artistAlbums.sort(
      (a, b) =>
        Math.abs(a.album.year - eventYear) - Math.abs(b.album.year - eventYear)
    );
    matched.push(...artistAlbums);
  }

  if (matched.length >= MAX_ALBUMS_PER_EVENT) {
    return matched.slice(0, MAX_ALBUMS_PER_EVENT);
  }

  // Layer 3: Era-proximity — albums from same era within ±2 years
  const eraAlbums = albumsByEra.get(event.era) ?? [];
  const proximityMatches: MatchedAlbum[] = [];
  for (const album of eraAlbums) {
    if (
      !seen.has(album.id) &&
      album.year >= eventYear - 2 &&
      album.year <= eventEndYear + 2 &&
      album.coverUrl // prefer albums with covers for visual strip
    ) {
      seen.add(album.id);
      proximityMatches.push({ album, matchType: 'era-proximity' });
    }
  }
  proximityMatches.sort(
    (a, b) =>
      Math.abs(a.album.year - eventYear) - Math.abs(b.album.year - eventYear)
  );
  matched.push(...proximityMatches);

  return matched.slice(0, MAX_ALBUMS_PER_EVENT);
}

let _cachedEnrichedEvents: EnrichedEvent[] | null = null;

export function getEnrichedEvents(): EnrichedEvent[] {
  if (_cachedEnrichedEvents) return _cachedEnrichedEvents;

  const allEvents = getAllEvents();
  _cachedEnrichedEvents = allEvents.map((event) => ({
    ...event,
    matchedAlbums: matchAlbumsToEvent(event),
  }));

  return _cachedEnrichedEvents;
}

export function getEnrichedEventsByCategories(
  categories: HistoricalEventCategory[]
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

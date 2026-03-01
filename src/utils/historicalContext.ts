import type { HistoricalEvent, HistoricalEventCategory, EraId } from '../types';
import eventsData from '../data/historicalEvents.json';

const events = eventsData as HistoricalEvent[];

interface CategoryConfig {
  label: string;
  color: string;
  icon: 'fist' | 'dollar' | 'flag' | 'mic' | 'globe';
}

export const EVENT_CATEGORIES: Record<HistoricalEventCategory, CategoryConfig> = {
  'civil-rights':  { label: 'Racial Justice',       color: '#D95B43', icon: 'fist' },
  'economics':     { label: 'Economics & Industry',  color: '#2B6B5E', icon: 'dollar' },
  'politics':      { label: 'Politics & War',        color: '#B8383B', icon: 'flag' },
  'technology':    { label: 'Recording & Tech',      color: '#3B8686', icon: 'mic' },
  'globalization': { label: 'Global Diaspora',       color: '#7B4B94', icon: 'globe' },
};

export const ALL_CATEGORIES: HistoricalEventCategory[] = [
  'civil-rights',
  'economics',
  'politics',
  'technology',
  'globalization',
];

export function getAllEvents(): HistoricalEvent[] {
  return events;
}

export function getEventsByEra(eraId: EraId): HistoricalEvent[] {
  return events.filter((e) => e.era === eraId).sort((a, b) => a.year - b.year);
}

export function getEventsForAlbum(albumId: string): HistoricalEvent[] {
  return events.filter((e) => e.relatedAlbumIds?.includes(albumId));
}

export function getEventsForArtist(artistId: string): HistoricalEvent[] {
  return events.filter((e) => e.relatedArtistIds?.includes(artistId));
}

export function getEventsByCategory(
  category: HistoricalEventCategory,
): HistoricalEvent[] {
  return events.filter((e) => e.category === category).sort((a, b) => a.year - b.year);
}

export function getEventsByCategories(
  categories: HistoricalEventCategory[],
): HistoricalEvent[] {
  if (categories.length === 0) return events.sort((a, b) => a.year - b.year);
  return events
    .filter((e) => categories.includes(e.category))
    .sort((a, b) => a.year - b.year);
}

export function getCategoryConfig(category: HistoricalEventCategory): CategoryConfig {
  return EVENT_CATEGORIES[category];
}

export function formatEventYear(event: HistoricalEvent): string {
  if (event.endYear) {
    return `${event.year}–${event.endYear}`;
  }
  return String(event.year);
}

import { useMemo, useEffect } from 'react';
import { useWeather } from '../../hooks/useWeather';
import { getTodaysPicks, getMoodDescription } from '../../utils/weatherMood';
import { markAsShown, clearOldEntries } from '../../utils/localStorage';
import { CarouselSection } from './CarouselSection';
import { AlbumCarousel } from './AlbumCarousel';
import type { Album } from '../../types';

interface TodaysPickProps {
  albums: Album[];
}

const CACHE_KEY = 'jazz-guide-todays-picks-cache';

interface CachedPicks {
  date: string;
  albumIds: string[];
}

function getCachedPicks(albums: Album[]): Album[] | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const cached: CachedPicks = JSON.parse(raw);
    const today = new Date().toISOString().split('T')[0];
    if (cached.date !== today) return null;
    // Resolve album IDs back to album objects
    const albumMap = new Map(albums.map((a) => [a.id, a]));
    const resolved = cached.albumIds
      .map((id) => albumMap.get(id))
      .filter((a): a is Album => a !== undefined);
    return resolved.length > 0 ? resolved : null;
  } catch {
    return null;
  }
}

function cachePicks(picks: Album[]): void {
  try {
    const today = new Date().toISOString().split('T')[0];
    const data: CachedPicks = { date: today, albumIds: picks.map((a) => a.id) };
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(data));
  } catch {
    // sessionStorage unavailable
  }
}

export function TodaysPick({ albums }: TodaysPickProps) {
  const { weather, loading } = useWeather();

  const picks = useMemo(() => {
    // Return cached picks if available (same day)
    const cached = getCachedPicks(albums);
    if (cached) return cached;

    // Compute picks (use weather if available, otherwise time-only)
    const w = loading ? null : weather;
    const computed = getTodaysPicks(albums, w);
    cachePicks(computed);
    return computed;
  }, [albums, weather, loading]);

  useEffect(() => {
    if (picks.length > 0) {
      clearOldEntries(7);
      markAsShown(picks.map((a) => a.id));
    }
  }, [picks]);

  const moodDescription = useMemo(() => {
    return getMoodDescription(loading ? null : weather);
  }, [weather, loading]);

  if (picks.length === 0) return null;

  return (
    <CarouselSection
      title="Today's Pick"
      subtitle={moodDescription}
    >
      <AlbumCarousel albums={picks} cardSize="md" showYear eagerCount={5} />
    </CarouselSection>
  );
}

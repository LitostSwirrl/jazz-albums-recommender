import { useMemo, useEffect, useState } from 'react';
import { useWeather } from '../../hooks/useWeather';
import { getTodaysPicks, getMoodDescription } from '../../utils/weatherMood';
import { markAsShown, clearOldEntries } from '../../utils/localStorage';
import { CarouselSection } from './CarouselSection';
import { AlbumCarousel } from './AlbumCarousel';
import type { Album } from '../../types';

interface TodaysPickProps {
  albums: Album[];
}

export function TodaysPick({ albums }: TodaysPickProps) {
  const { weather, loading } = useWeather();

  // Show time-based picks immediately, then refine with weather when available
  const immediatePicks = useMemo(() => getTodaysPicks(albums, null), [albums]);
  const [picks, setPicks] = useState<Album[]>(immediatePicks);

  useEffect(() => {
    if (!loading && weather) {
      const weatherPicks = getTodaysPicks(albums, weather);
      setPicks(weatherPicks);
    }
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

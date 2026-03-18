import { useMemo, useEffect } from 'react';
import { useWeather } from '../../hooks/useWeather';
import { getTodaysPicks, getMoodDescription, getWeatherEmoji } from '../../utils/weatherMood';
import { markAsShown, clearOldEntries } from '../../utils/localStorage';
import { CarouselSection } from './CarouselSection';
import { AlbumCarousel } from './AlbumCarousel';
import type { Album } from '../../types';

interface TodaysPickProps {
  albums: Album[];
}

function PickSkeleton() {
  return (
    <section className="mb-10">
      <div className="h-6 w-48 bg-surface rounded animate-pulse mb-4" />
      <div className="flex gap-4 overflow-hidden">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="flex-shrink-0 w-44">
            <div className="aspect-square bg-surface rounded-sm animate-pulse mb-2" />
            <div className="h-4 w-32 bg-surface rounded animate-pulse mb-1" />
            <div className="h-3 w-24 bg-surface rounded animate-pulse" />
          </div>
        ))}
      </div>
    </section>
  );
}

export function TodaysPick({ albums }: TodaysPickProps) {
  const { weather, loading } = useWeather();

  const picks = useMemo(() => {
    if (loading) return [];
    return getTodaysPicks(albums, weather);
  }, [albums, weather, loading]);

  // Side effects: mark picks as shown and clean old history
  useEffect(() => {
    if (picks.length > 0) {
      clearOldEntries(7);
      markAsShown(picks.map((a) => a.id));
    }
  }, [picks]);

  const moodDescription = useMemo(() => {
    if (loading) return '';
    return getMoodDescription(weather);
  }, [weather, loading]);

  if (loading) return <PickSkeleton />;
  if (picks.length === 0) return null;

  const weatherEmoji = weather ? getWeatherEmoji(weather.weatherCode) : '';
  const title = weather
    ? `${weatherEmoji} Today's Pick`
    : "Today's Pick";

  return (
    <CarouselSection
      title={title}
      subtitle={moodDescription}
    >
      <AlbumCarousel albums={picks} cardSize="md" showYear />
    </CarouselSection>
  );
}

import { useMemo } from 'react';
import { getDailyPicks } from '../../utils/discovery';
import { CarouselSection } from './CarouselSection';
import { AlbumCarousel } from './AlbumCarousel';
import type { Album } from '../../types';

interface TodaysPickProps {
  albums: Album[];
}

export function TodaysPick({ albums }: TodaysPickProps) {
  // Date-only daily rotation — no geolocation, no weather, no permission prompt.
  const picks = useMemo(() => getDailyPicks(albums), [albums]);

  if (picks.length === 0) return null;

  return (
    <CarouselSection title="Today's Pick" subtitle="Eight albums, refreshed daily">
      <AlbumCarousel albums={picks} cardSize="md" showYear eagerCount={5} trackSource="todays_pick" />
    </CarouselSection>
  );
}

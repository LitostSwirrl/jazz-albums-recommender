import { useMemo } from 'react';
import { CarouselSection } from './CarouselSection';
import { AlbumCarousel } from './AlbumCarousel';
import { seededShuffle } from '../../utils/random';
import type { Album } from '../../types';

interface GenreCollection {
  id: string;
  title: string;
  genres: string[];
  linkTo?: string;
}

const GENRE_COLLECTIONS: GenreCollection[] = [
  { id: 'grooves', title: 'Deep Grooves', genres: ['soul jazz', 'jazz-funk', 'hard bop', 'acid jazz'], linkTo: '/albums?genre=soul+jazz' },
  { id: 'bold', title: 'For the Bold', genres: ['free jazz', 'avant-garde jazz', 'free improvisation', 'experimental'], linkTo: '/albums?genre=free+jazz' },
  { id: 'calm', title: 'Cool & Calm', genres: ['cool jazz', 'bossa nova', 'chamber jazz', 'piano trio'], linkTo: '/albums?genre=cool+jazz' },
  { id: 'electric', title: 'Electric Explorations', genres: ['jazz fusion', 'jazz-funk'], linkTo: '/albums?genre=jazz+fusion' },
  { id: 'spiritual', title: 'Spiritual & Sacred', genres: ['spiritual jazz', 'modal jazz'], linkTo: '/albums?genre=spiritual+jazz' },
  { id: 'global', title: 'Global Jazz', genres: ['bossa nova', 'afro-cuban jazz', 'latin jazz', 'African jazz', 'world fusion', 'Brazilian jazz'], linkTo: '/albums?genre=latin+jazz' },
];

interface GenreRowsProps {
  albums: Album[];
}

export function GenreRows({ albums }: GenreRowsProps) {
  const daySeed = Math.floor(Date.now() / 86400000);

  const collections = useMemo(() => {
    return GENRE_COLLECTIONS.map((collection, idx) => {
      const matching = albums.filter((a) =>
        a.genres.some((g) =>
          collection.genres.some((cg) => g.toLowerCase() === cg.toLowerCase())
        ) && a.coverUrl
      );
      const shuffled = seededShuffle(matching, daySeed + idx);
      const seen = new Set<string>();
      const unique = shuffled.filter((a) => {
        if (seen.has(a.title)) return false;
        seen.add(a.title);
        return true;
      });
      return { ...collection, albums: unique.slice(0, 20) };
    }).filter((c) => c.albums.length >= 4);
  }, [albums, daySeed]);

  return (
    <>
      {collections.map((collection) => (
        <CarouselSection
          key={collection.id}
          title={collection.title}
          linkTo={collection.linkTo}
        >
          <AlbumCarousel albums={collection.albums} cardSize="sm" />
        </CarouselSection>
      ))}
    </>
  );
}

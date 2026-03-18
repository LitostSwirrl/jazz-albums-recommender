import { useRef, useState, useEffect, useCallback } from 'react';
import { AlbumCard } from './AlbumCard';
import type { Album } from '../../types';

interface AlbumCarouselProps {
  albums: Album[];
  cardSize?: 'sm' | 'md' | 'lg';
  showYear?: boolean;
  showEraTag?: boolean;
  eagerCount?: number;
  className?: string;
}

const cardWidths: Record<string, number> = {
  sm: 144 + 16,  // w-36 + gap-4
  md: 176 + 16,  // w-44 + gap-4
  lg: 224 + 16,  // w-56 + gap-4
};

export function AlbumCarousel({ albums, cardSize = 'md', showYear = false, showEraTag = false, eagerCount = 0, className = '' }: AlbumCarouselProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 4);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 4);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    checkScroll();
    el.addEventListener('scroll', checkScroll, { passive: true });
    const observer = new ResizeObserver(checkScroll);
    observer.observe(el);
    return () => {
      el.removeEventListener('scroll', checkScroll);
      observer.disconnect();
    };
  }, [checkScroll, albums]);

  const scroll = (direction: 'left' | 'right') => {
    const el = scrollRef.current;
    if (!el) return;
    const scrollAmount = cardWidths[cardSize] * 3;
    el.scrollBy({
      left: direction === 'left' ? -scrollAmount : scrollAmount,
      behavior: 'smooth',
    });
  };

  if (albums.length === 0) return null;

  return (
    <div className={`relative group/carousel ${className}`}>
      {/* Left fade + arrow */}
      {canScrollLeft && (
        <>
          <div className="absolute left-0 top-0 bottom-0 w-12 bg-gradient-to-r from-cream to-transparent z-10 pointer-events-none" />
          <button
            onClick={() => scroll('left')}
            className="absolute left-1 top-1/2 -translate-y-1/2 z-20 w-10 h-10 rounded-full bg-surface/90 border border-border shadow-elevated flex items-center justify-center text-charcoal hover:text-coral hover:border-coral/50 transition-all opacity-0 group-hover/carousel:opacity-100 focus-visible:opacity-100"
            aria-label="Scroll left"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        </>
      )}

      {/* Scrollable area */}
      <div
        ref={scrollRef}
        className="flex gap-4 overflow-x-auto pb-2 scrollbar-thin scroll-smooth"
        style={{ scrollSnapType: 'x mandatory' }}
      >
        {albums.map((album, index) => (
          <div key={album.id} style={{ scrollSnapAlign: 'start' }}>
            <AlbumCard
              album={album}
              size={cardSize}
              showYear={showYear}
              showEraTag={showEraTag}
              priority={index < eagerCount}
            />
          </div>
        ))}
      </div>

      {/* Right fade + arrow */}
      {canScrollRight && (
        <>
          <div className="absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-cream to-transparent z-10 pointer-events-none" />
          <button
            onClick={() => scroll('right')}
            className="absolute right-1 top-1/2 -translate-y-1/2 z-20 w-10 h-10 rounded-full bg-surface/90 border border-border shadow-elevated flex items-center justify-center text-charcoal hover:text-coral hover:border-coral/50 transition-all opacity-0 group-hover/carousel:opacity-100 focus-visible:opacity-100"
            aria-label="Scroll right"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </>
      )}
    </div>
  );
}

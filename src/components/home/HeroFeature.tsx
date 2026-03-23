import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { AlbumCover } from '../AlbumCover';
import { seededPick } from '../../utils/random';
import type { Album, Era } from '../../types';

interface HeroFeatureProps {
  albums: Album[];
  eras: Era[];
}

export function HeroFeature({ albums, eras }: HeroFeatureProps) {
  const featured = useMemo(() => {
    const withCovers = albums.filter((a) => a.coverUrl && a.description.length > 100);
    if (withCovers.length === 0) return null;
    const daySeed = Math.floor(Date.now() / 86400000);
    return seededPick(withCovers, daySeed) ?? null;
  }, [albums]);

  if (!featured) return null;

  const era = eras.find((e) => e.id === featured.era);
  const eraColor = era?.color ?? '#a89a7d';

  return (
    <section className="relative overflow-hidden rounded-xl mb-10 -mx-4 sm:mx-0">
      {/* Gradient background from era color */}
      <div
        className="absolute inset-0"
        style={{
          background: `linear-gradient(135deg, ${eraColor}30 0%, #1a1917 60%, #141210 100%)`,
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-navy/90 via-transparent to-transparent" />

      <div className="relative z-10 flex flex-col md:flex-row items-center gap-8 p-8 md:p-12">
        {/* Album cover */}
        <div className="flex-shrink-0 w-56 md:w-72 shadow-elevated rounded-sm overflow-hidden">
          <AlbumCover
            coverUrl={featured.coverUrl}
            title={featured.title}
            size="sm"
            pixelWidth={500}
            priority
          />
        </div>

        {/* Info */}
        <div className="flex-1 text-center md:text-left">
          <span
            className="inline-block px-3 py-1 text-[10px] font-mono uppercase tracking-widest rounded-full mb-4"
            style={{ backgroundColor: eraColor + '30', color: eraColor }}
          >
            Featured Today
          </span>
          <h1 className="text-3xl md:text-5xl font-display text-white leading-tight mb-3">
            {featured.title}
          </h1>
          <p className="text-lg text-white/70 font-body mb-1">
            {featured.artist} &middot; {featured.year}
          </p>
          <p className="text-sm text-white/50 mb-6 line-clamp-2 max-w-xl">
            {featured.significance}
          </p>
          <div className="flex gap-3 justify-center md:justify-start">
            <Link
              to={`/album/${featured.id}`}
              className="px-6 py-2.5 bg-coral text-white font-semibold rounded-lg hover:bg-coral/90 transition-colors text-sm"
            >
              Explore Album
            </Link>
            {featured.spotifyUrl && (
              <a
                href={featured.spotifyUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-2.5 border border-white/30 text-white rounded-lg hover:bg-white/10 transition-colors text-sm"
              >
                Listen on Spotify
              </a>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

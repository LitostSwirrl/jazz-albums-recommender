import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import erasData from '../data/eras.json';
import albumsData from '../data/albums.json';
import artistsData from '../data/artists.json';
import { AlbumCover } from '../components/AlbumCover';
import { ArtistPhoto } from '../components/ArtistPhoto';
import { SEO } from '../components/SEO';
import type { Era, Album, Artist } from '../types';

const eras = erasData as Era[];
const albums = albumsData as Album[];
const artists = artistsData as Artist[];

// Seeded PRNG for consistent daily mosaic
function seededShuffle<T>(arr: T[], seed: number): T[] {
  const shuffled = [...arr];
  let s = seed;
  for (let i = shuffled.length - 1; i > 0; i--) {
    s = (s * 16807 + 0) % 2147483647;
    const j = s % (i + 1);
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

function getMosaicAlbums(): Album[] {
  const withCovers = albums.filter((a) => a.coverUrl);
  const daySeed = Math.floor(Date.now() / 86400000);
  return seededShuffle(withCovers, daySeed).slice(0, 24);
}

function getEraHighlightAlbum(eraId: string): Album | undefined {
  // Pick the first album with a cover for each era
  return albums.find((a) => a.era === eraId && a.coverUrl);
}

function getInfluentialArtists(): Artist[] {
  return artists
    .filter((a) => a.influences.length > 0 || a.influencedBy.length > 0)
    .slice(0, 6);
}

export function Home() {
  const mosaicAlbums = useMemo(() => getMosaicAlbums(), []);
  const influentialArtists = useMemo(() => getInfluentialArtists(), []);

  return (
    <div className="page-enter">
      <SEO
        title="Your Jazz Library"
        description={`A curated guide to ${albums.length} jazz albums from New Orleans to today. Explore jazz history, discover ${artists.length} artists, and understand how they shaped each other.`}
      />

      {/* Hero Section — Full-bleed Navy */}
      <section className="relative text-center overflow-hidden bg-navy py-20 md:py-28 px-4 -mx-4 sm:-mx-6 lg:-mx-8 mb-16">
        {/* Album cover mosaic background */}
        <div className="absolute inset-0 grid grid-cols-6 grid-rows-4 gap-1 opacity-[0.06] rotate-[-2deg] scale-110 pointer-events-none">
          {mosaicAlbums.map((album) => (
            <div key={album.id} className="aspect-square overflow-hidden">
              <AlbumCover coverUrl={album.coverUrl} title={album.title} size="sm" pixelWidth={200} />
            </div>
          ))}
        </div>

        {/* Hero content */}
        <div className="relative z-10 max-w-4xl mx-auto">
          <h1 className="text-6xl md:text-8xl font-display text-white uppercase tracking-wider mb-6">
            Your Jazz Library
          </h1>
          <p className="text-xl text-white/70 font-body max-w-2xl mx-auto mb-10">
            A curated guide to jazz history — from New Orleans to today.
            Explore albums, understand the music, and discover how artists shaped each other.
          </p>
          <div className="flex justify-center gap-4 flex-wrap">
            <Link
              to="/timeline"
              className="px-8 py-3.5 bg-coral text-white font-semibold rounded-lg hover:bg-coral/90 transition-colors"
            >
              Start with the Timeline
            </Link>
            <Link
              to="/albums"
              className="px-8 py-3.5 border border-white/30 text-white rounded-lg hover:bg-white/10 transition-colors"
            >
              Browse Albums
            </Link>
          </div>
        </div>
      </section>

      <div className="max-w-6xl mx-auto px-4">
        {/* Stats Bar */}
        <section className="mb-16">
          <div className="flex items-center justify-center divide-x divide-border">
            {[
              { value: albums.length, label: 'Albums' },
              { value: artists.length, label: 'Artists' },
              { value: eras.length, label: 'Eras' },
              { value: '100+', label: 'Years' },
            ].map((stat) => (
              <div
                key={stat.label}
                className="text-center px-8 md:px-12 py-4"
              >
                <div className="text-5xl font-display text-coral">
                  {stat.value}
                </div>
                <div className="font-mono text-warm-gray uppercase tracking-widest text-xs mt-2">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Learning Paths */}
        <section className="mb-16">
          <h2 className="text-2xl font-heading text-charcoal mb-6">Where to Begin</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Link
              to="/era/bebop"
              className="bg-surface shadow-card hover:shadow-card-hover rounded-lg overflow-hidden transition-all duration-300 group"
            >
              <div className="h-1" style={{ backgroundColor: '#3B8686' }} />
              <div className="p-6">
                <h3 className="text-xl font-heading text-charcoal mb-2">New to Jazz?</h3>
                <p className="text-warm-gray text-sm leading-relaxed">
                  Start with Bebop — the revolutionary sound that made jazz an art form.
                  Charlie Parker, Dizzy Gillespie, and the birth of modern jazz.
                </p>
                <span className="text-coral text-sm mt-4 inline-block group-hover:underline">
                  Explore Bebop &rarr;
                </span>
              </div>
            </Link>

            <Link
              to="/era/hard-bop"
              className="bg-surface shadow-card hover:shadow-card-hover rounded-lg overflow-hidden transition-all duration-300 group"
            >
              <div className="h-1" style={{ backgroundColor: '#B8383B' }} />
              <div className="p-6">
                <h3 className="text-xl font-heading text-charcoal mb-2">Want Soul & Groove?</h3>
                <p className="text-warm-gray text-sm leading-relaxed">
                  Hard Bop brought blues and gospel back into jazz.
                  Art Blakey, Horace Silver, and music that swings hard.
                </p>
                <span className="text-coral text-sm mt-4 inline-block group-hover:underline">
                  Explore Hard Bop &rarr;
                </span>
              </div>
            </Link>

            <Link
              to="/era/free-jazz"
              className="bg-surface shadow-card hover:shadow-card-hover rounded-lg overflow-hidden transition-all duration-300 group"
            >
              <div className="h-1" style={{ backgroundColor: '#7B4B94' }} />
              <div className="p-6">
                <h3 className="text-xl font-heading text-charcoal mb-2">Ready to Go Deep?</h3>
                <p className="text-warm-gray text-sm leading-relaxed">
                  Free Jazz broke all the rules.
                  Ornette Coleman, John Coltrane's later work, and pure expression.
                </p>
                <span className="text-coral text-sm mt-4 inline-block group-hover:underline">
                  Explore Free Jazz &rarr;
                </span>
              </div>
            </Link>
          </div>
        </section>

        {/* Era Journey */}
        <section className="mb-16">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-heading text-charcoal">The Jazz Journey</h2>
            <Link to="/timeline" className="text-coral hover:text-coral/80 text-sm transition-colors">
              Full Timeline &rarr;
            </Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {eras.map((era) => (
              <Link
                key={era.id}
                to={`/era/${era.id}`}
                className="p-4 rounded-lg bg-surface shadow-card border border-border hover:shadow-card-hover transition-all duration-300 hover:scale-[1.02]"
                style={{ borderLeftColor: era.color, borderLeftWidth: '4px' }}
              >
                <h3 className="font-semibold text-charcoal">{era.name}</h3>
                <p className="text-sm text-warm-gray">{era.period}</p>
                <p className="text-xs text-warm-gray/70 mt-2 line-clamp-2">
                  {era.characteristics.slice(0, 2).join(', ')}
                </p>
              </Link>
            ))}
          </div>
        </section>

        {/* Era Highlights — 1 standout per era */}
        <section className="mb-16">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-heading text-charcoal">Highlights from Every Era</h2>
            <Link to="/albums" className="text-coral hover:text-coral/80 text-sm transition-colors">
              View all {albums.length} albums &rarr;
            </Link>
          </div>
          <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-thin -mx-4 px-4">
            {eras.map((era) => {
              const album = getEraHighlightAlbum(era.id);
              if (!album) return null;
              return (
                <Link
                  key={era.id}
                  to={`/album/${album.id}`}
                  className="flex-shrink-0 w-48 group"
                >
                  <div className="relative rounded-sm overflow-hidden mb-3 shadow-card group-hover:shadow-card-hover transition-all duration-300 group-hover:scale-[1.03]">
                    <AlbumCover coverUrl={album.coverUrl} title={album.title} size="md" />
                    <div
                      className="absolute bottom-0 left-0 right-0 px-2 py-1 text-[10px] font-mono font-semibold uppercase tracking-wider text-center"
                      style={{ backgroundColor: era.color + 'CC', color: '#fff' }}
                    >
                      {era.name.split(' ')[0]}
                    </div>
                  </div>
                  <h3 className="font-semibold text-charcoal text-sm group-hover:text-coral transition-colors truncate">
                    {album.title}
                  </h3>
                  <p className="text-warm-gray text-xs truncate">{album.artist}</p>
                </Link>
              );
            })}
          </div>
        </section>

        {/* Artist Connections */}
        <section className="mb-16">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-heading text-charcoal">How Artists Connect</h2>
              <p className="text-warm-gray text-sm">Jazz is a conversation across generations</p>
            </div>
            <Link to="/influence" className="text-coral hover:text-coral/80 text-sm transition-colors">
              View Influence Map &rarr;
            </Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {influentialArtists.map((artist) => (
              <Link
                key={artist.id}
                to={`/artist/${artist.id}`}
                className="p-4 rounded-lg bg-surface border border-border shadow-card hover:border-coral/50 hover:shadow-card-hover transition-all duration-300 text-center group"
              >
                <div className="mx-auto mb-3">
                  <ArtistPhoto
                    imageUrl={artist.imageUrl}
                    name={artist.name}
                    size="lg"
                  />
                </div>
                <h3 className="font-semibold text-charcoal text-sm group-hover:text-coral transition-colors">
                  {artist.name}
                </h3>
                <p className="text-xs text-warm-gray mt-1">
                  {artist.instruments[0]}
                </p>
              </Link>
            ))}
          </div>
        </section>

        {/* Jazz & Society */}
        <section className="mb-16">
          <Link
            to="/context"
            className="block p-8 rounded-lg bg-navy text-white hover:shadow-elevated transition-all duration-300 group"
          >
            <h2 className="text-xl font-heading text-white mb-2 group-hover:text-coral transition-colors">
              Jazz & Society
            </h2>
            <p className="text-white/70 text-sm mb-3">
              Jazz never existed in a vacuum. Explore how civil rights, war, economics, and
              technology shaped the music — and how the music shaped the world.
            </p>
            <span className="text-coral text-sm group-hover:underline">
              Explore the parallel timeline &rarr;
            </span>
          </Link>
        </section>

        {/* Educational Quote */}
        <section className="p-10 rounded-lg bg-surface shadow-card border border-border mb-12">
          <blockquote className="relative">
            <span className="absolute -top-4 -left-2 text-6xl text-coral/30 font-display leading-none select-none">&ldquo;</span>
            <p className="text-2xl text-charcoal font-heading italic leading-relaxed pl-6">
              Jazz is not just music, it's a way of life, it's a way of being, a way of thinking.
            </p>
            <span className="absolute -bottom-6 right-0 text-6xl text-coral/30 font-display leading-none select-none">&rdquo;</span>
          </blockquote>
          <cite className="block text-coral font-heading mt-6 pl-6 not-italic">— Nina Simone</cite>
          <p className="text-warm-gray text-sm mt-4 pl-6">
            This guide is your companion to understanding that way of thinking.
            Each album tells a story. Each artist is part of a tradition.
            Explore, listen, and let the music speak.
          </p>
        </section>
      </div>
    </div>
  );
}

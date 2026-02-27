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
    <div className="max-w-6xl mx-auto px-4 py-12 page-enter">
      <SEO
        title="Your Jazz Library"
        description={`A curated guide to ${albums.length} jazz albums from New Orleans to today. Explore jazz history, discover ${artists.length} artists, and understand how they shaped each other.`}
      />

      {/* Hero Section with Mosaic Background */}
      <section className="relative text-center mb-16 overflow-hidden rounded-2xl py-16 px-4">
        {/* Album cover mosaic background */}
        <div className="absolute inset-0 grid grid-cols-6 grid-rows-4 gap-1 opacity-[0.07] rotate-[-2deg] scale-110 pointer-events-none">
          {mosaicAlbums.map((album) => (
            <div key={album.id} className="aspect-square overflow-hidden">
              <AlbumCover coverUrl={album.coverUrl} title={album.title} size="sm" />
            </div>
          ))}
        </div>

        {/* Hero content */}
        <div className="relative z-10">
          <h1 className="text-5xl md:text-6xl font-bold mb-4 font-display bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent">
            Your Jazz Library
          </h1>
          <p className="text-xl text-zinc-400 max-w-2xl mx-auto mb-8">
            A curated guide to jazz history — from New Orleans to today.
            Explore albums, understand the music, and discover how artists shaped each other.
          </p>
          <div className="flex justify-center gap-4">
            <Link
              to="/timeline"
              className="px-6 py-3 bg-amber-500 text-black font-semibold rounded-xl hover:bg-amber-400 transition-colors"
            >
              Start with the Timeline
            </Link>
            <Link
              to="/albums"
              className="px-6 py-3 border border-zinc-700 text-zinc-300 rounded-xl hover:border-zinc-500 transition-colors"
            >
              Browse Albums
            </Link>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="mb-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { value: albums.length, label: 'Albums' },
            { value: artists.length, label: 'Artists' },
            { value: eras.length, label: 'Eras' },
            { value: '100+', label: 'Years' },
          ].map((stat) => (
            <div
              key={stat.label}
              className="text-center p-4 rounded-xl bg-zinc-900/50 border border-zinc-800"
            >
              <div className="text-3xl font-bold text-amber-400 font-display">
                {stat.value}
              </div>
              <div className="text-xs text-zinc-500 uppercase tracking-wider mt-1">
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Learning Paths */}
      <section className="mb-16">
        <h2 className="text-2xl font-bold mb-6 font-display">Where to Begin</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link
            to="/era/bebop"
            className="p-6 rounded-xl bg-gradient-to-br from-lime-900/30 to-zinc-900 border border-lime-800/30 hover:border-lime-700/50 hover:shadow-xl hover:shadow-black/20 transition-all duration-300 group"
          >
            <h3 className="text-xl font-bold text-lime-400 mb-2">New to Jazz?</h3>
            <p className="text-zinc-400 text-sm">
              Start with Bebop — the revolutionary sound that made jazz an art form.
              Charlie Parker, Dizzy Gillespie, and the birth of modern jazz.
            </p>
            <span className="text-lime-400 text-sm mt-3 inline-block group-hover:underline">
              Explore Bebop →
            </span>
          </Link>

          <Link
            to="/era/hard-bop"
            className="p-6 rounded-xl bg-gradient-to-br from-blue-900/30 to-zinc-900 border border-blue-800/30 hover:border-blue-700/50 hover:shadow-xl hover:shadow-black/20 transition-all duration-300 group"
          >
            <h3 className="text-xl font-bold text-blue-400 mb-2">Want Soul & Groove?</h3>
            <p className="text-zinc-400 text-sm">
              Hard Bop brought blues and gospel back into jazz.
              Art Blakey, Horace Silver, and music that swings hard.
            </p>
            <span className="text-blue-400 text-sm mt-3 inline-block group-hover:underline">
              Explore Hard Bop →
            </span>
          </Link>

          <Link
            to="/era/free-jazz"
            className="p-6 rounded-xl bg-gradient-to-br from-purple-900/30 to-zinc-900 border border-purple-800/30 hover:border-purple-700/50 hover:shadow-xl hover:shadow-black/20 transition-all duration-300 group"
          >
            <h3 className="text-xl font-bold text-purple-400 mb-2">Ready to Go Deep?</h3>
            <p className="text-zinc-400 text-sm">
              Free Jazz broke all the rules.
              Ornette Coleman, John Coltrane's later work, and pure expression.
            </p>
            <span className="text-purple-400 text-sm mt-3 inline-block group-hover:underline">
              Explore Free Jazz →
            </span>
          </Link>
        </div>
      </section>

      {/* Era Journey */}
      <section className="mb-16">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold font-display">The Jazz Journey</h2>
          <Link to="/timeline" className="text-amber-400 hover:text-amber-300 text-sm">
            Full Timeline →
          </Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {eras.map((era) => (
            <Link
              key={era.id}
              to={`/era/${era.id}`}
              className="p-4 rounded-xl border border-zinc-800 hover:border-zinc-600 transition-all duration-300 hover:scale-105 hover:shadow-xl hover:shadow-black/20"
              style={{ borderLeftColor: era.color, borderLeftWidth: '4px' }}
            >
              <h3 className="font-semibold text-white">{era.name}</h3>
              <p className="text-sm text-zinc-500">{era.period}</p>
              <p className="text-xs text-zinc-600 mt-2 line-clamp-2">
                {era.characteristics.slice(0, 2).join(', ')}
              </p>
            </Link>
          ))}
        </div>
      </section>

      {/* Era Highlights — 1 standout per era */}
      <section className="mb-16">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold font-display">Highlights from Every Era</h2>
          <Link to="/albums" className="text-amber-400 hover:text-amber-300 text-sm">
            View all {albums.length} albums →
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
                <div className="relative rounded-xl overflow-hidden mb-3 group-hover:scale-105 transition-transform duration-300">
                  <AlbumCover coverUrl={album.coverUrl} title={album.title} size="md" />
                  <div
                    className="absolute bottom-0 left-0 right-0 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-center"
                    style={{ backgroundColor: era.color + 'CC', color: '#000' }}
                  >
                    {era.name.split(' ')[0]}
                  </div>
                </div>
                <h3 className="font-semibold text-white text-sm group-hover:text-amber-400 transition-colors truncate">
                  {album.title}
                </h3>
                <p className="text-zinc-400 text-xs truncate">{album.artist}</p>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Artist Connections */}
      <section className="mb-16">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold font-display">How Artists Connect</h2>
            <p className="text-zinc-500 text-sm">Jazz is a conversation across generations</p>
          </div>
          <Link to="/influence" className="text-amber-400 hover:text-amber-300 text-sm">
            View Influence Map →
          </Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {influentialArtists.map((artist) => (
            <Link
              key={artist.id}
              to={`/artist/${artist.id}`}
              className="p-4 rounded-xl bg-zinc-900 border border-zinc-800 hover:border-amber-500/50 hover:shadow-xl hover:shadow-black/20 transition-all duration-300 text-center group"
            >
              <div className="mx-auto mb-3">
                <ArtistPhoto
                  imageUrl={artist.imageUrl}
                  name={artist.name}
                  size="lg"
                />
              </div>
              <h3 className="font-semibold text-white text-sm group-hover:text-amber-400 transition-colors">
                {artist.name}
              </h3>
              <p className="text-xs text-zinc-500 mt-1">
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
          className="block p-6 rounded-xl bg-gradient-to-br from-red-900/20 via-amber-900/20 to-purple-900/20 border border-zinc-700 hover:border-amber-500/50 hover:shadow-xl hover:shadow-black/20 transition-all duration-300 group"
        >
          <h2 className="text-xl font-bold text-amber-400 mb-2 group-hover:text-amber-300 transition-colors font-display">
            Jazz & Society
          </h2>
          <p className="text-zinc-400 text-sm mb-3">
            Jazz never existed in a vacuum. Explore how civil rights, war, economics, and
            technology shaped the music — and how the music shaped the world.
          </p>
          <span className="text-amber-400 text-sm group-hover:underline">
            Explore the parallel timeline →
          </span>
        </Link>
      </section>

      {/* Educational Quote */}
      <section className="p-8 rounded-xl bg-gradient-to-r from-zinc-900 to-zinc-800 border border-zinc-700">
        <blockquote className="text-xl text-zinc-300 italic mb-4 font-display">
          "Jazz is not just music, it's a way of life, it's a way of being, a way of thinking."
        </blockquote>
        <cite className="text-amber-400">— Nina Simone</cite>
        <p className="text-zinc-500 text-sm mt-4">
          This guide is your companion to understanding that way of thinking.
          Each album tells a story. Each artist is part of a tradition.
          Explore, listen, and let the music speak.
        </p>
      </section>
    </div>
  );
}

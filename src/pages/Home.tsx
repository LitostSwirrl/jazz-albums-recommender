import { Link } from 'react-router-dom';
import erasData from '../data/eras.json';
import albumsData from '../data/albums.json';
import artistsData from '../data/artists.json';
import { AlbumCover } from '../components/AlbumCover';
import { ArtistPhoto } from '../components/ArtistPhoto';
import type { Era, Album, Artist } from '../types';

const eras = erasData as Era[];
const albums = albumsData as Album[];
const artists = artistsData as Artist[];

// Get a diverse mix of albums
function getFeaturedAlbums(): Album[] {
  const eraAlbums: Album[] = [];
  eras.forEach((era) => {
    const eraAlbum = albums.find((a) => a.era === era.id);
    if (eraAlbum) eraAlbums.push(eraAlbum);
  });
  return eraAlbums.slice(0, 4);
}

// Get influential artists
function getInfluentialArtists(): Artist[] {
  return artists
    .filter((a) => a.influences.length > 0 || a.influencedBy.length > 0)
    .slice(0, 6);
}

export function Home() {
  const featuredAlbums = getFeaturedAlbums();
  const influentialArtists = getInfluentialArtists();

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      {/* Hero Section */}
      <section className="text-center mb-16">
        <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent">
          Your Jazz Library
        </h1>
        <p className="text-xl text-zinc-400 max-w-2xl mx-auto mb-8">
          A curated guide to jazz history — from New Orleans to today.
          Explore albums, understand the music, and discover how artists shaped each other.
        </p>
        <div className="flex justify-center gap-4">
          <Link
            to="/timeline"
            className="px-6 py-3 bg-amber-500 text-black font-semibold rounded-lg hover:bg-amber-400 transition-colors"
          >
            Start with the Timeline
          </Link>
          <Link
            to="/albums"
            className="px-6 py-3 border border-zinc-700 text-zinc-300 rounded-lg hover:border-zinc-500 transition-colors"
          >
            Browse Albums
          </Link>
        </div>
      </section>

      {/* Learning Paths */}
      <section className="mb-16">
        <h2 className="text-2xl font-bold mb-6">Where to Begin</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link
            to="/era/bebop"
            className="p-6 rounded-xl bg-gradient-to-br from-lime-900/30 to-zinc-900 border border-lime-800/30 hover:border-lime-700/50 transition-all group"
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
            className="p-6 rounded-xl bg-gradient-to-br from-blue-900/30 to-zinc-900 border border-blue-800/30 hover:border-blue-700/50 transition-all group"
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
            className="p-6 rounded-xl bg-gradient-to-br from-purple-900/30 to-zinc-900 border border-purple-800/30 hover:border-purple-700/50 transition-all group"
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
          <h2 className="text-2xl font-bold">The Jazz Journey</h2>
          <Link to="/timeline" className="text-amber-400 hover:text-amber-300 text-sm">
            Full Timeline →
          </Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {eras.map((era) => (
            <Link
              key={era.id}
              to={`/era/${era.id}`}
              className="p-4 rounded-lg border border-zinc-800 hover:border-zinc-600 transition-all hover:scale-105"
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

      {/* Featured Albums by Era */}
      <section className="mb-16">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">One Album Per Era</h2>
          <Link to="/albums" className="text-amber-400 hover:text-amber-300 text-sm">
            View all {albums.length} albums →
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {featuredAlbums.map((album) => {
            const era = eras.find((e) => e.id === album.era);
            return (
              <Link
                key={album.id}
                to={`/album/${album.id}`}
                className="group p-4 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-600 transition-all"
              >
                <div className="mb-3 group-hover:scale-105 transition-transform">
                  <AlbumCover coverUrl={album.coverUrl} title={album.title} size="md" />
                </div>
                <h3 className="font-semibold text-white group-hover:text-amber-400 transition-colors text-sm">
                  {album.title}
                </h3>
                <p className="text-zinc-400 text-sm">{album.artist}</p>
                {era && (
                  <span
                    className="inline-block mt-2 px-2 py-0.5 text-xs rounded"
                    style={{ backgroundColor: era.color + '20', color: era.color }}
                  >
                    {era.name}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </section>

      {/* Artist Connections */}
      <section className="mb-16">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold">How Artists Connect</h2>
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
              className="p-4 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-amber-500/50 transition-all text-center group"
            >
              <div className="mx-auto mb-3">
                <ArtistPhoto
                  imageUrl={artist.imageUrl}
                  name={artist.name}
                  size="lg"
                  showInstrument={artist.instruments[0]}
                />
              </div>
              <h3 className="font-semibold text-white text-sm group-hover:text-amber-400 transition-colors">
                {artist.name}
              </h3>
              <p className="text-xs text-zinc-500 mt-1">
                {artist.instruments.slice(0, 1).join(', ')}
              </p>
            </Link>
          ))}
        </div>
      </section>

      {/* Educational Quote */}
      <section className="p-8 rounded-xl bg-gradient-to-r from-zinc-900 to-zinc-800 border border-zinc-700">
        <blockquote className="text-xl text-zinc-300 italic mb-4">
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

import { Link } from 'react-router-dom';
import erasData from '../data/eras.json';
import albumsData from '../data/albums.json';
import { AlbumCover } from '../components/AlbumCover';
import type { Era, Album } from '../types';

const eras = erasData as Era[];
const albums = albumsData as Album[];

export function Home() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      {/* Hero Section */}
      <section className="text-center mb-16">
        <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent">
          Your Jazz Journey Starts Here
        </h1>
        <p className="text-xl text-zinc-400 max-w-2xl mx-auto">
          Explore 100+ years of jazz history through essential albums, legendary artists,
          and the connections that shaped the music.
        </p>
      </section>

      {/* Era Timeline Preview */}
      <section className="mb-16">
        <h2 className="text-2xl font-bold mb-6">Explore by Era</h2>
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
            </Link>
          ))}
        </div>
      </section>

      {/* Featured Albums */}
      <section className="mb-16">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">Essential Albums</h2>
          <Link to="/albums" className="text-amber-400 hover:text-amber-300 text-sm">
            View all →
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {albums.slice(0, 6).map((album) => (
            <Link
              key={album.id}
              to={`/album/${album.id}`}
              className="group p-6 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-600 transition-all"
            >
              <div className="mb-4 group-hover:scale-105 transition-transform">
                <AlbumCover coverUrl={album.coverUrl} title={album.title} size="md" />
              </div>
              <h3 className="font-semibold text-white group-hover:text-amber-400 transition-colors">
                {album.title}
              </h3>
              <p className="text-zinc-400">{album.artist}</p>
              <p className="text-sm text-zinc-500">{album.year}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Quick Stats */}
      <section className="grid grid-cols-3 gap-6 text-center">
        <div className="p-6 rounded-lg bg-zinc-900 border border-zinc-800">
          <div className="text-4xl font-bold text-amber-400">{eras.length}</div>
          <div className="text-zinc-400">Jazz Eras</div>
        </div>
        <div className="p-6 rounded-lg bg-zinc-900 border border-zinc-800">
          <div className="text-4xl font-bold text-amber-400">100+</div>
          <div className="text-zinc-400">Essential Albums</div>
        </div>
        <div className="p-6 rounded-lg bg-zinc-900 border border-zinc-800">
          <div className="text-4xl font-bold text-amber-400">100+</div>
          <div className="text-zinc-400">Years of History</div>
        </div>
      </section>
    </div>
  );
}

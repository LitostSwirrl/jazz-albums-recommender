import { Link } from 'react-router-dom';
import albumsData from '../data/albums.json';
import erasData from '../data/eras.json';
import type { Album, Era } from '../types';

const albums = albumsData as Album[];
const eras = erasData as Era[];

export function Albums() {
  const getEra = (eraId: string) => eras.find((e) => e.id === eraId);

  // Sort albums by year
  const sortedAlbums = [...albums].sort((a, b) => a.year - b.year);

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <h1 className="text-4xl font-bold mb-2">Essential Albums</h1>
      <p className="text-zinc-400 mb-8">
        100 albums that define jazz history
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {sortedAlbums.map((album) => {
          const era = getEra(album.era);
          return (
            <Link
              key={album.id}
              to={`/album/${album.id}`}
              className="group p-6 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-600 transition-all"
            >
              <div className="w-full aspect-square bg-zinc-800 rounded-lg flex items-center justify-center text-6xl mb-4 group-hover:scale-105 transition-transform">
                💿
              </div>

              <h2 className="text-lg font-bold text-white group-hover:text-amber-400 transition-colors">
                {album.title}
              </h2>

              <p className="text-zinc-400">{album.artist}</p>

              <div className="flex items-center justify-between mt-3">
                <span className="text-zinc-500">{album.year}</span>
                {era && (
                  <span
                    className="px-2 py-0.5 text-xs rounded"
                    style={{
                      backgroundColor: era.color + '30',
                      color: era.color
                    }}
                  >
                    {era.name.split(' ')[0]}
                  </span>
                )}
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

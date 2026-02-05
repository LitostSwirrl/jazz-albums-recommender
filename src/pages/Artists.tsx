import { Link } from 'react-router-dom';
import artistsData from '../data/artists.json';
import erasData from '../data/eras.json';
import type { Artist, Era } from '../types';
import { ArtistPhoto } from '../components/ArtistPhoto';

const artists = artistsData as Artist[];
const eras = erasData as Era[];

export function Artists() {
  const getEraColor = (eraId: string) => {
    const era = eras.find((e) => e.id === eraId);
    return era?.color || '#888';
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <h1 className="text-4xl font-bold mb-2">Jazz Artists</h1>
      <p className="text-zinc-400 mb-8">
        Discover the legends who shaped jazz history
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {artists.map((artist) => (
          <Link
            key={artist.id}
            to={`/artist/${artist.id}`}
            className="group p-6 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-600 transition-all"
          >
            <div className="mb-4 group-hover:scale-110 transition-transform">
              <ArtistPhoto
                imageUrl={artist.imageUrl}
                name={artist.name}
                size="lg"
                showInstrument={artist.instruments[0]}
              />
            </div>

            <h2 className="text-xl font-bold text-white group-hover:text-amber-400 transition-colors">
              {artist.name}
            </h2>

            <p className="text-zinc-500 text-sm mb-3">
              {artist.birthYear}–{artist.deathYear || 'present'}
            </p>

            <p className="text-zinc-400 text-sm mb-4">
              {artist.instruments.join(', ')}
            </p>

            <div className="flex flex-wrap gap-1">
              {artist.eras.map((eraId) => (
                <span
                  key={eraId}
                  className="px-2 py-0.5 text-xs rounded"
                  style={{
                    backgroundColor: getEraColor(eraId) + '30',
                    color: getEraColor(eraId)
                  }}
                >
                  {eras.find((e) => e.id === eraId)?.name.split(' ')[0]}
                </span>
              ))}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

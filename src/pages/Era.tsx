import { useParams, Link } from 'react-router-dom';
import erasData from '../data/eras.json';
import artistsData from '../data/artists.json';
import albumsData from '../data/albums.json';
import type { Era as EraType, Artist, Album } from '../types';

const eras = erasData as EraType[];
const artists = artistsData as Artist[];
const albums = albumsData as Album[];

export function Era() {
  const { id } = useParams<{ id: string }>();
  const era = eras.find((e) => e.id === id);

  if (!era) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12 text-center">
        <h1 className="text-2xl font-bold text-red-400">Era not found</h1>
        <Link to="/eras" className="text-amber-400 hover:underline mt-4 inline-block">
          ← Back to Eras
        </Link>
      </div>
    );
  }

  const eraArtists = artists.filter((a) => a.eras.includes(era.id));
  const eraAlbums = albums.filter((a) => a.era === era.id);

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link to="/eras" className="text-zinc-500 hover:text-zinc-300">
          Eras
        </Link>
        <span className="text-zinc-600 mx-2">/</span>
        <span className="text-zinc-300">{era.name}</span>
      </div>

      {/* Header */}
      <header
        className="p-8 rounded-lg mb-8"
        style={{ backgroundColor: era.color + '20', borderLeft: `4px solid ${era.color}` }}
      >
        <h1 className="text-4xl font-bold mb-2">{era.name}</h1>
        <p className="text-xl text-zinc-400 font-mono">{era.period}</p>
      </header>

      {/* Description */}
      <section className="mb-12">
        <p className="text-lg text-zinc-300 leading-relaxed">{era.description}</p>
      </section>

      {/* Characteristics */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold mb-4">Characteristics</h2>
        <div className="flex flex-wrap gap-3">
          {era.characteristics.map((char) => (
            <span
              key={char}
              className="px-4 py-2 rounded-full text-sm"
              style={{ backgroundColor: era.color + '30', color: era.color }}
            >
              {char}
            </span>
          ))}
        </div>
      </section>

      {/* Key Artists */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold mb-6">Key Artists</h2>
        {eraArtists.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {eraArtists.map((artist) => (
              <Link
                key={artist.id}
                to={`/artist/${artist.id}`}
                className="p-4 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-600 transition-all group"
              >
                <h3 className="font-semibold text-white group-hover:text-amber-400 transition-colors">
                  {artist.name}
                </h3>
                <p className="text-sm text-zinc-500">
                  {artist.instruments.join(', ')}
                </p>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-zinc-500">No artists listed yet for this era.</p>
        )}
      </section>

      {/* Albums from this Era */}
      <section>
        <h2 className="text-2xl font-bold mb-6">Essential Albums</h2>
        {eraAlbums.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {eraAlbums.map((album) => (
              <Link
                key={album.id}
                to={`/album/${album.id}`}
                className="p-4 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-600 transition-all group"
              >
                <div className="text-4xl mb-3">💿</div>
                <h3 className="font-semibold text-white group-hover:text-amber-400 transition-colors">
                  {album.title}
                </h3>
                <p className="text-zinc-400">{album.artist}</p>
                <p className="text-sm text-zinc-500">{album.year}</p>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-zinc-500">No albums listed yet for this era.</p>
        )}
      </section>
    </div>
  );
}

import { Link } from 'react-router-dom';
import erasData from '../data/eras.json';
import albumsData from '../data/albums.json';
import artistsData from '../data/artists.json';
import type { Era, Album, Artist, EraId } from '../types';

const eras = erasData as Era[];
const albums = albumsData as Album[];
const artists = artistsData as Artist[];

const eraColors: Record<string, string> = {
  'early-jazz': '#f59e0b',
  'swing': '#eab308',
  'bebop': '#84cc16',
  'cool-jazz': '#22d3ee',
  'hard-bop': '#3b82f6',
  'free-jazz': '#a855f7',
  'fusion': '#ec4899',
  'contemporary': '#f43f5e',
};

function getEraStats(eraId: EraId) {
  const eraAlbums = albums.filter((a) => a.era === eraId);
  const eraArtists = artists.filter((a) => a.eras.includes(eraId));
  return { albumCount: eraAlbums.length, artistCount: eraArtists.length };
}

function getKeyArtists(eraId: EraId): Artist[] {
  return artists
    .filter((a) => a.eras.includes(eraId))
    .slice(0, 5);
}

function getKeyAlbums(eraId: EraId): Album[] {
  return albums
    .filter((a) => a.era === eraId)
    .slice(0, 3);
}

export function Timeline() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-bold mb-4">Jazz Through Time</h1>
        <p className="text-xl text-zinc-400 max-w-2xl mx-auto">
          From New Orleans to the present day, explore 100+ years of jazz evolution.
          Each era built on what came before while pushing music into new territory.
        </p>
      </div>

      {/* Visual Timeline */}
      <div className="relative">
        {/* Center line */}
        <div className="absolute left-1/2 top-0 bottom-0 w-1 bg-gradient-to-b from-amber-500 via-purple-500 to-rose-500 transform -translate-x-1/2 hidden md:block" />

        {eras.map((era, index) => {
          const stats = getEraStats(era.id);
          const keyArtists = getKeyArtists(era.id);
          const keyAlbums = getKeyAlbums(era.id);
          const isLeft = index % 2 === 0;
          const color = eraColors[era.id];

          return (
            <div
              key={era.id}
              className={`relative mb-12 md:mb-16 ${
                isLeft ? 'md:pr-[52%]' : 'md:pl-[52%]'
              }`}
            >
              {/* Timeline dot */}
              <div
                className="hidden md:block absolute left-1/2 top-8 w-6 h-6 rounded-full border-4 transform -translate-x-1/2 z-10"
                style={{ backgroundColor: color, borderColor: '#18181b' }}
              />

              {/* Era card */}
              <div
                className="p-6 rounded-xl border-2 bg-zinc-900/80 backdrop-blur transition-all hover:scale-[1.02]"
                style={{ borderColor: color }}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <Link
                      to={`/era/${era.id}`}
                      className="text-2xl font-bold hover:underline"
                      style={{ color }}
                    >
                      {era.name}
                    </Link>
                    <div className="text-zinc-500 font-mono text-sm mt-1">
                      {era.period}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold" style={{ color }}>
                      {stats.albumCount}
                    </div>
                    <div className="text-xs text-zinc-500">albums</div>
                  </div>
                </div>

                {/* Description */}
                <p className="text-zinc-300 mb-4 leading-relaxed">
                  {era.description}
                </p>

                {/* Characteristics */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {era.characteristics.slice(0, 4).map((char) => (
                    <span
                      key={char}
                      className="px-2 py-1 text-xs rounded-full"
                      style={{ backgroundColor: color + '20', color }}
                    >
                      {char}
                    </span>
                  ))}
                </div>

                {/* Key Artists */}
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-zinc-400 mb-2">
                    Key Artists
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {keyArtists.map((artist) => (
                      <Link
                        key={artist.id}
                        to={`/artist/${artist.id}`}
                        className="px-3 py-1 text-sm rounded-full bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition-colors"
                      >
                        {artist.name}
                      </Link>
                    ))}
                  </div>
                </div>

                {/* Key Albums */}
                <div>
                  <h4 className="text-sm font-semibold text-zinc-400 mb-2">
                    Essential Albums
                  </h4>
                  <div className="space-y-2">
                    {keyAlbums.map((album) => (
                      <Link
                        key={album.id}
                        to={`/album/${album.id}`}
                        className="flex items-center gap-3 p-2 rounded-lg bg-zinc-800/50 hover:bg-zinc-800 transition-colors group"
                      >
                        <div
                          className="w-10 h-10 rounded bg-zinc-700 flex items-center justify-center text-lg"
                        >
                          💿
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-white group-hover:text-amber-400 truncate transition-colors">
                            {album.title}
                          </div>
                          <div className="text-xs text-zinc-500 truncate">
                            {album.artist} · {album.year}
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>

                {/* Explore Link */}
                <Link
                  to={`/era/${era.id}`}
                  className="inline-flex items-center gap-1 mt-4 text-sm font-medium hover:underline"
                  style={{ color }}
                >
                  Explore {era.name} →
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      {/* Era Connections */}
      <div className="mt-16 p-8 rounded-xl bg-zinc-900 border border-zinc-800">
        <h2 className="text-2xl font-bold mb-6 text-center">How Eras Connect</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-lg bg-zinc-800/50">
            <div className="text-amber-400 font-semibold mb-2">Early Jazz → Swing</div>
            <p className="text-sm text-zinc-400">
              New Orleans pioneers created the vocabulary; big bands scaled it up for dance halls.
            </p>
          </div>
          <div className="p-4 rounded-lg bg-zinc-800/50">
            <div className="text-green-400 font-semibold mb-2">Swing → Bebop</div>
            <p className="text-sm text-zinc-400">
              Young rebels turned dance music into art music, emphasizing virtuosity and complexity.
            </p>
          </div>
          <div className="p-4 rounded-lg bg-zinc-800/50">
            <div className="text-cyan-400 font-semibold mb-2">Bebop → Cool/Hard Bop</div>
            <p className="text-sm text-zinc-400">
              Two paths diverged: West Coast cool sophistication vs. East Coast blues-drenched intensity.
            </p>
          </div>
          <div className="p-4 rounded-lg bg-zinc-800/50">
            <div className="text-purple-400 font-semibold mb-2">Hard Bop → Free Jazz</div>
            <p className="text-sm text-zinc-400">
              The ultimate rebellion: abandoning chord changes entirely for pure expression.
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="mt-12 flex justify-center gap-4">
        <Link
          to="/influence"
          className="px-6 py-3 rounded-lg bg-amber-500 text-black font-semibold hover:bg-amber-400 transition-colors"
        >
          View Influence Network →
        </Link>
        <Link
          to="/albums"
          className="px-6 py-3 rounded-lg border border-zinc-700 text-zinc-300 hover:border-zinc-500 transition-colors"
        >
          Browse All Albums
        </Link>
      </div>
    </div>
  );
}

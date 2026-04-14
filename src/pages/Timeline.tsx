import { Link } from 'react-router-dom';
import erasData from '../data/eras.json';
import albumsData from '../data/albums.json';
import artistsData from '../data/artists.json';
import { SEO } from '../components/SEO';
import { AlbumCover } from '../components/AlbumCover';
import { track } from '../utils/analytics';
import type { Era, Album, Artist, EraId } from '../types';

const eras = erasData as Era[];
const albums = albumsData as Album[];
const artists = artistsData as Artist[];

const eraColors: Record<string, string> = {
  'early-jazz': '#6b6358',
  'swing': '#7a7168',
  'bebop': '#897f75',
  'cool-jazz': '#988d83',
  'hard-bop': '#a79b90',
  'free-jazz': '#b6a99d',
  'fusion': '#c5b8ab',
  'contemporary': '#d4c7b9',
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
    <div className="max-w-6xl mx-auto px-4 py-12 page-enter">
      <SEO
        title="Jazz Timeline"
        description="Explore a century of jazz evolution from New Orleans to the present day. Discover how each era built on what came before while pushing music into new territory."
      />
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-bold mb-4 font-display text-charcoal">Jazz Through Time</h1>
      </div>

      {/* Visual Timeline */}
      <div className="relative">
        {/* Center line */}
        <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-charcoal transform -translate-x-1/2 hidden md:block" />

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
                style={{ backgroundColor: color, borderColor: '#1a1917' }}
              />

              {/* Era card */}
              <div
                className="p-6 rounded-xl border-2 bg-surface shadow-card transition-all hover:shadow-card-hover hover:scale-[1.02]"
                style={{ borderColor: color }}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <Link
                      to={`/era/${era.id}`}
                      onClick={() => track('era_click', { era_id: era.id })}
                      className="text-2xl font-bold font-heading hover:underline"
                      style={{ color }}
                    >
                      {era.name}
                    </Link>
                    <div className="text-warm-gray font-mono text-sm mt-1">
                      {era.period}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold" style={{ color }}>
                      {stats.albumCount}
                    </div>
                    <div className="text-xs text-warm-gray">albums</div>
                  </div>
                </div>

                {/* Description */}
                <p className="text-charcoal mb-4 leading-relaxed">
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
                  <h4 className="text-sm font-semibold text-warm-gray mb-2">
                    Key Artists
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {keyArtists.map((artist) => (
                      <Link
                        key={artist.id}
                        to={`/artist/${artist.id}`}
                        onClick={() => track('artist_click', { artist_id: artist.id, source: 'timeline' })}
                        className="px-3 py-1 text-sm rounded-full bg-surface border border-border text-charcoal hover:text-coral transition-colors"
                      >
                        {artist.name}
                      </Link>
                    ))}
                  </div>
                </div>

                {/* Key Albums */}
                <div>
                  <h4 className="text-sm font-semibold text-warm-gray mb-2">
                    Essential Albums
                  </h4>
                  <div className="space-y-2">
                    {keyAlbums.map((album) => (
                      <Link
                        key={album.id}
                        to={`/album/${album.id}`}
                        onClick={() => track('album_click', { album_id: album.id, source: 'album_grid' })}
                        className="flex items-center gap-3 p-2 rounded-lg bg-surface hover:bg-border transition-colors group"
                      >
                        <div className="w-10 h-10 flex-shrink-0">
                          <AlbumCover coverUrl={album.coverUrl} title={album.title} size="sm" pixelWidth={200} priority />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-charcoal group-hover:text-coral truncate transition-colors">
                            {album.title}
                          </div>
                          <div className="text-xs text-warm-gray truncate">
                            {album.artist} &middot; {album.year}
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
                  Explore {era.name} &rarr;
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      {/* Era Connections */}
      <div className="mt-16 p-8 rounded-xl bg-surface border border-border shadow-card">
        <h2 className="text-2xl font-bold mb-6 text-center font-heading text-charcoal">How Eras Connect</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-lg bg-surface border border-border">
            <div className="text-coral font-semibold mb-2">Early Jazz &rarr; Swing</div>
            <p className="text-sm text-warm-gray">
              New Orleans pioneers created the vocabulary; big bands scaled it up for dance halls.
            </p>
          </div>
          <div className="p-4 rounded-lg bg-surface border border-border">
            <div className="text-teal font-semibold mb-2">Swing &rarr; Bebop</div>
            <p className="text-sm text-warm-gray">
              Young rebels turned dance music into art music, emphasizing virtuosity and complexity.
            </p>
          </div>
          <div className="p-4 rounded-lg bg-surface border border-border">
            <div className="text-teal font-semibold mb-2">Bebop &rarr; Cool/Hard Bop</div>
            <p className="text-sm text-warm-gray">
              Two paths diverged: West Coast cool sophistication vs. East Coast blues-drenched intensity.
            </p>
          </div>
          <div className="p-4 rounded-lg bg-surface border border-border">
            <div className="text-coral font-semibold mb-2">Hard Bop &rarr; Free Jazz</div>
            <p className="text-sm text-warm-gray">
              The ultimate rebellion: abandoning chord changes entirely for pure expression.
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="mt-12 flex flex-wrap justify-center gap-4">
        <Link
          to="/context"
          className="px-6 py-3 rounded-xl bg-coral text-white font-semibold hover:bg-coral/90 transition-colors"
        >
          Jazz & Society &rarr;
        </Link>
        <Link
          to="/influence"
          className="px-6 py-3 rounded-xl border border-border text-charcoal hover:border-charcoal transition-colors"
        >
          Influence Network &rarr;
        </Link>
        <Link
          to="/albums"
          className="px-6 py-3 rounded-xl border border-border text-charcoal hover:border-charcoal transition-colors"
        >
          Browse All Albums
        </Link>
      </div>
    </div>
  );
}

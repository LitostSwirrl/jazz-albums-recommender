import { useParams, Link } from 'react-router-dom';
import { useState, useMemo } from 'react';
import erasData from '../data/eras.json';
import artistsData from '../data/artists.json';
import albumsData from '../data/albums.json';
import { AlbumCover } from '../components/AlbumCover';
import { HistoricalEventCard } from '../components/context/HistoricalEventCard';
import { SEO } from '../components/SEO';
import { Pagination } from '../components/Pagination';
import { getEventsByEra } from '../utils/historicalContext';
import { track } from '../utils/analytics';
import type { Era as EraType, Artist, Album, EraId } from '../types';

const ERA_ALBUMS_PER_PAGE = 36;

const eras = erasData as EraType[];
const artists = artistsData as Artist[];
const albums = albumsData as Album[];

export function Era() {
  const { id } = useParams<{ id: string }>();
  const era = eras.find((e) => e.id === id);

  if (!era) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12 text-center">
        <h1 className="text-2xl font-bold text-red-500">Era not found</h1>
        <Link to="/eras" className="text-coral hover:underline mt-4 inline-block">
          &larr; Back to Eras
        </Link>
      </div>
    );
  }

  const eraArtists = artists.filter((a) => a.eras.includes(era.id));
  const eraAlbums = useMemo(
    () => albums.filter((a) => a.era === era.id),
    [era.id]
  );
  const [albumPage, setAlbumPage] = useState(1);

  // Reset page when navigating between eras
  const [prevEraId, setPrevEraId] = useState(era.id);
  if (era.id !== prevEraId) {
    setPrevEraId(era.id);
    setAlbumPage(1);
  }

  const albumTotalPages = Math.ceil(eraAlbums.length / ERA_ALBUMS_PER_PAGE);
  const paginatedAlbums = useMemo(() => {
    const start = (albumPage - 1) * ERA_ALBUMS_PER_PAGE;
    return eraAlbums.slice(start, start + ERA_ALBUMS_PER_PAGE);
  }, [eraAlbums, albumPage]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 page-enter">
      <SEO
        title={`${era.name} Era (${era.period})`}
        description={era.description.slice(0, 160)}
      />
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link to="/eras" className="text-warm-gray hover:text-charcoal">
          Eras
        </Link>
        <span className="text-warm-gray mx-2">/</span>
        <span className="text-charcoal">{era.name}</span>
      </div>

      {/* Header */}
      <header
        className="p-8 rounded-lg mb-8"
        style={{ backgroundColor: era.color + '15', borderLeft: `4px solid ${era.color}` }}
      >
        <h1 className="text-4xl mb-2 font-display text-charcoal">{era.name}</h1>
        <p className="text-xl text-warm-gray font-mono">{era.period}</p>
      </header>

      {/* Description */}
      <section className="mb-12">
        <p className="text-lg text-charcoal leading-relaxed">{era.description}</p>
      </section>

      {/* Characteristics */}
      <section className="mb-12">
        <h2 className="text-2xl mb-4 font-heading text-charcoal">Characteristics</h2>
        <div className="flex flex-wrap gap-3">
          {era.characteristics.map((char) => (
            <span
              key={char}
              className="px-4 py-2 rounded-full text-sm"
              style={{ backgroundColor: era.color + '20', color: era.color }}
            >
              {char}
            </span>
          ))}
        </div>
      </section>

      {/* Historical Context */}
      <EraHistoricalContext eraId={era.id} />

      {/* Key Artists */}
      <section className="mb-12">
        <h2 className="text-2xl mb-6 font-heading text-charcoal">Key Artists</h2>
        {eraArtists.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {eraArtists.map((artist) => (
              <Link
                key={artist.id}
                to={`/artist/${artist.id}`}
                onClick={() => track('artist_click', { artist_id: artist.id, source: 'era_page' })}
                className="p-4 rounded-lg bg-surface shadow-card hover:shadow-card-hover transition-all group"
              >
                <h3 className="font-semibold text-charcoal font-heading group-hover:text-coral transition-colors">
                  {artist.name}
                </h3>
                <p className="text-sm text-warm-gray">
                  {(artist.instruments || []).join(', ')}
                </p>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-warm-gray">No artists listed yet for this era.</p>
        )}
      </section>

      {/* Albums from this Era */}
      <section id="essential-albums">
        <h2 className="text-2xl mb-6 font-heading text-charcoal">
          Essential Albums
          <span className="text-base font-normal text-warm-gray ml-3">
            {eraAlbums.length} albums
          </span>
        </h2>
        {eraAlbums.length > 0 ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {paginatedAlbums.map((album) => (
                <Link
                  key={album.id}
                  to={`/album/${album.id}`}
                  onClick={() => track('album_click', { album_id: album.id, source: 'album_grid' })}
                  className="p-4 rounded-lg bg-surface shadow-card hover:shadow-card-hover transition-all group"
                >
                  <div className="mb-3 group-hover:scale-105 transition-transform">
                    <AlbumCover coverUrl={album.coverUrl} title={album.title} size="sm" />
                  </div>
                  <h3 className="font-semibold text-charcoal font-heading group-hover:text-coral transition-colors">
                    {album.title}
                  </h3>
                  <p className="text-warm-gray">{album.artist}</p>
                  <p className="text-sm text-warm-gray">{album.year}</p>
                </Link>
              ))}
            </div>
            <Pagination
              currentPage={albumPage}
              totalPages={albumTotalPages}
              onPageChange={(page) => {
                setAlbumPage(page);
                document.getElementById('essential-albums')?.scrollIntoView({ behavior: 'smooth' });
              }}
            />
          </>
        ) : (
          <p className="text-warm-gray">No albums listed yet for this era.</p>
        )}
      </section>
    </div>
  );
}

const INITIAL_VISIBLE = 3;

function EraHistoricalContext({ eraId }: { eraId: EraId }) {
  const events = getEventsByEra(eraId);
  const [expanded, setExpanded] = useState(false);

  if (events.length === 0) return null;

  const visible = expanded ? events : events.slice(0, INITIAL_VISIBLE);
  const remaining = events.length - INITIAL_VISIBLE;

  return (
    <section className="mb-12">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-heading text-charcoal">Historical Context</h2>
        <Link
          to="/context"
          className="text-coral hover:text-coral/80 text-sm"
        >
          Full Timeline &rarr;
        </Link>
      </div>
      <div className="space-y-4">
        {visible.map((event) => (
          <HistoricalEventCard key={event.id} event={event} />
        ))}
      </div>
      {remaining > 0 && !expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="mt-4 text-sm text-coral hover:text-coral/80 transition-colors"
        >
          Show {remaining} more event{remaining > 1 ? 's' : ''} &rarr;
        </button>
      )}
    </section>
  );
}

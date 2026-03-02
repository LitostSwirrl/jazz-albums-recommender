import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import artistsData from '../data/artists.json';
import erasData from '../data/eras.json';
import type { Artist, Era } from '../types';
import { ArtistPhoto } from '../components/ArtistPhoto';
import { SEO } from '../components/SEO';
import { Pagination } from '../components/Pagination';

const ARTISTS_PER_PAGE = 24;

const artists = artistsData as Artist[];
const eras = erasData as Era[];

export function Artists() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEra, setSelectedEra] = useState<string | null>(null);
  const [selectedInstrument, setSelectedInstrument] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  const getEraColor = (eraId: string) => {
    const era = eras.find((e) => e.id === eraId);
    return era?.color || '#888';
  };

  // Top 8 instruments by frequency
  const topInstruments = useMemo(() => {
    const counts = new Map<string, number>();
    artists.forEach((artist) => {
      artist.instruments.forEach((inst) =>
        counts.set(inst, (counts.get(inst) ?? 0) + 1)
      );
    });
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([inst]) => inst);
  }, []);

  const filteredArtists = useMemo(() => {
    let result = [...artists];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (artist) =>
          artist.name.toLowerCase().includes(q) ||
          artist.instruments.some((i) => i.toLowerCase().includes(q))
      );
    }

    if (selectedEra) {
      result = result.filter((artist) => artist.eras.includes(selectedEra as typeof artist.eras[number]));
    }

    if (selectedInstrument) {
      result = result.filter((artist) =>
        artist.instruments.some((i) => i.toLowerCase() === selectedInstrument.toLowerCase())
      );
    }

    return result;
  }, [searchQuery, selectedEra, selectedInstrument]);

  const totalPages = Math.ceil(filteredArtists.length / ARTISTS_PER_PAGE);
  const paginatedArtists = useMemo(() => {
    const start = (currentPage - 1) * ARTISTS_PER_PAGE;
    return filteredArtists.slice(start, start + ARTISTS_PER_PAGE);
  }, [filteredArtists, currentPage]);

  const hasActiveFilters = !!(searchQuery || selectedEra || selectedInstrument);

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 page-enter">
      <SEO
        title="Jazz Artists"
        description={`Discover the legends who shaped jazz history. Explore profiles of ${artists.length} influential jazz musicians from Louis Armstrong to Kamasi Washington.`}
      />
      <h1 className="text-4xl font-bold mb-2 font-display text-charcoal">Jazz Artists</h1>
      <p className="text-warm-gray mb-6">
        {filteredArtists.length} {hasActiveFilters ? 'artists matching your filters' : 'legends who shaped jazz history'}
      </p>

      {/* Search Bar */}
      <div className="mb-6 relative">
        <svg
          className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-warm-gray"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
          placeholder="Search by name or instrument..."
          aria-label="Search artists"
          className="w-full pl-12 pr-4 py-3 bg-surface border border-border rounded-xl text-charcoal placeholder:text-warm-gray focus:outline-none focus:border-coral focus:ring-1 focus:ring-coral transition-colors"
        />
        {searchQuery && (
          <button
            onClick={() => { setSearchQuery(''); setCurrentPage(1); }}
            aria-label="Clear search"
            className="absolute right-4 top-1/2 -translate-y-1/2 text-warm-gray hover:text-charcoal transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Era Filter */}
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-warm-gray mb-2">Filter by Era</h3>
        <div className="flex flex-wrap gap-2">
          {eras.map((era) => (
            <button
              key={era.id}
              onClick={() => { setSelectedEra(selectedEra === era.id ? null : era.id); setCurrentPage(1); }}
              className={`px-3 py-1.5 text-sm rounded-full border transition-all ${
                selectedEra === era.id
                  ? 'border-transparent text-white font-medium'
                  : 'border-border text-warm-gray hover:border-charcoal hover:text-charcoal'
              }`}
              style={selectedEra === era.id ? { backgroundColor: era.color } : {}}
            >
              {era.name.split(' ')[0]}
            </button>
          ))}
        </div>
      </div>

      {/* Instrument Filter */}
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-warm-gray mb-2">Filter by Instrument</h3>
        <div className="flex flex-wrap gap-2">
          {topInstruments.map((inst) => (
            <button
              key={inst}
              onClick={() => { setSelectedInstrument(selectedInstrument === inst ? null : inst); setCurrentPage(1); }}
              className={`px-3 py-1.5 text-sm rounded-full border transition-all ${
                selectedInstrument === inst
                  ? 'bg-coral border-coral text-white font-medium'
                  : 'border-border text-warm-gray hover:border-charcoal hover:text-charcoal'
              }`}
            >
              {inst}
            </button>
          ))}
        </div>
      </div>

      {/* Active Filters */}
      {hasActiveFilters && (
        <div className="mb-6 flex items-center gap-3 flex-wrap">
          <span className="text-sm text-warm-gray">Active filters:</span>
          {searchQuery && (
            <span className="px-2 py-1 text-xs rounded-full bg-border-light text-charcoal">
              &ldquo;{searchQuery}&rdquo;
            </span>
          )}
          {selectedEra && (
            <span
              className="px-2 py-1 text-xs rounded-full"
              style={{
                backgroundColor: getEraColor(selectedEra) + '30',
                color: getEraColor(selectedEra),
              }}
            >
              {eras.find((e) => e.id === selectedEra)?.name}
            </span>
          )}
          {selectedInstrument && (
            <span className="px-2 py-1 text-xs rounded-full bg-coral/20 text-coral">
              {selectedInstrument}
            </span>
          )}
          <button
            onClick={() => {
              setSearchQuery('');
              setSelectedEra(null);
              setSelectedInstrument(null);
              setCurrentPage(1);
            }}
            className="text-sm text-warm-gray hover:text-charcoal underline"
          >
            Clear all
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {paginatedArtists.map((artist) => (
          <Link
            key={artist.id}
            to={`/artist/${artist.id}`}
            className="group p-6 rounded-xl bg-surface shadow-card hover:shadow-card-hover hover:-translate-y-1 transition-all duration-300"
          >
            <div className="mb-4 group-hover:scale-110 transition-transform duration-300">
              <ArtistPhoto
                imageUrl={artist.imageUrl}
                name={artist.name}
                size="lg"
              />
            </div>

            <h2 className="text-xl font-bold text-charcoal font-heading group-hover:text-coral transition-colors">
              {artist.name}
            </h2>

            <p className="text-warm-gray text-sm mb-3">
              {artist.birthYear}&ndash;{artist.deathYear || 'present'}
            </p>

            <p className="text-warm-gray text-sm mb-4">
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

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => {
          setCurrentPage(page);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
      />

      {/* Empty State */}
      {filteredArtists.length === 0 && (
        <div className="text-center py-12">
          <p className="text-warm-gray">No artists match your filters.</p>
          <button
            onClick={() => {
              setSearchQuery('');
              setSelectedEra(null);
              setSelectedInstrument(null);
              setCurrentPage(1);
            }}
            className="mt-4 text-coral hover:text-coral/80"
          >
            Clear filters
          </button>
        </div>
      )}
    </div>
  );
}

import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import albumsData from '../data/albums.json';
import erasData from '../data/eras.json';
import { AlbumCover } from '../components/AlbumCover';
import { SEO } from '../components/SEO';
import { Pagination } from '../components/Pagination';
import { normalizeSearchStr } from '../utils/strings';
import type { Album, Era } from '../types';

const albums = albumsData as Album[];
const eras = erasData as Era[];

const ALBUMS_PER_PAGE = 36;

type SortOption = 'year-asc' | 'year-desc' | 'artist-az' | 'title-az';

const SORT_OPTION_VALUES = ['year-asc', 'year-desc', 'artist-az', 'title-az'] as const;

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'year-asc', label: 'Year (oldest)' },
  { value: 'year-desc', label: 'Year (newest)' },
  { value: 'artist-az', label: 'Artist A\u2013Z' },
  { value: 'title-az', label: 'Title A\u2013Z' },
];

function isValidSortOption(value: string | null): value is SortOption {
  return value !== null && (SORT_OPTION_VALUES as readonly string[]).includes(value);
}

function sortAlbums(list: Album[], sort: SortOption): Album[] {
  const sorted = [...list];
  switch (sort) {
    case 'year-asc':
      return sorted.sort((a, b) => a.year - b.year);
    case 'year-desc':
      return sorted.sort((a, b) => b.year - a.year);
    case 'artist-az':
      return sorted.sort((a, b) => a.artist.localeCompare(b.artist));
    case 'title-az':
      return sorted.sort((a, b) => a.title.localeCompare(b.title));
    default: {
      const _exhaustive: never = sort;
      return _exhaustive;
    }
  }
}

export function Albums() {
  const [searchParams, setSearchParams] = useSearchParams();
  const topRef = useRef<HTMLDivElement>(null);

  const [searchQuery, setSearchQuery] = useState(searchParams.get('q') ?? '');
  const [selectedGenre, setSelectedGenre] = useState<string | null>(
    searchParams.get('genre')
  );
  const [selectedEra, setSelectedEra] = useState<string | null>(
    searchParams.get('era')
  );
  const [selectedLabel, setSelectedLabel] = useState<string | null>(
    searchParams.get('label')
  );
  const sortParam = searchParams.get('sort');
  const [sortBy, setSortBy] = useState<SortOption>(
    isValidSortOption(sortParam) ? sortParam : 'year-asc'
  );
  const [currentPage, setCurrentPage] = useState(
    parseInt(searchParams.get('page') ?? '1', 10)
  );
  const [showAllGenres, setShowAllGenres] = useState(false);
  const [showAllLabels, setShowAllLabels] = useState(false);

  const getEra = (eraId: string) => eras.find((e) => e.id === eraId);

  // Genres sorted by frequency
  const genresByFrequency = useMemo(() => {
    const counts = new Map<string, number>();
    albums.forEach((album) => {
      album.genres.forEach((genre) => counts.set(genre, (counts.get(genre) ?? 0) + 1));
    });
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([genre]) => genre);
  }, []);

  // Labels sorted by frequency
  const labelsByFrequency = useMemo(() => {
    const counts = new Map<string, number>();
    albums.forEach((album) => counts.set(album.label, (counts.get(album.label) ?? 0) + 1));
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([label]) => label);
  }, []);

  const visibleGenres = showAllGenres ? genresByFrequency : genresByFrequency.slice(0, 12);
  const visibleLabels = showAllLabels ? labelsByFrequency : labelsByFrequency.slice(0, 12);

  // Debounce search URL sync
  const searchParamsRef = useRef(searchParams);
  searchParamsRef.current = searchParams;

  useEffect(() => {
    const timer = setTimeout(() => {
      const newParams = new URLSearchParams(searchParamsRef.current);
      if (searchQuery) {
        newParams.set('q', searchQuery);
      } else {
        newParams.delete('q');
      }
      newParams.delete('page');
      setCurrentPage(1);
      setSearchParams(newParams, { replace: true });
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, setSearchParams]);

  // Filter + sort albums
  const filteredAlbums = useMemo(() => {
    let result = [...albums];

    if (searchQuery.trim()) {
      const q = normalizeSearchStr(searchQuery);
      result = result.filter(
        (album) =>
          normalizeSearchStr(album.title).includes(q) ||
          normalizeSearchStr(album.artist).includes(q) ||
          normalizeSearchStr(album.label).includes(q) ||
          album.genres.some((g) => normalizeSearchStr(g).includes(q))
      );
    }

    if (selectedGenre) {
      result = result.filter((album) =>
        album.genres.some((g) => g.toLowerCase() === selectedGenre.toLowerCase())
      );
    }

    if (selectedEra) {
      result = result.filter((album) => album.era === selectedEra);
    }

    if (selectedLabel) {
      result = result.filter(
        (album) => album.label.toLowerCase() === selectedLabel.toLowerCase()
      );
    }

    return sortAlbums(result, sortBy);
  }, [searchQuery, selectedGenre, selectedEra, selectedLabel, sortBy]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(filteredAlbums.length / ALBUMS_PER_PAGE));
  const safePage = Math.min(currentPage, totalPages);
  const startIdx = (safePage - 1) * ALBUMS_PER_PAGE;
  const endIdx = startIdx + ALBUMS_PER_PAGE;
  const paginatedAlbums = filteredAlbums.slice(startIdx, endIdx);

  const goToPage = useCallback(
    (page: number) => {
      setCurrentPage(page);
      setSearchParams((prev) => {
        const newParams = new URLSearchParams(prev);
        if (page > 1) {
          newParams.set('page', String(page));
        } else {
          newParams.delete('page');
        }
        return newParams;
      }, { replace: true });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },
    [setSearchParams]
  );

  const updateFilter = (key: string, value: string | null) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    newParams.delete('page');
    setCurrentPage(1);
    setSearchParams(newParams);
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedGenre(null);
    setSelectedEra(null);
    setSelectedLabel(null);
    setSortBy('year-asc');
    setCurrentPage(1);
    setSearchParams({});
  };

  const hasActiveFilters = !!(searchQuery || selectedGenre || selectedEra || selectedLabel);

  return (
    <div ref={topRef} className="max-w-6xl mx-auto px-4 py-12 page-enter">
      <SEO
        title="Essential Jazz Albums"
        description={`Explore ${albums.length} jazz albums that define the genre, from bebop classics to contemporary masterpieces. Filter by era, genre, and label.`}
      />

      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2 font-display text-charcoal">Essential Albums</h1>
        <p className="text-warm-gray">
          {filteredAlbums.length} albums{' '}
          {hasActiveFilters ? 'matching your filters' : 'that define jazz history'}
        </p>
      </div>

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
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search by title, artist, label, or genre..."
          aria-label="Search albums"
          className="w-full pl-12 pr-4 py-3 bg-surface border border-border rounded-xl text-charcoal placeholder:text-warm-gray focus:outline-none focus:border-coral focus:ring-1 focus:ring-coral transition-colors"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            aria-label="Clear search"
            className="absolute right-4 top-1/2 -translate-y-1/2 text-warm-gray hover:text-charcoal transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Sort + Filter Row */}
      <div className="flex items-center gap-4 mb-4">
        <select
          value={sortBy}
          onChange={(e) => {
            const value = e.target.value;
            if (isValidSortOption(value)) {
              setSortBy(value);
              updateFilter('sort', value === 'year-asc' ? null : value);
            }
          }}
          className="px-3 py-1.5 bg-surface border border-border rounded-lg text-sm text-charcoal focus:outline-none focus:border-coral focus:ring-1 focus:ring-coral"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Era Filter */}
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-warm-gray mb-2">Filter by Era</h3>
        <div className="flex flex-wrap gap-2">
          {eras.map((era) => (
            <button
              key={era.id}
              onClick={() => {
                const next = selectedEra === era.id ? null : era.id;
                setSelectedEra(next);
                updateFilter('era', next);
              }}
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

      {/* Genre Filter */}
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-warm-gray mb-2">Filter by Genre</h3>
        <div className="flex flex-wrap gap-2">
          {visibleGenres.map((genre) => (
            <button
              key={genre}
              onClick={() => {
                const next =
                  selectedGenre?.toLowerCase() === genre.toLowerCase() ? null : genre;
                setSelectedGenre(next);
                updateFilter('genre', next);
              }}
              className={`px-3 py-1.5 text-sm rounded-full border transition-all ${
                selectedGenre?.toLowerCase() === genre.toLowerCase()
                  ? 'bg-coral border-coral text-white font-medium'
                  : 'border-border text-warm-gray hover:border-charcoal hover:text-charcoal'
              }`}
            >
              {genre}
            </button>
          ))}
          {genresByFrequency.length > 12 && (
            <button
              onClick={() => setShowAllGenres((v) => !v)}
              className="px-3 py-1.5 text-sm text-coral hover:text-coral/80 transition-colors"
            >
              {showAllGenres ? 'Show less' : `Show all (${genresByFrequency.length})`}
            </button>
          )}
        </div>
      </div>

      {/* Label Filter */}
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-warm-gray mb-2">Filter by Label</h3>
        <div className="flex flex-wrap gap-2">
          {visibleLabels.map((label) => (
            <button
              key={label}
              onClick={() => {
                const next =
                  selectedLabel?.toLowerCase() === label.toLowerCase() ? null : label;
                setSelectedLabel(next);
                updateFilter('label', next);
              }}
              className={`px-3 py-1.5 text-sm rounded-full border transition-all ${
                selectedLabel?.toLowerCase() === label.toLowerCase()
                  ? 'bg-teal border-teal text-cream font-medium'
                  : 'border-border text-warm-gray hover:border-charcoal hover:text-charcoal'
              }`}
            >
              {label}
            </button>
          ))}
          {labelsByFrequency.length > 12 && (
            <button
              onClick={() => setShowAllLabels((v) => !v)}
              className="px-3 py-1.5 text-sm text-teal hover:text-teal/80 transition-colors"
            >
              {showAllLabels ? 'Show less' : `Show all (${labelsByFrequency.length})`}
            </button>
          )}
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
                backgroundColor: getEra(selectedEra)?.color + '30',
                color: getEra(selectedEra)?.color,
              }}
            >
              {getEra(selectedEra)?.name}
            </span>
          )}
          {selectedGenre && (
            <span className="px-2 py-1 text-xs rounded-full bg-coral/20 text-coral">
              {selectedGenre}
            </span>
          )}
          {selectedLabel && (
            <span className="px-2 py-1 text-xs rounded-full bg-teal/20 text-teal">
              {selectedLabel}
            </span>
          )}
          <button
            onClick={clearFilters}
            className="text-sm text-warm-gray hover:text-charcoal underline"
          >
            Clear all
          </button>
        </div>
      )}

      {/* Pagination Summary */}
      {filteredAlbums.length > 0 && (
        <div className="mb-4 flex items-center justify-between text-sm text-warm-gray">
          <span>
            Showing {startIdx + 1}&ndash;{Math.min(endIdx, filteredAlbums.length)} of{' '}
            {filteredAlbums.length} albums
          </span>
          {totalPages > 1 && (
            <span>
              Page {safePage} of {totalPages}
            </span>
          )}
        </div>
      )}

      {/* Albums Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {paginatedAlbums.map((album) => {
          const era = getEra(album.era);
          return (
            <Link
              key={album.id}
              to={`/album/${album.id}`}
              className="group p-6 rounded-xl bg-surface shadow-card hover:shadow-card-hover hover:-translate-y-1 transition-all duration-300"
            >
              <div className="mb-4 group-hover:scale-105 transition-transform duration-300">
                <AlbumCover coverUrl={album.coverUrl} title={album.title} size="md" />
              </div>

              <h2 className="text-lg font-bold text-charcoal font-heading group-hover:text-coral transition-colors">
                {album.title}
              </h2>

              <p className="text-warm-gray">{album.artist}</p>

              <div className="flex items-center justify-between mt-3">
                <span className="text-warm-gray">{album.year}</span>
                {era && (
                  <span
                    className="px-2 py-0.5 text-xs rounded"
                    style={{
                      backgroundColor: era.color + '30',
                      color: era.color,
                    }}
                  >
                    {era.name.split(' ')[0]}
                  </span>
                )}
              </div>

              <div className="flex flex-wrap gap-1.5 mt-2">
                {album.genres.slice(0, 2).map((genre) => (
                  <span
                    key={genre}
                    className="px-2 py-0.5 text-xs rounded-full bg-border-light text-warm-gray"
                  >
                    {genre}
                  </span>
                ))}
              </div>
            </Link>
          );
        })}
      </div>

      {/* Empty State */}
      {filteredAlbums.length === 0 && (
        <div className="text-center py-12">
          <p className="text-warm-gray">No albums match your filters.</p>
          <button
            onClick={clearFilters}
            className="mt-4 text-coral hover:text-coral/80"
          >
            Clear filters
          </button>
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <Pagination
          currentPage={safePage}
          totalPages={totalPages}
          onPageChange={goToPage}
        />
      )}
    </div>
  );
}

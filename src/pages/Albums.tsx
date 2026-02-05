import { useState, useMemo, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import albumsData from '../data/albums.json';
import erasData from '../data/eras.json';
import { AlbumCover } from '../components/AlbumCover';
import type { Album, Era } from '../types';

const albums = albumsData as Album[];
const eras = erasData as Era[];

export function Albums() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [selectedGenre, setSelectedGenre] = useState<string | null>(
    searchParams.get('genre')
  );
  const [selectedEra, setSelectedEra] = useState<string | null>(
    searchParams.get('era')
  );
  const [selectedLabel, setSelectedLabel] = useState<string | null>(
    searchParams.get('label')
  );
  const [selectedYear, setSelectedYear] = useState<number | null>(
    searchParams.get('year') ? parseInt(searchParams.get('year')!) : null
  );

  // Sync URL params to state on mount and param changes
  useEffect(() => {
    setSelectedGenre(searchParams.get('genre'));
    setSelectedEra(searchParams.get('era'));
    setSelectedLabel(searchParams.get('label'));
    setSelectedYear(searchParams.get('year') ? parseInt(searchParams.get('year')!) : null);
  }, [searchParams]);

  const getEra = (eraId: string) => eras.find((e) => e.id === eraId);

  // Extract all unique genres
  const allGenres = useMemo(() => {
    const genreSet = new Set<string>();
    albums.forEach((album) => {
      album.genres.forEach((genre) => genreSet.add(genre));
    });
    return Array.from(genreSet).sort();
  }, []);

  // Extract all unique labels
  const allLabels = useMemo(() => {
    const labelSet = new Set<string>();
    albums.forEach((album) => labelSet.add(album.label));
    return Array.from(labelSet).sort();
  }, []);

  // Filter and sort albums
  const filteredAlbums = useMemo(() => {
    let result = [...albums];

    if (selectedGenre) {
      result = result.filter((album) =>
        album.genres.some((g) => g.toLowerCase() === selectedGenre.toLowerCase())
      );
    }

    if (selectedEra) {
      result = result.filter((album) => album.era === selectedEra);
    }

    if (selectedLabel) {
      result = result.filter((album) =>
        album.label.toLowerCase() === selectedLabel.toLowerCase()
      );
    }

    if (selectedYear) {
      result = result.filter((album) => album.year === selectedYear);
    }

    return result.sort((a, b) => a.year - b.year);
  }, [selectedGenre, selectedEra, selectedLabel, selectedYear]);

  const clearFilters = () => {
    setSelectedGenre(null);
    setSelectedEra(null);
    setSelectedLabel(null);
    setSelectedYear(null);
    setSearchParams({});
  };

  const updateFilter = (key: string, value: string | null) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    setSearchParams(newParams);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Essential Albums</h1>
        <p className="text-zinc-400">
          {filteredAlbums.length} albums {(selectedGenre || selectedEra || selectedLabel || selectedYear) ? 'matching your filters' : 'that define jazz history'}
        </p>
      </div>

      {/* Era Filter */}
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-zinc-500 mb-2">Filter by Era</h3>
        <div className="flex flex-wrap gap-2">
          {eras.map((era) => (
            <button
              key={era.id}
              onClick={() => updateFilter('era', selectedEra === era.id ? null : era.id)}
              className={`px-3 py-1.5 text-sm rounded-full border transition-all ${
                selectedEra === era.id
                  ? 'border-transparent text-black font-medium'
                  : 'border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'
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
        <h3 className="text-sm font-semibold text-zinc-500 mb-2">Filter by Genre</h3>
        <div className="flex flex-wrap gap-2">
          {allGenres.map((genre) => (
            <button
              key={genre}
              onClick={() => updateFilter('genre', selectedGenre?.toLowerCase() === genre.toLowerCase() ? null : genre)}
              className={`px-3 py-1.5 text-sm rounded-full border transition-all ${
                selectedGenre?.toLowerCase() === genre.toLowerCase()
                  ? 'bg-amber-500 border-amber-500 text-black font-medium'
                  : 'border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'
              }`}
            >
              {genre}
            </button>
          ))}
        </div>
      </div>

      {/* Label Filter */}
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-zinc-500 mb-2">Filter by Label</h3>
        <div className="flex flex-wrap gap-2">
          {allLabels.slice(0, 12).map((label) => (
            <button
              key={label}
              onClick={() => updateFilter('label', selectedLabel?.toLowerCase() === label.toLowerCase() ? null : label)}
              className={`px-3 py-1.5 text-sm rounded-full border transition-all ${
                selectedLabel?.toLowerCase() === label.toLowerCase()
                  ? 'bg-cyan-500 border-cyan-500 text-black font-medium'
                  : 'border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Active Filters */}
      {(selectedGenre || selectedEra || selectedLabel || selectedYear) && (
        <div className="mb-6 flex items-center gap-3">
          <span className="text-sm text-zinc-500">Active filters:</span>
          {selectedEra && (
            <span
              className="px-2 py-1 text-xs rounded-full"
              style={{ backgroundColor: getEra(selectedEra)?.color + '30', color: getEra(selectedEra)?.color }}
            >
              {getEra(selectedEra)?.name}
            </span>
          )}
          {selectedGenre && (
            <span className="px-2 py-1 text-xs rounded-full bg-amber-500/20 text-amber-400">
              {selectedGenre}
            </span>
          )}
          {selectedLabel && (
            <span className="px-2 py-1 text-xs rounded-full bg-cyan-500/20 text-cyan-400">
              {selectedLabel}
            </span>
          )}
          {selectedYear && (
            <span className="px-2 py-1 text-xs rounded-full bg-purple-500/20 text-purple-400">
              {selectedYear}
            </span>
          )}
          <button
            onClick={clearFilters}
            className="text-sm text-zinc-500 hover:text-white underline"
          >
            Clear all
          </button>
        </div>
      )}

      {/* Albums Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredAlbums.map((album) => {
          const era = getEra(album.era);
          return (
            <Link
              key={album.id}
              to={`/album/${album.id}`}
              className="group p-6 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-600 transition-all"
            >
              <div className="mb-4 group-hover:scale-105 transition-transform">
                <AlbumCover coverUrl={album.coverUrl} title={album.title} size="md" />
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

              {/* Genre tags */}
              <div className="flex flex-wrap gap-1 mt-2">
                {album.genres.slice(0, 2).map((genre) => (
                  <span key={genre} className="text-xs text-zinc-600">
                    {genre}
                  </span>
                ))}
              </div>
            </Link>
          );
        })}
      </div>

      {filteredAlbums.length === 0 && (
        <div className="text-center py-12">
          <p className="text-zinc-500">No albums match your filters.</p>
          <button
            onClick={clearFilters}
            className="mt-4 text-amber-400 hover:text-amber-300"
          >
            Clear filters
          </button>
        </div>
      )}
    </div>
  );
}

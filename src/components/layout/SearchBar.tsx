import { useState, useRef, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import albumsData from '../../data/albums.json';
import artistsData from '../../data/artists.json';
import type { Album, Artist } from '../../types';

const albums = albumsData as Album[];
const artists = artistsData as Artist[];

interface SearchBarProps {
  onOpenChange?: (isOpen: boolean) => void;
  forceClose?: boolean;
}

interface ScoredArtist {
  artist: Artist;
  score: number;
}

interface ScoredAlbum {
  album: Album;
  score: number;
}

export function SearchBar({ onOpenChange, forceClose }: SearchBarProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const iconRef = useRef<HTMLButtonElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const open = () => {
    setIsOpen(true);
    onOpenChange?.(true);
  };

  const close = () => {
    setIsOpen(false);
    setQuery('');
    setDebouncedQuery('');
    onOpenChange?.(false);
    iconRef.current?.focus();
  };

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (forceClose && isOpen) {
      setIsOpen(false);
      setQuery('');
      setDebouncedQuery('');
      onOpenChange?.(false);
    }
  }, [forceClose]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 150);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        close();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  const { scoredArtists, scoredAlbums } = useMemo(() => {
    if (debouncedQuery.length < 2) {
      return { scoredArtists: [], scoredAlbums: [] };
    }

    const q = debouncedQuery.toLowerCase();

    const artistResults: ScoredArtist[] = artists
      .map((artist) => {
        const nameLower = artist.name.toLowerCase();
        let score = 0;
        if (nameLower.startsWith(q)) {
          score += 100;
        } else if (nameLower.includes(q)) {
          score += 50;
        }
        const instrumentMatch = artist.instruments.some((inst) =>
          inst.toLowerCase().includes(q)
        );
        if (instrumentMatch) score += 20;
        return { artist, score };
      })
      .filter((r) => r.score > 0)
      .sort((a, b) => b.score - a.score);

    const albumResults: ScoredAlbum[] = albums
      .map((album) => {
        const titleLower = album.title.toLowerCase();
        const artistNameLower = album.artist.toLowerCase();
        let score = 0;
        if (titleLower.startsWith(q)) {
          score += 100;
        } else if (titleLower.includes(q)) {
          score += 50;
        }
        if (artistNameLower.includes(q)) score += 30;
        return { album, score };
      })
      .filter((r) => r.score > 0)
      .sort((a, b) => b.score - a.score);

    return { scoredArtists: artistResults, scoredAlbums: albumResults };
  }, [debouncedQuery]);

  const showPopup = isOpen && debouncedQuery.length >= 2;
  const topArtists = scoredArtists.slice(0, 5);
  const topAlbums = scoredAlbums.slice(0, 5);
  const hasResults = topArtists.length > 0 || topAlbums.length > 0;

  return (
    <div ref={containerRef} className="relative">
      {isOpen ? (
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-warm-gray shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-label="Search artists and albums"
            aria-expanded={showPopup}
            placeholder="Search artists, albums..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="bg-transparent border-b border-warm-gray/40 text-charcoal text-sm outline-none flex-1 min-w-0 md:w-56 py-1 placeholder:text-warm-gray/60 focus:border-coral transition-colors"
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                e.stopPropagation();
                close();
              }
            }}
          />
          <button
            onClick={close}
            className="text-warm-gray hover:text-charcoal transition-colors p-0.5 focus:outline-none focus:ring-2 focus:ring-coral rounded"
            aria-label="Close search"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>

          {showPopup && (
            <div
              role="listbox"
              className="absolute top-full right-0 mt-2 w-[calc(100vw-2rem)] md:w-96 max-h-[400px] overflow-y-auto rounded-xl bg-charcoal/80 backdrop-blur-xl border border-white/10 shadow-2xl z-50"
            >
              {!hasResults ? (
                <div className="px-4 py-6 text-sm text-white/50 text-center">
                  No results for {debouncedQuery}
                </div>
              ) : (
                <>
                  {topArtists.length > 0 && (
                    <div>
                      <div className="px-4 pt-3 pb-1 text-xs font-semibold uppercase tracking-wider text-white/40">
                        Artists
                      </div>
                      {topArtists.map(({ artist }) => (
                        <button
                          key={artist.id}
                          role="option"
                          aria-selected={false}
                          className="w-full text-left px-4 py-2.5 hover:bg-white/10 transition-colors flex items-baseline gap-2"
                          onClick={() => {
                            navigate(`/artist/${artist.id}`);
                            close();
                          }}
                        >
                          <span className="text-sm text-white truncate">{artist.name}</span>
                          <span className="text-xs text-white/40 truncate shrink-0">
                            -- {artist.instruments.slice(0, 3).join(', ')}
                          </span>
                        </button>
                      ))}
                      {scoredArtists.length > 5 && (
                        <button
                          className="w-full text-left px-4 py-2 text-xs text-coral hover:text-coral/80 transition-colors"
                          onClick={() => {
                            navigate(`/artists?q=${encodeURIComponent(debouncedQuery)}`);
                            close();
                          }}
                        >
                          View all {scoredArtists.length} artists
                        </button>
                      )}
                    </div>
                  )}

                  {topArtists.length > 0 && topAlbums.length > 0 && (
                    <div className="border-t border-white/10" />
                  )}

                  {topAlbums.length > 0 && (
                    <div>
                      <div className="px-4 pt-3 pb-1 text-xs font-semibold uppercase tracking-wider text-white/40">
                        Albums
                      </div>
                      {topAlbums.map(({ album }) => (
                        <button
                          key={album.id}
                          role="option"
                          aria-selected={false}
                          className="w-full text-left px-4 py-2.5 hover:bg-white/10 transition-colors flex items-baseline gap-2"
                          onClick={() => {
                            navigate(`/album/${album.id}`);
                            close();
                          }}
                        >
                          <span className="text-sm text-white truncate">{album.title}</span>
                          <span className="text-xs text-white/40 truncate shrink-0">
                            -- {album.artist} ({album.year})
                          </span>
                        </button>
                      ))}
                      {scoredAlbums.length > 5 && (
                        <button
                          className="w-full text-left px-4 py-2 text-xs text-coral hover:text-coral/80 transition-colors"
                          onClick={() => {
                            navigate(`/albums?q=${encodeURIComponent(debouncedQuery)}`);
                            close();
                          }}
                        >
                          View all {scoredAlbums.length} albums
                        </button>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      ) : (
        <button
          ref={iconRef}
          onClick={open}
          className="text-warm-gray hover:text-coral transition-colors p-1 focus:outline-none focus:ring-2 focus:ring-coral focus:ring-offset-2 focus:ring-offset-cream rounded"
          aria-label="Open search"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </button>
      )}
    </div>
  );
}

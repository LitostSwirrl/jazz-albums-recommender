import { useState, useRef, useEffect, useMemo, useCallback, forwardRef, useImperativeHandle } from 'react';
import type { Artist } from '../../../types';
import { ArtistPhoto } from '../../ArtistPhoto';

interface ArtistDropdownProps {
  artists: Artist[];
  selectedArtist: Artist | null;
  onSelect: (artist: Artist | null) => void;
  placeholder: string;
  excludeArtistId?: string;
}

export interface ArtistDropdownHandle {
  focus: () => void;
}

export const ArtistDropdown = forwardRef<ArtistDropdownHandle, ArtistDropdownProps>(
  function ArtistDropdown({ artists, selectedArtist, onSelect, placeholder, excludeArtistId }, ref) {
    const [query, setQuery] = useState('');
    const [isOpen, setIsOpen] = useState(false);
    const [highlightedIndex, setHighlightedIndex] = useState(-1);
    const inputRef = useRef<HTMLInputElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const listRef = useRef<HTMLUListElement>(null);

    useImperativeHandle(ref, () => ({
      focus: () => inputRef.current?.focus(),
    }));

    // Connected artists sorted by connection count
    const connectedArtists = useMemo(() => {
      return artists
        .filter((a) => (a.influences.length > 0 || a.influencedBy.length > 0) && a.id !== excludeArtistId)
        .sort((a, b) =>
          (b.influences.length + b.influencedBy.length) - (a.influences.length + a.influencedBy.length)
        );
    }, [artists, excludeArtistId]);

    const filteredArtists = useMemo(() => {
      if (!query.trim()) {
        return connectedArtists.slice(0, 8);
      }
      const lowerQuery = query.toLowerCase();
      return connectedArtists
        .filter((a) =>
          a.name.toLowerCase().includes(lowerQuery) ||
          a.instruments.some((i) => i.toLowerCase().includes(lowerQuery))
        )
        .slice(0, 8);
    }, [connectedArtists, query]);

    // Close on click outside
    useEffect(() => {
      const handleMouseDown = (e: MouseEvent) => {
        if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
          setIsOpen(false);
        }
      };
      document.addEventListener('mousedown', handleMouseDown);
      return () => document.removeEventListener('mousedown', handleMouseDown);
    }, []);

    // Reset highlighted index when filtered results change
    useEffect(() => {
      setHighlightedIndex(-1);
    }, [filteredArtists]);

    // Scroll highlighted item into view
    useEffect(() => {
      if (highlightedIndex >= 0 && listRef.current) {
        const items = listRef.current.children;
        if (items[highlightedIndex]) {
          (items[highlightedIndex] as HTMLElement).scrollIntoView({ block: 'nearest' });
        }
      }
    }, [highlightedIndex]);

    const handleSelect = useCallback((artist: Artist) => {
      onSelect(artist);
      setQuery('');
      setIsOpen(false);
      setHighlightedIndex(-1);
    }, [onSelect]);

    const handleClear = useCallback(() => {
      onSelect(null);
      setQuery('');
      setHighlightedIndex(-1);
      inputRef.current?.focus();
    }, [onSelect]);

    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
      if (!isOpen) {
        if (e.key === 'ArrowDown' || e.key === 'Enter') {
          setIsOpen(true);
          e.preventDefault();
        }
        return;
      }

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev < filteredArtists.length - 1 ? prev + 1 : 0
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev > 0 ? prev - 1 : filteredArtists.length - 1
          );
          break;
        case 'Enter':
          e.preventDefault();
          if (highlightedIndex >= 0 && highlightedIndex < filteredArtists.length) {
            handleSelect(filteredArtists[highlightedIndex]);
          }
          break;
        case 'Escape':
          setIsOpen(false);
          setHighlightedIndex(-1);
          break;
      }
    }, [isOpen, highlightedIndex, filteredArtists, handleSelect]);

    // Selected state — show chip
    if (selectedArtist) {
      return (
        <div
          ref={containerRef}
          className="flex items-center gap-3 px-3 py-2.5 bg-surface border border-border rounded-lg"
        >
          <ArtistPhoto imageUrl={selectedArtist.imageUrl} name={selectedArtist.name} size="sm" />
          <div className="flex-1 min-w-0">
            <div className="text-charcoal font-medium truncate text-sm">{selectedArtist.name}</div>
            <div className="text-xs text-warm-gray truncate">
              {(selectedArtist.instruments || []).slice(0, 2).join(', ')}
            </div>
          </div>
          <button
            onClick={handleClear}
            aria-label={`Clear ${selectedArtist.name}`}
            className="text-warm-gray hover:text-coral transition-colors shrink-0 p-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      );
    }

    // Search input with dropdown
    return (
      <div ref={containerRef} className="relative">
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-warm-gray"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            role="combobox"
            aria-expanded={isOpen}
            aria-haspopup="listbox"
            aria-activedescendant={highlightedIndex >= 0 ? `artist-option-${highlightedIndex}` : undefined}
            className="w-full pl-9 pr-4 py-2.5 bg-surface border border-border rounded-lg text-charcoal text-sm placeholder:text-warm-gray focus:outline-none focus:border-coral focus:ring-1 focus:ring-coral transition-colors"
          />
        </div>

        {isOpen && filteredArtists.length > 0 && (
          <ul
            ref={listRef}
            role="listbox"
            className="absolute z-50 w-full mt-1 bg-surface border border-border rounded-lg shadow-elevated max-h-[320px] overflow-y-auto"
          >
            {filteredArtists.map((artist, index) => (
              <li
                key={artist.id}
                id={`artist-option-${index}`}
                role="option"
                aria-selected={highlightedIndex === index}
                onClick={() => handleSelect(artist)}
                onMouseEnter={() => setHighlightedIndex(index)}
                className={`flex items-center gap-3 px-3 py-2.5 cursor-pointer transition-colors ${
                  highlightedIndex === index ? 'bg-border' : 'hover:bg-border/50'
                }`}
              >
                <ArtistPhoto imageUrl={artist.imageUrl} name={artist.name} size="sm" />
                <div className="flex-1 min-w-0">
                  <div className="text-charcoal text-sm font-medium truncate">{artist.name}</div>
                  <div className="text-xs text-warm-gray truncate">
                    {artist.instruments.slice(0, 2).join(', ')}
                  </div>
                </div>
                <span className="text-xs text-warm-gray/60 shrink-0 font-mono">
                  {artist.influences.length + artist.influencedBy.length}
                </span>
              </li>
            ))}
          </ul>
        )}

        {isOpen && query.trim() && filteredArtists.length === 0 && (
          <div className="absolute z-50 w-full mt-1 bg-surface border border-border rounded-lg shadow-elevated px-4 py-6 text-center">
            <p className="text-warm-gray text-sm">No artists found for &ldquo;{query}&rdquo;</p>
          </div>
        )}
      </div>
    );
  }
);

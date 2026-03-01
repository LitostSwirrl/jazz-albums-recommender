import { useState, useMemo, useRef, useEffect } from 'react';
import type { Artist } from '../../../types';

interface SearchPanelProps {
  artists: Artist[];
  onSelect: (artist: Artist) => void;
  placeholder?: string;
}

export function SearchPanel({ artists, onSelect, placeholder = 'Search artists...' }: SearchPanelProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const filteredArtists = useMemo(() => {
    if (!query.trim()) return [];
    const lowerQuery = query.toLowerCase();
    return artists
      .filter((artist) =>
        artist.name.toLowerCase().includes(lowerQuery) ||
        artist.instruments.some((i) => i.toLowerCase().includes(lowerQuery))
      )
      .slice(0, 8);
  }, [artists, query]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as HTMLElement) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as HTMLElement)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (artist: Artist) => {
    onSelect(artist);
    setQuery('');
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          placeholder={placeholder}
          className="w-full px-4 py-2 pl-10 bg-surface border border-border rounded-lg text-charcoal placeholder-warm-gray focus:outline-none focus:ring-2 focus:ring-coral focus:border-transparent"
        />
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-warm-gray"
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
      </div>

      {isOpen && filteredArtists.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-1 bg-surface border border-border rounded-lg shadow-elevated overflow-hidden"
        >
          {filteredArtists.map((artist) => (
            <button
              key={artist.id}
              onClick={() => handleSelect(artist)}
              className="w-full px-4 py-2 text-left hover:bg-cream transition-colors flex items-center justify-between"
            >
              <div>
                <div className="text-charcoal font-medium">{artist.name}</div>
                <div className="text-xs text-warm-gray">
                  {artist.instruments.slice(0, 2).join(', ')}
                </div>
              </div>
              <span className="text-xs text-warm-gray/60">
                {artist.influences.length + artist.influencedBy.length} connections
              </span>
            </button>
          ))}
        </div>
      )}

      {isOpen && query && filteredArtists.length === 0 && (
        <div className="absolute z-50 w-full mt-1 bg-surface border border-border rounded-lg shadow-elevated p-4 text-center text-warm-gray">
          No artists found
        </div>
      )}
    </div>
  );
}

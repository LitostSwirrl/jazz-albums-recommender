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
          className="w-full px-4 py-2 pl-10 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent"
        />
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500"
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
          className="absolute z-50 w-full mt-1 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl overflow-hidden"
        >
          {filteredArtists.map((artist) => (
            <button
              key={artist.id}
              onClick={() => handleSelect(artist)}
              className="w-full px-4 py-2 text-left hover:bg-zinc-800 transition-colors flex items-center justify-between"
            >
              <div>
                <div className="text-white font-medium">{artist.name}</div>
                <div className="text-xs text-zinc-500">
                  {artist.instruments.slice(0, 2).join(', ')}
                </div>
              </div>
              <span className="text-xs text-zinc-600">
                {artist.influences.length + artist.influencedBy.length} connections
              </span>
            </button>
          ))}
        </div>
      )}

      {isOpen && query && filteredArtists.length === 0 && (
        <div className="absolute z-50 w-full mt-1 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl p-4 text-center text-zinc-500">
          No artists found
        </div>
      )}
    </div>
  );
}

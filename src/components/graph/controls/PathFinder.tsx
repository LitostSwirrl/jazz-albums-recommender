import { useState } from 'react';
import type { Artist } from '../../../types';
import { SearchPanel } from './SearchPanel';

interface PathFinderProps {
  artists: Artist[];
  onFindPath: (startId: string, endId: string) => void;
  onClear: () => void;
  currentPath: string[] | null;
  artistMap: Map<string, Artist>;
}

export function PathFinder({ artists, onFindPath, onClear, currentPath, artistMap }: PathFinderProps) {
  const [startArtist, setStartArtist] = useState<Artist | null>(null);
  const [endArtist, setEndArtist] = useState<Artist | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const handleFindPath = () => {
    if (startArtist && endArtist) {
      onFindPath(startArtist.id, endArtist.id);
    }
  };

  const handleClear = () => {
    setStartArtist(null);
    setEndArtist(null);
    onClear();
  };

  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-cream transition-colors"
      >
        <span className="font-medium text-coral">Find Connection</span>
        <svg
          className={`w-5 h-5 text-warm-gray transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="p-4 border-t border-border space-y-4">
          <div>
            <label className="block text-sm text-warm-gray mb-1">From Artist</label>
            {startArtist ? (
              <div className="flex items-center justify-between px-3 py-2 bg-cream rounded-lg">
                <span className="text-charcoal">{startArtist.name}</span>
                <button
                  onClick={() => setStartArtist(null)}
                  className="text-warm-gray hover:text-charcoal"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ) : (
              <SearchPanel
                artists={artists}
                onSelect={setStartArtist}
                placeholder="Select starting artist..."
              />
            )}
          </div>

          <div>
            <label className="block text-sm text-warm-gray mb-1">To Artist</label>
            {endArtist ? (
              <div className="flex items-center justify-between px-3 py-2 bg-cream rounded-lg">
                <span className="text-charcoal">{endArtist.name}</span>
                <button
                  onClick={() => setEndArtist(null)}
                  className="text-warm-gray hover:text-charcoal"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ) : (
              <SearchPanel
                artists={artists}
                onSelect={setEndArtist}
                placeholder="Select ending artist..."
              />
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleFindPath}
              disabled={!startArtist || !endArtist}
              className="flex-1 px-4 py-2 bg-coral hover:bg-coral/90 disabled:bg-border disabled:text-warm-gray text-white rounded-lg transition-colors font-medium"
            >
              Find Path
            </button>
            <button
              onClick={handleClear}
              className="px-4 py-2 bg-cream hover:bg-border text-charcoal rounded-lg transition-colors"
            >
              Clear
            </button>
          </div>

          {currentPath && (
            <div className="mt-4 p-3 bg-cream rounded-lg">
              <div className="text-sm text-coral mb-2">
                Connection found! ({currentPath.length - 1} degree{currentPath.length > 2 ? 's' : ''} of separation)
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {currentPath.map((id, index) => {
                  const artist = artistMap.get(id);
                  return (
                    <span key={id} className="flex items-center">
                      <span className="text-charcoal font-medium">{artist?.name || id}</span>
                      {index < currentPath.length - 1 && (
                        <svg className="w-4 h-4 mx-1 text-coral" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      )}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {currentPath === null && startArtist && endArtist && (
            <div className="mt-4 p-3 bg-cream rounded-lg text-warm-gray">
              No connection found between these artists.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

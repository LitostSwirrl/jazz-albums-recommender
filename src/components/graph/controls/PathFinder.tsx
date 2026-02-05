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
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-zinc-800 transition-colors"
      >
        <span className="font-medium text-amber-400">Find Connection</span>
        <svg
          className={`w-5 h-5 text-zinc-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="p-4 border-t border-zinc-700 space-y-4">
          <div>
            <label className="block text-sm text-zinc-400 mb-1">From Artist</label>
            {startArtist ? (
              <div className="flex items-center justify-between px-3 py-2 bg-zinc-800 rounded-lg">
                <span className="text-white">{startArtist.name}</span>
                <button
                  onClick={() => setStartArtist(null)}
                  className="text-zinc-500 hover:text-white"
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
            <label className="block text-sm text-zinc-400 mb-1">To Artist</label>
            {endArtist ? (
              <div className="flex items-center justify-between px-3 py-2 bg-zinc-800 rounded-lg">
                <span className="text-white">{endArtist.name}</span>
                <button
                  onClick={() => setEndArtist(null)}
                  className="text-zinc-500 hover:text-white"
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
              className="flex-1 px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-lg transition-colors font-medium"
            >
              Find Path
            </button>
            <button
              onClick={handleClear}
              className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg transition-colors"
            >
              Clear
            </button>
          </div>

          {currentPath && (
            <div className="mt-4 p-3 bg-zinc-800 rounded-lg">
              <div className="text-sm text-amber-400 mb-2">
                Connection found! ({currentPath.length - 1} degree{currentPath.length > 2 ? 's' : ''} of separation)
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {currentPath.map((id, index) => {
                  const artist = artistMap.get(id);
                  return (
                    <span key={id} className="flex items-center">
                      <span className="text-white font-medium">{artist?.name || id}</span>
                      {index < currentPath.length - 1 && (
                        <svg className="w-4 h-4 mx-1 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
            <div className="mt-4 p-3 bg-zinc-800 rounded-lg text-zinc-400">
              No connection found between these artists.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

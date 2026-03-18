import { useState, useRef, useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { AlbumCover } from '../AlbumCover';
import { getRandomAlbum } from '../../utils/discovery';
import type { Album, Era } from '../../types';

interface RandomAlbumPickerProps {
  albums: Album[];
  eras: Era[];
}

type Phase = 'idle' | 'spinning' | 'revealed';

export function RandomAlbumPicker({ albums, eras }: RandomAlbumPickerProps) {
  const [phase, setPhase] = useState<Phase>('idle');
  const [selectedAlbum, setSelectedAlbum] = useState<Album | null>(null);
  const [displayAlbum, setDisplayAlbum] = useState<Album | null>(null);
  const [filterEra, setFilterEra] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval>>(null);
  const recentRef = useRef<string[]>([]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const spin = useCallback(() => {
    const filter = filterEra ? { era: filterEra } : undefined;
    const excludeId = recentRef.current[recentRef.current.length - 1];

    // Pick the final album
    let picked: Album | null = null;
    for (let attempt = 0; attempt < 10; attempt++) {
      const candidate = getRandomAlbum(albums, excludeId, filter);
      if (candidate && !recentRef.current.includes(candidate.id)) {
        picked = candidate;
        break;
      }
      if (candidate) {
        picked = candidate;
        break;
      }
    }

    if (!picked) {
      picked = getRandomAlbum(albums, undefined, filter);
    }
    if (!picked) return;
    const finalPick = picked; // capture for closure (TypeScript narrowing)

    setSelectedAlbum(finalPick);
    setPhase('spinning');

    // Shuffle animation: cycle through random covers
    const withCovers = albums.filter((a) => a.coverUrl);
    let count = 0;
    const maxCycles = 8;

    timerRef.current = setInterval(() => {
      count++;
      const idx = Math.floor(Math.random() * withCovers.length);
      setDisplayAlbum(withCovers[idx]);

      if (count >= maxCycles) {
        if (timerRef.current) clearInterval(timerRef.current);
        setDisplayAlbum(finalPick);
        setPhase('revealed');

        // Track recent picks
        recentRef.current = [...recentRef.current.slice(-4), finalPick.id];
      }
    }, 100);
  }, [albums, filterEra]);

  const shownAlbum = phase === 'spinning' ? displayAlbum : (phase === 'revealed' ? selectedAlbum : null);
  const selectedEra = selectedAlbum ? eras.find((e) => e.id === selectedAlbum.era) : null;

  return (
    <section className="mb-10 rounded-xl bg-surface border border-border p-6 md:p-8">
      <div className="flex flex-col items-center">
        {/* Title */}
        <h2 className="text-xl font-heading text-charcoal mb-4">Discover Something New</h2>

        {/* Era filter chips */}
        <div className="flex flex-wrap gap-2 justify-center mb-6">
          <button
            onClick={() => setFilterEra(null)}
            className={`px-3 py-1 rounded-full text-xs font-mono uppercase tracking-wider transition-colors ${
              !filterEra
                ? 'bg-coral text-white'
                : 'bg-border text-warm-gray hover:text-charcoal'
            }`}
          >
            Any Era
          </button>
          {eras.map((era) => (
            <button
              key={era.id}
              onClick={() => setFilterEra(era.id)}
              className={`px-3 py-1 rounded-full text-xs font-mono uppercase tracking-wider transition-colors ${
                filterEra === era.id
                  ? 'text-white'
                  : 'bg-border text-warm-gray hover:text-charcoal'
              }`}
              style={filterEra === era.id ? { backgroundColor: era.color } : undefined}
            >
              {era.name}
            </button>
          ))}
        </div>

        {/* Album display area */}
        <div className="relative w-56 h-56 md:w-64 md:h-64 mb-6">
          {phase === 'idle' && (
            <div className="w-full h-full rounded-sm bg-border-light flex items-center justify-center">
              <div className="text-center">
                <svg className="w-16 h-16 text-warm-gray/40 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                </svg>
                <p className="text-warm-gray/60 text-sm">Hit spin to discover</p>
              </div>
            </div>
          )}

          {(phase === 'spinning' || phase === 'revealed') && shownAlbum && (
            <div
              className={`w-full h-full rounded-sm overflow-hidden shadow-elevated ${
                phase === 'revealed' ? 'animate-[albumReveal_0.4s_ease-out]' : ''
              }`}
            >
              <AlbumCover
                coverUrl={shownAlbum.coverUrl}
                title={shownAlbum.title}
                size="sm"
                pixelWidth={512}
              />
            </div>
          )}
        </div>

        {/* Album info (revealed state) */}
        {phase === 'revealed' && selectedAlbum && (
          <div className="text-center mb-5 animate-[fadeInUp_0.3s_ease-out]">
            <h3 className="text-xl font-heading text-charcoal mb-1">{selectedAlbum.title}</h3>
            <p className="text-warm-gray text-sm">
              {selectedAlbum.artist} &middot; {selectedAlbum.year}
            </p>
            {selectedEra && (
              <span
                className="inline-block mt-2 px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded-full"
                style={{ backgroundColor: selectedEra.color + '30', color: selectedEra.color }}
              >
                {selectedEra.name}
              </span>
            )}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3">
          {phase === 'revealed' && selectedAlbum && (
            <Link
              to={`/album/${selectedAlbum.id}`}
              className="px-5 py-2.5 bg-coral text-white font-semibold rounded-lg hover:bg-coral/90 transition-colors text-sm"
            >
              Explore Album
            </Link>
          )}

          <button
            onClick={spin}
            disabled={phase === 'spinning'}
            className={`px-5 py-2.5 rounded-lg font-semibold text-sm transition-all flex items-center gap-2 ${
              phase === 'spinning'
                ? 'bg-border text-warm-gray cursor-wait'
                : phase === 'revealed'
                  ? 'border border-border text-charcoal hover:border-coral/50 hover:text-coral'
                  : 'bg-coral text-white hover:bg-coral/90'
            }`}
          >
            <svg className={`w-4 h-4 ${phase === 'spinning' ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {phase === 'revealed' ? 'Spin Again' : phase === 'spinning' ? 'Spinning...' : 'Spin'}
          </button>
        </div>
      </div>
    </section>
  );
}

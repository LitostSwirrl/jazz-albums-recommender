import { Link } from 'react-router-dom';
import { useState } from 'react';

export function Header() {
  const [showExplore, setShowExplore] = useState(false);

  return (
    <header className="bg-zinc-900 border-b border-zinc-800">
      <nav className="max-w-6xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-white hover:text-amber-400 transition-colors">
            Jazz Guide
          </Link>
          <div className="flex gap-6 items-center">
            <Link to="/" className="text-zinc-300 hover:text-white transition-colors">
              Home
            </Link>
            <Link to="/eras" className="text-zinc-300 hover:text-white transition-colors">
              Eras
            </Link>
            <Link to="/artists" className="text-zinc-300 hover:text-white transition-colors">
              Artists
            </Link>
            <Link to="/albums" className="text-zinc-300 hover:text-white transition-colors">
              Albums
            </Link>
            <div className="relative">
              <button
                onClick={() => setShowExplore(!showExplore)}
                onBlur={() => setTimeout(() => setShowExplore(false), 150)}
                className="text-amber-400 hover:text-amber-300 transition-colors flex items-center gap-1"
              >
                Explore
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showExplore && (
                <div className="absolute right-0 mt-2 w-48 rounded-lg bg-zinc-800 border border-zinc-700 shadow-xl z-50">
                  <Link
                    to="/timeline"
                    className="block px-4 py-3 text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors rounded-t-lg"
                  >
                    <div className="font-medium">Timeline</div>
                    <div className="text-xs text-zinc-500">Jazz through the ages</div>
                  </Link>
                  <Link
                    to="/influence"
                    className="block px-4 py-3 text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors rounded-b-lg"
                  >
                    <div className="font-medium">Influence Network</div>
                    <div className="text-xs text-zinc-500">Artist connections</div>
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>
    </header>
  );
}

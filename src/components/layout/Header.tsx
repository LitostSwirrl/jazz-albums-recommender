import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react';

export function Header() {
  const [showExplore, setShowExplore] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Close mobile menu on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMobileMenuOpen(false);
        setShowExplore(false);
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, []);

  return (
    <header className="bg-zinc-900 border-b border-zinc-800">
      <nav className="max-w-6xl mx-auto px-4 py-4" aria-label="Main navigation">
        <div className="flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-white hover:text-amber-400 transition-colors">
            Jazz Guide
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex gap-6 items-center">
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
                onKeyDown={(e) => e.key === 'Escape' && setShowExplore(false)}
                aria-expanded={showExplore}
                aria-haspopup="menu"
                aria-controls="explore-menu"
                className="text-amber-400 hover:text-amber-300 transition-colors flex items-center gap-1 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 focus:ring-offset-zinc-900 rounded"
              >
                Explore
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showExplore && (
                <div
                  id="explore-menu"
                  role="menu"
                  className="absolute right-0 mt-2 w-48 rounded-lg bg-zinc-800 border border-zinc-700 shadow-xl z-50"
                >
                  <Link
                    to="/timeline"
                    role="menuitem"
                    className="block px-4 py-3 text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors rounded-t-lg focus:outline-none focus:bg-zinc-700"
                  >
                    <div className="font-medium">Timeline</div>
                    <div className="text-xs text-zinc-500">Jazz through the ages</div>
                  </Link>
                  <Link
                    to="/influence"
                    role="menuitem"
                    className="block px-4 py-3 text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors focus:outline-none focus:bg-zinc-700"
                  >
                    <div className="font-medium">Influence Network</div>
                    <div className="text-xs text-zinc-500">Artist connections</div>
                  </Link>
                  <Link
                    to="/context"
                    role="menuitem"
                    className="block px-4 py-3 text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors rounded-b-lg focus:outline-none focus:bg-zinc-700"
                  >
                    <div className="font-medium">Jazz & Society</div>
                    <div className="text-xs text-zinc-500">History & context</div>
                  </Link>
                </div>
              )}
            </div>
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2 text-zinc-300 hover:text-white focus:outline-none focus:ring-2 focus:ring-amber-500 rounded"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-menu"
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
          >
            {mobileMenuOpen ? (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div
            id="mobile-menu"
            className="md:hidden mt-4 pt-4 border-t border-zinc-800"
          >
            <div className="flex flex-col space-y-3">
              <Link
                to="/"
                onClick={() => setMobileMenuOpen(false)}
                className="text-zinc-300 hover:text-white transition-colors py-2"
              >
                Home
              </Link>
              <Link
                to="/eras"
                onClick={() => setMobileMenuOpen(false)}
                className="text-zinc-300 hover:text-white transition-colors py-2"
              >
                Eras
              </Link>
              <Link
                to="/artists"
                onClick={() => setMobileMenuOpen(false)}
                className="text-zinc-300 hover:text-white transition-colors py-2"
              >
                Artists
              </Link>
              <Link
                to="/albums"
                onClick={() => setMobileMenuOpen(false)}
                className="text-zinc-300 hover:text-white transition-colors py-2"
              >
                Albums
              </Link>
              <Link
                to="/timeline"
                onClick={() => setMobileMenuOpen(false)}
                className="text-amber-400 hover:text-amber-300 transition-colors py-2"
              >
                Timeline
              </Link>
              <Link
                to="/influence"
                onClick={() => setMobileMenuOpen(false)}
                className="text-amber-400 hover:text-amber-300 transition-colors py-2"
              >
                Influence Network
              </Link>
              <Link
                to="/context"
                onClick={() => setMobileMenuOpen(false)}
                className="text-amber-400 hover:text-amber-300 transition-colors py-2"
              >
                Jazz & Society
              </Link>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}

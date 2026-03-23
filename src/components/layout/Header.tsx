import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { SearchBar } from './SearchBar';

export function Header() {
  const [showExplore, setShowExplore] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const handleSearchOpenChange = (open: boolean) => {
    if (open) {
      setMobileMenuOpen(false);
      setShowExplore(false);
    }
  };

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
    <header className="bg-cream border-b border-border">
      <nav className="max-w-6xl mx-auto px-4 py-5" aria-label="Main navigation">
        <div className="flex items-center justify-between">
          <Link to="/" className="font-display uppercase tracking-[0.2em] text-xl hover:opacity-80 transition-opacity">
            <span className="text-coral font-black">Jazz</span>
            <span className="text-charcoal font-bold ml-1">Guide</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex gap-8 items-center">
            {[
              { to: '/', label: 'Home' },
              { to: '/eras', label: 'Eras' },
              { to: '/artists', label: 'Artists' },
              { to: '/albums', label: 'Albums' },
            ].map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="relative text-warm-gray hover:text-charcoal transition-colors text-sm tracking-wide uppercase after:absolute after:bottom-[-4px] after:left-0 after:w-0 after:h-[2px] after:bg-coral after:transition-all after:duration-300 hover:after:w-full"
              >
                {link.label}
              </Link>
            ))}
            <div className="relative">
              <button
                onClick={() => setShowExplore(!showExplore)}
                onBlur={() => setTimeout(() => setShowExplore(false), 150)}
                onKeyDown={(e) => e.key === 'Escape' && setShowExplore(false)}
                aria-expanded={showExplore}
                aria-haspopup="menu"
                aria-controls="explore-menu"
                className="text-coral hover:text-coral/80 transition-colors flex items-center gap-1 text-sm tracking-wide uppercase focus:outline-none focus:ring-2 focus:ring-coral focus:ring-offset-2 focus:ring-offset-cream rounded"
              >
                Explore
                <svg className={`w-3.5 h-3.5 transition-transform duration-200 ${showExplore ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showExplore && (
                <div
                  id="explore-menu"
                  role="menu"
                  className="absolute right-0 mt-3 w-52 rounded-lg bg-surface border border-border shadow-elevated z-50"
                >
                  <Link
                    to="/timeline"
                    role="menuitem"
                    className="block px-4 py-3 text-charcoal hover:text-coral hover:bg-border/30 transition-colors rounded-t-lg focus:outline-none focus:bg-border/30"
                  >
                    <div className="font-medium text-sm">Timeline</div>
                    <div className="text-xs text-warm-gray mt-0.5">Jazz through the ages</div>
                  </Link>
                  <Link
                    to="/influence"
                    role="menuitem"
                    className="block px-4 py-3 text-charcoal hover:text-coral hover:bg-border/30 transition-colors focus:outline-none focus:bg-border/30"
                  >
                    <div className="font-medium text-sm">Connection Finder</div>
                    <div className="text-xs text-warm-gray mt-0.5">Trace artist influence</div>
                  </Link>
                  <Link
                    to="/context"
                    role="menuitem"
                    className="block px-4 py-3 text-charcoal hover:text-coral hover:bg-border/30 transition-colors rounded-b-lg focus:outline-none focus:bg-border/30"
                  >
                    <div className="font-medium text-sm">Jazz & Society</div>
                    <div className="text-xs text-warm-gray mt-0.5">History & context</div>
                  </Link>
                </div>
              )}
            </div>
            <SearchBar onOpenChange={handleSearchOpenChange} forceClose={mobileMenuOpen} />
          </div>

          {/* Search (mobile) + hamburger */}
          <div className="flex md:hidden items-center gap-2">
            <SearchBar onOpenChange={handleSearchOpenChange} forceClose={mobileMenuOpen} />
            <button
              className="md:hidden p-2 text-warm-gray hover:text-coral focus:outline-none focus:ring-2 focus:ring-coral rounded"
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
        </div>

        {/* Mobile menu — full-screen overlay */}
        {mobileMenuOpen && (
          <div
            id="mobile-menu"
            className="md:hidden fixed inset-0 top-[65px] bg-cream z-50 px-6 py-8"
          >
            <div className="flex flex-col space-y-1">
              {[
                { to: '/', label: 'Home' },
                { to: '/eras', label: 'Eras' },
                { to: '/artists', label: 'Artists' },
                { to: '/albums', label: 'Albums' },
              ].map((link) => (
                <Link
                  key={link.to}
                  to={link.to}
                  onClick={() => setMobileMenuOpen(false)}
                  className="text-charcoal hover:text-coral transition-colors py-3 text-2xl font-display tracking-wide border-b border-border"
                >
                  {link.label}
                </Link>
              ))}
              <div className="pt-4 mt-2">
                <p className="text-xs text-warm-gray uppercase tracking-widest mb-3 font-mono">Explore</p>
                {[
                  { to: '/timeline', label: 'Timeline' },
                  { to: '/influence', label: 'Connection Finder' },
                  { to: '/context', label: 'Jazz & Society' },
                ].map((link) => (
                  <Link
                    key={link.to}
                    to={link.to}
                    onClick={() => setMobileMenuOpen(false)}
                    className="block text-coral hover:text-coral/80 transition-colors py-3 text-lg font-heading"
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}

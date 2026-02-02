import { Link } from 'react-router-dom';

export function Header() {
  return (
    <header className="bg-zinc-900 border-b border-zinc-800">
      <nav className="max-w-6xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-white hover:text-amber-400 transition-colors">
            🎷 Jazz Guide
          </Link>
          <div className="flex gap-6">
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
          </div>
        </div>
      </nav>
    </header>
  );
}

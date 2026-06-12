import { Link } from 'react-router-dom';
import { SEO } from '../components/SEO';

export function NotFound() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-24 text-center page-enter">
      <SEO title="Page not found" description="The page you are looking for is not in the catalog." />
      <p className="text-7xl font-display text-coral mb-4">404</p>
      <h1 className="text-2xl font-heading text-charcoal mb-3">This track skipped</h1>
      <p className="text-warm-gray mb-8">
        The page you are looking for is not in the catalog. It may have moved, or never existed.
      </p>
      <div className="flex flex-wrap gap-3 justify-center">
        <Link
          to="/"
          className="px-5 py-2.5 rounded-full bg-coral text-white font-medium hover:bg-coral/90 transition-colors"
        >
          Back home
        </Link>
        <Link
          to="/paths"
          className="px-5 py-2.5 rounded-full bg-surface border border-border text-charcoal hover:border-coral/40 transition-colors"
        >
          Browse the paths
        </Link>
      </div>
    </div>
  );
}

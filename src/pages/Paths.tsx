import { Link } from 'react-router-dom';
import pathsData from '../data/paths.json';
import { SEO } from '../components/SEO';
import { track } from '../utils/analytics';
import type { PathsData } from '../types';

const { agenda, paths } = pathsData as PathsData;

export function Paths() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-12 page-enter">
      <SEO
        title="Paths"
        description="Opinionated listening routes through jazz, built for players: a guitar lineage, the records that broke the language, late-night tone, groove, the avant-garde leap, and where to start tonight."
      />

      <header className="mb-12 max-w-3xl">
        <p className="text-xs font-mono uppercase tracking-widest text-coral mb-3">The agenda</p>
        <h1 className="text-4xl md:text-5xl font-display uppercase tracking-wide text-charcoal mb-6">
          Paths
        </h1>
        <p className="text-lg text-charcoal/80 leading-relaxed">{agenda}</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {paths.map((path, i) => (
          <Link
            key={path.id}
            to={`/path/${path.id}`}
            onClick={() => track('path_click', { path_id: path.id })}
            className="group block p-6 rounded-lg bg-surface border border-border shadow-card hover:shadow-card-hover hover:border-coral/30 transition-all duration-300"
          >
            <div className="flex items-baseline justify-between mb-3 font-mono text-xs text-warm-gray">
              <span>{String(i + 1).padStart(2, '0')}</span>
              <span>{path.albumIds.length} records</span>
            </div>
            <h2 className="text-2xl font-heading text-charcoal group-hover:text-coral transition-colors mb-1">
              {path.title}
            </h2>
            <p className="text-sm text-coral/80 mb-3 font-mono">{path.subtitle}</p>
            <p className="text-warm-gray leading-relaxed line-clamp-3">{path.rationale}</p>
            <span className="inline-block mt-4 text-coral text-sm group-hover:translate-x-1 transition-transform">
              Follow this path &rarr;
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}

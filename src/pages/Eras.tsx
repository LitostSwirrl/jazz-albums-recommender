import { Link } from 'react-router-dom';
import erasData from '../data/eras.json';
import { SEO } from '../components/SEO';
import type { Era } from '../types';

const eras = erasData as Era[];

export function Eras() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-12 page-enter">
      <SEO
        title="Jazz Eras"
        description="Explore the evolution of jazz through eight distinct periods, from early jazz and swing to bebop, hard bop, free jazz, fusion, and contemporary styles."
      />
      <h1 className="text-4xl font-bold mb-2 font-display text-charcoal">Jazz Eras</h1>
      <p className="text-warm-gray mb-8">
        Explore the evolution of jazz through eight distinct periods
      </p>

      {/* Timeline */}
      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-border hidden md:block" />

        <div className="space-y-8">
          {eras.map((era) => (
            <Link
              key={era.id}
              to={`/era/${era.id}`}
              className="group block relative pl-0 md:pl-20"
            >
              {/* Timeline dot */}
              <div
                className="absolute left-6 top-6 w-4 h-4 rounded-full border-2 border-border hidden md:block group-hover:scale-150 transition-transform"
                style={{ backgroundColor: era.color }}
              />

              <div
                className="p-6 rounded-xl bg-surface shadow-card group-hover:shadow-card-hover transition-all duration-300"
                style={{ borderLeftColor: era.color, borderLeftWidth: '4px' }}
              >
                <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4">
                  <h2 className="text-2xl font-bold text-charcoal font-heading group-hover:text-coral transition-colors">
                    {era.name}
                  </h2>
                  <span className="text-warm-gray font-mono">{era.period}</span>
                </div>

                <p className="text-warm-gray mb-4">{era.description}</p>

                <div className="flex flex-wrap gap-2">
                  {era.characteristics.slice(0, 3).map((char) => (
                    <span
                      key={char}
                      className="px-2 py-1 text-xs rounded bg-border-light text-warm-gray"
                    >
                      {char}
                    </span>
                  ))}
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

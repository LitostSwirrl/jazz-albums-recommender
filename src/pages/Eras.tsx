import { Link } from 'react-router-dom';
import erasData from '../data/eras.json';
import type { Era } from '../types';

const eras = erasData as Era[];

export function Eras() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <h1 className="text-4xl font-bold mb-2">Jazz Eras</h1>
      <p className="text-zinc-400 mb-8">
        Explore the evolution of jazz through eight distinct periods
      </p>

      {/* Timeline */}
      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-zinc-800 hidden md:block" />

        <div className="space-y-8">
          {eras.map((era) => (
            <Link
              key={era.id}
              to={`/era/${era.id}`}
              className="group block relative pl-0 md:pl-20"
            >
              {/* Timeline dot */}
              <div
                className="absolute left-6 top-6 w-4 h-4 rounded-full border-2 border-zinc-800 hidden md:block group-hover:scale-150 transition-transform"
                style={{ backgroundColor: era.color }}
              />

              <div
                className="p-6 rounded-lg bg-zinc-900 border border-zinc-800 group-hover:border-zinc-600 transition-all"
                style={{ borderLeftColor: era.color, borderLeftWidth: '4px' }}
              >
                <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4">
                  <h2 className="text-2xl font-bold text-white group-hover:text-amber-400 transition-colors">
                    {era.name}
                  </h2>
                  <span className="text-zinc-500 font-mono">{era.period}</span>
                </div>

                <p className="text-zinc-400 mb-4">{era.description}</p>

                <div className="flex flex-wrap gap-2">
                  {era.characteristics.slice(0, 3).map((char) => (
                    <span
                      key={char}
                      className="px-2 py-1 text-xs rounded bg-zinc-800 text-zinc-400"
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

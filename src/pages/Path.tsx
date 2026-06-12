import { useParams, Link } from 'react-router-dom';
import pathsData from '../data/paths.json';
import albumsData from '../data/albums.json';
import { AlbumCover } from '../components/AlbumCover';
import { SEO } from '../components/SEO';
import { track } from '../utils/analytics';
import { prefetchRoute } from '../utils/prefetch';
import type { PathsData, Album } from '../types';

const { paths } = pathsData as PathsData;
const albums = albumsData as Album[];
const albumById = new Map(albums.map((a) => [a.id, a]));

export function Path() {
  const { id } = useParams<{ id: string }>();
  const path = paths.find((p) => p.id === id);

  if (!path) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12 text-center">
        <h1 className="text-2xl font-bold text-coral">Path not found</h1>
        <Link to="/paths" className="text-coral hover:text-coral/80 mt-4 inline-block">
          &larr; All paths
        </Link>
      </div>
    );
  }

  const pathAlbums = path.albumIds
    .map((aid) => albumById.get(aid))
    .filter((a): a is Album => Boolean(a));

  return (
    <div className="max-w-4xl mx-auto px-4 py-12 page-enter">
      <SEO title={path.title} description={path.subtitle} />

      {/* Breadcrumb */}
      <div className="mb-6">
        <Link to="/paths" className="text-warm-gray hover:text-coral transition-colors">
          Paths
        </Link>
        <span className="text-border mx-2">/</span>
        <span className="text-charcoal">{path.title}</span>
      </div>

      <header className="mb-10">
        <h1 className="text-4xl md:text-5xl font-display uppercase tracking-wide text-charcoal mb-2">
          {path.title}
        </h1>
        <p className="text-lg text-coral font-heading mb-6">{path.subtitle}</p>
        <p className="text-lg text-charcoal/80 leading-relaxed">{path.rationale}</p>
      </header>

      {/* For the player */}
      <section className="mb-12 p-6 rounded-lg bg-surface border-l-4 border-coral shadow-card">
        <p className="text-xs font-mono uppercase tracking-widest text-coral mb-2">For the player</p>
        <p className="text-charcoal/90 leading-relaxed">{path.forThePlayer}</p>
      </section>

      {/* Listening order */}
      <section>
        <h2 className="text-2xl font-heading text-charcoal mb-6">The listening order</h2>
        <ol className="space-y-3">
          {pathAlbums.map((album, i) => (
            <li key={album.id}>
              <Link
                to={`/album/${album.id}`}
                onClick={() => track('album_click', { album_id: album.id, source: 'path' })}
                onMouseEnter={() => prefetchRoute('album')}
                onFocus={() => prefetchRoute('album')}
                className="group flex items-center gap-4 p-3 rounded-lg bg-surface border border-border hover:border-coral/40 hover:shadow-card-hover transition-all"
              >
                <span className="flex-shrink-0 w-7 text-center font-mono text-warm-gray text-sm">
                  {i + 1}
                </span>
                <div className="flex-shrink-0 w-14 h-14 rounded-sm overflow-hidden">
                  <AlbumCover
                    coverUrl={album.coverUrl}
                    title={album.title}
                    size="sm"
                    pixelWidth={112}
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="font-semibold text-charcoal group-hover:text-coral transition-colors truncate">
                    {album.title}
                  </h3>
                  <p className="text-sm text-warm-gray truncate">
                    {album.artist} &middot; {album.year}
                  </p>
                </div>
                <svg
                  className="w-4 h-4 text-warm-gray group-hover:text-coral transition-colors flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </li>
          ))}
        </ol>
        {pathAlbums.length !== path.albumIds.length && (
          <p className="text-warm-gray/60 text-sm mt-4 font-heading italic">
            Some records in this path are not yet in the catalog.
          </p>
        )}
      </section>
    </div>
  );
}

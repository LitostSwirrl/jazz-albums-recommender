import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import artistsData from '../data/artists.json';
import albumsData from '../data/albums.json';
import erasData from '../data/eras.json';
import type { Artist as ArtistType, Album, Era, ArtistConnection } from '../types';
import { MiniInfluenceNetwork } from '../components/graph';
import { ArtistPhoto } from '../components/ArtistPhoto';
import { AlbumCover } from '../components/AlbumCover';
import { SEO } from '../components/SEO';
import { getConnection } from '../utils/connections';

const artists = artistsData as ArtistType[];
const albums = albumsData as Album[];
const eras = erasData as Era[];

function SourceBadge({ source }: { source: ArtistConnection['sources'][number] }) {
  const labels: Record<ArtistConnection['sources'][number]['type'], string> = {
    wikipedia: 'Wikipedia',
    allmusic: 'AllMusic',
    book: 'Book',
    interview: 'Interview',
    'liner-notes': 'Liner Notes',
  };
  const label = labels[source.type];

  if (source.url) {
    return (
      <a
        href={source.url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-zinc-800 text-zinc-400 hover:text-amber-400 transition-colors"
      >
        {label}
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
      </a>
    );
  }

  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-zinc-800 text-zinc-500">
      {label}
      {source.title && `: ${source.title}`}
    </span>
  );
}

function ConnectionCard({ artist, connection }: { artist: ArtistType; connection?: ArtistConnection }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = connection && (connection.explanation || connection.sources.length > 0);

  return (
    <div className="rounded bg-zinc-900 border border-zinc-800 hover:border-zinc-600 transition-all">
      <div className="flex items-center justify-between p-3">
        <Link to={`/artist/${artist.id}`} className="flex-1 min-w-0">
          <span className="text-white hover:text-amber-400">{artist.name}</span>
          <span className="text-xs text-zinc-500 ml-2">{artist.instruments.slice(0, 2).join(', ')}</span>
        </Link>
        <div className="flex items-center gap-2 ml-2 flex-shrink-0">
          {connection?.verified && (
            <span className="text-emerald-500" title="Source verified">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </span>
          )}
          {hasDetails && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-zinc-500 hover:text-zinc-300 transition-colors"
              title={expanded ? 'Hide details' : 'Show connection details'}
            >
              <svg className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}
        </div>
      </div>
      {expanded && connection && (
        <div className="px-3 pb-3 border-t border-zinc-800">
          {connection.explanation && (
            <p className="text-sm text-zinc-400 mt-2 leading-relaxed italic">
              &ldquo;{connection.explanation}&rdquo;
            </p>
          )}
          {connection.sources.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {connection.sources.map((source, i) => (
                <SourceBadge key={i} source={source} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function Artist() {
  const { id } = useParams<{ id: string }>();
  const artist = artists.find((a) => a.id === id);

  if (!artist) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12 text-center">
        <h1 className="text-2xl font-bold text-red-400">Artist not found</h1>
        <Link to="/artists" className="text-amber-400 hover:underline mt-4 inline-block">
          ← Back to Artists
        </Link>
      </div>
    );
  }

  const artistAlbums = albums.filter((a) => a.artistId === artist.id);
  const artistEras = eras.filter((e) => artist.eras.includes(e.id));
  const influencedArtists = artists.filter((a) => artist.influences.includes(a.id));
  const influencedByArtists = artists.filter((a) => artist.influencedBy.includes(a.id));

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <SEO
        title={artist.name}
        description={artist.bio.slice(0, 160)}
        image={artist.imageUrl}
        type="profile"
      />
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link to="/artists" className="text-zinc-500 hover:text-zinc-300">
          Artists
        </Link>
        <span className="text-zinc-600 mx-2">/</span>
        <span className="text-zinc-300">{artist.name}</span>
      </div>

      {/* Header */}
      <header className="flex flex-col md:flex-row gap-8 mb-12">
        <ArtistPhoto
          imageUrl={artist.imageUrl}
          name={artist.name}
          size="xl"
          className="flex-shrink-0"
        />
        <div>
          <h1 className="text-4xl font-bold mb-2">{artist.name}</h1>
          <p className="text-xl text-zinc-400 mb-4">
            {artist.birthYear}–{artist.deathYear || 'present'} · {artist.instruments.join(', ')}
          </p>
          <div className="flex flex-wrap gap-2">
            {artistEras.map((era) => (
              <Link
                key={era.id}
                to={`/era/${era.id}`}
                className="px-3 py-1 rounded-full text-sm hover:opacity-80 transition-opacity"
                style={{ backgroundColor: era.color + '30', color: era.color }}
              >
                {era.name}
              </Link>
            ))}
          </div>
        </div>
      </header>

      {/* Biography */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold mb-4">Biography</h2>
        <p className="text-lg text-zinc-300 leading-relaxed">{artist.bio}</p>
        {artist.wikipedia && (
          <a
            href={artist.wikipedia}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block mt-4 text-amber-400 hover:text-amber-300"
          >
            Read more on Wikipedia →
          </a>
        )}
      </section>

      {/* Influence Network Visual */}
      <section className="mb-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">Influence Network</h2>
          <Link
            to="/influence"
            className="text-amber-400 hover:text-amber-300 text-sm flex items-center gap-1"
          >
            Explore full network
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </Link>
        </div>
        <p className="text-zinc-500 text-sm mb-4">
          {influencedByArtists.length > 0 && `Influenced by ${influencedByArtists.length} artist${influencedByArtists.length > 1 ? 's' : ''}`}
          {influencedByArtists.length > 0 && influencedArtists.length > 0 && ' · '}
          {influencedArtists.length > 0 && `Influenced ${influencedArtists.length} artist${influencedArtists.length > 1 ? 's' : ''}`}
        </p>
        <MiniInfluenceNetwork artist={artist} allArtists={artists} eras={eras} />
      </section>

      {/* Influence Lists */}
      <section className="mb-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Influenced By */}
          <div>
            <h3 className="text-lg font-semibold text-zinc-400 mb-4">Influenced by</h3>
            {influencedByArtists.length > 0 ? (
              <div className="space-y-2">
                {influencedByArtists.map((a) => (
                  <ConnectionCard
                    key={a.id}
                    artist={a}
                    connection={getConnection(a.id, artist.id)}
                  />
                ))}
              </div>
            ) : (
              <p className="text-zinc-600">No documented influences</p>
            )}
          </div>

          {/* Influenced */}
          <div>
            <h3 className="text-lg font-semibold text-zinc-400 mb-4">Influenced</h3>
            {influencedArtists.length > 0 ? (
              <div className="space-y-2">
                {influencedArtists.map((a) => (
                  <ConnectionCard
                    key={a.id}
                    artist={a}
                    connection={getConnection(artist.id, a.id)}
                  />
                ))}
              </div>
            ) : (
              <p className="text-zinc-600">No documented influence</p>
            )}
          </div>
        </div>
      </section>

      {/* Discography */}
      <section>
        <h2 className="text-2xl font-bold mb-6">Key Albums</h2>
        {artistAlbums.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {artistAlbums.map((album) => (
              <Link
                key={album.id}
                to={`/album/${album.id}`}
                className="group p-4 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-600 transition-all"
              >
                <div className="mb-3 w-full">
                  <AlbumCover coverUrl={album.coverUrl} title={album.title} size="sm" />
                </div>
                <h3 className="font-semibold text-white group-hover:text-amber-400 transition-colors">
                  {album.title}
                </h3>
                <p className="text-sm text-zinc-500">{album.year} · {album.label}</p>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-zinc-500">No albums listed yet.</p>
        )}
      </section>
    </div>
  );
}

import { useParams, Link } from 'react-router-dom';
import albumsData from '../data/albums.json';
import artistsData from '../data/artists.json';
import erasData from '../data/eras.json';
import { AlbumCover } from '../components/AlbumCover';
import { ArtistPhoto } from '../components/ArtistPhoto';
import { RelatedAlbums } from '../components/discovery/RelatedAlbums';
import { SpotifyIcon, YouTubeIcon } from '../components/icons';
import type { Album as AlbumType, Artist, Era } from '../types';

const albums = albumsData as AlbumType[];
const artists = artistsData as Artist[];
const eras = erasData as Era[];

export function Album() {
  const { id } = useParams<{ id: string }>();
  const album = albums.find((a) => a.id === id);

  if (!album) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12 text-center">
        <h1 className="text-2xl font-bold text-red-400">Album not found</h1>
        <Link to="/albums" className="text-amber-400 hover:underline mt-4 inline-block">
          ← Back to Albums
        </Link>
      </div>
    );
  }

  const artist = artists.find((a) => a.id === album.artistId);
  const era = eras.find((e) => e.id === album.era);

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link to="/albums" className="text-zinc-500 hover:text-zinc-300">
          Albums
        </Link>
        <span className="text-zinc-600 mx-2">/</span>
        <span className="text-zinc-300">{album.title}</span>
      </div>

      {/* Header */}
      <header className="flex flex-col md:flex-row gap-8 mb-12">
        <div className="flex-shrink-0">
          <AlbumCover coverUrl={album.coverUrl} title={album.title} size="lg" />
        </div>
        <div className="flex-1">
          <h1 className="text-4xl font-bold mb-2">{album.title}</h1>
          <Link
            to={`/artist/${album.artistId}`}
            className="text-2xl text-amber-400 hover:text-amber-300 transition-colors"
          >
            {album.artist}
          </Link>

          <div className="flex flex-wrap items-center gap-4 mt-4 text-zinc-400">
            <Link
              to={`/albums?year=${album.year}`}
              className="hover:text-amber-400 transition-colors"
            >
              {album.year}
            </Link>
            <span>·</span>
            <Link
              to={`/albums?label=${encodeURIComponent(album.label)}`}
              className="hover:text-amber-400 transition-colors"
            >
              {album.label}
            </Link>
            {era && (
              <>
                <span>·</span>
                <Link
                  to={`/era/${era.id}`}
                  className="px-3 py-1 rounded-full text-sm hover:opacity-80 transition-opacity"
                  style={{ backgroundColor: era.color + '30', color: era.color }}
                >
                  {era.name}
                </Link>
              </>
            )}
          </div>

          <div className="flex flex-wrap gap-2 mt-4">
            {album.genres.map((genre) => (
              <Link
                key={genre}
                to={`/albums?genre=${encodeURIComponent(genre)}`}
                className="px-3 py-1 rounded-full text-sm bg-zinc-800 text-zinc-300 hover:bg-amber-500/20 hover:text-amber-400 transition-colors"
              >
                {genre}
              </Link>
            ))}
          </div>
        </div>
      </header>

      {/* Description */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold mb-4">About This Album</h2>
        <p className="text-lg text-zinc-300 leading-relaxed mb-6">{album.description}</p>

        <h3 className="text-xl font-semibold mb-3 text-amber-400">Why It Matters</h3>
        <p className="text-zinc-300 leading-relaxed">{album.significance}</p>
      </section>

      {/* Critics Reviews */}
      {album.reviews && album.reviews.length > 0 && (
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4">What Critics Said</h2>
          <div className="space-y-4">
            {album.reviews.map((review, index) => (
              <blockquote
                key={index}
                className="p-4 rounded-lg bg-zinc-900 border-l-4 border-amber-500"
              >
                <p className="text-zinc-300 italic mb-2">"{review.quote}"</p>
                <footer className="text-sm text-zinc-500">
                  — {review.author && `${review.author}, `}
                  {review.url ? (
                    <a
                      href={review.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-amber-400 hover:underline"
                    >
                      {review.source}
                    </a>
                  ) : (
                    <span>{review.source}</span>
                  )}
                  {review.rating && (
                    <span className="ml-2 text-amber-400">({review.rating}/5)</span>
                  )}
                </footer>
              </blockquote>
            ))}
          </div>
        </section>
      )}

      {/* Key Tracks */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold mb-4">Key Tracks</h2>
        <ul className="space-y-2">
          {album.keyTracks.map((track, index) => (
            <li
              key={track}
              className="flex items-center gap-4 p-3 rounded bg-zinc-900 border border-zinc-800"
            >
              <span className="w-8 h-8 flex items-center justify-center rounded-full bg-zinc-800 text-zinc-400 text-sm">
                {index + 1}
              </span>
              <span className="text-white">{track}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* Listen & Learn More */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold mb-4">Listen & Learn More</h2>

        {/* Streaming Links */}
        {(album.spotifyUrl || album.youtubeUrl) && (
          <div className="flex flex-wrap gap-4 mb-4">
            {album.spotifyUrl && (
              <a
                href={album.spotifyUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#1DB954] text-black font-medium hover:bg-[#1ed760] transition-colors"
              >
                <SpotifyIcon className="w-5 h-5" />
                Listen on Spotify
              </a>
            )}
            {album.youtubeUrl && (
              <a
                href={album.youtubeUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#FF0000] text-white font-medium hover:bg-[#cc0000] transition-colors"
              >
                <YouTubeIcon className="w-5 h-5" />
                Watch on YouTube
              </a>
            )}
          </div>
        )}

        {/* Reference Links */}
        <div className="flex flex-wrap gap-4">
          {album.discogs && (
            <a
              href={album.discogs}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition-colors"
            >
              View on Discogs →
            </a>
          )}
          {album.allMusic && (
            <a
              href={album.allMusic}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition-colors"
            >
              View on AllMusic →
            </a>
          )}
        </div>
      </section>

      {/* Artist info */}
      {artist && (
        <section className="mb-12 p-6 rounded-lg bg-zinc-900 border border-zinc-800">
          <h2 className="text-xl font-bold mb-4">About the Artist</h2>
          <Link
            to={`/artist/${artist.id}`}
            className="flex items-center gap-4 group"
          >
            <ArtistPhoto
              imageUrl={artist.imageUrl}
              name={artist.name}
              size="lg"
              showInstrument={artist.instruments[0]}
            />
            <div>
              <h3 className="text-lg font-semibold text-white group-hover:text-amber-400 transition-colors">
                {artist.name}
              </h3>
              <p className="text-zinc-500">{artist.instruments.join(', ')}</p>
            </div>
          </Link>
        </section>
      )}

      {/* Related Albums */}
      <section>
        <h2 className="text-2xl font-bold mb-6">Discover More</h2>
        <RelatedAlbums currentAlbum={album} allAlbums={albums} />
      </section>
    </div>
  );
}

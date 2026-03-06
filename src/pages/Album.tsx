import { useParams, Link } from 'react-router-dom';
import albumsData from '../data/albums.json';
import artistsData from '../data/artists.json';
import erasData from '../data/eras.json';
import { AlbumCover } from '../components/AlbumCover';
import { ArtistPhoto } from '../components/ArtistPhoto';
import { RelatedAlbums } from '../components/discovery/RelatedAlbums';
import { HistoricalEventCard } from '../components/context/HistoricalEventCard';
import { SpotifyIcon, AppleMusicIcon, YouTubeMusicIcon, YouTubeIcon } from '../components/icons';
import { SEO } from '../components/SEO';
import { getEventsForAlbum } from '../utils/historicalContext';
import { isForwardLooking } from '../utils/discovery';
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
        <h1 className="text-2xl font-bold text-coral">Album not found</h1>
        <Link to="/albums" className="text-coral hover:text-coral/80 mt-4 inline-block">
          &larr; Back to Albums
        </Link>
      </div>
    );
  }

  const artist = artists.find((a) => a.id === album.artistId);
  const era = eras.find((e) => e.id === album.era);
  const forwardLooking = isForwardLooking(album);

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 page-enter">
      <SEO
        title={`${album.title} by ${album.artist}`}
        description={album.description.slice(0, 160)}
        image={album.coverUrl}
        type="music.album"
      />
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link to="/albums" className="text-warm-gray hover:text-coral transition-colors">
          Albums
        </Link>
        <span className="text-border mx-2">/</span>
        <span className="text-charcoal">{album.title}</span>
      </div>

      {/* Header */}
      <header className="flex flex-col md:flex-row gap-8 mb-12">
        <div className="flex-shrink-0 rounded-sm overflow-hidden shadow-elevated">
          <AlbumCover coverUrl={album.coverUrl} title={album.title} size="lg" priority />
        </div>
        <div className="flex-1">
          <h1 className="text-4xl md:text-5xl font-display text-charcoal uppercase tracking-wide mb-2">
            {album.title}
          </h1>
          <Link
            to={`/artist/${album.artistId}`}
            className="text-2xl text-coral font-heading hover:text-coral/80 transition-colors"
          >
            {album.artist}
          </Link>

          <div className="flex flex-wrap items-center gap-4 mt-4 font-mono text-warm-gray">
            {album.year ? (
              <Link to={`/albums?year=${album.year}`} className="hover:text-coral transition-colors">
                {album.year}
              </Link>
            ) : (
              <span className="text-warm-gray/50 font-heading italic text-sm not-italic font-mono">Year unknown</span>
            )}
            <span>&middot;</span>
            <Link
              to={`/albums?label=${encodeURIComponent(album.label)}`}
              className="hover:text-coral transition-colors"
            >
              {album.label}
            </Link>
          </div>

          {/* Era + Genre distinction */}
          <div className="flex flex-col gap-3 mt-4">
            {/* Era badge */}
            {era && (
              <Link
                to={`/era/${era.id}`}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded border-l-4 bg-surface border border-border hover:opacity-80 transition-opacity self-start"
                style={{ borderLeftColor: era.color }}
              >
                <span className="text-[10px] uppercase tracking-wider font-semibold text-warm-gray">Era</span>
                <span className="text-sm font-medium text-charcoal">{era.name.split(' ')[0]}</span>
              </Link>
            )}

            {/* Genre pills */}
            {album.genres.length > 0 && (
              <div
                className="flex flex-wrap items-center gap-2 px-3 py-1.5 rounded border-l-4 bg-surface border border-border self-start"
                style={{ borderLeftColor: era?.color }}
              >
                <span className="text-[10px] uppercase tracking-wider font-semibold text-warm-gray">Genre</span>
                {album.genres.map((genre) => (
                  <Link
                    key={genre}
                    to={`/albums?genre=${encodeURIComponent(genre)}`}
                    className="px-2.5 py-0.5 rounded-full text-sm bg-border/50 text-charcoal hover:bg-coral/10 hover:text-coral transition-colors"
                  >
                    {genre}
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Forward-looking indicator */}
          {forwardLooking.ahead && forwardLooking.futureEra && (
            <p className="mt-3 text-sm font-heading italic text-warm-gray">
              <span className="not-italic">&rarr;</span> Recorded during the {era?.name.split(' ')[0]} period, but pointing toward {forwardLooking.futureEra}
            </p>
          )}
        </div>
      </header>

      {/* Description */}
      <section className="mb-12">
        <h2 className="text-2xl font-heading text-charcoal mb-4">About This Album</h2>
        <p className="text-lg text-charcoal/80 leading-relaxed mb-6">{album.description}</p>
        {/^.{10,60} is a .{5,40} (album|record) by .{5,40} from \d{4}/i.test(album.description) && (
          <p className="text-xs text-warm-gray/50 font-mono -mt-4 mb-6">Limited editorial info available</p>
        )}

        <h3 className="text-xl font-heading text-coral mb-3">Why It Matters</h3>
        <p className="text-charcoal/80 leading-relaxed">{album.significance}</p>
        {/^A .{5,40} (entry|album|recording) from \d{4}/i.test(album.significance) && (
          <p className="text-xs text-warm-gray/50 font-mono mt-2">Limited editorial info available</p>
        )}
        {album.wikipedia && (
          <a
            href={album.wikipedia}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block mt-4 text-coral hover:text-coral/80 transition-colors"
          >
            Read more on Wikipedia &rarr;
          </a>
        )}
      </section>

      {/* Historical Context */}
      <AlbumHistoricalContext albumId={album.id} />

      {/* Critics Reviews */}
      {album.reviews && album.reviews.length > 0 && (
        <section className="mb-12">
          <h2 className="text-2xl font-heading text-charcoal mb-4">What Critics Said</h2>
          <div className="space-y-4">
            {album.reviews.map((review, index) => (
              <blockquote
                key={index}
                className="p-5 rounded-lg bg-surface border-l-4 border-coral shadow-card"
              >
                <p className="text-charcoal font-heading italic mb-2">&ldquo;{review.quote}&rdquo;</p>
                <footer className="text-sm text-warm-gray">
                  &mdash; {review.author && `${review.author}, `}
                  {review.url ? (
                    <a
                      href={review.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-coral hover:underline"
                    >
                      {review.source}
                    </a>
                  ) : (
                    <span>{review.source}</span>
                  )}
                  {review.rating && (
                    <span className="ml-2 text-coral">({review.rating}/5)</span>
                  )}
                </footer>
              </blockquote>
            ))}
          </div>
        </section>
      )}

      {/* Key Tracks */}
      <section className="mb-12">
        <h2 className="text-2xl font-heading text-charcoal mb-4">Key Tracks</h2>
        {album.keyTracks.length === 0 ? (
          <p className="text-warm-gray/60 font-heading italic text-sm">Key tracks not yet listed.</p>
        ) : (
          <ul className="space-y-2">
            {album.keyTracks.map((track, index) => (
              <li
                key={track}
                className="flex items-center gap-4 p-3 rounded-lg bg-surface border border-border"
              >
                <span className="w-8 h-8 flex items-center justify-center rounded-full border-2 border-coral text-coral text-sm font-mono">
                  {index + 1}
                </span>
                <span className="text-charcoal">{track}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Listen */}
      {(album.spotifyUrl || album.appleMusicUrl || album.youtubeMusicUrl || album.youtubeUrl) && (
        <section className="mb-12">
          <h2 className="text-2xl font-heading text-charcoal mb-4">Listen</h2>
          <div className="flex flex-wrap gap-3">
            {album.spotifyUrl && (
              <a
                href={album.spotifyUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#1DB954] text-white font-medium hover:bg-[#1ed760] transition-colors"
              >
                <SpotifyIcon className="w-5 h-5" />
                Spotify
              </a>
            )}
            {album.appleMusicUrl && (
              <a
                href={album.appleMusicUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#FA243C] text-white font-medium hover:bg-[#d91e33] transition-colors"
              >
                <AppleMusicIcon className="w-5 h-5" />
                Apple Music
              </a>
            )}
            {album.youtubeMusicUrl && (
              <a
                href={album.youtubeMusicUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#FF0000] text-white font-medium hover:bg-[#cc0000] transition-colors"
              >
                <YouTubeMusicIcon className="w-5 h-5" />
                YouTube Music
              </a>
            )}
            {album.youtubeUrl && (
              <a
                href={album.youtubeUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#333333] text-white font-medium hover:bg-[#444444] transition-colors"
              >
                <YouTubeIcon className="w-5 h-5" />
                YouTube
              </a>
            )}
          </div>
          {album.spotifyUrl && (() => {
            const match = album.spotifyUrl.match(/album\/([A-Za-z0-9]+)/);
            if (!match) return null;
            return (
              <div className="mt-6 rounded-xl overflow-hidden">
                <iframe
                  src={`https://open.spotify.com/embed/album/${match[1]}?utm_source=generator&theme=0`}
                  width="100%"
                  height="352"
                  frameBorder="0"
                  allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                  loading="lazy"
                  title={`${album.title} on Spotify`}
                />
              </div>
            );
          })()}
        </section>
      )}

      {/* Artist info */}
      {artist && (
        <section className="mb-12 p-6 rounded-lg bg-surface border border-border shadow-card">
          <h2 className="text-xl font-heading text-charcoal mb-4">About the Artist</h2>
          <Link
            to={`/artist/${artist.id}`}
            className="flex items-center gap-4 group"
          >
            <ArtistPhoto
              imageUrl={artist.imageUrl}
              name={artist.name}
              size="lg"
            />
            <div>
              <h3 className="text-lg font-semibold text-charcoal group-hover:text-coral transition-colors">
                {artist.name}
              </h3>
              <p className="text-warm-gray">{artist.instruments.join(', ')}</p>
            </div>
          </Link>
        </section>
      )}

      {/* Related Albums */}
      <section>
        <h2 className="text-2xl font-heading text-charcoal mb-6">Discover More</h2>
        <RelatedAlbums currentAlbum={album} allAlbums={albums} allArtists={artists} />
      </section>
    </div>
  );
}

function AlbumHistoricalContext({ albumId }: { albumId: string }) {
  const events = getEventsForAlbum(albumId);

  if (events.length === 0) return null;

  return (
    <section className="mb-12">
      <h2 className="text-2xl font-heading text-charcoal mb-4">The World Around This Album</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {events.map((event) => (
          <HistoricalEventCard key={event.id} event={event} compact />
        ))}
      </div>
    </section>
  );
}

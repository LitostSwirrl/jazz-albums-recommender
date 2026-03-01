import { Link } from 'react-router-dom';
import type { HistoricalEvent, Album, Artist } from '../../types';
import { getCategoryConfig, formatEventYear } from '../../utils/historicalContext';
import { CategoryBadge } from './CategoryBadge';
import albumsData from '../../data/albums.json';
import artistsData from '../../data/artists.json';

const albums = albumsData as Album[];
const artists = artistsData as Artist[];

interface HistoricalEventCardProps {
  event: HistoricalEvent;
  compact?: boolean;
}

export function HistoricalEventCard({ event, compact = false }: HistoricalEventCardProps) {
  const config = getCategoryConfig(event.category);

  if (compact) {
    return (
      <div
        className="p-4 rounded-lg bg-surface border border-border shadow-card"
        style={{ borderLeftWidth: '3px', borderLeftColor: config.color }}
      >
        <div className="flex items-start justify-between gap-2 mb-2">
          <CategoryBadge category={event.category} />
          <span className="text-xs text-warm-gray font-mono whitespace-nowrap">
            {formatEventYear(event)}
          </span>
        </div>
        <h4 className="font-semibold text-charcoal text-sm mb-1">{event.title}</h4>
        <p className="text-warm-gray text-sm leading-relaxed">{event.jazzConnection}</p>
      </div>
    );
  }

  const relatedAlbums = albums.filter((a) => event.relatedAlbumIds?.includes(a.id));
  const relatedArtists = artists.filter((a) => event.relatedArtistIds?.includes(a.id));

  return (
    <div
      className="p-5 rounded-lg bg-surface border border-border shadow-card"
      style={{ borderLeftWidth: '4px', borderLeftColor: config.color }}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <CategoryBadge category={event.category} size="md" />
        <span className="text-sm text-warm-gray font-mono whitespace-nowrap">
          {formatEventYear(event)}
        </span>
      </div>

      <h3 className="text-lg font-bold text-charcoal mb-2">{event.title}</h3>
      <p className="text-warm-gray text-sm leading-relaxed mb-3">{event.description}</p>

      <div className="p-3 rounded-md bg-cream mb-3">
        <p className="text-sm font-medium text-charcoal mb-1" style={{ color: config.color }}>
          Jazz Connection
        </p>
        <p className="text-charcoal text-sm leading-relaxed">{event.jazzConnection}</p>
      </div>

      {(relatedArtists.length > 0 || relatedAlbums.length > 0) && (
        <div className="flex flex-wrap gap-2">
          {relatedArtists.map((artist) => (
            <Link
              key={artist.id}
              to={`/artist/${artist.id}`}
              className="px-2 py-1 text-xs rounded-full bg-cream text-charcoal border border-border hover:border-coral hover:text-coral transition-colors"
            >
              {artist.name}
            </Link>
          ))}
          {relatedAlbums.map((album) => (
            <Link
              key={album.id}
              to={`/album/${album.id}`}
              className="px-2 py-1 text-xs rounded-full bg-coral/10 text-coral hover:bg-coral/20 transition-colors"
            >
              {album.title}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

import { Link } from 'react-router-dom';
import { AlbumCover } from '../AlbumCover';
import type { CuratedPlaylist, Album } from '../../types';

interface PlaylistCardProps {
  playlist: CuratedPlaylist;
  albums: Album[];
}

const MOOD_LABELS: Record<string, string> = {
  morning: 'Morning',
  afternoon: 'Afternoon',
  evening: 'Evening',
  night: 'Late Night',
  gateway: 'Essential',
  cerebral: 'Deep Listen',
  melancholy: 'Melancholy',
  joyful: 'Joyful',
  urban: 'NYC',
  european: 'European',
  spiritual: 'Spiritual',
  fusion: 'Electric',
};

export function PlaylistCard({ playlist, albums }: PlaylistCardProps) {
  const coverAlbum = albums.find((a) => a.id === playlist.coverAlbumId);
  const trackCount = playlist.tracks.length;

  return (
    <Link
      to={`/playlists/${playlist.id}`}
      className="group block rounded-lg overflow-hidden bg-surface border border-border shadow-card hover:shadow-card-hover transition-all"
    >
      <div className="relative aspect-square overflow-hidden">
        {coverAlbum ? (
          <AlbumCover
            coverUrl={coverAlbum.coverUrl}
            title={coverAlbum.title}
            size="md"
            className="w-full h-full group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full bg-charcoal/10 flex items-center justify-center">
            <span className="text-4xl font-display text-charcoal/30">{playlist.name[0]}</span>
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-charcoal/80 via-charcoal/20 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-4">
          <span className="inline-block px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-coral/80 text-white mb-1">
            {MOOD_LABELS[playlist.mood] ?? playlist.mood}
          </span>
          <h3 className="text-white font-display text-xl leading-tight">{playlist.name}</h3>
        </div>
      </div>
      <div className="p-4">
        <p className="text-sm text-warm-gray leading-relaxed line-clamp-2">{playlist.description}</p>
        <div className="flex items-center justify-between mt-3">
          <div className="flex gap-1.5 flex-wrap">
            {playlist.tags.map((tag) => (
              <span
                key={tag}
                className="px-2 py-0.5 rounded-full text-xs bg-border/50 text-warm-gray"
              >
                {tag}
              </span>
            ))}
          </div>
          <span className="text-xs font-mono text-warm-gray/70 shrink-0 ml-2">
            {trackCount} tracks
          </span>
        </div>
      </div>
    </Link>
  );
}

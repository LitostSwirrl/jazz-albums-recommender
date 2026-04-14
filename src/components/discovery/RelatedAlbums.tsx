import { Link } from 'react-router-dom';
import type { Album, Artist } from '../../types';
import { AlbumCover } from '../AlbumCover';
import { getRelatedAlbums } from '../../utils/discovery';
import { track } from '../../utils/analytics';

interface RelatedAlbumsProps {
  currentAlbum: Album;
  allAlbums: Album[];
  allArtists?: Artist[];
}

export function RelatedAlbums({ currentAlbum, allAlbums, allArtists }: RelatedAlbumsProps) {
  const related = getRelatedAlbums(currentAlbum, allAlbums, 8);
  const artistMap = allArtists
    ? new Map(allArtists.map((a) => [a.id, a]))
    : null;

  const sections: { title: string; albums: Album[]; limit: number }[] = [];

  // Primary artist section (up to 16)
  if (related.artist.length > 0) {
    const primaryArtist = artistMap?.get(currentAlbum.artistId);
    const primaryName = primaryArtist?.name ?? currentAlbum.artist;
    sections.push({ title: `More from ${primaryName}`, albums: related.artist, limit: 16 });
  }

  // Secondary artist sections (up to 16)
  for (const sec of related.secondaryArtists) {
    const secArtist = artistMap?.get(sec.artistId);
    if (secArtist && sec.albums.length > 0) {
      sections.push({
        title: `More from ${secArtist.name}`,
        albums: sec.albums,
        limit: 16,
      });
    }
  }

  // Genre and label sections (up to 8)
  if (related.genre.length > 0) {
    sections.push({ title: `More ${currentAlbum.genres[0] || 'Jazz'}`, albums: related.genre, limit: 8 });
  }
  if (related.label.length > 0) {
    sections.push({ title: `More from ${currentAlbum.label}`, albums: related.label, limit: 8 });
  }
  if (related.year.length > 0) {
    sections.push({ title: `Albums from around ${currentAlbum.year}`, albums: related.year, limit: 8 });
  }

  if (sections.length === 0) return null;

  return (
    <div className="space-y-8">
      {sections.slice(0, 3).map((section) => (
        <div key={section.title}>
          <h3 className="text-lg font-semibold font-heading text-charcoal mb-4">{section.title}</h3>
          <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-thin">
            {section.albums.slice(0, section.limit).map((album) => (
              <Link
                key={album.id}
                to={`/album/${album.id}`}
                onClick={() => track('album_click', { album_id: album.id, source: 'related' })}
                className="group flex-shrink-0 w-36 md:w-44"
              >
                <div className="mb-2 group-hover:scale-105 transition-transform">
                  <AlbumCover coverUrl={album.coverUrl} title={album.title} size="sm" />
                </div>
                <h4 className="text-sm font-medium text-charcoal group-hover:text-coral transition-colors truncate">
                  {album.title}
                </h4>
                <p className="text-xs text-warm-gray truncate">{album.artist}</p>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

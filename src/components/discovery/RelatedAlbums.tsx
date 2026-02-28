import { Link } from 'react-router-dom';
import type { Album, Artist } from '../../types';
import { AlbumCover } from '../AlbumCover';
import { getRelatedAlbums } from '../../utils/discovery';

interface RelatedAlbumsProps {
  currentAlbum: Album;
  allAlbums: Album[];
  allArtists?: Artist[];
}

export function RelatedAlbums({ currentAlbum, allAlbums, allArtists }: RelatedAlbumsProps) {
  const related = getRelatedAlbums(currentAlbum, allAlbums, 4);
  const artistMap = allArtists
    ? new Map(allArtists.map((a) => [a.id, a]))
    : null;

  const sections: { title: string; albums: Album[] }[] = [];

  // Primary artist section
  if (related.artist.length > 0) {
    const primaryArtist = artistMap?.get(currentAlbum.artistId);
    const primaryName = primaryArtist?.name ?? currentAlbum.artist;
    sections.push({ title: `More from ${primaryName}`, albums: related.artist });
  }

  // Secondary artist sections (for collaborative albums)
  for (const sec of related.secondaryArtists) {
    const secArtist = artistMap?.get(sec.artistId);
    if (secArtist && sec.albums.length > 0) {
      sections.push({
        title: `More from ${secArtist.name}`,
        albums: sec.albums,
      });
    }
  }

  // Genre and label sections
  if (related.genre.length > 0) {
    sections.push({ title: `More ${currentAlbum.genres[0] || 'Jazz'}`, albums: related.genre });
  }
  if (related.label.length > 0) {
    sections.push({ title: `More from ${currentAlbum.label}`, albums: related.label });
  }
  if (related.year.length > 0) {
    sections.push({ title: `Albums from ${currentAlbum.year}`, albums: related.year });
  }

  if (sections.length === 0) return null;

  return (
    <div className="space-y-8">
      {sections.slice(0, 3).map((section) => (
        <div key={section.title}>
          <h3 className="text-lg font-semibold text-zinc-300 mb-4">{section.title}</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {section.albums.slice(0, 4).map((album) => (
              <Link
                key={album.id}
                to={`/album/${album.id}`}
                className="group"
              >
                <div className="mb-2 group-hover:scale-105 transition-transform">
                  <AlbumCover coverUrl={album.coverUrl} title={album.title} size="sm" />
                </div>
                <h4 className="text-sm font-medium text-white group-hover:text-amber-400 transition-colors truncate">
                  {album.title}
                </h4>
                <p className="text-xs text-zinc-500 truncate">{album.artist}</p>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

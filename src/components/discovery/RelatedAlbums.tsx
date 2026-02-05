import { Link } from 'react-router-dom';
import type { Album } from '../../types';
import { AlbumCover } from '../AlbumCover';
import { getRelatedAlbums } from '../../utils/discovery';

interface RelatedAlbumsProps {
  currentAlbum: Album;
  allAlbums: Album[];
}

export function RelatedAlbums({ currentAlbum, allAlbums }: RelatedAlbumsProps) {
  const related = getRelatedAlbums(currentAlbum, allAlbums, 4);

  const sections = [
    { title: `More from ${currentAlbum.artist}`, albums: related.artist },
    { title: `More ${currentAlbum.genres[0] || 'Jazz'}`, albums: related.genre },
    { title: `More from ${currentAlbum.label}`, albums: related.label },
    { title: `Albums from ${currentAlbum.year}`, albums: related.year },
  ].filter((section) => section.albums.length > 0);

  if (sections.length === 0) return null;

  return (
    <div className="space-y-8">
      {sections.slice(0, 2).map((section) => (
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

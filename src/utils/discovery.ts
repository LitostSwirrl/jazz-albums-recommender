import type { Album, Artist } from '../types';

// Get all unique genres from albums
export function getAllGenres(albums: Album[]): string[] {
  const genreSet = new Set<string>();
  albums.forEach((album) => {
    album.genres.forEach((genre) => genreSet.add(genre));
  });
  return Array.from(genreSet).sort();
}

// Get all unique labels from albums
export function getAllLabels(albums: Album[]): string[] {
  const labelSet = new Set<string>();
  albums.forEach((album) => labelSet.add(album.label));
  return Array.from(labelSet).sort();
}

// Get all unique instruments from artists
export function getAllInstruments(artists: Artist[]): string[] {
  const instrumentSet = new Set<string>();
  artists.forEach((artist) => {
    artist.instruments.forEach((inst) => instrumentSet.add(inst));
  });
  return Array.from(instrumentSet).sort();
}

// Get albums by genre
export function getAlbumsByGenre(albums: Album[], genre: string): Album[] {
  return albums.filter((album) =>
    album.genres.some((g) => g.toLowerCase() === genre.toLowerCase())
  );
}

// Get albums by label
export function getAlbumsByLabel(albums: Album[], label: string): Album[] {
  return albums.filter((album) =>
    album.label.toLowerCase() === label.toLowerCase()
  );
}

// Get albums by year
export function getAlbumsByYear(albums: Album[], year: number): Album[] {
  return albums.filter((album) => album.year === year);
}

// Get artists by instrument
export function getArtistsByInstrument(artists: Artist[], instrument: string): Artist[] {
  return artists.filter((artist) =>
    artist.instruments.some((i) => i.toLowerCase() === instrument.toLowerCase())
  );
}

// Get related albums for discovery
export function getRelatedAlbums(
  currentAlbum: Album,
  allAlbums: Album[],
  limit: number = 4
): { genre: Album[]; label: Album[]; year: Album[]; artist: Album[] } {
  const otherAlbums = allAlbums.filter((a) => a.id !== currentAlbum.id);

  // Same genre (primary genre)
  const genre = otherAlbums
    .filter((a) =>
      a.genres.some((g) => currentAlbum.genres.includes(g))
    )
    .slice(0, limit);

  // Same label
  const label = otherAlbums
    .filter((a) => a.label === currentAlbum.label)
    .slice(0, limit);

  // Same year (within 2 years)
  const year = otherAlbums
    .filter((a) => Math.abs(a.year - currentAlbum.year) <= 2)
    .slice(0, limit);

  // Same artist
  const artist = otherAlbums
    .filter((a) => a.artistId === currentAlbum.artistId)
    .slice(0, limit);

  return { genre, label, year, artist };
}

// Get a random album
export function getRandomAlbum(
  albums: Album[],
  exclude?: string,
  filter?: { era?: string; genre?: string; label?: string }
): Album | null {
  let filtered = albums;

  if (exclude) {
    filtered = filtered.filter((a) => a.id !== exclude);
  }

  if (filter?.era) {
    filtered = filtered.filter((a) => a.era === filter.era);
  }

  if (filter?.genre) {
    filtered = filtered.filter((a) =>
      a.genres.some((g) => g.toLowerCase() === filter.genre!.toLowerCase())
    );
  }

  if (filter?.label) {
    filtered = filtered.filter((a) =>
      a.label.toLowerCase() === filter.label!.toLowerCase()
    );
  }

  if (filtered.length === 0) return null;

  return filtered[Math.floor(Math.random() * filtered.length)];
}

// Get a random artist
export function getRandomArtist(
  artists: Artist[],
  exclude?: string,
  filter?: { era?: string; instrument?: string }
): Artist | null {
  let filtered = artists;

  if (exclude) {
    filtered = filtered.filter((a) => a.id !== exclude);
  }

  if (filter?.era) {
    filtered = filtered.filter((a) =>
      a.eras.includes(filter.era as Artist['eras'][number])
    );
  }

  if (filter?.instrument) {
    filtered = filtered.filter((a) =>
      a.instruments.some((i) => i.toLowerCase() === filter.instrument!.toLowerCase())
    );
  }

  if (filtered.length === 0) return null;

  return filtered[Math.floor(Math.random() * filtered.length)];
}

// Generate URL slugs
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

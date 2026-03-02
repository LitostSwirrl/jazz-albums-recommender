import type { Album, Artist, EraId } from '../types';

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
): { genre: Album[]; label: Album[]; year: Album[]; artist: Album[]; secondaryArtists: { artistId: string; albums: Album[] }[] } {
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

  // Same artist (primary)
  const artist = otherAlbums
    .filter((a) => a.artistId === currentAlbum.artistId)
    .slice(0, limit);

  // Secondary artists — albums by featured collaborators
  const secondaryArtists: { artistId: string; albums: Album[] }[] = [];
  if (currentAlbum.secondaryArtistIds) {
    for (const secId of currentAlbum.secondaryArtistIds) {
      const secAlbums = otherAlbums
        .filter((a) => a.artistId === secId)
        .slice(0, limit);
      if (secAlbums.length > 0) {
        secondaryArtists.push({ artistId: secId, albums: secAlbums });
      }
    }
  }

  return { genre, label, year, artist, secondaryArtists };
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

// Map genres to their "home" era (where they originated)
const GENRE_ERA_MAP: Record<string, EraId> = {
  'early jazz': 'early-jazz',
  'dixieland': 'early-jazz',
  'swing': 'swing',
  'big band': 'swing',
  'bebop': 'bebop',
  'cool jazz': 'cool-jazz',
  'bossa nova': 'cool-jazz',
  'chamber jazz': 'cool-jazz',
  'hard bop': 'hard-bop',
  'soul jazz': 'hard-bop',
  'post-bop': 'hard-bop',
  'modal jazz': 'hard-bop',
  'free jazz': 'free-jazz',
  'avant-garde jazz': 'free-jazz',
  'free improvisation': 'free-jazz',
  'spiritual jazz': 'free-jazz',
  'loft jazz': 'free-jazz',
  'experimental': 'free-jazz',
  'jazz fusion': 'fusion',
  'jazz-funk': 'fusion',
  'contemporary jazz': 'contemporary',
  'acid jazz': 'contemporary',
  'smooth jazz': 'contemporary',
};

const ERA_ORDER: EraId[] = [
  'early-jazz', 'swing', 'bebop', 'cool-jazz',
  'hard-bop', 'free-jazz', 'fusion', 'contemporary',
];

const ERA_DISPLAY_NAMES: Record<EraId, string> = {
  'early-jazz': 'Early Jazz',
  'swing': 'Swing',
  'bebop': 'Bebop',
  'cool-jazz': 'Cool Jazz',
  'hard-bop': 'Hard Bop',
  'free-jazz': 'Free Jazz',
  'fusion': 'Fusion',
  'contemporary': 'Contemporary',
};

/**
 * Check if an album's genres suggest forward-looking music beyond its era.
 * Returns ahead: true if any genre belongs to an era 2+ positions later.
 */
export function isForwardLooking(album: Album): {
  ahead: boolean;
  futureEra?: string;
  futureEraId?: EraId;
} {
  const albumEraIdx = ERA_ORDER.indexOf(album.era);
  if (albumEraIdx === -1) return { ahead: false };

  for (const genre of album.genres) {
    const genreEra = GENRE_ERA_MAP[genre];
    if (!genreEra) continue;
    const genreEraIdx = ERA_ORDER.indexOf(genreEra);
    if (genreEraIdx - albumEraIdx >= 2) {
      return {
        ahead: true,
        futureEra: ERA_DISPLAY_NAMES[genreEra],
        futureEraId: genreEra,
      };
    }
  }

  return { ahead: false };
}

// Generate URL slugs
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

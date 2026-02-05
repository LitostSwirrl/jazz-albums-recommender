export type EraId =
  | 'early-jazz'
  | 'swing'
  | 'bebop'
  | 'cool-jazz'
  | 'hard-bop'
  | 'free-jazz'
  | 'fusion'
  | 'contemporary';

export interface Era {
  id: EraId;
  name: string;
  period: string;
  years: [number, number];
  description: string;
  characteristics: string[];
  keyArtists: string[];
  color: string;
}

export interface Artist {
  id: string;
  name: string;
  birthYear: number;
  deathYear?: number;
  bio: string;
  instruments: string[];
  eras: EraId[];
  influences: string[];
  influencedBy: string[];
  keyAlbums: string[];
  imageUrl?: string;
  wikipedia?: string;
}

export interface CriticReview {
  quote: string;
  source: string;
  author?: string;
  rating?: number;
  url?: string;
}

export interface Album {
  id: string;
  title: string;
  artist: string;
  artistId: string;
  year: number;
  label: string;
  era: EraId;
  genres: string[];
  description: string;
  significance: string;
  keyTracks: string[];
  coverUrl?: string;
  discogs?: string;
  allMusic?: string;
  spotifyUrl?: string;
  youtubeUrl?: string;
  reviews?: CriticReview[];
}

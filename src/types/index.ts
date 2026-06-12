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
  instruments: string[];
  eras: EraId[];
  influences: string[];
  influencedBy: string[];
  keyAlbums: string[];
  imageUrl?: string;
}

// Heavy, detail-page-only fields. Loaded lazily via artistsDetail.json (Artist route only).
export interface ArtistDetail {
  bio: string;
  wikipedia?: string;
}

export type ConnectionSourceType = 'wikipedia' | 'allmusic' | 'book' | 'interview' | 'liner-notes';

export interface ConnectionSource {
  type: ConnectionSourceType;
  url?: string;
  title?: string;
  quote?: string;
}

export interface ArtistConnection {
  from: string;
  to: string;
  explanation: string;
  sources: ConnectionSource[];
  verified: boolean;
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
  secondaryArtistIds?: string[];
  year: number;
  label: string;
  era: EraId;
  genres: string[];
  albumDNA: string;
  coverUrl?: string;
  spotifyUrl?: string;
  appleMusicUrl?: string;
  youtubeMusicUrl?: string;
  youtubeUrl?: string;
}

// Heavy, detail-page-only fields. Loaded lazily via albumsDetail.json (Album route only).
export interface AlbumDetail {
  keyTracks?: string[];
  wikipedia?: string;
  reviews?: CriticReview[];
}


export type HistoricalEventCategory =
  | 'civil-rights'
  | 'economics'
  | 'politics'
  | 'technology'
  | 'globalization';

export interface HistoricalEvent {
  id: string;
  title: string;
  year: number;
  endYear?: number;
  category: HistoricalEventCategory;
  description: string;
  jazzConnection: string;
  era: EraId;
  relatedArtistIds?: string[];
  relatedAlbumIds?: string[];
  source?: string;
}

// Curated, opinionated listening routes ("the agenda"). See src/data/paths.json.
export interface CuratedPath {
  id: string;
  title: string;
  subtitle: string;
  rationale: string;
  forThePlayer: string;
  albumIds: string[];
}

export interface PathsData {
  agenda: string;
  paths: CuratedPath[];
}

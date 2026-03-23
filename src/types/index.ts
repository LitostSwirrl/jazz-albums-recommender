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
  description: string;
  significance: string;
  keyTracks: string[];
  coverUrl?: string;
  spotifyUrl?: string;
  appleMusicUrl?: string;
  youtubeMusicUrl?: string;
  youtubeUrl?: string;
  wikipedia?: string;
  reviews?: CriticReview[];
}

export interface PlaylistTrack {
  albumId: string;
  track: string;
}

export interface CuratedPlaylist {
  id: string;
  name: string;
  description: string;
  mood: string;
  tags: string[];
  tracks: PlaylistTrack[];
  coverAlbumId: string;
  spotifyUrl?: string;
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

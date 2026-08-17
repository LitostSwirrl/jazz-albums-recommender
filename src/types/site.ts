export interface SiteFeatures {
  connections: boolean;
  historicalEvents: boolean;
  discover: boolean;
}

export interface EraTransition {
  label: string;
  note: string;
  accent: 'coral' | 'teal';
}

export interface SiteCopy {
  homeTitle: string;
  homeDescription: string;
  albumsPageTitle: string;
  albumsDescriptionSuffix: string;
  artistsPageTitle: string;
  artistsDescriptionSuffix: string;
  erasPageTitle: string;
  erasDescription: string;
  timelinePageTitle: string;
  timelineHeading: string;
  timelineDescription: string;
  timelineNavSubtitle: string;
  eraTransitions: EraTransition[];
  contextPageTitle: string;
  contextDescription: string;
  eventConnectionLabel: string;
  pathsDescription: string;
  influenceDescription: string;
  noPathNote: string;
  defaultGenreLabel: string;
}

export interface SiteConfig {
  id: string;
  name: string;
  tagline: string;
  url: string;
  seoDescription: string;
  fallbackColors: string[];
  features: SiteFeatures;
  analyticsWebsiteId: string;
  copy: SiteCopy;
}

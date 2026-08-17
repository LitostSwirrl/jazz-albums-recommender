export interface SiteFeatures {
  connections: boolean;
  historicalEvents: boolean;
  discover: boolean;
}

export interface SiteCopy {
  homeTitle: string;
  homeDescription: string;
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

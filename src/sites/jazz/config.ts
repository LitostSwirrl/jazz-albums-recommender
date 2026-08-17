import type { SiteConfig } from '../../types/site';

export const siteConfig: SiteConfig = {
  id: 'jazz',
  name: 'Smack Cats',
  tagline: 'A Personal Jazz Companion',
  url: 'https://smack-cats-jazz.web.app',
  seoDescription:
    'A curated guide to 1000 jazz albums from New Orleans to today. Explore jazz history, discover artists, and understand how they shaped each other.',
  fallbackColors: [
    '#6b6358', '#7a7168', '#897f75', '#988d83',
    '#a79b90', '#b6a99d', '#c5b8ab', '#d4c7b9',
  ],
  features: { connections: true, historicalEvents: true, discover: true },
  analyticsWebsiteId: '64877654-bcc7-40f4-a769-e8744a6c519a',
  copy: {
    homeTitle: 'Your Jazz Library',
    homeDescription: '1000 jazz albums, 275 artists, 8 eras.',
  },
};

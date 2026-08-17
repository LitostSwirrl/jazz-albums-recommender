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
    albumsPageTitle: 'Essential Jazz Albums',
    albumsDescriptionSuffix: 'jazz albums across 8 eras.',
    artistsPageTitle: 'Jazz Artists',
    artistsDescriptionSuffix: 'jazz artists across all eras.',
    erasPageTitle: 'Jazz Eras',
    erasDescription: '8 jazz eras from the 1900s to present.',
    timelinePageTitle: 'Jazz Timeline',
    timelineHeading: 'Jazz Through Time',
    timelineDescription:
      'Explore a century of jazz evolution from New Orleans to the present day. Discover how each era built on what came before while pushing music into new territory.',
    timelineNavSubtitle: 'Jazz through the ages',
    eraTransitions: [
      {
        label: 'Early Jazz → Swing',
        note: 'New Orleans pioneers created the vocabulary; big bands scaled it up for dance halls.',
        accent: 'coral',
      },
      {
        label: 'Swing → Bebop',
        note: 'Young rebels turned dance music into art music, emphasizing virtuosity and complexity.',
        accent: 'teal',
      },
      {
        label: 'Bebop → Cool/Hard Bop',
        note: 'Two paths diverged: West Coast cool sophistication vs. East Coast blues-drenched intensity.',
        accent: 'teal',
      },
      {
        label: 'Hard Bop → Free Jazz',
        note: 'The ultimate rebellion: abandoning chord changes entirely for pure expression.',
        accent: 'coral',
      },
    ],
    contextPageTitle: 'Jazz & Society',
    contextDescription:
      'Explore the interweaving of jazz music with civil rights, politics, economics, technology, and globalization. A parallel timeline of music and history.',
    eventConnectionLabel: 'Jazz Connection',
    pathsDescription:
      'Opinionated listening routes through jazz, built for players: a guitar lineage, the records that broke the language, late-night tone, groove, the avant-garde leap, and where to start tonight.',
    influenceDescription:
      'Trace influence paths between jazz musicians. Discover how artists shaped each other across generations.',
    noPathNote: 'They may be from unrelated jazz traditions.',
    defaultGenreLabel: 'Jazz',
  },
};

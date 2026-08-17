import type { SiteConfig } from '../../types/site';

export const siteConfig: SiteConfig = {
  id: 'funk',
  name: 'Fatback',
  tagline: 'An Instrumental Funk & Soul Guide',
  url: 'https://fatback.web.app',
  seoDescription:
    'A curated guide to instrumental funk and soul — from soul-jazz roots to the new pocket. Built for the groove, safe for the party.',
  fallbackColors: [
    '#5c3a21', '#7a4a24', '#985a26', '#b56d28',
    '#c98634', '#d9a04a', '#c2762f', '#8a5527',
  ],
  features: { connections: false, historicalEvents: false, discover: false },
  analyticsWebsiteId: '',
  copy: {
    homeTitle: 'Your Funk Library',
    homeDescription: 'Instrumental funk and soul, from soul-jazz roots to the new pocket.',
    albumsPageTitle: 'Essential Funk Albums',
    albumsDescriptionSuffix: 'funk and soul albums across 6 eras.',
    artistsPageTitle: 'Funk Artists',
    artistsDescriptionSuffix: 'funk and soul artists across all eras.',
    erasPageTitle: 'Funk Eras',
    erasDescription: '6 funk eras from the late 1950s to present.',
    timelinePageTitle: 'Funk Timeline',
    timelineHeading: 'Funk Through Time',
    timelineDescription:
      'Follow the groove from soul-jazz organ trios to the new pocket. Every era kept the rhythm section out front and rebuilt what sat on top of it.',
    timelineNavSubtitle: 'The groove through the ages',
    eraTransitions: [
      {
        label: 'Soul-Jazz Roots → Classic Funk',
        note: 'Organ trios and house bands built the vocabulary; James Brown stripped it down to a one-chord vamp with everything landing on the first beat.',
        accent: 'coral',
      },
      {
        label: 'Classic Funk → Jazz-Funk',
        note: 'Jazz players took the backbeat, plugged in Rhodes, clavinet and synthesizers, and kept the solos.',
        accent: 'teal',
      },
      {
        label: 'Jazz-Funk → P-Funk & Boogie',
        note: 'George Clinton built funk a mythology; by the 1980s synthesizers and drum machines carried the same groove onto the dance floor.',
        accent: 'teal',
      },
      {
        label: 'P-Funk & Boogie → Rare Groove & The New Pocket',
        note: 'London DJs and hip-hop producers dug the old records back up, and a generation of bands started cutting new ones to tape.',
        accent: 'coral',
      },
    ],
    contextPageTitle: 'Funk & Society',
    contextDescription:
      'How funk and soul ran alongside civil rights, city politics, the record business, and the studio technology that changed how records got made.',
    eventConnectionLabel: 'Funk Connection',
    pathsDescription:
      'Opinionated listening routes through funk and soul, built for players: the pocket, the organ trios, the horn arrangements, and where to start tonight.',
    influenceDescription:
      'Trace influence paths between funk and soul musicians. Discover how bands and rhythm sections shaped each other across generations.',
    noPathNote: 'They may be from unrelated funk traditions.',
    defaultGenreLabel: 'Funk',
  },
};

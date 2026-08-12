# Discover into Home — design

Date: 2026-08-12
Status: approved (Joseph, in-session)

## Problem

/discover duplicates the Home page's shape (rows of album carousels) while Home's
own era/genre rows carry less editorial value than the recommendation shelves.
Joseph also could not reach /discover on his phone. Merge the two pages.

## Decisions (made with Joseph)

- Home keeps: hero feature, Today's Pick, spin picker (RandomAlbumPicker).
- Home drops: 8 era carousels, 6 genre rows, Artist Spotlight, quick-links grid.
- Discover content moves in whole: the 8-pick "Tonight" grid with reasons, plus
  all 9 shelves. No daily rotation of shelves.
- Order: hero → Today's Pick → spin picker → Tonight → shelves.
- /discover route is removed; it redirects to `/` so old links don't 404.
  Nav link removed from desktop nav and mobile hamburger menu.

## Implementation shape

- New `src/components/home/DiscoverSection.tsx` holds Tonight + shelves and is
  the only importer of `recommendations.json` (265KB) and `recCoverManifest.json`
  (37KB). Home mounts it via `React.lazy` inside a `LazySection`, so the JSON
  stays out of the initial bundle and loads on scroll — Home's first paint is
  unchanged.
- `priority` preload on Tonight cards is dropped: the section is below the fold
  by construction.
- Empty state: if no top picks and no shelves resolve, the section renders null.
- Deletions: `pages/Discover.tsx`, `home/GenreRow.tsx`, `home/ArtistSpotlight.tsx`,
  `home/QuickLinksGrid.tsx` (verified unused outside Home), Discover export in
  `pages/index.ts`, Discover lazy import + route in `App.tsx` (route becomes
  `<Navigate to="/" replace />`).
- `AlbumCarousel` stays (TodaysPick uses it). `RecCard` stays where it is.

## Verification

- `npm run build` clean.
- Browser at 390px viewport: hamburger opens without Discover link, Tonight grid
  is 2 columns, shelves scroll horizontally with no page-level horizontal
  scroll, spin picker works. Repeat structure check at desktop width.

# Jazz Albums Recommender

A personal jazz listening guide and companion application.

## Project Overview

This is a static reference site to explore jazz history, discover 1000 curated albums, and understand connections between 315 artists across different eras.

## Tech Stack

- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router DOM (HashRouter)
- **Data Viz**: React Flow (@xyflow/react) for artist connection graphs
- **PWA**: hand-rolled service worker (`public-shared/sw.js`) — offline + instant repeat visits
- **Deployment**: Firebase Hosting — jazz → smack-cats-jazz.web.app, funk → fatback-funk.web.app

## Project Structure

```
public-shared/               # Static files copied into every site's dist/
├── sw.js                    #   Service worker
└── 404.html
src/
├── components/
│   ├── home/        # Landing page: hero, carousels, picker, today's pick
│   ├── layout/      # Header, navigation, search
│   ├── discovery/   # Related albums, surprise button
│   ├── discover/    # Recommendation card used by the Discover section
│   ├── context/     # Historical-context cards (jazz & society)
│   ├── icons/       # Streaming + UI icons
│   └── graph/       # Artist influence graph (React Flow)
├── sites/                           # One pack per site; VITE_SITE picks it, @site resolves to it
│   ├── jazz/
│   │   ├── config.ts                # SiteConfig: name, URL, palette, feature flags, all UI copy
│   │   ├── public/                  # favicon, PWA icons, manifest, robots.txt, sitemap.xml, covers/
│   │   └── data/
│   │       ├── eras.json            # Jazz era definitions (8 eras)
│   │       ├── artists.json         # Artist profiles (315) — slim; bios split out
│   │       ├── artistsDetail.json   # Per-artist bio/wikipedia (lazy, Artist page only)
│   │       ├── albums.json          # Album catalog (1000) — slim; heavy fields split out
│   │       ├── albumsDetail.json    # Per-album keyTracks/wikipedia/reviews (lazy, Album page)
│   │       ├── connections.json     # 377 source-verified artist connections
│   │       ├── historicalEvents.json# Jazz & society timeline events
│   │       ├── paths.json           # Curated "Paths" agenda + 6 listening routes
│   │       ├── recommendations.json # Discover shelves + "Tonight" picks (lazy)
│   │       ├── coverManifest.json   # Album id → self-hosted /covers/*.webp
│   │       ├── recCoverManifest.json# Same, for recommendation covers
│   │       └── library.json         # Owned-catalog snapshot
│   └── funk/                        # Same three-part shape: config.ts + data/ + public/
├── hooks/
│   └── usePreloadImages.ts  # Preload above-the-fold cover images
├── pages/                   # Home, Albums, Album, Artists, Artist, Eras, Era,
│                            #   Paths, Path, Timeline, ParallelTimeline,
│                            #   InfluenceGraph, NotFound (catch-all 404)
├── types/                   # TypeScript interfaces
└── utils/
    ├── random.ts       # Seeded PRNG + DAY_SEED for daily content rotation
    ├── discovery.ts    # Album filtering, recommendations, getDailyPicks
    ├── prefetch.ts     # Hover-prefetch of lazy route chunks
    └── ...             # analytics, connections, historicalContext, imageProxy, colors, strings
```

## Code Standards

- TypeScript strict mode, no `any`
- Use `interface` over `type` (except unions)
- Early returns, flat code structure
- Tailwind for all styling
- Handle all UI states: loading, error, empty, success

## Common Commands

```bash
npm run dev:jazz     # Start dev server for the jazz site
npm run dev:funk     # Start dev server for the funk site
npm run build:jazz   # Validate the jazz pack, then production build
npm run build:funk   # Validate the funk pack, then production build
npm run preview      # Preview the last production build
npm run deploy:jazz  # build:jazz + firebase deploy --only hosting:jazz
npm run deploy:funk  # build:funk + firebase deploy --only hosting:funk
npm run typecheck    # tsc -b
npm run lint         # eslint .
```

Bare `dev`, `build`, and `deploy` alias the jazz versions. Both builds write to the same `dist/`, so always build the site you are about to deploy.

## Multi-site template

One codebase, two sites. A site pack (`src/sites/<id>/`) holds everything site-specific — `config.ts`, `data/`, `public/` — and nothing else in `src/` names a site.

- **Selection**: `VITE_SITE=jazz|funk` at build/dev time. `vite.config.ts` reads it to point the `@site` alias and `publicDir` at that pack, and to fill `%SITE_*%` tokens in `index.html`. Shared code imports data as `@site/data/albums.json` and config as `@site/config` — never a hard-coded path.
- **Feature flags**: `siteConfig.features` (`connections`, `historicalEvents`, `discover`) gate routes, nav items, and page sections. Jazz has all three on; funk has all three off.
- **Copy**: every user-facing string that mentions a genre lives in `siteConfig.copy` (see `src/types/site.ts`), so shared components stay genre-neutral.
- **Validation**: `scripts/validate_site_pack.mjs <id>` runs before each build — checks required fields on albums/artists/eras, presence of the detail and manifest files, and that every album's era exists.
- **Sites**: jazz = **Smack Cats** (smack-cats-jazz.web.app), the full 1000-album guide. funk = **Fatback** (fatback-funk.web.app), an instrumental-lean funk & soul guide, currently a 10-album placeholder scaffold.

## Data Sources

Content is curated from reliable sources:
- Wikipedia (history, artist bios)
- MusicBrainz (album metadata)
- Discogs (community ratings)
- AllMusic (editorial context)

## Current Status

All 4 phases complete: foundation, core content (1000 albums, 315 artists), visualization (377 artist connections), discovery (Spotify-style landing, date-based Today's Pick, random picker, curated Paths).

## Landing Page Features

- **Hero Feature**: Daily rotating featured album with era-colored gradient
- **Today's Pick**: 8 albums that rotate daily by date (seeded — no location, no weather, no permission prompt)
- **Paths**: opinionated curated listening routes — the site's editorial "agenda" (a guide for players), including a jazz-guitar lineage. Lives at /paths and /path/:id
- **Random Album Picker**: "Vinyl Reveal" spin animation with era filter chips
- **Discover Section**: the former /discover page merged into Home (2026-08-12) — "Tonight" grid of 8 recommendation picks with reasons, plus 9 themed shelves from recommendations.json. Lazy code-split chunk (DiscoverSection.tsx) so the ~300KB rec JSON stays out of the initial bundle. /discover redirects to /. Era carousels, genre collections, artist spotlight, and quick-links grid were dropped in the same merge

## Content Stats
- **Albums**: 1000 curated albums across all eras
- **Artists**: 315 jazz legends with full bios
- **Eras**: 8 distinct periods from 1920s to present
- **Connections**: 377 source-verified artist connections

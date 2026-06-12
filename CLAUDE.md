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
- **PWA**: hand-rolled service worker (`public/sw.js`) — offline + instant repeat visits
- **Deployment**: Firebase Hosting (smack-cats-jazz.web.app)

## Project Structure

```
src/
├── components/
│   ├── home/        # Landing page: hero, carousels, picker, today's pick
│   ├── layout/      # Header, navigation, search
│   ├── discovery/   # Related albums, surprise button
│   ├── context/     # Historical-context cards (jazz & society)
│   ├── icons/       # Streaming + UI icons
│   ├── timeline/    # Era timeline components
│   └── graph/       # Artist influence graph (React Flow)
├── data/
│   ├── eras.json            # Jazz era definitions (8 eras)
│   ├── artists.json         # Artist profiles (315) — slim; bios split out
│   ├── artistsDetail.json   # Per-artist bio/wikipedia (lazy, Artist page only)
│   ├── albums.json          # Album catalog (1000) — slim; heavy fields split out
│   ├── albumsDetail.json    # Per-album keyTracks/wikipedia/reviews (lazy, Album page)
│   ├── connections.json     # 377 source-verified artist connections
│   ├── historicalEvents.json# Jazz & society timeline events
│   └── paths.json           # Curated "Paths" agenda + 6 listening routes
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
npm run dev          # Start dev server
npm run build        # Production build
npm run preview      # Preview production build
npm run deploy       # Build + deploy to Firebase Hosting (project: smack-cats-jazz)
```

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
- **Era Carousels**: One scrollable row per era (8 rows)
- **Genre Collections**: 6 curated groupings (Deep Grooves, For the Bold, Cool & Calm, etc.)
- **Artist Spotlight**: Daily featured artist with discography carousel
- **Quick Links Grid**: Navigation to all major sections

## Content Stats
- **Albums**: 1000 curated albums across all eras
- **Artists**: 315 jazz legends with full bios
- **Eras**: 8 distinct periods from 1920s to present
- **Connections**: 377 source-verified artist connections

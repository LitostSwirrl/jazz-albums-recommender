# Jazz Albums Recommender

A personal jazz listening guide and companion application.

## Project Overview

This is a static reference site to explore jazz history, discover 1000 curated albums, and understand connections between 275 artists across different eras.

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router DOM
- **Data Viz**: React Flow (for artist connection graphs)
- **Deployment**: GitHub Pages

## Project Structure

```
src/
├── components/
│   ├── home/        # Landing page: carousels, hero, picker, today's pick
│   ├── layout/      # Header, Footer, Navigation
│   ├── discovery/   # Related albums, surprise button
│   ├── playlist/    # Playlist cards, Spotify integration
│   ├── timeline/    # Era timeline components
│   └── graph/       # Artist influence graph
├── data/
│   ├── eras.json    # Jazz era definitions (8 eras)
│   ├── artists.json # Artist profiles (275 artists)
│   ├── albums.json  # Album data (1000 albums)
│   └── playlists.json # Curated playlists
├── hooks/
│   └── useWeather.ts # Geolocation + Open-Meteo weather hook
├── pages/
│   ├── Home.tsx     # Spotify-style landing with carousels
│   ├── Albums.tsx   # Filterable album grid
│   ├── Era.tsx      # Era detail
│   ├── Artist.tsx   # Artist profile + influence network
│   └── Album.tsx    # Album detail
├── types/           # TypeScript interfaces
└── utils/
    ├── weatherMood.ts  # Weather-to-mood engine (5 dimensions, 30+ genres)
    ├── random.ts       # Seeded PRNG for daily content rotation
    ├── localStorage.ts # Pick history tracking
    ├── discovery.ts    # Album filtering & recommendation
    └── ...             # Image proxy, connections, colors, etc.
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
npm run deploy       # Deploy to GitHub Pages
```

## Data Sources

Content is curated from reliable sources:
- Wikipedia (history, artist bios)
- MusicBrainz (album metadata)
- Discogs (community ratings)
- AllMusic (editorial context)

## Development Notes

- Keep CLAUDE.md and plan.md updated as project evolves
- Commit frequently with conventional commit messages
- Push to GitHub regularly

## Current Status

✅ **Phase 1: Foundation** - COMPLETE
✅ **Phase 2: Core Content** - 1000 albums, 275 artists added
✅ **Phase 3: Visualization** - Artist influence graph with 377 connections
✅ **Phase 4: Discovery** - Spotify-style landing, Today's Pick, random album picker

## Landing Page Features

- **Hero Feature**: Daily rotating featured album with era-colored gradient
- **Today's Pick**: 8 weather-mood-matched albums via Open-Meteo API (rule-based mood engine with 5 dimensions: energy, warmth, introspection, darkness, groove). Falls back to time+season when geolocation is denied. 7-day no-repeat history via localStorage.
- **Random Album Picker**: "Vinyl Reveal" spin animation with era filter chips
- **Era Carousels**: One scrollable row per era (8 rows)
- **Genre Collections**: 6 curated groupings (Deep Grooves, For the Bold, Cool & Calm, etc.)
- **Artist Spotlight**: Daily featured artist with discography carousel
- **Quick Links Grid**: Navigation to all major sections

## Content Stats
- **Albums**: 1000 curated albums across all eras
- **Artists**: 275 jazz legends with full bios
- **Eras**: 8 distinct periods from 1920s to present
- **Connections**: 377 source-verified artist connections

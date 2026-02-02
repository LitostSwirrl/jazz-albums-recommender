# Jazz Albums Recommender

A personal jazz listening guide and companion application.

## Project Overview

This is a static reference site to explore jazz history, discover 100 essential albums, and understand connections between artists across different eras.

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
│   ├── layout/      # Header, Footer, Navigation
│   ├── timeline/    # Era timeline components
│   └── graph/       # Artist influence graph
├── data/
│   ├── eras.json    # Jazz era definitions
│   ├── artists.json # Artist profiles
│   └── albums.json  # Album data (100 albums)
├── pages/
│   ├── Home.tsx
│   ├── Era.tsx
│   ├── Artist.tsx
│   └── Album.tsx
├── types/           # TypeScript interfaces
└── utils/           # Helper functions
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
🚧 **Phase 2: Core Content** - Need to expand to 100 albums

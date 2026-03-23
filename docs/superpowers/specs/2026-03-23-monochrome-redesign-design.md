# Design Spec: Monochrome Redesign, Playlists, and Copy Cleanup

Date: 2026-03-23

## Overview

Three changes to the jazz albums recommender site:

1. **Monochrome warm-gray redesign with serif fonts** -- replace the current terracotta/colorful palette with a warm-gray monochrome scheme and switch from sans-serif to serif typography (DM Serif Display + Source Serif 4)
2. **Song-based playlists** -- rebuild playlist data from album-based compilations to auto-generated track-based playlists using `keyTracks` from matching albums
3. **Strip verbose descriptions** -- remove all subtitle/description text from page headers, keep only titles

---

## 1. Monochrome Warm-Gray Redesign

### Color System

Replace all color tokens in `src/index.css` `@theme` block:

| Token | Current | New | Purpose |
|-------|---------|-----|---------|
| `--color-cream` | `#0D0D0D` | `#1a1917` | Page background (warm-tinted dark) |
| `--color-surface` | `#161616` | `#242220` | Card/surface background |
| `--color-charcoal` | `#F5F0EB` | `#e8e4df` | Primary text (warm off-white) |
| `--color-warm-gray` | `#8A8A8A` | `#9a9590` | Secondary text |
| `--color-border` | `#2A2A2A` | `#332f2b` | Borders |
| `--color-border-light` | `#1F1F1F` | `#2a2725` | Subtle borders |
| `--color-coral` | `#C2694F` | `#a89a7d` | Accent (desaturated warm gold) |
| `--color-teal` | `#A8DADC` | `#b5b0a8` | Map to warm-gray |
| `--color-mustard` | `#D4A843` | `#a89a7d` | Map to accent |
| `--color-olive` | `#7DA87D` | `#9a9590` | Map to warm-gray |
| `--color-navy` | `#0A0A0A` | `#141210` | Deepest dark |

### Era Colors -- CSS Custom Properties + JSON

Replace chromatic era colors in both `src/index.css` `@theme` block (`--color-era-*` tokens) and `src/data/eras.json` (`color` field). Each era gets a distinct warm-gray shade, progressing lighter as eras advance:

| Era | CSS Token | Current | New |
|-----|-----------|---------|-----|
| Early Jazz | `--color-era-early-jazz` | `#C9A84C` | `#6b6358` |
| Swing | `--color-era-swing` | `#E6704E` | `#7a7168` |
| Bebop | `--color-era-bebop` | `#4ECDC4` | `#897f75` |
| Cool Jazz | `--color-era-cool-jazz` | `#84B4B4` | `#988d83` |
| Hard Bop | `--color-era-hard-bop` | `#D04E51` | `#a79b90` |
| Free Jazz | `--color-era-free-jazz` | `#A06BCA` | `#b6a99d` |
| Fusion | `--color-era-fusion` | `#E89B4C` | `#c5b8ab` |
| Contemporary | `--color-era-contemporary` | `#3DA68E` | `#d4c7b9` |

### Hardcoded Era Color Maps

Two files contain duplicate era color maps that must be updated to match:

- `src/pages/Timeline.tsx` lines 13-22 -- local `eraColors` object
- `src/components/graph/hooks/useInfluenceGraph.ts` lines 22-31 -- exported `eraColors` object

### Historical Context Category Colors

`src/utils/historicalContext.ts` lines 13-17 has hardcoded category colors. Replace with warm-gray variants:

| Category | Current | New |
|----------|---------|-----|
| civil-rights | `#E63946` | `#a89a7d` (accent) |
| economics | `#3DA68E` | `#897f75` |
| politics | `#D04E51` | `#7a7168` |
| technology | `#A8DADC` | `#b5b0a8` |
| globalization | `#A06BCA` | `#988d83` |

### Other Hardcoded Colors to Update

| File | Current Hex | New Hex | Context |
|------|-------------|---------|---------|
| `src/components/home/HeroFeature.tsx` | `#C2694F` | `#a89a7d` | Fallback accent |
| `src/components/home/HeroFeature.tsx` | `#0D0D0D`, `#0A0A0A` | `#1a1917`, `#141210` | Gradient backgrounds |
| `src/pages/InfluenceGraph.tsx` | `#E63946` (x3) | `#a89a7d` | Edge highlight color |
| `src/pages/InfluenceGraph.tsx` | `#D4A843` (x2) | `#c5b8ab` | Path edge color |
| `src/pages/InfluenceGraph.tsx` | `#A8DADC` (x1) | `#b5b0a8` | Connected edge color |
| `src/pages/InfluenceGraph.tsx` | `#1A1A2E` | `#1a1917` | Background |
| `src/pages/InfluenceGraph.tsx` | `#4A4A5A` | `#332f2b` | Minimap fallback |
| `src/components/graph/MiniInfluenceNetwork.tsx` | `#E63946` (x3) | `#a89a7d` | Edge stroke |
| `src/components/graph/MiniInfluenceNetwork.tsx` | `#1A1A2E` | `#1a1917` | Background |
| `src/components/graph/MiniInfluenceNetwork.tsx` | `#4A4A5A` | `#332f2b` | Fallback border |
| `src/components/graph/nodes/ArtistNode.tsx` | `#4A4A5A` | `#332f2b` | Fallback border |
| `src/pages/Timeline.tsx` | `#0D0D0D` | `#1a1917` | Border color |

### Explicitly Out of Scope

Brand colors stay as-is (they represent external services):
- Spotify green `#1DB954` in `SaveToSpotify.tsx` and `PlaylistAlbumRow.tsx`
- Apple Music red `#FA243C` in `Album.tsx`
- YouTube red `#FF0000` in `Album.tsx`

### Stray Tailwind Built-in Colors

Search for and replace any Tailwind built-in color classes (`text-emerald-400`, `text-red-500`, `bg-red-50`, etc.) with custom token equivalents to maintain monochrome consistency. Exception: brand-colored buttons (Spotify, Apple Music, YouTube).

### Fallback Colors (`src/utils/colors.ts`)

Replace the chromatic `FALLBACK_COLORS` array with 8 warm-gray shades matching the era scale.

### Typography

**Fonts to load** (replace current Google Fonts import in `index.html`):
- DM Serif Display: weight 400
- Source Serif 4: weights 300, 400, 500, 600
- JetBrains Mono: weights 400, 700 (keep as-is)

**Font stack assignment** in `src/index.css`:

| Token | Current | New |
|-------|---------|-----|
| `--font-display` | Space Grotesk | DM Serif Display, Georgia, serif |
| `--font-heading` | Inter | Source Serif 4, Georgia, serif |
| `--font-body` | DM Sans | Source Serif 4, Georgia, serif |
| `--font-mono` | JetBrains Mono | JetBrains Mono (unchanged) |

### Shadows

Update shadow tokens for warm tint:
- `--shadow-card`: `0 1px 3px rgba(20, 18, 16, 0.1), 0 4px 12px rgba(0, 0, 0, 0.3)`
- `--shadow-card-hover`: `0 4px 16px rgba(20, 18, 16, 0.15), 0 8px 32px rgba(0, 0, 0, 0.4)`
- `--shadow-elevated`: `0 8px 24px rgba(0, 0, 0, 0.5), 0 0 1px rgba(232, 228, 223, 0.05)`

Easing tokens (`--ease-smooth`, `--ease-bounce`) are unchanged.

### Selection Color

`::selection` uses `var(--color-coral)` which auto-updates to `#a89a7d`. White text on warm gold has 4.8:1 contrast -- adequate.

### Loading State (`index.html`)

Update inline styles in `<div id="root">` fallback:
- Background: `#1a1917`
- Text: `#9a9590`
- Font-family: `'Source Serif 4', Georgia, serif`

Update `<meta name="theme-color" content="#1a1917">`.

---

## 2. Song-Based Playlists

### Current State

`playlists.json` contains 6 mood-based playlists. Each has `tracks: PlaylistTrack[]` where `PlaylistTrack = { albumId, track }`. Tracks are manually curated as album-based compilations.

### Change

Write a script (`scripts/generate_playlists.py`) that:

1. For each mood category, defines matching criteria (genre keywords, era preferences, label)
2. Filters albums matching those criteria
3. Pulls individual tracks from each album's `keyTracks` array
4. Selects ~20-30 tracks per playlist, ensuring artist diversity (max 2 tracks from same artist)
5. Picks a representative `coverAlbumId` from the selected albums
6. Outputs new `playlists.json` with 12 playlists (6 existing moods + 6 new)

### Mood-to-Filter Mapping

Matching uses the `genres` array on each album, plus `label` and `era` fields where noted.

| Mood | Filter Criteria |
|------|----------------|
| morning | genres: `cool jazz`, `bossa nova`, `vocal jazz`, `swing` |
| afternoon | genres: `hard bop`, `post-bop`, `soul jazz` |
| evening | genres: `cool jazz`, `modal jazz`, `vocal jazz`; eras: `cool-jazz`, `bebop` |
| night | genres: `free jazz`, `avant-garde`, `modal jazz`; eras: `free-jazz` |
| gateway | top albums by era spread -- pick 3-4 from each era, prioritizing albums with `spotifyUrl` set |
| cerebral | genres: `free jazz`, `avant-garde`, `experimental`, `third stream` |
| melancholy | genres: `blues`, `vocal jazz`, `cool jazz`; filter for slower-tempo keywords in description |
| joyful | genres: `swing`, `bebop`, `soul jazz`, `latin jazz` |
| urban | genres: `hard bop`, `post-bop`, `soul jazz`; eras: `hard-bop` |
| european | label: `ECM`; genres: `chamber jazz`, `nordic jazz`, `contemporary jazz` |
| spiritual | genres: `spiritual jazz`, `free jazz`; artists with gospel/spiritual in description |
| fusion | genres: `jazz fusion`, `jazz-funk`, `jazz-rock`, `electric jazz` |

### Data Model

No changes to `CuratedPlaylist` or `PlaylistTrack` interfaces -- same shape, regenerated content.

### SaveToSpotify

No code changes. The existing PKCE flow searches by `track + artist` and creates playlists.

### Playlist Descriptions

Keep playlist descriptions but make them short and factual (1 sentence, no marketing prose). The generator script outputs these.

---

## 3. Strip Verbose Descriptions

### Pages to Update

| Page | File | Current Subtitle | After |
|------|------|-----------------|-------|
| Home | `Home.tsx:67` | "A curated guide to {n} jazz albums..." | Shorten SEO desc, no visible subtitle |
| Albums | `Albums.tsx:208-211` | "{n} albums that define jazz history" | Remove. Show "{n} albums" only when filters active |
| Artists | `Artists.tsx:92-93` | "{n} legends who shaped jazz history" | Remove. Show "{n} artists" only when filters active |
| Eras | `Eras.tsx:16-18` | "Explore the evolution of jazz..." | Remove `<p>` block |
| Playlists | `Playlists.tsx:30-32` | "Curated listening journeys..." | Remove `<p>` block |
| Timeline | `ParallelTimeline.tsx:77-79` | "Jazz never existed in a vacuum..." | Remove `<p>` block |
| Timeline | `Timeline.tsx:51-54` | "From New Orleans to the present day..." | Remove `<p>` block |

### Not Stripped

- Individual era detail pages (`Era.tsx`) -- `era.description` from `eras.json` is content, not marketing. Keep.
- Influence graph subtitle ("Select two artists...") -- functional UI guidance. Keep.

### SEO Descriptions

Keep `<SEO description>` props for meta tags but shorten to factual one-liners.

---

## Files Changed

### Theme (Item 1)
- `src/index.css` -- all color and font tokens
- `src/utils/colors.ts` -- fallback colors
- `src/data/eras.json` -- era `color` fields
- `index.html` -- Google Fonts import, inline loading styles, meta theme-color
- `src/pages/Timeline.tsx` -- hardcoded `eraColors` map + `#0D0D0D`
- `src/components/graph/hooks/useInfluenceGraph.ts` -- exported `eraColors` map
- `src/utils/historicalContext.ts` -- category colors
- `src/components/home/HeroFeature.tsx` -- hardcoded hex in gradient
- `src/pages/InfluenceGraph.tsx` -- hardcoded edge/path/bg colors
- `src/components/graph/MiniInfluenceNetwork.tsx` -- hardcoded edge/bg colors
- `src/components/graph/nodes/ArtistNode.tsx` -- hardcoded fallback border
- Any files with stray Tailwind built-in color classes

### Playlists (Item 2)
- `scripts/generate_playlists.py` -- new script
- `src/data/playlists.json` -- regenerated

### Copy (Item 3)
- `src/pages/Home.tsx`
- `src/pages/Albums.tsx`
- `src/pages/Artists.tsx`
- `src/pages/Eras.tsx`
- `src/pages/Playlists.tsx`
- `src/pages/ParallelTimeline.tsx`
- `src/pages/Timeline.tsx`

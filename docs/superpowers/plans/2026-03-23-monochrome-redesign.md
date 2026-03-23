# Monochrome Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the jazz albums site from a colorful terracotta palette to a warm-gray monochrome aesthetic with serif typography, rebuild playlists as song-based auto-generated collections, and strip verbose page descriptions.

**Architecture:** Three independent workstreams: (1) theme swap across CSS tokens, hardcoded colors, and fonts, (2) Python script to regenerate playlist data, (3) JSX edits to remove subtitle text. All changes are additive/replacement -- no structural refactors.

**Tech Stack:** React/TypeScript, Tailwind CSS, Vite, Python 3 (for playlist script)

**Spec:** `docs/superpowers/specs/2026-03-23-monochrome-redesign-design.md`

---

## File Structure

No new source files created (except the playlist generation script). All changes are modifications to existing files:

| File | Change Type | Responsibility |
|------|------------|----------------|
| `src/index.css` | Modify | All color tokens, font tokens, shadows |
| `index.html` | Modify | Google Fonts import, meta theme-color, loading fallback |
| `src/utils/colors.ts` | Modify | Fallback color array |
| `src/data/eras.json` | Modify | Era `color` fields |
| `src/pages/Timeline.tsx` | Modify | Local eraColors map, hardcoded hex, verbose text |
| `src/components/graph/hooks/useInfluenceGraph.ts` | Modify | Exported eraColors map |
| `src/utils/historicalContext.ts` | Modify | Category colors |
| `src/components/home/HeroFeature.tsx` | Modify | Hardcoded gradient hex |
| `src/pages/InfluenceGraph.tsx` | Modify | Hardcoded edge/path colors, Tailwind class |
| `src/pages/Artist.tsx` | Modify | Stray Tailwind `text-emerald-500` class |
| `src/components/graph/MiniInfluenceNetwork.tsx` | Modify | Hardcoded edge/bg colors |
| `src/components/graph/nodes/ArtistNode.tsx` | Modify | Hardcoded fallback border |
| `scripts/generate_playlists.py` | Create | Playlist generation script |
| `src/data/playlists.json` | Modify (regenerated) | Playlist data |
| `src/pages/Home.tsx` | Modify | SEO description |
| `src/pages/Albums.tsx` | Modify | Subtitle removal |
| `src/pages/Artists.tsx` | Modify | Subtitle removal |
| `src/pages/Eras.tsx` | Modify | Subtitle removal |
| `src/pages/Playlists.tsx` | Modify | Subtitle removal |
| `src/pages/ParallelTimeline.tsx` | Modify | Subtitle removal |

---

## Task 1: Core Theme Tokens (CSS + Fonts)

**Files:**
- Modify: `src/index.css:7-47` (all @theme tokens)
- Modify: `index.html:12,30-33,58-59`

- [ ] **Step 1: Replace color tokens in `src/index.css`**

Replace the entire `@theme` block (lines 7-47) with new warm-gray monochrome values:

```css
@theme {
  /* Typography -- Serif stack */
  --font-display: 'DM Serif Display', Georgia, serif;
  --font-heading: 'Source Serif 4', Georgia, serif;
  --font-body: 'Source Serif 4', Georgia, serif;
  --font-mono: 'JetBrains Mono', 'Courier New', monospace;

  /* Core palette -- Warm-gray monochrome */
  --color-cream: #1a1917;
  --color-surface: #242220;
  --color-charcoal: #e8e4df;
  --color-warm-gray: #9a9590;
  --color-border: #332f2b;
  --color-border-light: #2a2725;

  /* Accent palette -- Desaturated warm */
  --color-coral: #a89a7d;
  --color-teal: #b5b0a8;
  --color-mustard: #a89a7d;
  --color-olive: #9a9590;
  --color-navy: #141210;

  /* Era colors -- Warm-gray scale (dark to light) */
  --color-era-early-jazz: #6b6358;
  --color-era-swing: #7a7168;
  --color-era-bebop: #897f75;
  --color-era-cool-jazz: #988d83;
  --color-era-hard-bop: #a79b90;
  --color-era-free-jazz: #b6a99d;
  --color-era-fusion: #c5b8ab;
  --color-era-contemporary: #d4c7b9;

  /* Shadows -- Warm tint */
  --shadow-card: 0 1px 3px rgba(20, 18, 16, 0.1), 0 4px 12px rgba(0, 0, 0, 0.3);
  --shadow-card-hover: 0 4px 16px rgba(20, 18, 16, 0.15), 0 8px 32px rgba(0, 0, 0, 0.4);
  --shadow-elevated: 0 8px 24px rgba(0, 0, 0, 0.5), 0 0 1px rgba(232, 228, 223, 0.05);

  /* Easing */
  --ease-smooth: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

- [ ] **Step 2: Update Google Fonts import in `index.html`**

Replace line 30 comment and line 33 `<link>` with:

```html
<!-- Google Fonts: Serif type stack -->
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Source+Serif+4:wght@300;400;500;600&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet" />
```

- [ ] **Step 3: Update `index.html` meta and loading fallback**

Line 12 -- change theme-color:
```html
<meta name="theme-color" content="#1a1917" />
```

Line 58 -- update inline loading div:
```html
<div style="padding: 40px; text-align: center; font-family: 'Source Serif 4', Georgia, serif; background: #1a1917; min-height: 100vh;">
```

Line 59 -- update text color:
```html
<p style="color: #9a9590;">Loading Jazz Guide...</p>
```

Line 60 -- update text color:
```html
<p style="color: #9a9590; font-size: 14px;">If this message stays visible, JavaScript may be blocked.</p>
```

- [ ] **Step 4: Verify dev server starts**

Run: `npm run dev`
Expected: Site loads with new warm-gray background and serif fonts. All text should render in Source Serif 4 / DM Serif Display.

- [ ] **Step 5: Commit**

```bash
git add src/index.css index.html
git commit -m "feat: replace color tokens and fonts with warm-gray monochrome serif theme"
```

---

## Task 2: Fallback Colors and Era JSON

**Files:**
- Modify: `src/utils/colors.ts:2-11`
- Modify: `src/data/eras.json` (color field in all 8 era objects)

- [ ] **Step 1: Replace FALLBACK_COLORS in `src/utils/colors.ts`**

Replace lines 2-11:

```typescript
export const FALLBACK_COLORS = [
  '#6b6358', // early jazz
  '#7a7168', // swing
  '#897f75', // bebop
  '#988d83', // cool jazz
  '#a79b90', // hard bop
  '#b6a99d', // free jazz
  '#c5b8ab', // fusion
  '#d4c7b9', // contemporary
];
```

- [ ] **Step 2: Update era colors in `src/data/eras.json`**

For each of the 8 era objects, update the `color` field:

| Era ID | New Color |
|--------|-----------|
| `early-jazz` | `#6b6358` |
| `swing` | `#7a7168` |
| `bebop` | `#897f75` |
| `cool-jazz` | `#988d83` |
| `hard-bop` | `#a79b90` |
| `free-jazz` | `#b6a99d` |
| `fusion` | `#c5b8ab` |
| `contemporary` | `#d4c7b9` |

- [ ] **Step 3: Verify era badges render with new colors**

Run: `npm run dev`, navigate to `/eras` and `/albums`
Expected: Era badges show warm-gray tones instead of chromatic colors.

- [ ] **Step 4: Commit**

```bash
git add src/utils/colors.ts src/data/eras.json
git commit -m "feat: update fallback colors and era JSON to warm-gray scale"
```

---

## Task 3: Hardcoded Era Color Maps + Timeline Border

**Files:**
- Modify: `src/pages/Timeline.tsx:13-22,79`
- Modify: `src/components/graph/hooks/useInfluenceGraph.ts:22-31,124,131`

- [ ] **Step 1: Replace eraColors in `src/pages/Timeline.tsx`**

Replace lines 13-22:

```typescript
const eraColors: Record<string, string> = {
  'early-jazz': '#6b6358',
  'swing': '#7a7168',
  'bebop': '#897f75',
  'cool-jazz': '#988d83',
  'hard-bop': '#a79b90',
  'free-jazz': '#b6a99d',
  'fusion': '#c5b8ab',
  'contemporary': '#d4c7b9',
};
```

- [ ] **Step 2: Replace Timeline border color**

Line 79 -- change `#0D0D0D` to `#1a1917`:
```typescript
style={{ backgroundColor: color, borderColor: '#1a1917' }}
```

- [ ] **Step 3: Replace eraColors in `src/components/graph/hooks/useInfluenceGraph.ts`**

Replace lines 22-31:

```typescript
export const eraColors: Record<string, string> = {
  'early-jazz': '#6b6358',
  'swing': '#7a7168',
  'bebop': '#897f75',
  'cool-jazz': '#988d83',
  'hard-bop': '#a79b90',
  'free-jazz': '#b6a99d',
  'fusion': '#c5b8ab',
  'contemporary': '#d4c7b9',
};
```

- [ ] **Step 4: Replace edge colors in `useInfluenceGraph.ts`**

Line 124: `'#E63946'` -> `'#a89a7d'` (edge stroke)
Line 131: `'#E63946'` -> `'#a89a7d'` (marker arrow color)

- [ ] **Step 5: Commit**

```bash
git add src/pages/Timeline.tsx src/components/graph/hooks/useInfluenceGraph.ts
git commit -m "feat: update hardcoded era color maps and edge colors to warm-gray scale"
```

---

## Task 4: Historical Context Category Colors

**Files:**
- Modify: `src/utils/historicalContext.ts:13-17`

- [ ] **Step 1: Replace category colors**

Replace the color values in lines 13-17 of the `EVENT_CATEGORIES` object:

```typescript
'civil-rights':  { label: 'Racial Justice',       color: '#a89a7d', icon: 'fist' },
'economics':     { label: 'Economics & Industry',  color: '#897f75', icon: 'dollar' },
'politics':      { label: 'Politics & War',        color: '#7a7168', icon: 'flag' },
'technology':    { label: 'Recording & Tech',      color: '#b5b0a8', icon: 'mic' },
'globalization': { label: 'Global Diaspora',       color: '#988d83', icon: 'globe' },
```

- [ ] **Step 2: Commit**

```bash
git add src/utils/historicalContext.ts
git commit -m "feat: update historical context category colors to warm-gray"
```

---

## Task 5: HeroFeature Hardcoded Colors

**Files:**
- Modify: `src/components/home/HeroFeature.tsx:23,31`

- [ ] **Step 1: Replace fallback accent color**

Line 23 -- change `#C2694F` to `#a89a7d`:
```typescript
const eraColor = era?.color ?? '#a89a7d';
```

- [ ] **Step 2: Replace gradient background colors**

Line 31 -- change `#0D0D0D` to `#1a1917` and `#0A0A0A` to `#141210`:
```typescript
background: `linear-gradient(135deg, ${eraColor}30 0%, #1a1917 60%, #141210 100%)`,
```

- [ ] **Step 3: Commit**

```bash
git add src/components/home/HeroFeature.tsx
git commit -m "feat: update HeroFeature gradient to warm-gray palette"
```

---

## Task 6: Graph Component Colors + Stray Tailwind Classes

**Files:**
- Modify: `src/pages/InfluenceGraph.tsx:58,152,196,323,332,337`
- Modify: `src/pages/Artist.tsx:64`
- Modify: `src/components/graph/MiniInfluenceNetwork.tsx:28,124,132,158,170`
- Modify: `src/components/graph/nodes/ArtistNode.tsx:38`

- [ ] **Step 1: Update `src/pages/InfluenceGraph.tsx`**

Apply these replacements:
- Line 58: `text-emerald-400` -> `text-coral` (use custom token)
- Line 152: `'#D4A843'` -> `'#c5b8ab'` and `'#E63946'` -> `'#a89a7d'`
- Line 196: `'#D4A843'` -> `'#c5b8ab'`, `'#A8DADC'` -> `'#b5b0a8'`, `'#E63946'` -> `'#a89a7d'`
- Line 323: `'#E63946'` -> `'#a89a7d'`
- Line 332: `"#1A1A2E"` -> `"#1a1917"`
- Line 337: `'#4A4A5A'` -> `'#332f2b'` (both occurrences)

- [ ] **Step 2: Update `src/pages/Artist.tsx`**

Line 64: `text-emerald-500` -> `text-coral` (source verification icon)

- [ ] **Step 3: Update `src/components/graph/MiniInfluenceNetwork.tsx`**

Apply these replacements (search by content, not line numbers -- line numbers are approximate):
- `'#4A4A5A'` -> `'#332f2b'` (all occurrences, ~line 28)
- `'#E63946'` -> `'#a89a7d'` (all occurrences, ~lines 124, 132, 158)
- `"#1A1A2E"` -> `"#1a1917"` (~line 170)

- [ ] **Step 4: Update `src/components/graph/nodes/ArtistNode.tsx`**

~Line 38: `'#4A4A5A'` -> `'#332f2b'` (both occurrences on the line)

- [ ] **Step 5: Verify graph renders correctly**

Run: `npm run dev`, navigate to an artist page and check the mini influence graph, then navigate to `/influence` for the full graph.
Expected: All edges, backgrounds, and node borders use warm-gray tones.

- [ ] **Step 6: Commit**

```bash
git add src/pages/InfluenceGraph.tsx src/pages/Artist.tsx src/components/graph/MiniInfluenceNetwork.tsx src/components/graph/nodes/ArtistNode.tsx
git commit -m "feat: update graph component colors to warm-gray monochrome"
```

**Note on error-state reds:** `text-red-500` in `Era.tsx:26`, `text-red-600` in `ErrorBoundary.tsx:59`, and `bg-red-50`/`border-red-200`/`text-red-600` in `SaveToSpotify.tsx:89-93` are semantic error indicators. These stay as-is -- they are not theme colors.

---

## Task 7: Strip Verbose Descriptions

**Note:** Line numbers below are approximate -- earlier tasks may shift lines in `Timeline.tsx`. Search for the text content rather than relying on exact line numbers.

**Files:**
- Modify: `src/pages/Home.tsx:~65-68`
- Modify: `src/pages/Albums.tsx:~201-211`
- Modify: `src/pages/Artists.tsx:~87-93`
- Modify: `src/pages/Eras.tsx:~11-18`
- Modify: `src/pages/Playlists.tsx:~24-32`
- Modify: `src/pages/ParallelTimeline.tsx:~77-80`
- Modify: `src/pages/Timeline.tsx:~51-54`

- [ ] **Step 1: Update `src/pages/Home.tsx`**

Lines 65-68 -- shorten SEO description (no visible subtitle exists on home):
```tsx
<SEO
  title="Your Jazz Library"
  description="1000 jazz albums, 275 artists, 8 eras."
/>
```

- [ ] **Step 2: Update `src/pages/Albums.tsx`**

Lines 201-211 -- shorten SEO, show count only when filters active:
```tsx
<SEO
  title="Essential Jazz Albums"
  description={`${albums.length} jazz albums across 8 eras.`}
/>

<div className="mb-8">
  <h1 className="text-4xl font-bold mb-2 font-display text-charcoal">Essential Albums</h1>
  {hasActiveFilters && (
    <p className="text-warm-gray">
      {filteredAlbums.length} albums matching your filters
    </p>
  )}
</div>
```

- [ ] **Step 3: Update `src/pages/Artists.tsx`**

Lines 87-93 -- shorten SEO, show count only when filters active:
```tsx
<SEO
  title="Jazz Artists"
  description={`${artists.length} jazz artists across all eras.`}
/>
<h1 className="text-4xl mb-2 font-display text-charcoal">Jazz Artists</h1>
{hasActiveFilters && (
  <p className="text-warm-gray mb-6">
    {filteredArtists.length} artists matching your filters
  </p>
)}
```

- [ ] **Step 4: Update `src/pages/Eras.tsx`**

Lines 11-18 -- shorten SEO, remove subtitle `<p>`:
```tsx
<SEO
  title="Jazz Eras"
  description="8 jazz eras from the 1900s to present."
/>
<h1 className="text-4xl font-bold mb-8 font-display text-charcoal">Jazz Eras</h1>
```

Note: Remove the `mb-2` from h1 and change to `mb-8` since the `<p>` below it is gone.

- [ ] **Step 5: Update `src/pages/Playlists.tsx`**

Lines 24-32 -- shorten SEO, remove subtitle `<p>`:
```tsx
<SEO
  title="Jazz Playlists"
  description="Curated jazz playlists for every mood."
/>

<h1 className="text-4xl mb-8 font-display text-charcoal">Playlists</h1>
```

Note: Change h1 `mb-2` to `mb-8` since the `<p>` is removed.

- [ ] **Step 6: Update `src/pages/ParallelTimeline.tsx`**

Lines 77-80 -- remove the `<p>` block:
```tsx
{/* Remove:
<p className="text-xl text-warm-gray max-w-2xl mx-auto mb-2">
  Jazz never existed in a vacuum. Explore how racial justice, economics, politics,
  technology, and globalization shaped — and were shaped by — the music.
</p>
*/}
```

- [ ] **Step 7: Update `src/pages/Timeline.tsx`**

Lines 51-54 -- remove the `<p>` block:
```tsx
{/* Remove:
<p className="text-xl text-warm-gray max-w-2xl mx-auto">
  From New Orleans to the present day, explore a century of jazz evolution.
  Each era built on what came before while pushing music into new territory.
</p>
*/}
```

- [ ] **Step 8: Verify all pages**

Run: `npm run dev`, check each page: Home, Albums, Artists, Eras, Playlists, Timeline, ParallelTimeline.
Expected: No verbose subtitles. Titles only. Filter counts appear only when filters are active (Albums, Artists).

- [ ] **Step 9: Commit**

```bash
git add src/pages/Home.tsx src/pages/Albums.tsx src/pages/Artists.tsx src/pages/Eras.tsx src/pages/Playlists.tsx src/pages/ParallelTimeline.tsx src/pages/Timeline.tsx
git commit -m "feat: strip verbose page descriptions, keep titles only"
```

---

## Task 8: Generate Song-Based Playlists

**Files:**
- Create: `scripts/generate_playlists.py`
- Modify (output): `src/data/playlists.json`

- [ ] **Step 1: Write the playlist generation script**

Create `scripts/generate_playlists.py`:

```python
#!/usr/bin/env python3
"""Generate song-based playlists from album keyTracks data."""

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALBUMS_PATH = ROOT / "src" / "data" / "albums.json"
OUTPUT_PATH = ROOT / "src" / "data" / "playlists.json"

random.seed(42)  # Reproducible output

PLAYLIST_DEFS = [
    {
        "id": "morning-jazz",
        "name": "Morning Jazz",
        "mood": "morning",
        "description": "Bright, melodic jazz for starting the day.",
        "tags": ["bright", "energizing", "melodic"],
        "genres": ["cool jazz", "bossa nova", "vocal jazz", "swing"],
        "eras": [],
        "labels": [],
    },
    {
        "id": "afternoon-groove",
        "name": "Afternoon Groove",
        "mood": "afternoon",
        "description": "Hard-swinging grooves for the middle of the day.",
        "tags": ["groovy", "warm", "rhythmic"],
        "genres": ["hard bop", "post-bop", "soul jazz"],
        "eras": [],
        "labels": [],
    },
    {
        "id": "evening-wind-down",
        "name": "Evening Wind Down",
        "mood": "evening",
        "description": "Cool, unhurried jazz for the evening.",
        "tags": ["relaxed", "warm", "easy"],
        "genres": ["cool jazz", "modal jazz", "vocal jazz"],
        "eras": ["cool-jazz", "bebop"],
        "labels": [],
    },
    {
        "id": "late-night",
        "name": "Late Night",
        "mood": "night",
        "description": "Dark, searching jazz for after midnight.",
        "tags": ["dark", "introspective", "late-night"],
        "genres": ["free jazz", "avant-garde jazz", "modal jazz"],
        "eras": ["free-jazz"],
        "labels": [],
    },
    {
        "id": "first-listen",
        "name": "Gateway to Jazz",
        "mood": "gateway",
        "description": "Entry points across every era.",
        "tags": ["essential", "accessible", "classic"],
        "genres": [],
        "eras": [],
        "labels": [],
    },
    {
        "id": "deep-focus",
        "name": "Deep Focus",
        "mood": "cerebral",
        "description": "Complex, demanding jazz that rewards close listening.",
        "tags": ["complex", "cerebral", "deep-cuts"],
        "genres": ["free jazz", "avant-garde jazz", "experimental", "free improvisation"],
        "eras": [],
        "labels": [],
    },
    {
        "id": "blue-hours",
        "name": "Blue Hours",
        "mood": "melancholy",
        "description": "Ballads and blues-drenched jazz.",
        "tags": ["melancholy", "slow", "emotional"],
        "genres": ["blues", "vocal jazz", "cool jazz"],
        "eras": [],
        "labels": [],
    },
    {
        "id": "joyful-noise",
        "name": "Joyful Noise",
        "mood": "joyful",
        "description": "Upbeat, high-energy jazz that swings hard.",
        "tags": ["joyful", "energizing", "upbeat"],
        "genres": ["swing", "bebop", "soul jazz", "latin jazz"],
        "eras": [],
        "labels": [],
    },
    {
        "id": "city-streets",
        "name": "City Streets",
        "mood": "urban",
        "description": "Hard bop and soul jazz from the city.",
        "tags": ["urban", "gritty", "soulful"],
        "genres": ["hard bop", "post-bop", "soul jazz"],
        "eras": ["hard-bop"],
        "labels": [],
    },
    {
        "id": "european-voices",
        "name": "European Voices",
        "mood": "european",
        "description": "ECM aesthetics and European jazz traditions.",
        "tags": ["atmospheric", "european", "chamber"],
        "genres": ["chamber jazz", "contemporary jazz", "world jazz"],
        "eras": [],
        "labels": ["ECM"],
    },
    {
        "id": "spiritual-jazz",
        "name": "Spiritual Jazz",
        "mood": "spiritual",
        "description": "Gospel-inflected, transcendent jazz.",
        "tags": ["spiritual", "transcendent", "devotional"],
        "genres": ["spiritual jazz", "free jazz"],
        "eras": [],
        "labels": [],
    },
    {
        "id": "electric-era",
        "name": "Electric Era",
        "mood": "fusion",
        "description": "Jazz meets rock, funk, and electronics.",
        "tags": ["electric", "funky", "fusion"],
        "genres": ["jazz fusion", "jazz-funk"],
        "eras": [],
        "labels": [],
    },
]


def matches_playlist(album: dict, pdef: dict) -> bool:
    """Check if an album matches a playlist definition's criteria."""
    # Gateway playlist: special handling -- pick from all eras, prefer albums with spotifyUrl
    if pdef["mood"] == "gateway":
        return bool(album.get("spotifyUrl"))

    album_genres = [g.lower() for g in album.get("genres", [])]
    album_era = album.get("era", "")
    album_label = album.get("label", "")

    genre_match = any(
        g.lower() in album_genres for g in pdef["genres"]
    ) if pdef["genres"] else False

    era_match = album_era in pdef["eras"] if pdef["eras"] else False

    label_match = any(
        l.lower() in album_label.lower() for l in pdef["labels"]
    ) if pdef["labels"] else False

    return genre_match or era_match or label_match


def build_playlist(albums: list[dict], pdef: dict) -> dict:
    """Build a single playlist from matching albums."""
    # Find matching albums
    if pdef["mood"] == "gateway":
        # Pick 3-4 from each era, prioritizing albums with spotifyUrl
        era_buckets: dict[str, list[dict]] = {}
        for a in albums:
            if not a.get("keyTracks"):
                continue
            era = a.get("era", "")
            if era not in era_buckets:
                era_buckets[era] = []
            era_buckets[era].append(a)

        # Sort each bucket: spotifyUrl first, then shuffle
        matching = []
        for era, bucket in sorted(era_buckets.items()):
            with_spotify = [a for a in bucket if a.get("spotifyUrl")]
            without = [a for a in bucket if not a.get("spotifyUrl")]
            random.shuffle(with_spotify)
            random.shuffle(without)
            matching.extend((with_spotify + without)[:4])
    else:
        matching = [a for a in albums if matches_playlist(a, pdef) and a.get("keyTracks")]
        random.shuffle(matching)

    # Build track list with artist diversity cap
    tracks: list[dict] = []
    artist_count: dict[str, int] = {}
    used_albums: list[dict] = []

    for album in matching:
        artist = album.get("artist", "")
        if artist_count.get(artist, 0) >= 2:
            continue

        # Pick 1 track from this album
        key_tracks = album.get("keyTracks", [])
        if not key_tracks:
            continue

        track = random.choice(key_tracks)
        tracks.append({"albumId": album["id"], "track": track})
        artist_count[artist] = artist_count.get(artist, 0) + 1
        used_albums.append(album)

        if len(tracks) >= 25:
            break

    # Pick cover album from the first matching album
    cover_album_id = used_albums[0]["id"] if used_albums else matching[0]["id"] if matching else "kind-of-blue"

    return {
        "id": pdef["id"],
        "name": pdef["name"],
        "mood": pdef["mood"],
        "description": pdef["description"],
        "tags": pdef["tags"],
        "tracks": tracks,
        "coverAlbumId": cover_album_id,
    }


def main():
    with open(ALBUMS_PATH) as f:
        albums = json.load(f)

    playlists = [build_playlist(albums, pdef) for pdef in PLAYLIST_DEFS]

    with open(OUTPUT_PATH, "w") as f:
        json.dump(playlists, f, indent=2, ensure_ascii=False)

    for p in playlists:
        count = len(p['tracks'])
        warning = " ** LOW TRACK COUNT" if count < 10 else ""
        print(f"  {p['name']}: {count} tracks{warning}")

    print(f"\nWrote {len(playlists)} playlists to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script**

Run: `python3 scripts/generate_playlists.py`
Expected: Output showing 12 playlists with ~20-25 tracks each. File `src/data/playlists.json` updated.

- [ ] **Step 3: Verify playlist page**

Run: `npm run dev`, navigate to `/playlists`
Expected: 12 playlists displayed with individual tracks. Tag filters work.

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_playlists.py src/data/playlists.json
git commit -m "feat: auto-generate song-based playlists from album keyTracks"
```

---

## Task 9: Build Verification

- [ ] **Step 1: Run production build**

Run: `npm run build`
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 2: Preview production build**

Run: `npm run preview`
Expected: Site loads correctly with all monochrome colors, serif fonts, stripped descriptions, and new playlists.

- [ ] **Step 3: Commit (if any fixes needed)**

Only if the build revealed issues that required fixes.

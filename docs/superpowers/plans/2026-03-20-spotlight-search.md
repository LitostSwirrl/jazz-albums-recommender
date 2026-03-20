# Spotlight Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Spotlight-style search to the site header that searches across 1000 albums and 275 artists with a translucent floating results popup.

**Architecture:** Single new component (`SearchBar.tsx`) handles all search state, filtering, scoring, and popup rendering. Integrated into the existing `Header.tsx` via import. Minor update to `Artists.tsx` to accept `?q=` URL param for "View all" links.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, React Router DOM (existing stack, no new deps)

**Spec:** `docs/superpowers/specs/2026-03-20-spotlight-search-design.md`

---

### Task 1: Create SearchBar component -- icon + expandable input

**Files:**
- Create: `src/components/layout/SearchBar.tsx`

This task builds the shell: a magnifying glass icon button that expands into an input field with smooth animation. No search logic yet.

- [ ] **Step 1: Create SearchBar.tsx with icon-only state**

```tsx
import { useState, useRef, useEffect } from 'react';

interface SearchBarProps {
  onOpenChange?: (isOpen: boolean) => void;
}

export function SearchBar({ onOpenChange }: SearchBarProps) {
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const iconRef = useRef<HTMLButtonElement>(null);

  const open = () => {
    setIsOpen(true);
    onOpenChange?.(true);
  };

  const close = () => {
    setIsOpen(false);
    onOpenChange?.(false);
    iconRef.current?.focus();
  };

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  return (
    <div className="relative">
      {isOpen ? (
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-warm-gray shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-label="Search artists and albums"
            aria-expanded={false}
            aria-autocomplete="list"
            placeholder="Search artists, albums..."
            className="bg-transparent border-b border-warm-gray/40 text-charcoal text-sm outline-none flex-1 min-w-0 md:w-56 py-1 placeholder:text-warm-gray/60 focus:border-coral transition-colors"
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                e.stopPropagation();
                close();
              }
            }}
          />
          <button
            onClick={close}
            className="text-warm-gray hover:text-charcoal transition-colors p-0.5"
            aria-label="Close search"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      ) : (
        <button
          ref={iconRef}
          onClick={open}
          className="text-warm-gray hover:text-coral transition-colors p-1 focus:outline-none focus:ring-2 focus:ring-coral focus:ring-offset-2 focus:ring-offset-cream rounded"
          aria-label="Open search"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify the component renders**

Run: `npm run dev`
Manually verify: Open the browser, import SearchBar anywhere temporarily, confirm the magnifying glass icon renders and toggles to input on click.

- [ ] **Step 3: Commit**

```bash
git add src/components/layout/SearchBar.tsx
git commit -m "feat: add SearchBar component shell with expandable input"
```

---

### Task 2: Integrate SearchBar into Header

**Files:**
- Modify: `src/components/layout/Header.tsx`

Place the SearchBar in the header nav, coordinate with mobile menu state.

- [ ] **Step 1: Add SearchBar to desktop nav**

In `Header.tsx`, add a `searchOpen` state. Import `SearchBar`. Place it after the Explore dropdown in the desktop nav. Pass `onOpenChange` to close the mobile menu when search opens. Close search when mobile menu opens.

```tsx
// Add to imports:
import { SearchBar } from './SearchBar';

// Add state inside Header():
const [searchOpen, setSearchOpen] = useState(false);

// When search opens, close mobile menu:
const handleSearchOpenChange = (open: boolean) => {
  setSearchOpen(open);
  if (open) {
    setMobileMenuOpen(false);
    setShowExplore(false);
  }
};

// When mobile menu opens, close search:
// Modify the mobile menu button onClick:
onClick={() => {
  setMobileMenuOpen(!mobileMenuOpen);
  if (!mobileMenuOpen) setSearchOpen(false);
}}
```

Place `<SearchBar onOpenChange={handleSearchOpenChange} />` after the Explore dropdown `<div>` in the desktop nav, and before the mobile hamburger button (so it shows on mobile too). On mobile, add `className` adjustments so the input takes more width.

- [ ] **Step 2: Add SearchBar to mobile-visible area**

Move the SearchBar outside the `hidden md:flex` desktop nav container. Place it in the header bar between the desktop nav and the hamburger button, so it's visible on both desktop and mobile:

```tsx
{/* Desktop nav */}
<div className="hidden md:flex gap-8 items-center">
  {/* ... nav links, Explore dropdown ... */}
  <SearchBar onOpenChange={handleSearchOpenChange} />
</div>

{/* Mobile: search + hamburger */}
<div className="flex md:hidden items-center gap-2">
  <SearchBar onOpenChange={handleSearchOpenChange} />
  {/* hamburger button */}
</div>
```

- [ ] **Step 3: Verify in browser**

Run: `npm run dev`
Check:
- Desktop: search icon appears in nav bar, expands on click, Escape closes it
- Mobile: search icon appears next to hamburger, expands on click
- Opening search closes mobile menu and Explore dropdown

- [ ] **Step 4: Commit**

```bash
git add src/components/layout/Header.tsx
git commit -m "feat: integrate SearchBar into Header with menu coordination"
```

---

### Task 3: Add search logic with scoring

**Files:**
- Modify: `src/components/layout/SearchBar.tsx`

Add the debounced search, scoring, and result computation.

- [ ] **Step 1: Add data imports and search state**

```tsx
import { useState, useRef, useEffect, useMemo } from 'react';
import albumsData from '../../data/albums.json';
import artistsData from '../../data/artists.json';
import type { Album, Artist } from '../../types';

const albums = albumsData as Album[];
const artists = artistsData as Artist[];
```

Add `query` and `debouncedQuery` state:

```tsx
const [query, setQuery] = useState('');
const [debouncedQuery, setDebouncedQuery] = useState('');

useEffect(() => {
  const timer = setTimeout(() => setDebouncedQuery(query), 150);
  return () => clearTimeout(timer);
}, [query]);
```

- [ ] **Step 2: Add scoring function and results computation**

```tsx
interface ScoredArtist {
  artist: Artist;
  score: number;
}

interface ScoredAlbum {
  album: Album;
  score: number;
}

const { scoredArtists, scoredAlbums } = useMemo(() => {
  if (debouncedQuery.length < 2) {
    return { scoredArtists: [], scoredAlbums: [] };
  }

  const q = debouncedQuery.toLowerCase();

  const scoredArtists: ScoredArtist[] = [];
  for (const artist of artists) {
    let score = 0;
    const nameLower = artist.name.toLowerCase();
    if (nameLower.startsWith(q)) {
      score = 100;
    } else if (nameLower.includes(q)) {
      score = 50;
    }
    if (artist.instruments.some((i) => i.toLowerCase().includes(q))) {
      score = Math.max(score, 20);
    }
    if (score > 0) {
      scoredArtists.push({ artist, score });
    }
  }
  scoredArtists.sort((a, b) => b.score - a.score);

  const scoredAlbums: ScoredAlbum[] = [];
  for (const album of albums) {
    let score = 0;
    const titleLower = album.title.toLowerCase();
    if (titleLower.startsWith(q)) {
      score = 100;
    } else if (titleLower.includes(q)) {
      score = 50;
    }
    if (album.artist.toLowerCase().includes(q)) {
      score = Math.max(score, 30);
    }
    if (score > 0) {
      scoredAlbums.push({ album, score });
    }
  }
  scoredAlbums.sort((a, b) => b.score - a.score);

  return { scoredArtists, scoredAlbums };
}, [debouncedQuery]);
```

- [ ] **Step 3: Wire input to query state**

Update the `<input>` to use `query` state:

```tsx
value={query}
onChange={(e) => setQuery(e.target.value)}
aria-expanded={debouncedQuery.length >= 2}
```

Update `close()` to also reset query:

```tsx
const close = () => {
  setIsOpen(false);
  setQuery('');
  setDebouncedQuery('');
  onOpenChange?.(false);
  iconRef.current?.focus();
};
```

- [ ] **Step 4: Verify search logic**

Run: `npm run dev`
Open search, type "miles" -- should see console.log or just verify no errors. Results rendering comes next task.

- [ ] **Step 5: Commit**

```bash
git add src/components/layout/SearchBar.tsx
git commit -m "feat: add debounced search logic with scoring for artists and albums"
```

---

### Task 4: Render the floating results popup

**Files:**
- Modify: `src/components/layout/SearchBar.tsx`

Add the translucent popup with grouped results, click-outside dismissal, and navigation.

- [ ] **Step 1: Add navigation import and click-outside handler**

```tsx
import { useNavigate } from 'react-router-dom';

// Inside component:
const navigate = useNavigate();
const containerRef = useRef<HTMLDivElement>(null);

useEffect(() => {
  if (!isOpen) return;
  const handleClickOutside = (e: MouseEvent) => {
    if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
      close();
    }
  };
  document.addEventListener('mousedown', handleClickOutside);
  return () => document.removeEventListener('mousedown', handleClickOutside);
}, [isOpen]);
```

Wrap the entire component return in `<div ref={containerRef}>`.

- [ ] **Step 2: Add the results popup JSX**

Below the input `<div>`, add the popup. It renders when `debouncedQuery.length >= 2`:

```tsx
const showPopup = isOpen && debouncedQuery.length >= 2;
const hasResults = scoredArtists.length > 0 || scoredAlbums.length > 0;
const displayArtists = scoredArtists.slice(0, 5);
const displayAlbums = scoredAlbums.slice(0, 5);

// In JSX, after the input container:
{showPopup && (
  <div
    role="listbox"
    className="absolute top-full right-0 mt-2 w-[calc(100vw-2rem)] md:w-96 max-h-[400px] overflow-y-auto rounded-xl bg-charcoal/80 backdrop-blur-xl border border-white/10 shadow-2xl z-50"
  >
    {!hasResults ? (
      <div className="px-4 py-6 text-center text-warm-gray/70 text-sm">
        No results for "{debouncedQuery}"
      </div>
    ) : (
      <>
        {displayArtists.length > 0 && (
          <div>
            <div className="px-4 pt-3 pb-1 text-xs text-warm-gray/50 uppercase tracking-wider font-mono">
              Artists
            </div>
            {displayArtists.map(({ artist }) => (
              <button
                key={artist.id}
                role="option"
                aria-selected={false}
                className="w-full text-left px-4 py-2.5 hover:bg-white/10 transition-colors cursor-pointer"
                onClick={() => {
                  navigate(`/artist/${artist.id}`);
                  close();
                }}
              >
                <span className="text-cream text-sm">{artist.name}</span>
                <span className="text-warm-gray/50 text-xs ml-2">
                  -- {artist.instruments.slice(0, 3).join(', ')}
                </span>
              </button>
            ))}
            {scoredArtists.length > 5 && (
              <button
                className="w-full text-left px-4 py-2 text-coral/80 hover:text-coral text-xs transition-colors"
                onClick={() => {
                  navigate(`/artists?q=${encodeURIComponent(query)}`);
                  close();
                }}
              >
                View all {scoredArtists.length} artists
              </button>
            )}
          </div>
        )}
        {displayAlbums.length > 0 && (
          <div className={displayArtists.length > 0 ? 'border-t border-white/10' : ''}>
            <div className="px-4 pt-3 pb-1 text-xs text-warm-gray/50 uppercase tracking-wider font-mono">
              Albums
            </div>
            {displayAlbums.map(({ album }) => (
              <button
                key={album.id}
                role="option"
                aria-selected={false}
                className="w-full text-left px-4 py-2.5 hover:bg-white/10 transition-colors cursor-pointer"
                onClick={() => {
                  navigate(`/album/${album.id}`);
                  close();
                }}
              >
                <span className="text-cream text-sm">{album.title}</span>
                <span className="text-warm-gray/50 text-xs ml-2">
                  -- {album.artist} ({album.year})
                </span>
              </button>
            ))}
            {scoredAlbums.length > 5 && (
              <button
                className="w-full text-left px-4 py-2 text-coral/80 hover:text-coral text-xs transition-colors"
                onClick={() => {
                  navigate(`/albums?q=${encodeURIComponent(query)}`);
                  close();
                }}
              >
                View all {scoredAlbums.length} albums
              </button>
            )}
          </div>
        )}
      </>
    )}
  </div>
)}
```

- [ ] **Step 3: Verify popup in browser**

Run: `npm run dev`
Check:
- Type "miles" -- shows Artists section with Miles Davis, Albums section with his albums
- Type "kind of" -- shows "Kind of Blue" in albums
- Type "xyznoexist" -- shows "No results" message
- Click a result -- navigates to detail page, popup closes
- Click outside -- popup closes

- [ ] **Step 4: Commit**

```bash
git add src/components/layout/SearchBar.tsx
git commit -m "feat: add translucent floating results popup with grouped results"
```

---

### Task 5: Add keyboard navigation (arrow keys + Enter)

**Files:**
- Modify: `src/components/layout/SearchBar.tsx`

- [ ] **Step 1: Add highlightedIndex state and keyboard handler**

```tsx
const [highlightedIndex, setHighlightedIndex] = useState(-1);

// Reset highlighted index when results change
useEffect(() => {
  setHighlightedIndex(-1);
}, [debouncedQuery]);

// Build a flat list of all navigable results for keyboard nav
const allResults = useMemo(() => {
  const results: Array<{ type: 'artist'; id: string } | { type: 'album'; id: string }> = [];
  displayArtists.forEach(({ artist }) => results.push({ type: 'artist', id: artist.id }));
  displayAlbums.forEach(({ album }) => results.push({ type: 'album', id: album.id }));
  return results;
}, [displayArtists, displayAlbums]);
```

- [ ] **Step 2: Add onKeyDown handler to input**

```tsx
onKeyDown={(e) => {
  if (e.key === 'Escape') {
    e.stopPropagation();
    close();
    return;
  }
  if (!showPopup || !hasResults) return;
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    setHighlightedIndex((prev) => (prev + 1) % allResults.length);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    setHighlightedIndex((prev) => (prev - 1 + allResults.length) % allResults.length);
  } else if (e.key === 'Enter' && highlightedIndex >= 0) {
    e.preventDefault();
    const selected = allResults[highlightedIndex];
    navigate(`/${selected.type === 'artist' ? 'artist' : 'album'}/${selected.id}`);
    close();
  }
}}
```

- [ ] **Step 3: Highlight the active result row**

Compute a running index for each result button to compare with `highlightedIndex`. Update `aria-selected` and add a highlight class:

For each artist button, track its position in the flat list (index `i` where `i` is the loop index). For album buttons, offset by `displayArtists.length`.

```tsx
// Artist buttons:
{displayArtists.map(({ artist }, i) => (
  <button
    key={artist.id}
    role="option"
    aria-selected={highlightedIndex === i}
    className={`w-full text-left px-4 py-2.5 transition-colors cursor-pointer ${
      highlightedIndex === i ? 'bg-white/15' : 'hover:bg-white/10'
    }`}
    ...
  >

// Album buttons (offset by displayArtists.length):
{displayAlbums.map(({ album }, i) => {
  const flatIndex = displayArtists.length + i;
  return (
    <button
      key={album.id}
      role="option"
      aria-selected={highlightedIndex === flatIndex}
      className={`w-full text-left px-4 py-2.5 transition-colors cursor-pointer ${
        highlightedIndex === flatIndex ? 'bg-white/15' : 'hover:bg-white/10'
      }`}
      ...
    >
```

- [ ] **Step 4: Verify keyboard navigation**

Run: `npm run dev`
Check:
- Type "miles", press Down arrow -- first result highlights
- Keep pressing Down -- cycles through results
- Press Up -- moves backward
- Press Enter on highlighted result -- navigates to that page
- Press Escape -- closes search

- [ ] **Step 5: Commit**

```bash
git add src/components/layout/SearchBar.tsx
git commit -m "feat: add arrow key navigation and Enter selection to search"
```

---

### Task 6: Add ?q= URL param support to Artists.tsx

**Files:**
- Modify: `src/pages/Artists.tsx`

The Albums page already reads `?q=` from URL params. Artists page needs the same so "View all N artists" links from the search popup work.

**Note:** Albums.tsx initializes `searchQuery` from `useState(searchParams.get('q'))` which only reads on mount. If the user is already on `/albums` and clicks "View all albums" from search, the URL updates but the component won't re-read the param. Add a `useEffect` syncing `searchParams.get('q')` into the search state to fix this.

- [ ] **Step 1: Add useSearchParams to Artists.tsx**

Replace the local `searchQuery` state with URL-driven state:

```tsx
// Add import:
import { Link, useSearchParams } from 'react-router-dom';

// Replace useState for searchQuery:
const [searchParams, setSearchParams] = useSearchParams();
const searchQuery = searchParams.get('q') || '';

// Replace setSearchQuery calls with:
const updateSearch = (value: string) => {
  const params = new URLSearchParams(searchParams);
  if (value) {
    params.set('q', value);
  } else {
    params.delete('q');
  }
  params.delete('page');
  setSearchParams(params);
  setCurrentPage(1);
};
```

Update the search input's `value` to use `searchQuery` and `onChange` to call `updateSearch(e.target.value)`.

- [ ] **Step 2: Verify "View all" link works**

Run: `npm run dev`
Check:
- Open search, type "trumpet", click "View all N artists"
- Should navigate to `/artists?q=trumpet`
- Artists page should show filtered results with "trumpet" in the search input
- Same for albums: "View all N albums" navigates to `/albums?q=...`

- [ ] **Step 3: Commit**

```bash
git add src/pages/Artists.tsx
git commit -m "feat: add URL search param support to Artists page for search integration"
```

---

### Task 7: Final polish and build verification

**Files:**
- All modified files

- [ ] **Step 1: Run production build**

```bash
npm run build
```

Fix any TypeScript errors.

- [ ] **Step 2: Test full flow end-to-end**

Run: `npm run preview`
Check:
- Search icon in header on desktop and mobile
- Click to expand, type query, see translucent popup
- Results grouped: Artists on top, Albums below
- Click result -- navigates to detail page
- "View all" links work for both artists and albums
- Escape key closes search
- Click outside closes search
- Arrow keys + Enter work
- Mobile: input takes full width, popup is full width
- No console errors

- [ ] **Step 3: Commit any polish fixes**

```bash
git add src/components/layout/SearchBar.tsx src/components/layout/Header.tsx src/pages/Artists.tsx
git commit -m "fix: polish search bar styling and edge cases"
```

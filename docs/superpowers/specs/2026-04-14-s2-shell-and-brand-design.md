# S2 — Shell & Brand

**Parent:** `2026-04-14-overhaul-master.md`
**Scope:** PWA icons + manifest, font swap (serif → sans), footer removal, app rename "Jazz Guide" → "Smack Cats".

All four items are shell/brand layer. No data changes. No new features. Shippable in a single deploy.

## 1. PWA homescreen icon

### Problem
Mobile "Add to Home Screen" produces a generic screenshot-of-page icon because `index.html` has no manifest and no rasterized icon PNGs. The existing `public/favicon.svg` renders fine in browser tabs (desktop) but iOS/Android homescreen do not accept SVG.

### Required artifacts
1. `public/manifest.webmanifest` — PWA manifest referencing PNG icons and matching current theme color (`#1a1917` — dark editorial background).
2. Rasterized PNGs generated from the existing `public/favicon.svg` **without modifying the SVG**:
   - `public/icon-192.png` (192×192, Android)
   - `public/icon-512.png` (512×512, Android / PWA install)
   - `public/apple-touch-icon.png` (180×180, iOS homescreen)
3. New link tags in `index.html`:
   - `<link rel="manifest" href="/jazz-albums-recommender/manifest.webmanifest" />`
   - `<link rel="apple-touch-icon" href="/jazz-albums-recommender/apple-touch-icon.png" />`

### How to rasterize
Use a one-off Python script in `scripts/` (e.g., `scripts/generate_pwa_icons.py`) that uses `cairosvg` or `Pillow + rsvg-convert`. Run it once, commit the PNGs to `public/`, don't keep regenerating in CI.

### Manifest contents
```json
{
  "name": "Smack Cats",
  "short_name": "Smack Cats",
  "description": "A personal jazz listening guide.",
  "start_url": "/jazz-albums-recommender/",
  "display": "standalone",
  "background_color": "#1a1917",
  "theme_color": "#1a1917",
  "icons": [
    { "src": "/jazz-albums-recommender/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/jazz-albums-recommender/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

### Verification
- `npm run build` succeeds; PNG files present in `dist/`.
- Open `npm run preview` on mobile (or Chrome DevTools → Application → Manifest) — manifest validates, icons resolve.
- Actually perform "Add to Home Screen" on a real iPhone OR verify via Chrome DevTools Lighthouse PWA audit ≥ green on "Installable" section.

## 2. Font swap (serif → modern sans)

### Problem
`index.html` loads DM Serif Display + Source Serif 4 from Google Fonts. `src/index.css` points `--font-display`, `--font-heading`, `--font-body` all at serif values. User finds this "feels so old."

### Target stack
- **Display** (large headings, hero type): `Space Grotesk` (400, 500, 700) — architectural, slightly geometric, pairs with monochrome editorial
- **Body** (paragraphs, UI): `Inter` (300, 400, 500, 600) — neutral workhorse, excellent at small sizes
- **Mono** (accents, meta): `JetBrains Mono` — keep as-is

### Changes required

**`index.html`:**
- Replace the Google Fonts `<link>` at line 33 with:
  ```html
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet" />
  ```
- Update the comment from "Serif type stack" to something neutral.
- Replace the serif loading-screen `<div>` style at line 58:
  - `font-family: 'Source Serif 4', Georgia, serif;` → `font-family: 'Inter', system-ui, sans-serif;`

**`src/index.css`:**
- Update `@theme` tokens at lines 9–12:
  ```css
  --font-display: 'Space Grotesk', system-ui, sans-serif;
  --font-heading: 'Space Grotesk', system-ui, sans-serif;
  --font-body: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Courier New', monospace;
  ```
- Update the comment on line 8 from "Typography -- Serif stack" to "Typography — Sans stack".

### Memory update at end of session
- **Delete** `feedback_serif_override.md` (user has reversed that preference).
- **Create** a new feedback memory capturing: "As of 2026-04-14, no serifs in this project. Earlier 'nostalgic' exception is revoked. Defaults to global no-serif rule."
- Update `MEMORY.md` index to match.

### Verification
- `npm run dev` — visually spot-check home page, album detail page, artist page. No serif glyphs anywhere.
- Run `rg -i 'serif' src/ index.html` — only match allowed is `system-ui, sans-serif` fallbacks.
- `rg 'DM Serif|Source Serif|Crimson|Playfair|Merriweather|Lora|Fraunces'` — should return nothing.

## 3. Remove footer

### Problem
`src/components/layout/Footer.tsx` renders "A personal jazz listening guide" + "Data sourced from Wikipedia and MusicBrainz". User: reads as AI-generated boilerplate.

### Approach
**Delete the component entirely**, not just its contents. Then remove its import and `<Footer />` usage site.

### Steps
1. Find all imports: `rg "from.*layout/Footer" src/`
2. Remove `<Footer />` from the layout component that uses it (likely `src/components/layout/` sibling or a root App).
3. Delete `src/components/layout/Footer.tsx`.
4. If the parent layout used `flex flex-col min-h-screen` with the footer as the mt-auto anchor, verify the layout still looks correct without it (main content should still fill the viewport cleanly).

### Verification
- `rg "Footer" src/` — returns zero matches.
- Visual check: bottom of any page looks clean, no awkward whitespace.

## 4. Rename "Jazz Guide" → "Smack Cats"

### Locations to change
- `index.html`:
  - Line 6: `<title>` — "Jazz Guide - Your Personal Jazz Companion" → "Smack Cats — A Personal Jazz Companion"
  - Line 9: meta description — replace "750+" with the real number (1000) AND any "Jazz Guide" self-reference
  - Line 11: `meta name="author"` — "Jazz Guide" → "Smack Cats"
  - Line 15: `og:site_name` — "Jazz Guide" → "Smack Cats"
  - Line 18: `og:title` — same swap as title
  - Line 19: `og:description` — same swap as meta description
  - Line 24: `twitter:title` — same swap
  - Line 25: `twitter:description` — same swap
  - Line 59: loading screen text "Loading Jazz Guide..." → "Loading Smack Cats…"
  - Line 65: noscript message — "Jazz Guide" → "Smack Cats"
- `src/components/SEO.tsx` — any hardcoded "Jazz Guide" string (check with grep).
- `public/404.html` — "Jazz Guide" reference.
- `package.json` — check `"name"` (currently `jazz_albums_recommends`). DO NOT rename the package or repo — the GitHub Pages URL (`litostswirrl.github.io/jazz-albums-recommender/`) must stay stable. Only user-visible strings change.

### Verification
- `rg -i "jazz guide" .` → zero matches (excluding node_modules, dist, docs/superpowers).
- Browser tab title reads "Smack Cats — …".
- View source on deployed site: OG tags show "Smack Cats".

## 5. Out of scope for S2
- Do not touch `albums.json`, `artists.json`, or any data files.
- Do not change the "Why It Matters" / "About this Album" rendering in `Album.tsx` — that's S3.
- Do not add analytics — that's S4.
- Do not add dark-mode toggle, PWA offline support, or any new features.

## Completion checklist (all must be true before handoff)

- [ ] PWA: manifest + 3 PNG icons committed, link tags added, Lighthouse "Installable" passes
- [ ] Fonts: no serif references left in `src/` or `index.html` (Tailwind fallback keywords OK)
- [ ] Footer: component deleted, no `<Footer />` references
- [ ] Rename: "Jazz Guide" nowhere except inside `docs/` and repo URL
- [ ] `npm run typecheck` passes
- [ ] `npm run build` passes
- [ ] `npm run dev` — manual smoke test of home, album, artist, era pages
- [ ] Memory: `feedback_serif_override.md` deleted, replaced with reinstated no-serif rule. `MEMORY.md` updated.
- [ ] New memory entry: app is now named "Smack Cats" (stays useful into S3/S4)
- [ ] Commit(s) pushed; deploy via `npm run deploy`
- [ ] Log entry appended to `docs/superpowers/logs/2026-04-14-overhaul-log.md`
- [ ] S3 kickoff prompt written into the same log file as a code block

## Memory entries to create/update

At end of session:
1. **Update** (or create) a memory noting the app's current name is "Smack Cats".
2. **Delete** `feedback_serif_override.md`.
3. **Create** a new feedback entry: `feedback_no_serifs.md` — "No serifs anywhere in this project. Earlier override revoked 2026-04-14 because serifs 'felt old.' This matches global CLAUDE.md rule."
4. **Update** `MEMORY.md` index accordingly.

## S3 kickoff prompt

Write this as the final step of S2, appended to `docs/superpowers/logs/2026-04-14-overhaul-log.md` under a "## Next session" heading. Template:

```
I'm continuing the jazz site v2 overhaul. S2 is done (shell & brand).

Please read these files in order, then execute S3:
1. docs/superpowers/specs/2026-04-14-overhaul-master.md
2. docs/superpowers/specs/2026-04-14-s3-data-audit-design.md
3. docs/superpowers/logs/2026-04-14-overhaul-log.md (for what S2 actually shipped)

Follow the spec exactly. At the end, update memory entries as listed in the S3 spec, append a log entry, and write the S4 kickoff prompt to the log file. Don't ask for clarifications unless truly stuck.
```

# v2 Overhaul — Session Log

Append-only. Each session writes an entry at the end.

---

## S1 — Brainstorm & decomposition (2026-04-14)

**Shipped:**
- Master spec + S2/S3/S4 specs written to `docs/superpowers/specs/`.
- This log file seeded.
- App rename decided: "Jazz Guide" → **"Smack Cats"** (user overrode AI pushback on the "smack" substance-abuse association — trade-off accepted).
- Issue #7 (feature triage) deferred to a post-analytics session; replaced in S4 with analytics install.
- Album schema decision: full migration to single `albumDNA` field in S3 (chosen over display-only merge).
- Fonts decision: Inter + Space Grotesk + JetBrains Mono (replacing DM Serif Display + Source Serif 4).
- PWA icon source: existing `public/favicon.svg` (vinyl with red label). No redesign — just rasterize to PNG.

**Deferred / open:**
- Feature triage until analytics data accumulates (≥ 2–4 weeks after S4 ships).

**Memory updates:**
- None this session. Reversal of `feedback_serif_override.md` happens in S2 (don't invalidate preferences before the code matches).

---

## S2 — Shell & brand (2026-04-14)

**Shipped:**
- PWA wiring: `public/manifest.webmanifest` created (name "Smack Cats", theme `#1a1917`, start_url `/jazz-albums-recommender/`, display `standalone`). Three PNGs rasterized from existing `public/favicon.svg` via `scripts/generate_pwa_icons.py` (cairosvg): `icon-192.png`, `icon-512.png`, `apple-touch-icon.png` (180x180). `index.html` now has `<link rel="apple-touch-icon">` and `<link rel="manifest">`. Favicon SVG untouched.
- Font swap: `src/index.css` `@theme` tokens moved from DM Serif Display / Source Serif 4 to Space Grotesk (display/heading) + Inter (body). JetBrains Mono kept. `index.html` Google Fonts `<link>` replaced; loading screen inline style moved from Source Serif 4 to Inter. Comment updated from "Serif stack" to "Sans stack."
- Footer removed: `src/components/layout/Footer.tsx` deleted; `<Footer />` stripped from `Layout.tsx`; re-export stripped from `layout/index.ts`. Layout still uses `flex flex-col min-h-screen` — main cleanly fills viewport without the footer anchor.
- Rename: "Jazz Guide" → "Smack Cats" everywhere user-visible. `index.html` title / meta / OG / Twitter / loading / noscript updated. Description updated to cite the real 1000-album count (was "750+"). `src/components/SEO.tsx` `fullTitle` template now `${title} | Smack Cats`. `public/404.html` title updated. Repo, package name, and GitHub Pages URL intentionally unchanged.

**Incidental cleanup:**
- Deleted `src/components/layout/SearchBar 2.tsx` — orphaned macOS Finder duplicate (space-in-name, syntax error at line 274, not imported anywhere). Surfaced by `tsc -b` on a clean first run. Not a refactor — dead artifact removal.

**Verification:**
- `npm run typecheck` → exit 0, clean (re-run after orphan removal).
- `npm run build` → exit 0. `dist/` contains all three icons + `manifest.webmanifest` + updated `index.html` (title "Smack Cats — A Personal Jazz Companion", font link points to Space Grotesk + Inter + JetBrains Mono).
- `rg -i "jazz guide"` outside `docs/` → 0 matches.
- `rg 'DM Serif|Source Serif|Crimson|Playfair|Merriweather|Lora|Fraunces'` in `src/` + `index.html` → 0 matches.
- `rg "Footer" src/` → 0 matches.
- Dev-server manual smoke test skipped — vite was slow to bind locally; relied on production build output instead. Flag if any runtime issue surfaces post-deploy.

**Memory updates:**
- Deleted `feedback_serif_override.md` (reversal enacted).
- Created `feedback_no_serifs.md` reinstating the no-serif rule with the 2026-04-14 reasoning.
- Created `project_app_name.md` locking in "Smack Cats" as the user-facing name.
- Updated `project_v2_overhaul.md` — marked S2 done.
- Updated `MEMORY.md` index to reflect all three changes.

**Deferred / open:**
- Real-device "Add to Home Screen" test deferred — the user can do this on their iPhone after deploy; manifest validates via Chrome DevTools but a Lighthouse PWA pass hasn't been run from CLI.

---

## S3 — Data audit & Album DNA (2026-04-14 → 2026-04-15)

**Shipped:**

- **Schema migration (destructive):** `scripts/migrate_to_album_dna.py`
  collapsed `description` + `significance` into one `albumDNA` field on all
  1000 albums. Pre-migration snapshot saved to
  `scripts/out/albums_pre_dna_backup.json` (gitignored — rollback via git
  history). `src/types/index.ts` Album interface updated. Consumers
  migrated in the same pass: `src/pages/Album.tsx` (single "Album DNA"
  section replaces "About this Album" + "Why It Matters"),
  `src/pages/Home.tsx`, `src/components/home/HeroFeature.tsx`,
  `src/components/home/RandomAlbumPicker.tsx`.
- **Description audit (principled detector):**
  `scripts/audit_album_descriptions.py` builds a 578-name index from
  artists.json and flags word-bounded cross-artist contamination + low
  Wikipedia jaccard for borderline cases. Iterative triage caught **10
  true corruptions**. Re-audit is idempotent and runnable in future
  sessions as the data evolves. Known limitation documented in the
  docstring: the cross-artist check over-flags editorial-style DNA that
  names personnel but not the leader — manual triage of borderline
  candidates is required. 2026-04-14 run: 9 candidates from the
  principled auditor, triaged to 3 rewrites + 6 false positives
  (editorial-style, topically correct).
- **Description rewrites:** `scripts/rewrite_album_dna.py` rewrote 10
  albums using MusicBrainz release-group metadata + curated dataset
  fields (year, label, genres, era, keyTracks). Targets: Art Tatum /
  In Private (Dusty Springfield corruption — now mentions Pablo 1976 +
  Fresh Sound 1991 reissue, spec-aligned manual curation); Joel Ross
  Broken Circles (was about the Levellers); Jaco Pastorius Jazz Street
  (was about Paul McCartney/Wings); Dave Brubeck Lullabies (was about
  Vijay Iyer); Various Artists The Real Book (was about Leonard Cohen);
  Eric Dolphy Screamin' the Blues (Oliver Nelson attribution noted);
  Jelly Roll Morton Volume 1 1923-1929 (was about Mingus Ah Um); Louis
  Armstrong Armstrong Alumni Allstars (was generic Wikipedia jazz
  article); Christian Sands Christmas Stories (was essay about Christmas
  in literature); Sun Ra Solo Piano at WKCR 1977 (was Charlie Parker
  biography).
- **Spot-check (50 random + Tatum):** 50/50 artist-name-present. Tatum
  "In Private" verified: mentions Tatum + Pablo, no Dusty / Springfield.
- **Spotify URL fill:** 946/1000 → **954/1000** (+8). Two passes: 3 found
  via `scripts/find_missing_spotify.py` (MusicBrainz URL relations); 5
  found via `scripts/fill_spotify_urls.py` with `market=US` + artist-sim
  ≥ 0.85 (spec threshold). 46 remain unresolved — listed in
  `scripts/out/spotify_fill_report.md`. Root cause of the low hit-rate:
  these are genuinely niche albums (free improv, avant-garde, posthumous
  compilations) that may not be on Spotify or that Spotify catalogs under
  a different primary artist. Spotify client-credential burst rate limits
  forced a wait between passes — documented.
- **Artist images:** `scripts/repair_artist_images.py` resolved 9 images
  (Art Tatum explicit re-source with 800px thumbnail URL + 8 of the 14
  previously-missing). Method: Wikipedia `pageimages` API (preferring
  thumbnail over multi-megabyte original), falling back to the
  `prop=images` list filtered for non-chrome/non-grave files, then
  Wikidata P18. **Bulk HEAD-verification was attempted and abandoned** —
  Wikimedia's upload.wikimedia.org CDN rate-limits parallel HEADs (429
  with explicit "use thumbnails" message). Existing URLs have been
  working in production; only the 14 missing + Tatum were touched. 5
  still unresolved (Various Artists, Yuki Arimasa, Johnny Dodds, Jazz
  Composer's Orchestra, Latin Jazz Quintet, Clarence Williams) — listed
  in `scripts/out/artist_images_report.md`. Spec flagged Tatum
  specifically; his new thumbnail URL is materially smaller (800px vs
  full 4.5MB JPEG) and should resolve the "photo doesn't render"
  complaint.

**Deferred / open:**

- 46 Spotify URLs unresolved by automation (user can hand-curate from
  `scripts/out/spotify_fill_report.md`).
- 5 artist images unresolved (listed in `artist_images_report.md`).
- 6 audit candidates left as editorial-style false positives (listed in
  `data_gaps.md`) — a future SEO pass could add leader names to these
  DNAs without changing factual content.
- **Album metadata questions** surfaced but not edited (scope): Tatum
  era/year mismatch, Brubeck/Pastorius posthumous-release dates, Dolphy
  vs Nelson attribution on Screamin' the Blues, etc. All listed in
  `data_gaps.md`.

**Verification:**

- `npm run typecheck` → exit 0 clean (after manually patching a stale
  `src/types/index.ts` that the first Edit didn't apply — the
  regression showed up as `tsc -b` errors about `albumDNA` not existing
  on Album).
- `npm run build` → exit 0. Dist regenerated with the new albumDNA Album
  page layout.
- Spot-check 50/50 artists present. Tatum assertion holds.

**Memory updates:**

- Updated `project_spotify_history.md` — 253 missing → 46 missing; noted
  the 2026-04-14 batch-fill method.
- Created `project_album_dna_schema.md` — locks the destructive
  migration + identifies `albumDNA` as the canonical field.
- Created `project_data_audit_tooling.md` — documents the audit's known
  limitation (over-flags editorial-style DNA) for future sessions.
- Updated `project_v2_overhaul.md` — marked S3 done, S4 next.
- Updated `MEMORY.md` index.

---

## Next session

Paste this into a fresh chat to kick off S4:

```
I'm continuing the jazz site v2 overhaul. S3 is done (data audit & Album DNA).

Please read these files in order, then execute S4:
1. docs/superpowers/specs/2026-04-14-overhaul-master.md
2. docs/superpowers/specs/2026-04-14-s4-analytics-install-design.md
3. docs/superpowers/logs/2026-04-14-overhaul-log.md (for what S2 and S3 shipped)

Follow the spec exactly. At the end, update memory, append a log entry, and note that feature triage is now deferred until 2–4 weeks of analytics data accumulate. Don't ask for clarifications unless truly stuck.
```

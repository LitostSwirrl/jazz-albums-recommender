# 2026-06-12 — Production-Grade Pass

Goal: ship to production grade on four fronts — secure (no leaks), Spotify-smooth (cache), inspiring-first / historically-flawless-second jazz content beyond Wikipedia, simple but with a clear agenda. North-star user: a guitarist seeking inspiration ("Orpheus").

## Security (Goal 1)
- Audited: NO secrets in tracked files, the deployed `gh-pages` branch, or the `dist` bundle (git grep + dist grep). No `import.meta.env`/`process.env` in client code → nothing sensitive bundled. No XSS sinks. Analytics (`track()`) sends only album/artist/era IDs — no PII/location.
- Hardened: geolocation rounded to ~1km before sharing with Open-Meteo (`src/hooks/useWeather.ts`).
- Pending USER action: rotate the dormant Spotify Client Secret in `.env` (OAuth removed 2026-03-23; unused but live; gitignored, not leaked). `VITE_SPOTIFY_CLIENT_ID` is dead too.

## Spotify-smooth (Goal 2)
- Service worker `public/sw.js` (hand-rolled, dependency-free, prod-only, registered in `main.tsx`): cache-first hashed assets + images (wsrv.nl) + fonts, network-first navigation with offline shell fallback. Verified registered in browser.
- Data split (`scripts/split_detail_fields.py`): detail-only fields moved to `albumsDetail.json` (keyTracks/wikipedia/reviews) + `artistsDetail.json` (bio/wikipedia), imported statically by the already-lazy `Album.tsx`/`Artist.tsx` → land in lazy chunks, NOT the initial bundle (no async loading). `albums.json` 1197K→980K, `artists.json` 308K→163K. `albumDNA` kept eager (Home hero/picker render it). New types `AlbumDetail`/`ArtistDetail`.
- Vendor chunks (`vite.config.ts`): `react-vendor` + `graph-vendor` (graph-vendor stays lazy).
- Hover/focus prefetch of the album route chunk (`src/utils/prefetch.ts` wired into `AlbumCard`).
- Result: initial JS 1,561K → 1,278K (gzip 453K → 351K, ~22% lighter). Build clean.

## Inspiration (Goals 4, 6, 8) — Paths feature
- New routes `/paths` (agenda manifesto + 6 cards) and `/path/:id` (rationale + "For the player" steal-this callout + numbered listening order). Lazy. Nav links (desktop + mobile) + Home QuickLinks entry.
- Agenda: "a guide for players, not collectors … the history you can hear and steal."
- 6 paths, 57 unique albums (all ids verified to resolve): guitar-lineage (Django→Christian→Wes→Hall→Metheny→Halvorson), broke-the-language, late-night-tone, groove-and-grease, avant-leap, first-night.
- Data `src/data/paths.json`; types `CuratedPath`/`PathsData`; spec `docs/superpowers/specs/2026-06-12-inspiration-agenda-paths.md`.

## Accuracy (Goals 3, 6, 7) — beyond Wikipedia
- 10 multi-source corrections applied (`scripts/apply_accuracy_corrections.py`; sources incl. jazzdisco.org, AllMusic, Discogs, Wax Poetics, RIAA, Ashley Kahn books): Crescent (Garrison = bass, not drums); Miles Smiles / Such Sweet Thunder / Milestones label → Columbia; Bitches Brew superlative; Song for My Father (interpolation not sample); Afrodisia (makossa not Afrobeat); Giant Steps ("first as sole leader"); My Favorite Things ("first released"); Django bio.
- 5 albumDNA corruption repairs applied (`scripts/apply_corruption_repairs.py`) — prose had described the wrong artist: King Oliver (was King Princess), Joel Ross (was Diana Ross), Mark Whitfield (was gospel's Thomas Whitfield), Nancy Wilson/Cannonball (was duplicated Somethin' Else), Baby Face Willette (was the wrong Willette album).
- Spec: `docs/superpowers/specs/2026-06-12-accuracy-spotcheck.md`. 38 high-risk claims checked; landmark records (Kind of Blue, A Love Supreme, Blue Train, etc.) verified correct.

## Production hardening (Goal 5)
- Catch-all `*` route → `NotFound.tsx` (on-brand 404). All detail routes already guard bad ids.
- Browser smoke test (Chrome DevTools, production preview): home, /paths, /path/guitar-lineage, /album/crescent (corrected DNA + keyTracks via lazy detail), /artist/django-reinhardt (corrected bio via lazy detail), bad route → 404, SW registered. No console errors (only pre-existing benign image-preload warnings).

## Verification
- `npm run typecheck` clean. `npm run build` clean. Browser smoke test passed.
- Lint: 19 pre-existing errors remain (Math.random purity in Home, prefer-const in weatherMood, setState-in-effect patterns). NONE introduced by this pass; left untouched (surgical-change discipline).

## Artifacts added
- Scripts: `split_detail_fields.py`, `apply_accuracy_corrections.py`, `apply_corruption_repairs.py`.
- Agent outputs (scripts/out): `curated_paths.json`, `accuracy_corrections.json`, `corruption_repairs.json`.
- New source: `src/pages/{Paths,Path,NotFound}.tsx`, `src/utils/prefetch.ts`, `src/data/{paths,albumsDetail,artistsDetail}.json`, `public/sw.js`.

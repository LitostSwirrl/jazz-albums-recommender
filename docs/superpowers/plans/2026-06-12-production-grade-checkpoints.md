# Smack Cats — Production-Grade Goal — Cross-Session Checkpoints

> Emergent multi-phase task (no separate PLAN.md). This file carries the plan shape.
> Append-only for resume prompts. Update the 狀態/Status block as phases complete.
> A new session reading only CLAUDE.md + this file should be able to resume.

## The Goal (verbatim intent)

Drive the site to production grade on four fronts:
1. **Security** — audit for dangerous information leaks.
2. **Spotify-smooth** — perceived speed + cache for best customer experience ("Spotify CEO behind you").
3. **Jazz authority** — historian-grade, a team of jazz professors behind you.
4. **Orpheus** — a guitarist (the GOD) seeking inspiration for guitar playing/ideation is the north-star user.
5. Production ready, handle absurd use cases.
6. **Inspiration first** priority; **historical accuracy second but with zero mistakes**.
7. Don't just rely on Wikipedia — jazz history lives in books, oral histories, obscure publications.
8. Simple and straightforward, but with a clear agenda.

## Status — ALL PHASES COMPLETE (2026-06-12)

- **Phase 1 — Security audit**: DONE. Clean (no leaks anywhere). Hardened geolocation precision. One USER action outstanding: rotate the dormant Spotify secret (see findings below).
- **Phase 2 — Spotify-smooth perf + cache**: DONE. Service worker (`public/sw.js`), data split (slim catalog + lazy detail chunks; albumDNA kept eager because Home uses it), vendor chunks, hover-prefetch. Initial JS 1,561K→1,278K (gzip 453K→351K). Verified by build + browser (SW registers).
- **Phase 3 — Inspiration + accuracy**: DONE. Paths feature (`/paths`, `/path/:id`; 6 player-first paths incl. a guitar lineage; agenda "a guide for players, not collectors"). 10 multi-source accuracy corrections + 5 albumDNA corruption repairs applied (beyond Wikipedia).
- **Phase 4 — Production hardening**: DONE. Catch-all 404 (`NotFound.tsx`), all detail routes guard bad ids. Browser smoke test passed (home / paths / path detail / corrected album+artist / 404 / SW) with no console errors.

No `/clear` handoff needed — goal complete in this session. Session log: `docs/superpowers/logs/2026-06-12-production-grade-log.md`.

## Cross-cutting contracts (shared every session)

- **Project root**: `/Users/jinsoon/Documents/Work/Music Projects/jazz_albums_recommends`
- **Stack**: React 19 + TS strict + Vite 7 + Tailwind 4 + React Router 7 (HashRouter) + @xyflow/react + dagre. Deploy: GitHub Pages via `gh-pages -d dist`, base `/jazz-albums-recommender/`.
- **Build/verify**: `npm run build` (tsc -b implied via typecheck script: `npm run typecheck`), `npm run preview`, `npm run lint`.
- **Data**: `src/data/{albums(1000),artists(275),connections(377),eras(8),historicalEvents}.json`. Albums imported STATICALLY by every page → all 1000 land in the initial JS chunk (the perf problem). Album fields: id,title,artist,artistId,year,era,genres[],keyTracks[],albumDNA(prose),coverUrl,spotifyUrl,label.
- **Secrets**: `.env`/`.env.local` gitignored, never committed, not in dist/gh-pages. `VITE_SPOTIFY_CLIENT_ID` is DEAD (no client code reads any env var). Umami website ID in index.html is public-by-design. Umami API key in `.env.local` is server-side only.
- **No emojis anywhere** (user rule). English-led project. No serifs (Space Grotesk + Inter + JetBrains Mono).
- **Analytics**: `track()` in `src/utils/analytics.ts` → Umami; sends only IDs, NO PII/location. Keep it that way.

## Phase 1 — Security findings (recorded)

CLEAN on what matters:
- No secrets in tracked files, deployed `gh-pages` branch, or `dist` bundle (git grep + dist grep verified).
- No `import.meta.env`/`process.env` in client code → nothing sensitive bundled.
- No XSS sinks (no dangerouslySetInnerHTML/eval/innerHTML).
- Analytics payloads carry only album/artist/era IDs + source — no location/weather/PII.
- Weather hook: lat/lon → Open-Meteo only, sessionStorage cached, never logged/shown.

Actions taken:
- Rounded geolocation to ~1km (2 decimals) before sharing with Open-Meteo (`src/hooks/useWeather.ts`).

Outstanding (USER action — cannot self-do, needs Spotify dashboard):
- **Rotate/delete the dormant Spotify Client Secret** in `.env` (`7109ca…`). OAuth was removed 2026-03-23; the secret is unused but live. Not leaked (gitignored), but a dormant live credential should be revoked at https://developer.spotify.com/dashboard.
- Minor: `VITE_SPOTIFY_CLIENT_ID` / `.env.example` reference a now-dead feature; left in place (documentation), flagged only.

## Phase 2 — Plan (Spotify-smooth)

Problem: initial JS chunk = 1.5MB (≈ entire catalog bundled). No service worker. 
Deliverables + verification:
- [ ] **Service worker / PWA** (vite-plugin-pwa + Workbox): precache build, runtime-cache wsrv.nl images (CacheFirst) + Google Fonts, offline fallback, auto-update. Register in main.tsx. Respect base `/jazz-albums-recommender/`. Verify: SW registers, repeat load served from cache, offline works in preview.
- [ ] **Bundle slim**: split detail-only `albumDNA` (354KB, 30% of albums.json) into a lazy file loaded only by `Album.tsx`. Verify: build, initial chunk shrinks ~350KB, detail page still shows DNA. Backup data first.
- [ ] **Vendor manualChunks**: stable long-term caching across content updates.
- [ ] **Prefetch on intent**: warm lazy route chunks on hover/viewport for instant nav.
- [ ] Image lazy/async already in AlbumCover (verify ArtistPhoto too).
- Verify: `npm run build` before/after chunk sizes; `npm run typecheck` clean; browser smoke test in preview.

## Phase 3 — Plan (inspiration + accuracy)

- [ ] **Inspiration agenda + curated paths** (background agent → `scripts/out/curated_paths.json`): build a "Paths" feature — opinionated, player-centric collections (incl. a jazz-guitar lineage for Orpheus). Express the "clear agenda" editorially. Inspiration-first.
- [ ] **Accuracy hardening** (background agent → `scripts/out/accuracy_corrections.json`): apply verified, multi-source (beyond-Wiki) corrections to the riskiest factual claims. Zero-mistake floor.
- Verify: every cited album id exists; every correction has a live source URL; build clean.

## Phase 4 — Plan (production hardening / absurd use cases)

- [ ] All UI states everywhere (loading/error/empty/success), bad routes, missing fields, broken images, huge inputs, offline, a11y basics, external-link rel=noopener, 404, SEO/sitemap sanity.
- Verify: browser smoke test of edge routes; build clean.

---

(No resume prompt committed yet — work continues in the current session. A resume prompt will be appended here at a real phase gate or before any `/clear`.)

# Template Split + Fatback Pilot — Design Spec

Date: 2026-08-17
Status: approved in conversation; awaiting written-spec review

## Goal

Turn this repo into a multi-site template — one codebase, per-site data packs and config — and pilot a second site, **Fatback**, an instrumental-leaning funk/soul guide. The jazz site (Smack Cats) must come through the split with zero behavior change.

## Non-goals

- No new features for the jazz site.
- No separate template repo; everything stays in this repo.
- Fatback pilot excludes: artist connections graph, historical events layer, Discover/recommendations section. Feature flags keep the code paths; only content is skipped.
- No collector-scale catalog. Pilot is ~200 albums, not 1000.

## 1. Template mechanism

- Each site lives in `src/sites/<name>/` (`jazz`, `funk`), containing:
  - `site.config.ts` — site name, tagline, site URL, SEO description strings, fallback color palette (currently `src/utils/colors.ts`), feature flags, analytics website id (empty string = omit the script).
  - `data/` — the full JSON pack. Jazz's existing `src/data/*.json` moves here unchanged; schemas are untouched.
  - `public/` — per-site static assets (see §2).
- Vite alias `@site` → `src/sites/${VITE_SITE}`. The 19 files importing from `src/data/` switch to `@site/data/`. Config consumers import from `@site/config`.
- Feature flags: `connections`, `historicalEvents`, `discover`. Flag off = route not registered, nav item not rendered, data file is an empty stub (`[]`) so the lazy chunk stays trivial. Jazz: all on. Fatback: all off.
- `index.html` values (title, meta description, og tags, Umami id, loading text) come from Vite HTML env replacement (`%VITE_SITE_NAME%` etc.), fed from the site config at build time.
- Scripts: `dev:jazz` / `dev:funk`, `build:jazz` / `build:funk`, `deploy:jazz` / `deploy:funk`. Bare `dev`/`build`/`deploy` keep working as aliases for jazz.
- No runtime site detection. Each build bundles exactly one site's data.

## 2. Static assets and PWA

- Per-site `src/sites/<name>/public/`: manifest, favicon, icons, sitemap, robots.txt, `covers/`. Shared `public-shared/`: `sw.js`, `404.html`. Build merges shared + per-site into `dist`.
- Rationale: the 807 jazz cover files must not ship in the Fatback deploy; each PWA needs its own name and icons.
- `sw.js` stays one shared file: caches are per-origin, so the two deployed sites cannot collide. Cache version bump discipline unchanged.

## 3. Hosting

- Second hosting site inside the existing `smack-cats-jazz` Firebase project: `firebase hosting:sites:create fatback` (fallback slug `fatback-funk` if taken).
- `firebase.json` converts to hosting targets (array form), one entry per site, same headers/rewrites for both. `.firebaserc` maps targets. Each deploy script pushes one target.

## 4. Fatback identity and content shape

- Name: **Fatback**. Working URL: the slug created in §3.
- Curation stance: instrumental-led, roughly 70/30. Instrumental core (Meters, Booker T & the MG's, JBs, Jimmy Smith, Herbie Hancock/Headhunters, Roy Ayers, Idris Muhammad, Daptone/Big Crown roster, Vulfpeck lineage, Khruangbin, BadBadNotGood) plus the vocal canon the lineage demands (James Brown, Sly & the Family Stone, Parliament-Funkadelic).
- Eras (6):
  1. Soul-jazz & proto-funk roots (1958–1967)
  2. Classic funk (1967–1975)
  3. Jazz-funk & fusion (1970–1979)
  4. P-Funk, disco & boogie (1975–1984)
  5. Rare groove & revival (1985–2005)
  6. The new pocket (2005–now)
- Catalog: ~200 albums, ~60–80 artists.
- Paths (3–4): James Brown rhythm-section tree; organ grease (Jimmy Smith → Booker T → Medeski → Cory Henry); the sampled shelf (break-beat sources); party-starter set.
- Look: palette from config — warm 70s heat (browns, burnt orange, mustard) vs jazz's warm-gray monochrome. Era colors live in `eras.json` as today. Typography: pilot launches on Space Grotesk + Inter; its own design pass (frontend-design skill) later.

## 5. Content pipeline and data integrity

- Zero-hallucination standard from day one: albums curated against Wikipedia/Discogs/AllMusic; albumDNA prose per album; entity-verification pass before launch (no invented tracks, labels, years).
- Covers via existing `scripts/fetch_covers.py` + manifest machinery, self-hosted under the funk site's `public/covers/`.
- New schema-validation script checks any site pack for required fields; a broken pack fails the build, not the page.

## 6. Phases and gates

1. **Template extraction.** Config layer, `@site` alias, flags, asset split, HTML env replacement, hosting targets. Gate: typecheck + build pass; jazz site behaves identically on a full route click-through; jazz deploy verified live. No funk content.
2. **Fatback scaffold.** Site config, palette, hosting site created, ~10-album placeholder pack, deployed end to end. Gate: Fatback live at its slug with placeholder content; all flagged-off routes absent from nav and 404-safe.
3. **Content production.** Eras, ~200 albums with DNA prose, ~60–80 artists, verification pass, covers. Multi-session. Gate: validation script passes; entity spot-checks clean; cover coverage reported honestly.
4. **Paths + launch polish.** 3–4 paths, sitemap, empty-state checks, final click-through of both sites, deploy.

Strict phase gates: no phase starts while the previous one has open sub-tasks.

## Verification summary

- `tsc` strict + `vite build` for both sites on every phase.
- Jazz regression: full route click-through after Phase 1, compared against production behavior.
- Data: schema validation in build; entity verification per §5.
- Deploys verified by loading the live URL, not by deploy exit code.

## Open items

- Umami website id for Fatback: create in dashboard when wanted; pilot ships without analytics until then.
- Final Fatback typography: dedicated design pass after pilot content exists.
- Slug availability (`fatback` vs `fatback-funk`): resolved at Phase 2 creation time.

# Template Split + Fatback Pilot — Progress

Spec: 2026-08-17-template-split-fatback-pilot-design.md

## End goal

One codebase serving per-site packs; Fatback (instrumental-leaning funk/soul, ~200 albums) live as a sibling site; jazz site unchanged.

## Decisions

- One repo with `src/sites/<name>/` packs, `@site` Vite alias, `VITE_SITE` build switch. Rejected: separate template repo (three repos to maintain).
- Pilot features: Paths + Eras/timeline only. Connections graph, historical events, Discover flagged off (content cost, not code cost).
- Curation: instrumental-led 70/30 — strict-instrumental rejected because the history reads wrong without James Brown/Sly.
- Name: Fatback. Hosting: second site in the smack-cats-jazz Firebase project via targets.
- sw.js stays shared: SW caches are per-origin, no cross-site collision.
- index.html per-site values via Vite HTML env replacement (title, meta, Umami id, loading text).

## Status

- [x] Brainstorm + scope decisions (2026-08-17)
- [x] Spec written
- [ ] User reviews spec
- [ ] Implementation plan (writing-plans)
- [x] Phase 1: template extraction — DONE + deployed live (2026-08-17, commits 7770dff..5e2d25f on feat/template-split-fatback). Firebase note: ck991004@gmail.com added as project Owner (was GCAA-account only); org-parent check pending (user follow-up).
- [x] Phase 2: Fatback scaffold — DONE + live at https://fatback-funk.web.app (2026-08-17; slug `fatback` was reserved, fallback per spec). 10 verified placeholder albums, 6 eras, PWA assets, flags off, no analytics. Awaiting final whole-branch review + merge.
- [ ] Phase 3: content production (gate: validation + entity checks pass)
- [ ] Phase 4: paths + launch polish

## Open blockers

None. Open items tracked in spec §Open items (Umami id, typography pass, slug availability).

## Phase 3 preconditions and carry-notes (from execution ledger, 2026-08-17)

- Step 0 of Phase 3: fix the data-pipeline scripts. `scripts/fetch_covers.py` is internally inconsistent (COVERS_DIR updated, ALBUMS_PATH/MANIFEST_PATH still point at deleted src/data/ — crashes on launch); ~15 other scripts still hard-code src/data/. Add a site argument rather than re-hardcoding.
- Funk era year ranges (classic-funk 1965-1974, rare-groove 1985-2009, new-pocket 2010-) deliberately deviate from spec §4 and are RATIFIED — do not re-derive from the spec; album placements depend on them.
- Funk artist birth/death years use band formation/disband semantics and were not entity-verified (albums were) — verify in the artist pass. Parliament 1968-2018 will render oddly as a lifespan.
- Funk Home stays visually bare until covers land: HeroFeature/getDailyPicks/picker all gate on coverUrl.
- Copy contract: `albumsDescriptionSuffix`/`artistsDescriptionSuffix` follow an interpolated "{count} " prefix; eraTransitions renders a 4-column grid — keep exactly 4 entries.
- new-pocket era description over-generalizes from Vulfpeck's story — tighten when real catalog lands.
- Phase 4 owns: empty-state fixes in shared code (/paths empty grid, empty Biography heading), real funk sitemap routes, per-site outDir consideration (bare `firebase deploy` would ship one dist to both targets), Fatback design pass (theme-color, loading colors #1a1917/#9a9590 still jazz's, typography).
- Template-quality debt (non-blocking): EraId union is jazz-typed (funk data never typechecked — validator is the funk gate); ERA_DISPLAY_NAMES + genre-era heuristic provably inert on funk data.

## Notes

- 19 src files import from `src/data/` — the alias migration surface.
- Umami id currently hard-coded in index.html (public, fine per reference_umami_credentials memory).
- Jazz covers: 807 files in public/covers must not ship in Fatback deploy — the reason for per-site public dirs.

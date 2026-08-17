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

## Notes

- 19 src files import from `src/data/` — the alias migration surface.
- Umami id currently hard-coded in index.html (public, fine per reference_umami_credentials memory).
- Jazz covers: 807 files in public/covers must not ship in Fatback deploy — the reason for per-site public dirs.

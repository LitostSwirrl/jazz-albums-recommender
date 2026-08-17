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
- [ ] Phase 1: template extraction (gate: jazz regression-free, deployed)
- [ ] Phase 2: Fatback scaffold (gate: live at slug with placeholder pack)
- [ ] Phase 3: content production (gate: validation + entity checks pass)
- [ ] Phase 4: paths + launch polish

## Open blockers

None. Open items tracked in spec §Open items (Umami id, typography pass, slug availability).

## Notes

- 19 src files import from `src/data/` — the alias migration surface.
- Umami id currently hard-coded in index.html (public, fine per reference_umami_credentials memory).
- Jazz covers: 807 files in public/covers must not ship in Fatback deploy — the reason for per-site public dirs.

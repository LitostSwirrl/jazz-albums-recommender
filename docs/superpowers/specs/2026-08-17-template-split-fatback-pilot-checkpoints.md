# Template Split + Fatback Pilot -- Cross-Session Checkpoints

> Multi-session resume file. At each phase gate the agent appends a self-contained resume prompt here and pbcopies it silently. After /clear, paste the clipboard into the new session to continue.
>
> Rules: append-only -- never edit committed prompts. Every prompt must be self-contained (a new session sees only CLAUDE.md + the pasted prompt).

## 狀態

- **Spec + scope decisions**: done (2026-08-17), commit cb9a9ff
- **User spec review**: done (2026-08-17, approved)
- **Implementation plan (writing-plans)**: done (2026-08-17), commit cb80bd7
- **Phase 1 -- Template extraction**: done (2026-08-17), commits 7770dff..5e2d25f, jazz live-verified on template architecture
- **Phase 2 -- Fatback scaffold**: done (2026-08-17), commits a300365..caae22a, live at https://fatback-funk.web.app (slug `fatback` reserved → fallback). Final whole-branch review clean; merged to main at f0a53c0, branch deleted
- **Phase 3 -- Content production**: pending (multi-session; ~200 albums, 60-80 artists, covers, verification)
- **Phase 4 -- Paths + launch polish**: pending (incl. deferred empty-state fixes in shared code)

## Cross-cutting contracts (shared by every session)

- **Project root**: `/Users/jinsoon/Work/Projects/personal/jazz_albums_recommends`
- **Read order (new session)**: CLAUDE.md -> `docs/superpowers/specs/2026-08-17-template-split-fatback-pilot-design.md` (the spec) -> `...-progress.md` (decisions + status) -> this file's 狀態 block
- **Build switch**: `VITE_SITE=jazz|funk`; scripts `dev:jazz`/`dev:funk`, `build:*`, `deploy:*`; bare `dev`/`build`/`deploy` alias jazz
- **Jazz is regression-frozen**: Phase 1 must leave the jazz site behaviorally identical; any jazz-visible change is a bug
- **Content standard**: zero-hallucination (Wikipedia/Discogs/AllMusic-verifiable; no invented tracks/labels/years); covers self-hosted via `scripts/fetch_covers.py` + manifest
- **Verification**: `tsc` strict + `vite build` both sites at every gate; deploys verified by loading the live URL, not exit code
- **Code style**: no comments, surgical diffs, `interface` over `type`, no `any`
- **At every phase gate**: update progress.md status + append What/Why/Next entry; update 狀態 here; generate resume prompt + pbcopy + recommend /clear only when the window is worth shedding (~30%+ or session ending)

---

## Phase 3 Resume Prompt

(2026-08-17 產生，Phase 2 完成、merge to main 後)

```
繼續 Phase 3: Fatback content production — build the real funk/soul catalog (~200 albums, 60-80 artists) on the now-live scaffold.

Working directory: /Users/jinsoon/Work/Projects/personal/jazz_albums_recommends (main branch; Phases 1-2 merged at f0a53c0, both sites live: smack-cats-jazz.web.app, fatback-funk.web.app)

狀態:
- Template split DONE: site packs at src/sites/{jazz,funk}/, VITE_SITE + @site alias, validate_site_pack.mjs gates builds. CLAUDE.md documents it.
- Fatback scaffold live with 10 verified placeholder albums, 6 eras, PWA assets; features (connections/historicalEvents/discover) OFF.
- Spec: docs/superpowers/specs/2026-08-17-template-split-fatback-pilot-design.md (§4 content shape, §5 pipeline standard)
- Progress + Phase 3 preconditions: docs/superpowers/specs/2026-08-17-template-split-fatback-pilot-progress.md — READ THE "Phase 3 preconditions and carry-notes" SECTION FIRST; it lists ratified decisions and known breakage.

開始前 (read order): CLAUDE.md → spec §4-§5 → progress.md Phase 3 section → this checkpoints file 狀態.

目標:
1. Step 0 (hard precondition): fix scripts/fetch_covers.py — COVERS_DIR was updated but ALBUMS_PATH/MANIFEST_PATH still point at deleted src/data/; add a --site argument instead of re-hardcoding. Sweep the other ~15 scripts/ files that hard-code src/data/ as needed (fix what Phase 3 actually runs, note the rest).
2. Expand funk albums.json to ~200 albums, instrumental-led 70/30, across the 6 eras (era year ranges are RATIFIED as committed — do not re-derive from the spec). Every album: verified facts only (Wikipedia/Discogs/AllMusic), albumDNA 2-3 factual sentences. Batch-parallel Opus workers for per-album research; verification pass before commit (zero-hallucination, entity checks).
3. artists.json to ~60-80 entries; VERIFY the existing 10 scaffold artists' birth/death years (band formation/disband semantics were not entity-verified — e.g. Parliament 1968-2018 renders as a lifespan; decide encoding and apply consistently).
4. Covers: run the fixed fetch_covers.py for the funk pack → src/sites/funk/public/covers/ + coverManifest.json. Home stays bare until coverUrl is populated — this is the fix.
5. Tighten the new-pocket era description (currently over-generalizes from Vulfpeck's story — scope claims to catalog bands).
6. Gate: node scripts/validate_site_pack.mjs funk exit 0; npm run build:funk green; entity spot-checks clean; cover coverage reported honestly; deploy:funk + live verification.

慣例: zero-hallucination absolute (no invented tracks/labels/years; report gaps honestly); copy contract — albumsDescriptionSuffix/artistsDescriptionSuffix follow an interpolated "{count} " prefix, eraTransitions stays exactly 4 entries; no code comments; surgical diffs; jazz site untouched; Conventional Commits; parallel agents = Opus 5 workers, judgment in main loop; keep a progress log; strict gate before Phase 4 (paths + empty-state fixes + design pass are Phase 4, not this phase).

完成後必做: update progress.md (What/Why/Next + status checkboxes) and the checkpoints 狀態; commit docs; generate the Phase 4 resume prompt per the checkpointing skill (pbcopy + append to docs/superpowers/specs/2026-08-17-template-split-fatback-pilot-checkpoints.md) when the window is worth shedding or the session ends.
```

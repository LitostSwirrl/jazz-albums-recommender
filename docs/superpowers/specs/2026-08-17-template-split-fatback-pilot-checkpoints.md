# Template Split + Fatback Pilot -- Cross-Session Checkpoints

> Multi-session resume file. At each phase gate the agent appends a self-contained resume prompt here and pbcopies it silently. After /clear, paste the clipboard into the new session to continue.
>
> Rules: append-only -- never edit committed prompts. Every prompt must be self-contained (a new session sees only CLAUDE.md + the pasted prompt).

## 狀態

- **Spec + scope decisions**: done (2026-08-17), commit cb9a9ff
- **User spec review**: done (2026-08-17, approved)
- **Implementation plan (writing-plans)**: done (2026-08-17), commit cb80bd7
- **Phase 1 -- Template extraction**: done (2026-08-17), commits 7770dff..5e2d25f, jazz live-verified on template architecture
- **Phase 2 -- Fatback scaffold**: done (2026-08-17), commits a300365..caae22a, live at https://fatback-funk.web.app (slug `fatback` reserved → fallback). Final whole-branch review + merge to main in progress
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

(Resume prompts appended below as phases complete.)

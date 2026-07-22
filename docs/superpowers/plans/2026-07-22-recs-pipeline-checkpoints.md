# Recs Pipeline (Plan 1) -- Cross-Session Checkpoints

> Multi-session resume file. At each phase gate the agent logs the phase here; when a window is worth shedding, it appends the next resume prompt, pbcopies it silently, and tells Joseph it is safe to `/clear`. Paste the clipboard into the fresh session to continue.
>
> Rules: append-only -- never modify committed prompts. Every prompt must be self-contained (a new session sees only CLAUDE.md + the pasted prompt).

## Status

- **Phase A -- Foundation + taste (plan Tasks 1-3)**: pending
- **Phase B -- Backbone fetchers: Discogs + Last.fm (Tasks 4-5)**: pending
- **Phase C -- Pitchfork + Reddit (Tasks 6-7)**: pending
- **Phase D -- RYM assisted import (Task 8, Joseph present)**: pending
- **Phase E -- Scoring + shelves (Tasks 9-10)**: pending
- **Phase F -- End-to-end + taste gate (Task 11)**: pending
- **Plan 2 -- UI (/discover, Home row, badges)**: written only after Phase F emits real data

## Cross-cutting contracts (shared by every session)

- **Project root**: `/Users/jinsoon/Work/Projects/personal/jazz_albums_recommends`
- **Read order (new session)**: CLAUDE.md -> spec `docs/superpowers/specs/2026-07-22-taste-recommendation-engine-design.md` -> plan `docs/superpowers/plans/2026-07-22-recs-pipeline.md` (only the tasks for this phase) -> this file's Status + Log
- **Run from repo root**: `python3 -m scripts.recs.<module>`; tests: `python3 -m pytest scripts/recs/tests -q`
- **Commits**: Conventional Commits on `main`, `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
- **Secrets**: tokens in `.env` (gitignored); never print values; `scripts/recs/cache/` + `.spotify_token.json` stay untracked
- **User setup gate**: table at top of the plan -- confirm the phase's gate items exist in `.env` before starting; if missing, stop and ask, don't stub
- **Zero-hallucination**: reasons must trace to cache records; integrity check failure = build failure, never soften it
- **Log location**: `## Log` section at the bottom of this file (this project has no PROJECT_LOG.md); every phase gate appends What / Why / Next
- **At every phase gate**: update Status here + append Log entry; generate resume prompt + pbcopy + recommend `/clear` only when the window is worth shedding (~30%+ or an override); mid-flow scope decisions commit the resume prompt immediately regardless of context level

---

## Log

(phase entries appended here: What / Why / Next)

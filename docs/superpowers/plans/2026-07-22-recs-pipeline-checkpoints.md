# Recs Pipeline (Plan 1) -- Cross-Session Checkpoints

> Multi-session resume file. At each phase gate the agent logs the phase here; when a window is worth shedding, it appends the next resume prompt, pbcopies it silently, and tells Joseph it is safe to `/clear`. Paste the clipboard into the fresh session to continue.
>
> Rules: append-only -- never modify committed prompts. Every prompt must be self-contained (a new session sees only CLAUDE.md + the pasted prompt).

## Status

- **Phase A -- Foundation + taste (plan Tasks 1-3)**: implemented + reviewed (2026-07-23, commits 2775f8b..1f2d645, 44 tests green). LIVE VERIFY PENDING: needs Joseph — Spotify dashboard redirect URI `http://127.0.0.1:8888/callback`, then `python3 -m scripts.recs.sync_spotify` (one browser consent; 2nd run must not open browser), then `python3 -m scripts.recs.build_taste_profile` (review top-15 + unmatched report)
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
- **Commits**: Conventional Commits on branch `feat/recs-pipeline` (merge to main at Phase F via finishing-a-development-branch), `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
- **Secrets**: tokens in `.env` (gitignored); never print values; `scripts/recs/cache/` + `.spotify_token.json` stay untracked
- **User setup gate**: table at top of the plan -- confirm the phase's gate items exist in `.env` before starting; if missing, stop and ask, don't stub
- **Zero-hallucination**: reasons must trace to cache records; integrity check failure = build failure, never soften it
- **Log location**: `## Log` section at the bottom of this file (this project has no PROJECT_LOG.md); every phase gate appends What / Why / Next
- **At every phase gate**: update Status here + append Log entry; generate resume prompt + pbcopy + recommend `/clear` only when the window is worth shedding (~30%+ or an override); mid-flow scope decisions commit the resume prompt immediately regardless of context level

---

## Log

(phase entries appended here: What / Why / Next)

### 2026-07-23 — Phase A (Tasks 1-3)

- **What**: Built via subagent-driven dev on `feat/recs-pipeline` (2775f8b..1f2d645): `scripts/recs/common.py` (env/normalization/cached HTTP), `sync_spotify.py` (PKCE OAuth + full library pull, live run deferred), `build_taste_profile.py` (affinity scores, 3-tier ownership matching, labels/styles, unmatched report). 44 tests green. Every task passed implement -> review -> fix -> re-review.
- **Why (decisions a future session can't infer from code)**: (1) params folded into HTTP cache key after reviewer proved silent collision by execution. (2) OAuth callback path-gated + bounded loop — stray localhost GETs were stealing the one-shot slot. (3) 28/1000 catalog records lack the `spotifyUrl` KEY (not just empty) — `.get()` everywhere. (4) lastfm contract RESOLVED: single `cache/lastfm.json`, `artist_tags` maps `norm(artist)` -> [tags] — Task 5 must emit exactly this. (5) `top_tracks` pulled but deliberately unscored (plan defines no weight) — tuning lever for the Task 11 taste gate. (6) Review minors deferred to final whole-branch review are itemized in `.superpowers/sdd/progress.md`.
- **Next**: Joseph setup (redirect URI, DISCOGS_TOKEN, LASTFM_API_KEY, REDDIT creds) -> live-verify Phase A -> Phase B (Tasks 4-5).

---

## Phase B Resume Prompt

(2026-07-23 generated, after Phase A implementation complete; also in clipboard)

```
Continue Phase B of the recs pipeline: live-verify Phase A, then implement Tasks 4-5 (Discogs + Last.fm fetchers).

Working directory: /Users/jinsoon/Work/Projects/personal/jazz_albums_recommends (branch feat/recs-pipeline)

State:
- Phase A (plan Tasks 1-3) implemented, reviewed, committed: scripts/recs/{common.py, sync_spotify.py, build_taste_profile.py} + tests, 44 passing. Commits 2775f8b..1f2d645.
- LIVE VERIFY STILL PENDING (needs Joseph): (1) `python3 -m scripts.recs.sync_spotify` — opens browser once for Spotify consent (requires redirect URI http://127.0.0.1:8888/callback added in the Spotify developer dashboard first); a second run must NOT open the browser (refresh-token path). (2) `python3 -m scripts.recs.build_taste_profile` — then review the top-15 artists table + unmatched-albums report with Joseph.
- Execution mode: superpowers:subagent-driven-development (fresh implementer subagent per task + task-reviewer subagent + fix loop). Ledger at .superpowers/sdd/progress.md — read it; tasks marked complete are DONE, never re-dispatch. Use the skill's scripts/task-brief and scripts/review-package helpers; record BASE commit before each dispatch.

Before starting:
1. Read CLAUDE.md, then docs/superpowers/plans/2026-07-22-recs-pipeline.md (Global Constraints + USER SETUP GATE table + Tasks 4-5 only), then .superpowers/sdd/progress.md, then docs/superpowers/plans/2026-07-22-recs-pipeline-checkpoints.md (Status + Log).
2. Gate check: DISCOGS_TOKEN and LASTFM_API_KEY must exist in .env (check key names only — never print values). If either is missing, stop and ask Joseph; do not stub.
3. Run the two live verifies above with Joseph present FIRST — they unblock real-data runs downstream.

Goals (Phase B):
- Task 4: scripts/recs/fetch_discogs.py per plan — artist + label sweeps, community rating/haves/wants, credits; disk-cached via common.cached_get_json; second run prints api_calls: 0; spot-check 3 known albums' ratings against discogs.com.
- Task 5: scripts/recs/fetch_lastfm.py per plan — similar-artist edges, tag top albums, artist tags. Resolved contract from Task 3 review: output is a SINGLE file cache/lastfm.json whose artist_tags key maps norm(artist) -> [tags]; build_taste_profile.py already consumes exactly that shape. After Task 5, rerun build_taste_profile — it must print `styles source: catalog+lastfm`.

Conventions: all cross-cutting contracts in docs/superpowers/plans/2026-07-22-recs-pipeline-checkpoints.md apply (branch feat/recs-pipeline, Conventional Commits + Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>, secrets never printed, caches untracked, completeness over silent drops).

Output: committed fetchers + tests green (`python3 -m pytest scripts/recs/tests -q`) + populated scripts/recs/cache/ (untracked).

Post-completion checklist (every phase gate): update Status + append a What/Why/Next entry to the Log in docs/superpowers/plans/2026-07-22-recs-pipeline-checkpoints.md; update .superpowers/sdd/progress.md; generate the next phase's resume prompt, pbcopy it silently, append it to the checkpoints file, and tell Joseph it is safe to /clear ONLY when the window is worth shedding (~30%+) or Joseph is stopping for the session; if a mid-flow scope decision arrives, commit the resume prompt immediately before any execution regardless of context level.
```

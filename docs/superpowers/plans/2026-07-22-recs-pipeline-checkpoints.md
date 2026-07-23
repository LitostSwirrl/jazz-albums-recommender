# Recs Pipeline (Plan 1) -- Cross-Session Checkpoints

> Multi-session resume file. At each phase gate the agent logs the phase here; when a window is worth shedding, it appends the next resume prompt, pbcopies it silently, and tells Joseph it is safe to `/clear`. Paste the clipboard into the fresh session to continue.
>
> Rules: append-only -- never modify committed prompts. Every prompt must be self-contained (a new session sees only CLAUDE.md + the pasted prompt).

## Status

- **Phase A -- Foundation + taste (plan Tasks 1-3)**: COMPLETE incl. live verify (2026-07-23). Sync: 1531 saved albums / 572 tracks / 50x3 top / 488 followed; silent refresh confirmed. Profile: 137 catalog matches, 1394 unmatched (expected — mixed library), top-15 sanity-checked by Joseph (guitar-heavy, cool-jazz lean, reads true). Known artifacts for Phase B: "Various Artists" #7 affinity + "Various"/"Unknown" labels need stop-list before Task 4's sweep; singles/EPs inflate saved-album counts (accepted).
- **Phase B -- Backbone fetchers: Discogs + Last.fm (Tasks 4-5)**: COMPLETE (2026-07-23). Pre-task stop-list (VA + Various/Unknown) committed. Discogs: 1381 releases (37/40 artists + 18 labels swept), rerun api_calls: 0, 3/3 spot-check exact. Last.fm: similar 29 / tag_albums 12 / artist_tags 893, rerun api_calls: 0; taste profile now prints `styles source: catalog+lastfm` (top-10 all jazz). 88 tests green. Commits 2be4278..98e0ade. Taste-gate questions parked in ledger (lastfm artist_tags scope; non-jazz artists in Discogs pool).
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

### 2026-07-23 — Phase A live verify + scope decisions (same day, later session)

- **What**: Live sync + taste profile ran with Joseph present; both verified (see Status). DISCOGS_TOKEN + LASTFM_API_KEY added to .env. Two scope decisions taken.
- **Why**: (1) Reddit closed self-service API signup -> Task 7 AMENDED to RSS transport (research verified 2026-07-23: libreddit dead since 2023-07; Redlib functions via Android-app OAuth spoofing — rejected on principle, we do not build on credential spoofing; reddit.com RSS endpoints answer HTTP 200 unauthenticated). Amendment note lives inside the plan's Task 7 section; hard rule added: if RSS 403s, stop and surface, never escalate to spoofing. (2) Taste profile artifacts found in live data -> pre-Task-4 stop-list work item (VA + Various/Unknown labels) recorded in Phase B resume prompt v2.
- **Next**: Phase B per resume prompt v2 (below): stop-list tweak -> Task 4 Discogs -> Task 5 Last.fm. Phase C after: Task 6 Pitchfork + Task 7 RSS. Phase D (RYM) whenever Joseph is at his logged-in Chrome.

### Correction note on "Phase B Resume Prompt" below

Superseded by **Phase B Resume Prompt v2** (appended after it). v1 was written before the live verify happened and before the Reddit amendment; do not use it.

### 2026-07-23 — Phase B (stop-list + Tasks 4-5)

- **What**: Stop-list commit `2be4278` (VA out of artist affinity, Various/Unknown out of labels). Task 4 `fetch_discogs.py` (`aa5637f`+fix `cb2b05e`): artist sweep 37/40 (1 empty-norm CJK + 2 no-exact-match, all counted) + 18 labels, 1381 releases with rating/haves/wants/credits, steady rerun `api_calls: 0`, controller spot-check 3/3 exact vs fresh API. Task 5 `fetch_lastfm.py` (`e532bce`+fix `98e0ade`): similar 29 seeds / 12 tag charts / 893 artist_tags, rerun `api_calls: 0`; `build_taste_profile` now prints `styles source: catalog+lastfm`, top-10 styles all jazz. 88 tests green. Both tasks passed implement -> review -> fix -> approved.
- **Why (decisions a future session can't infer from code)**: (1) Discogs "Riverside" exact-norm matched the Polish band's homonym entity via suffix-cleanup; fixed with a ONE-entry alias `{"Riverside": "Riverside Records"}` (verified Discogs label 34094) — deliberately no general homonym heuristic, contamination was isolated. (2) Emitted Discogs `artist` = release-detail `artists[0]` primary credit, NOT the swept artist (549847 Journey In Satchidananda is Alice Coltrane's) — norm_key is the cross-source join key for Task 9 merge + owned matching; post-detail owned re-check added. (3) `common.http_stats` (api_calls/cache_hits) added to `cached_get_json` — every future fetcher prints both. (4) Last.fm sweeps catch `requests.RequestException`, not just HTTPError: the api_key rides in query params and an uncaught ConnectionError/Timeout message embeds the full URL = key leak (review Important, fixed). Discogs keeps HTTPError-only (token in headers, no leak; deferred Minor). (5) "Second run api_calls: 0" is a STEADY-STATE criterion — a rerun may legitimately retry run-1's transient never-cached failures once. (6) lastfm `artist_tags` covers only artists appearing in similar/tag RESULTS (plan-literal) — 12 non-jazz top-30 seeds excluded, which accidentally shields the jazz style profile; parked as a Task 11 taste-gate question, never "fix" silently. (7) Operational: a subagent's background process dies when its turn pauses — long fetches run controller-side background, or foreground-chunked (420 s timeout + rerun; cache makes resumes free).
- **Next**: Phase C (Task 6 Pitchfork + Task 7 Reddit-RSS per amendment) via resume prompt below. Phase D (RYM, Task 8) whenever Joseph is at his logged-in Chrome. Deferred Minors + taste-gate questions itemized in `.superpowers/sdd/progress.md`.

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

## Phase B Resume Prompt v2

(2026-07-23 generated after live verify + Reddit amendment; supersedes v1; also in clipboard)

```
Continue Phase B of the recs pipeline: taste-profile stop-list tweak, then Tasks 4-5 (Discogs + Last.fm fetchers).

Working directory: /Users/jinsoon/Work/Projects/personal/jazz_albums_recommends (branch feat/recs-pipeline)

State:
- Phase A FULLY VERIFIED 2026-07-23: live Spotify sync done (saved_albums 1531 / saved_tracks 572 / top 50x3 / followed 488; second run silent = refresh path confirmed); taste profile built (137 catalog matches, 1394 unmatched = expected breadth of a mixed library, styles source: catalog). Top-15 sanity-checked with Joseph: guitar-heavy, cool-jazz lean, reads true.
- .env now holds DISCOGS_TOKEN + LASTFM_API_KEY (gate for Tasks 4-5 satisfied; never print values). REDDIT creds are NOT needed: plan Task 7 was AMENDED 2026-07-23 to an RSS-based fetch after Reddit closed self-service API signup (libreddit is dead since 2023; Redlib works via Android-app OAuth spoofing = rejected on principle; reddit.com/r/jazz/top.rss + per-thread .rss + search .rss verified live HTTP 200 on 2026-07-23). Details in the checkpoints Log. Task 7 is Phase C work — do NOT build it now.
- Execution mode: superpowers:subagent-driven-development (fresh implementer subagent per task + task-reviewer subagent + fix loop). Ledger at .superpowers/sdd/progress.md — tasks marked complete are DONE, never re-dispatch. Use the skill's scripts/task-brief and scripts/review-package helpers; record BASE commit before each dispatch.

Before starting:
1. Read CLAUDE.md, then docs/superpowers/plans/2026-07-22-recs-pipeline.md (Global Constraints + Tasks 4-5), then .superpowers/sdd/progress.md, then docs/superpowers/plans/2026-07-22-recs-pipeline-checkpoints.md (Status + Log).
2. First work item (pre-Task-4, small, direct or one subagent): stop-list in scripts/recs/build_taste_profile.py — exclude norm(artist) == "various artists" from artist affinity, and labels "Various"/"Unknown" from label affinity. They are compilation artifacts (VA ranked #7 with 16 "albums"; labels Various:8, Unknown:6) and Task 4's Discogs artist sweep consumes top-40 affinity artists — it must not waste its call budget on them. Constant + filter + test; rerun python3 -m scripts.recs.build_taste_profile; commit fix(recs).
3. Known accepted quirk, no action: Spotify saved "albums" include singles/EPs, inflating some artist counts.

Goals (Phase B):
- Task 4: scripts/recs/fetch_discogs.py per plan — artist sweep (top 40 affinity artists, up to 12 main masters each) + label sweep (affinity count >= 3 plus the plan's fixed scene-label list), community rating/haves/wants, personnel credits; all HTTP through common.cached_get_json (min_interval=1.1, Discogs token header, UA SmackCatsRecs/1.0); release detail only for candidates not already owned; second run must print api_calls: 0; spot-check 3 known albums' ratings against discogs.com pages.
- Task 5: scripts/recs/fetch_lastfm.py per plan — artist.getsimilar for top 30 affinity artists (limit 30), tag.gettopalbums (limit 100) for the plan's 12 tags, artist.gettoptags for artists in results. Output contract (RESOLVED in Task 3 review): single file cache/lastfm.json with keys similar, tag_albums, artist_tags where artist_tags maps norm(artist) -> [tags]; build_taste_profile.py already consumes exactly that shape. After Task 5: rerun build_taste_profile — must print styles source: catalog+lastfm.

Conventions: all cross-cutting contracts in docs/superpowers/plans/2026-07-22-recs-pipeline-checkpoints.md apply (branch feat/recs-pipeline, Conventional Commits + Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>, secrets never printed, caches untracked, completeness over silent drops).

Output: committed fetchers + tests green (python3 -m pytest scripts/recs/tests -q) + populated scripts/recs/cache/. Phase C next (Task 6 Pitchfork scrape + Task 7 Reddit-RSS per amended design).

Post-completion checklist (every phase gate): update Status + append What/Why/Next to the Log in the checkpoints file; update .superpowers/sdd/progress.md; generate next resume prompt, pbcopy silently, append to checkpoints file, and tell Joseph safe to /clear ONLY when the window is worth shedding (~30%+) or he is stopping; a mid-flow scope decision commits its resume prompt immediately regardless of context level.
```

## Phase C Resume Prompt

(2026-07-23 generated after Phase B completion; also in clipboard)

```
Continue Phase C of the recs pipeline: Tasks 6-7 (Pitchfork fetcher + Reddit-RSS fetcher).

Working directory: /Users/jinsoon/Work/Projects/personal/jazz_albums_recommends (branch feat/recs-pipeline)

State:
- Phases A+B COMPLETE and live-verified (2026-07-23), commits through 98e0ade. scripts/recs/ has: common.py (norm/norm_key/load_env/cached_get_json with http_stats api_calls+cache_hits counters), sync_spotify.py, build_taste_profile.py (VA + Various/Unknown stop-listed), fetch_discogs.py, fetch_lastfm.py. Tests: 88 passing (python3 -m pytest scripts/recs/tests -q).
- Caches populated (all untracked): spotify_library.json (1531/572/50x3/488), taste_profile.json (styles source: catalog+lastfm), discogs.json (1381 releases, steady rerun api_calls: 0), lastfm.json (similar 29 / tag_albums 12 / artist_tags 893, rerun api_calls: 0). HTTP buckets cache/http/{discogs,lastfm}/ warm.
- Execution mode: superpowers:subagent-driven-development (fresh implementer subagent per task + task-reviewer subagent + fix loop). Ledger at .superpowers/sdd/progress.md — tasks marked complete are DONE, never re-dispatch. Use the skill's scripts/task-brief and scripts/review-package helpers; record BASE commit before each dispatch. Deferred Minor findings live in the ledger — do NOT fix mid-phase; they go to the final whole-branch review.

Before starting:
1. Read CLAUDE.md, then docs/superpowers/plans/2026-07-22-recs-pipeline.md (Global Constraints + Tasks 6-7 INCLUDING the Task 7 amendment note), then .superpowers/sdd/progress.md, then docs/superpowers/plans/2026-07-22-recs-pipeline-checkpoints.md (Status + Log).
2. No .env gate for Phase C: Pitchfork needs no key; Task 7 is RSS-based (amended 2026-07-23), REDDIT_* creds obsolete. Task 7's LLM step shells out to `claude -p --model haiku` — verify the CLI exists (claude --version) before dispatching Task 7.

Hard-won conventions for Phase C dispatches (from Phase B, encode into implementer prompts):
- Long live runs: a SUBAGENT's background process dies when its turn pauses. Either the controller runs long fetches in ITS background, or the implementer runs foreground-chunked (timeout 420000, rerun to resume — cached_get_json makes completed calls free). Task 6 at min_interval=3.0 x up to 40 listing pages + per-review pages WILL exceed 420 s; plan the split up front.
- Per-item fault tolerance: catch requests.RequestException (NOT just HTTPError — Task 5 review finding), skip lines print entity names only (never exception text or URLs), every skip category counted and reported in the summary.
- Summaries print api_calls/cache_hits from common.http_stats; verification = rerun prints api_calls: 0 (steady state; a rerun may legitimately retry run-1 transient never-cached failures once).
- Empty-norm names (CJK -> "") skipped + counted wherever norm-keyed joins occur.
- Task 7 hard rule (in the plan amendment): if reddit RSS returns 403, STOP and surface to Joseph — never escalate to JSON scraping or Redlib-style spoofing. min_interval >= 10 s for reddit; browser UA; parse Atom via stdlib xml.etree; fetch via cached_get_json(as_text=True).
- Task 7 LLM step: claude -p --model haiku, cached per post id (never re-extract), parse-failure retry once then record {"error": "unparseable"} and continue (counted). LLM is extraction-only; aggregation is plain code (12-Factor: own your control flow).

Goals (Phase C):
- Task 6: scripts/recs/fetch_pitchfork.py per plan — jazz-genre listing crawl (cap 40 pages, min_interval=3.0, stop when a page yields no new links or published < 2018), per-review JSON-LD parse (reviewRating.ratingValue) with regex fallback, BNM detection, fail-loud contract (assert >= 50 reviews and every review has artist+title+score, else dump one raw HTML sample path to cache and exit 1 — never return zeros). Verify: rerun = 0 fetches; spot-check 3 scores against live pitchfork.com pages (note: if WebFetch gets 403'd, verify via a second independent fetch path and record the caveat honestly).
- Task 7: scripts/recs/fetch_reddit.py per the AMENDED plan — RSS transport (r/jazz top.rss t=year + t=all, r/jazzguitar top.rss t=all, r/jazz search.rss q=best+albums, per-thread /comments/<id>/.rss), raw threads to cache/reddit_threads/<post_id>.json, LLM extraction to cache/reddit_extracted/<post_id>.json, aggregate cache/reddit.json {"mentions": [{norm_key, artist, title, count, post_ids}]} counting DISTINCT posts. Verify: rerun = 0 fetches 0 LLM calls; top-10 mentions table eyeballed as real albums.

Conventions: all cross-cutting contracts in docs/superpowers/plans/2026-07-22-recs-pipeline-checkpoints.md apply (branch feat/recs-pipeline, Conventional Commits + Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>, secrets never printed, caches untracked, completeness over silent drops).

Parked for Task 11 taste gate (do NOT act on these now; itemized in ledger): lastfm artist_tags resolution-8 scope (12 non-jazz top-30 seeds excluded from style enrichment — currently shields the jazz profile); non-jazz artists in the Discogs candidate pool via affinity (e.g. Deep Purple) — Task 9 scoring/shelf matchers are the intended filter.

Output: committed fetchers + tests green + populated cache/pitchfork.json + cache/reddit.json (+ reddit_threads/, reddit_extracted/). Phase D next (Task 8 RYM assisted import — needs Joseph present at his logged-in Chrome).

Post-completion checklist (every phase gate): update Status + append What/Why/Next to the Log in the checkpoints file; update .superpowers/sdd/progress.md; generate next resume prompt, pbcopy silently, append to checkpoints file, and tell Joseph safe to /clear ONLY when the window is worth shedding (~30%+) or he is stopping; a mid-flow scope decision commits its resume prompt immediately regardless of context level.
```

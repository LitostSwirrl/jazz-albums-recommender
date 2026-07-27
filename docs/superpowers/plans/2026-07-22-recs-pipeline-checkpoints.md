# Recs Pipeline (Plan 1) -- Cross-Session Checkpoints

> Multi-session resume file. At each phase gate the agent logs the phase here; when a window is worth shedding, it appends the next resume prompt, pbcopies it silently, and tells Joseph it is safe to `/clear`. Paste the clipboard into the fresh session to continue.
>
> Rules: append-only -- never modify committed prompts. Every prompt must be self-contained (a new session sees only CLAUDE.md + the pasted prompt).

## Status

- **Phase A -- Foundation + taste (plan Tasks 1-3)**: COMPLETE incl. live verify (2026-07-23). Sync: 1531 saved albums / 572 tracks / 50x3 top / 488 followed; silent refresh confirmed. Profile: 137 catalog matches, 1394 unmatched (expected — mixed library), top-15 sanity-checked by Joseph (guitar-heavy, cool-jazz lean, reads true). Known artifacts for Phase B: "Various Artists" #7 affinity + "Various"/"Unknown" labels need stop-list before Task 4's sweep; singles/EPs inflate saved-album counts (accepted).
- **Phase B -- Backbone fetchers: Discogs + Last.fm (Tasks 4-5)**: COMPLETE (2026-07-23). Pre-task stop-list (VA + Various/Unknown) committed. Discogs: 1381 releases (37/40 artists + 18 labels swept), rerun api_calls: 0, 3/3 spot-check exact. Last.fm: similar 29 / tag_albums 12 / artist_tags 893, rerun api_calls: 0; taste profile now prints `styles source: catalog+lastfm` (top-10 all jazz). 88 tests green. Commits 2be4278..98e0ade. Taste-gate questions parked in ledger (lastfm artist_tags scope; non-jazz artists in Discogs pool).
- **Phase C -- Pitchfork + Reddit (Tasks 6-7)**: COMPLETE (verified 2026-07-27). Task 6: pitchfork.json = 374 reviews, steady api_calls: 0, 3/3 spot-check. Task 7: run finished across 3 detached segments (2 machine-sleep/reboot deaths, free cache resumes) — **383/383 extracted, unparseable 0** (was 33% pre-fix; recovery fixes 6c24dfb parser + bb4cc6b timeout-300s field-proven, zero >300s residue), distinct albums 2733, skip counters all 0; steady-state rerun llm_calls: 0 / api_calls: 0 / cache_hits: 387; top-10 mentions all real (Kind of Blue 33 / Bitches Brew 29 / A Love Supreme 26). 215 tests. Joseph confirmed both recovery commits 2026-07-27.
- **Phase D -- RYM assisted import (Task 8)**: COMPLETE 2026-07-27. Validator committed (2f88c50 feat + a07b2d5 contract fixes; task-review APPROVED, 0 Critical/Important, 4 Minors -> ledger; 225 tests). Assisted capture done via claude-in-chrome in Joseph's real Chrome (not logged in -- he chose to proceed on public chart data): 6 of 7 charts captured to cache/rym_charts/ (untracked) -- spiritual-jazz, hard-bop, post-bop, avant-garde-jazz, jazz-fusion, soul-jazz, 80 each = 480 entries, 0 nulls. validate_rym passed on real data (480, exit 0); rym.json written (norm_key + edition-strip verified). jazz-guitar DROPPED: not a real RYM slug (silently serves the global chart), Joseph chose to close at 6. Capture = no commit (cache gitignored).
- **Phase E -- Scoring + shelves (Tasks 9-10)**: COMPLETE 2026-07-27. Task 9 `build_recommendations.py` (deterministic scoring + <=3 cache-traceable reasons + zero-hallucination integrity gate) -- task-review APPROVED (0 Critical/0 Important, 2 Minors -> ledger), controller re-verified first-hand: 231 tests green, real build deterministic, integrity PASS; 4850 candidates -> 300 emitted (catalog 206 / external 4644), sources/emitted {1:186,2:60,3:40,4:13,5:1}. Task 10 `shelves.json` -- nine authored shelves in the Paths voice; 7/9 healthy (all 12 except ECM 9), 2 starved (strata-east-independents 1, j-jazz 0 -- under-owned scenes not in the emitted top-300, matcher-loosening can't fix, flagged for the taste gate). Commits 0961e94 + 14440b0 + a05bbc5. Baked `src/data/{recommendations,library}.json` are on disk + integrity PASS but INTENTIONALLY UNCOMMITTED (Task 11 commits after tuning). Final whole-branch review deferred to Phase F (after the taste gate, before merge).
- **Phase F -- End-to-end + taste gate (Task 11)**: IN PROGRESS. Step 1 (autonomous verify + review tables) done. Taste gate ROUND 1 done -- Joseph's verdicts on the four Phase-E flags became **Task 11a** (six build changes: affinity-ceiling/rank fix, comp filter, leaders matcher, full-pool shelves + per-artist cap, albums = emitted u shelf-only with the integrity gate covering the union, topPicks cap). Task 11a is COMPLETE (commits 899c348..8b50632; task-review NEEDS-FIXES -> fix round 1 -> scoped re-review "all findings addressed"); 243 tests green, integrity PASS, all 9 shelves now 12. Taste gate ROUND 2 tables presented; **awaiting Joseph's verdicts on 11 items** -> those become Task 11b. Baked src/data/*.json still uncommitted (Step 3 commits after sign-off).
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

### 2026-07-23 — Phase C (Tasks 6-7, code complete; reddit live run overnight)

- **What**: Task 6 `fetch_pitchfork.py` (af6eaf0 + fix 6c7341e): listing crawl + embedded-state parse, 374 reviews cached (bnm 17, 2018-2026), steady-state `api_calls: 0`, spot-check 3/3 exact (WebFetch blocked by pitchfork.com — verified via fresh curl + independent regex parse, caveat recorded). One review fix cycle: fallback-regex gated to single-item pages, artists-key-absent routed to fail-loud, listing href/date pair guard — all three reviewer-reproduced before fixing. Task 7 `fetch_reddit.py` (4279759 + fixes 3a1bdc8, 64ab916): RSS transport per amendment, 383 distinct posts from 4 feeds, per-post `claude -p --model haiku` extraction cached forever, plain-code aggregation; review approved with 0 Critical/Important. 211 tests green. Full reddit run detached overnight (log `scripts/recs/cache/reddit_run.log`).
- **Why (decisions a future session can't infer from code)**: (1) Pitchfork moved site-side: listing is `/genre/jazz/review/?page=N` (plan's `?genre=` scheme 301-loops into a soft-404); JSON-LD `reviewRating` is now null — primary parse is `__PRELOADED_STATE__` `itemsReviewed`/`musicRating`, plan's regex demoted to single-item-only fallback (it also misses integer scores like `"score":9` — acceptable: that degradation path is fail-loud, never silent). (2) Pitchfork `publisher` = LABEL, not artist (proved via Nonesuch on a collab review) — artist comes from `headerProps.artists[]`, `artists[0]` primary-credit to match Task 4's Discogs join convention; multi-item pages pair positionally only when counts match (15/374 ambiguous, counted). (3) Reddit's unauthenticated RSS quota is the real constraint: 429s carry no usable Retry-After and at 10 s spacing the window pins (observed ~4 min/post with 4-6 wasted attempts; 383 posts ≈ 24 h). Joseph chose 90 s pacing (~1 attempt/post, ~9.5 h overnight; amendment floor is >= 10 s). Listing-feed failures abort loudly (a listing is 1/4 of the post universe); thread failures skip+count; the 403 hard-stop never fired and was never worked around. (4) haiku extraction runs 1-11 s/post — never the bottleneck. (5) Overnight run detached via `nohup` so it survives session close; every fetched thread/extraction is cache-permanent, so a dead run costs only a rerun. (6) All deferred Minors + the new "LLM extraction is shape-validated but not grounded" taste-gate note are itemized in `.superpowers/sdd/progress.md`.
- **Next**: morning session verifies the run and closes Phase C (resume prompt below), then Phase D (Task 8 RYM assisted import — Joseph at his logged-in Chrome).

### 2026-07-24 — Phase C recovery: reboot death + two extraction-bug fixes; clean run relaunched

- **What**: Morning verify found the overnight reddit run dead at 36/383 — the machine **rebooted 2026-07-23 20:56** (`last reboot`), killing the nohup'd run (not a crash/rate-limit; the 403 hard-stop never fired). Relaunching to resume exposed a 33% false-`unparseable` rate (12/36 extractions), so before letting it run I reproduced the cause and found TWO independent bugs, both fixed via TDD (215 tests green): (1) **parser** `6c24dfb` — Haiku ignores the prompt's "no prose" rule on empty/ambiguous threads and returns a valid array + a trailing explanation; `_parse_llm_output` ran `json.loads` on the whole stdout, choked on the prose → None → retry → cached `{"error":"unparseable"}` forever. New `_first_json_array` scans for the first decodable top-level array, tolerating fences + prose, skipping `[link]`/`[comments]` boilerplate; 4 regression tests built from the real Haiku output shapes. (2) **timeout** `bb4cc6b` — album-rich threads make Haiku generate 100+ items; post 178in0e (12000-char) measured **250s → 118 items**, but `LLM_TIMEOUT=120` cut off both the call and its retry → false `unparseable`, dropping exactly the richest threads. Raised to 300s. Deleted the 12 stale error files (they re-extract clean); relaunched detached with both fixes live.
- **Why (a future session can't infer this)**: (1) Both fixes are plain-code / config **correctness** (they recover real, already-produced data), NOT extraction-*prompt* tuning — the "don't silently tune extraction" guardrail is about LLM judgment, so these were made autonomously; the PROMPT and the 12000-char input cap were left untouched (those are Joseph's tuning levers). (2) Timeout was raised, not the input shrunk, because **completeness > speed** (standing rule): shrinking the cap would truncate the biggest threads. 300s clears the observed 250s with margin; a *supervised* session slows `claude -p` (a 172-item thread had succeeded under the old 120s during the truly-unattended overnight run), so most of 300s is headroom. (3) Consequence: the clean run is **slow** (~250s per big thread, est. ~12-16h) and must run **UNSUPERVISED** — an active Opus session contends for account rate and pushes `claude -p` extractions past even 250s (that contention, not the threads, is why re-extraction timed out during recovery). (4) A reboot can't be prevented from the shell; `caffeinate -i` only guards idle sleep. Cache-permanence makes any death a free resume. (5) A residue of the very largest threads may still exceed 300s — recoverable later by deleting their error files and re-running under light load; never a silent drop.
- **Next**: a fresh session (afternoon 2026-07-24; leave the run UNSUPERVISED until then) verifies the clean run per the resume prompt below — log summary sane, steady-state rerun `api_calls: 0` + `llm_calls: 0`, counters honest, top-10 mentions real — reviews the two fix commits (6c24dfb, bb4cc6b), then closes Task 7 + Phase C. Phase D (RYM) still needs Joseph at his logged-in Chrome.

### 2026-07-27 — Phase C CLOSED: reddit run verified complete; both recovery fixes field-proven

- **What**: Final run segment (340→383, relaunched ~12:00 after a second machine-sleep death) completed 13:15. Summary: `posts: 383 | extracted: 383 | unparseable: 0 | distinct albums: 2733 | llm_calls: 43 | api_calls: 42 | cache_hits: 345`; skip counters all 0. Steady-state rerun (<2 s, fully cached): `llm_calls: 0 | api_calls: 0 | cache_hits: 387`, identical top-10. Spot-checks: 178in0e = list(114) (was the 250s false-unparseable poster child); all 383 extracted files are lists (3978 raw items), 0 error dicts. Top-10 eyeballed real (Kind of Blue 33, Bitches Brew 29, A Love Supreme 26, Giant Steps, Mingus, Ahmad Jamal — no junk). 215 tests green. Joseph reviewed both recovery commits and confirmed "keep both". Task 7 + Phase C closed in ledger.
- **Why (a future session can't infer this)**: (1) `unparseable: 0` across the full corpus — including every album-rich thread — retro-validates both fixes; the feared >300s residue never materialized (unattended runs don't contend for `claude -p` account rate, so 300s is ample headroom). (2) The only failure mode all week was machine sleep/reboot killing the detached process — `caffeinate -i` does not block lid-close sleep; cache-permanence made all 3 segments sum to one complete run with zero data loss and zero re-extraction waste. (3) Monitoring pattern that worked: dynamic /loop self-paced wakeups (25 min → 15 min near the end), each tick a pure filesystem check (pgrep + ls counts + error-dict scan) — never `tail`-driven, since nohup+Python block-buffering leaves the log minutes stale; taught the loop to auto-relaunch on death. Background bash watchers proved fragile (killed by /reload-plugins). (4) The 2733-album pool is shape-validated but NOT grounded — hallucinated pairs pass validate_items; taste-gate note stands (ledger).
- **Next**: Phase D in this same session (Joseph present at his logged-in Chrome): validator TDD via subagent → chart-list agreement → assisted capture at human pace → commit validator only. Then Phase E (Tasks 9-10 scoring + shelves).

### 2026-07-27 — Phase D (Task 8): validator built + reviewed (capture leg still pending)

- **What**: RYM validator implemented, task-reviewed, APPROVED, committed: `scripts/recs/validate_rym.py` + `tests/test_rym_validate.py` (10 tests); 225-test suite green, controller-verified first-hand. TWO commits from a two-implementer RACE: a background agent (name "Implement Task 8 RYM validator", id a87eda5a9...) was already running when this session dispatched its own implementer, so both landed — `2f88c50` = background agent's feat, `a07b2d5` = second implementer's fix on top correcting 6 deviations from the authoritative input contract. Net diff coherent: only the two files (+395 lines), nothing else touched. Task-review: 0 Critical / 0 Important, 4 Minors (in ledger); reviewer independently smoke-ran the empty-dir fail-loud path and cross-checked `norm_key`/`save_json` against `common.py`.
- **Why (a future session can't infer this)**: (1) The AUTHORITATIVE input contract is stricter/clearer than the plan+brief prose ("rating 0-5 float"): each `cache/rym_charts/<slug>.json` is a JSON array of `{rank:int, artist:str, album:str, year:int|null, rating: number(int|float) in 0-5, rating_count:int>0}`; validator maps `album`->`title`, adds `norm_key=common.norm_key(artist,album)`, preserves input order, writes `{"charts":{slug:[...]}}` via `common.save_json`. The six fixes in `a07b2d5`: rating int-or-float (not strict float — a bare JSON `4` is valid); `ValueError` (not `SystemExit`) for bad entries; live `common.CACHE` reference so the `monkeypatch.setattr(vr.common,"CACHE",...)` test idiom works; missing-dir message to stderr; `year` int|null type check; a total-count print line. `bool` is excluded from every int/number check (JSON `true/false` gotcha). (2) The two commits + a `Fable 5`-vs-`Sonnet 5` trailer mismatch are LEFT for Joseph to squash/normalize at the Phase F merge — deliberately NOT amended mid-branch (never rewrite another agent's committed history without his say). (3) `main()` cannot be run against real data yet (no charts captured) — verification is TDD + the fail-loud smoke test; the real ~80/chart run is part of the capture leg.
- **Next**: the ASSISTED CAPTURE leg (Task 8 Step 2) — needs Joseph present at his logged-in Chrome. Invoke the claude-in-chrome skill; confirm RYM chart selectors live; per-slug in-page JS extract → `cache/rym_charts/<slug>.json` at ≥10 s human pacing (never bulk-crawl; captured once, never re-fetch); then `python3 -m scripts.recs.validate_rym` (per-chart ≈ 80) + spot-check 2 entries/chart vs the live page. RYM is aggressively anti-bot: if it blocks or Joseph is absent, STOP and ask whether to defer RYM and proceed to Phase E (Task 9 scoring runs without `rym.json` — per-source badges optional). The "Phase D Resume Prompt (mid-phase insurance)" below still applies verbatim; the ledger now records the validator as DONE so a resume correctly skips to capture.

### 2026-07-27 — Phase D CLOSED: RYM assisted capture done (6 charts), Task 8 complete

- **What**: Assisted capture ran in the same session with Joseph present. 6 of 7 charts captured to `cache/rym_charts/` (untracked) — spiritual-jazz, hard-bop, post-bop, avant-garde-jazz, jazz-fusion, soul-jazz — 80 entries each, 480 total, 0 nulls. `python3 -m scripts.recs.validate_rym` passed on real data (480 entries, exit 0); `rym.json` written and shape-verified (norm_key present, album→title, edition-strip working: "Ascension [Edition I]" → norm_key "john coltrane::ascension"). jazz-guitar was NOT captured — `g:jazz-guitar` is not a real RYM descriptor and silently serves the global all-genre chart (#1 Kendrick Lamar); Joseph chose to close at 6 rather than chase a substitute. No commit for the capture (cache is gitignored; the validator commits are the only tracked artifact).
- **Why (a future session can't infer this)**: (1) Joseph's Chrome was NOT logged in to RYM (the plan's gate assumed logged-in). Surfaced it; he chose to proceed on public data — RYM's all-time genre charts are public and byte-identical logged-out, and I cannot enter his credentials. So the "logged-in" gate is satisfied-in-spirit, not literally; note this if re-capturing. (2) Method that worked (claude-in-chrome in his real browser, NOT devtools-mcp which wouldn't have his session): per-chart in-page JS extraction of `.page_charts_section_charts_item` (rank by DOM position since RYM renders the rank digit as a CSS pseudo-element; rating_count is RYM's abbreviated "47k"→47000, fine for the log10 quality use). TWO harness limits forced a workaround: `javascript_tool` caps returns at ~1KB AND blocks raw-HTML returns as "[BLOCKED: Cookie/query string data]" — so I extract clean JSON in-page, overwrite `document.body` with a `<pre>` of `RYMSTART{json}RYMEND`, and read it back via `get_page_text` (~50KB capacity, returns it verbatim). Files written through a `python -c json.load` heredoc so a bad transcription fails loud. All detail is in the ledger's Task 8 CAPTURE METHOD note. (3) Guitar north-star is not lost by dropping jazz-guitar: Task 10's "Guitar After Wes" shelf keys off player-lineage + "jazz guitar" tags, and guitarists (Wes, Grant Green, Kenny Burrell) already chart in hard-bop/soul-jazz so they still get an RYM signal.
- **Next**: Phase E (Tasks 9-10) — deterministic scoring + reasons + integrity gate (`build_recommendations.py`), then authored shelves (`shelves.json`). All 6 caches now exist for the Task 9 merge: spotify_library, taste_profile, discogs, lastfm, pitchfork, reddit, **rym**. Resume prompt below.

### 2026-07-27 — Phase E CLOSED: scoring + reasons + integrity gate (Task 9) + nine shelves (Task 10)

- **What**: Task 9 `build_recommendations.py` (833 lines) + `test_scoring.py` (6 TDD tests a-f) + a 2-shelf stub, built subagent-driven (implementer+reviewer on opus): consumes all 7 caches + `albums.json` + `taste_profile` + `shelves.json`, merges a 4850-candidate pool (catalog 206 / external 4644) by `norm_key`, excludes owned, scores `0.45·A + 0.40·Q + 0.15·N`, attaches <=3 reasons + per-source badges, emits top 300 + 8 topPicks + shelves. The zero-hallucination integrity gate re-derives every emitted reason from a FRESH cache reload through the same `render_reason` + derivation helpers and `sys.exit(1)`s on any mismatch. Empty-shape `src/data/{recommendations,library}.json` committed first (0961e94); feat commit 14440b0; task-review APPROVED (0 Critical/0 Important, 2 Minors). Task 10 replaced the stub with nine authored shelves (a05bbc5); real run bakes provisional data (uncommitted), integrity PASS, 231 tests green. Controller re-verified the suite + a deterministic rebuild first-hand.
- **Why (a future session can't infer this)**: (1) The plan left real gaps that a controller design pack (`.superpowers/sdd/task-9-context.md`) resolved and that BIND Task 9: candidate pool = union of discogs/rym/lastfm.tag_albums/pitchfork/reddit minus owned; candidate tags = lastfm `artist_tags` (uniform for externals, catalog `genres` deliberately unused); the `label` reason uses `src="taste_profile"` (NOT the brief schema's illustrative `discogs`) so the integrity gate can reconstruct the owned-count `n`; integrity reconstruction PINS the stored `ref` + reloads cache fresh + shares the renderer/derivation so generation and reconstruction cannot drift (the reviewer traced all 7 reason types — drift-proof by construction, the one unverifiable assumption fails safe as a build-fail, never a silent hallucination). (2) Baked data is deliberately UNCOMMITTED at Phase E — the plan commits baked `recommendations.json`/`library.json` at Task 11 AFTER taste-gate tuning, so no provisional/rough pairing reaches git. (3) Task 10's two starved shelves are REAL SIGNAL, not a bug: strata-east/j-jazz scenes are under-owned in this guitar/cool-jazz library, so their albums never reach the emitted top-300 and shelves match within emitted; broadening the label list to 20 labels changed nothing (empirically confirmed). Plan makes <5 a WARNING not a failure and routes shelf tuning to the Task 11 human gate, so they ship as a flagged v1 draft rather than being silently swapped (Joseph chose these nine). (4) after-midnight was tightened mid-authoring because artist-level "cool jazz" tagged ALL of Miles (pulling his electric On the Corner/Dark Magus into a ballads shelf) — a systemic limit of artist-level tags for album-mood shelves; now vocal/ballad tags yield Chet Baker ballads (accurate). (5) The final whole-branch review is a Phase F activity (reviews Tasks 1-11 before the merge), NOT run at this gate.
- **Next**: Phase F = Task 11 end-to-end + HUMAN TASTE GATE with Joseph (needs him present): review top 20 + the nine shelves, tune constants/matchers, decide the four taste-gate flags (starved shelves -> full-pool matching vs swap; single-artist dominance; drummers-table leader-vs-sideman; mood-shelf album-id matcher), rerun, then commit the tuned constants + baked `recommendations.json` + `library.json` (`feat(recs): first baked recommendations`). Then the SDD final whole-branch review over the full branch, then finishing-a-development-branch (merge to main) -> Plan 2 (UI). Resume prompt at the bottom of this file.

### 2026-07-27 — Phase F in progress: taste gate round 1 -> Task 11a (closed) -> round 2 tables presented, awaiting verdicts

- **What**: Taste gate ROUND 1 produced Task 11a — Joseph's verdicts on the four Phase-E flags, implemented as six build changes (brief `.superpowers/sdd/task-11a-brief.md`, report `task-11a-report.md`): affinity-ceiling + rank fix via a shared `usable_artists()`; compilation/box filter (`COMP_ARTISTS` + `COMP_TITLE_RE`); `leaders` matcher for drummers-table; full-pool shelf matching + `SHELF_PER_ARTIST=3`; `albums` = emitted u shelf-only with the integrity gate covering the union; `TOP_PICKS_PER_ARTIST=2`. Commit `8b3e4d0` (DONE_WITH_CONCERNS). Task review (opus) returned spec-compliant but **Needs fixes** — 0 Critical, 2 Important: (1) no integrity test covered a rank-bearing reason, so reverting the derivation would have left all 242 tests green; (2) `max_affinity` used a positional lookup where the brief says "the max", an unclamped-score failure mode the integrity gate structurally cannot catch (it validates reason strings, not scores). Fix round 1 = `8b50632`; scoped re-review verdict **all findings addressed**, with the re-reviewer independently reproducing both experiments rather than trusting the report. Task 11a closed: 243 tests green, integrity PASS, real run = 4684 candidates / 300 emitted / 166 comps excluded / 351 albums (51 shelf-only) / all nine shelves at 12 / determinism byte-identical after masking `generated`. Round-2 tables (top 20, topPicks, nine shelves) were then built and presented to Joseph with 11 flagged items; **his verdicts are still outstanding** and become Task 11b.
- **Why (a future session can't infer this)**: (1) The Phase-E starved shelves are genuinely fixed — full-pool matching filled strata-east (1->12) and j-jazz (0->12), and those shelves are now mostly sub-top-300 items (scores 31-45), which is the intended editorial consequence, not a defect. (2) Two parked questions were closed with EVIDENCE this session, not assumption: **reddit grounding** — across all 100 emitted albums carrying a reddit reason (560 cited posts), the album title appears verbatim in the thread text 560/560 and the artist name 546/560; the 14 exceptions were read individually and are threads where the artist is contextual (a Ron Carter sideman-credits thread listing Miles Smiles/Nefertiti/Sorcerer; a Kind of Blue thread mentioning Somethin' Else), NOT misattributions. So "shape-validated but not grounded" can be retired for the data that ships. (3) NEW findings from cache inspection that Joseph must rule on: **the `year` field is not one quantity** — RYM gives original release, Discogs gives the specific pressing fetched, Pitchfork gives the reviewed edition's year (all 374 pitchfork reviews fall in 2018-2026 because the crawl stopped at the 2018 boundary), and 45 of the 55 pitchfork-citing output albums display the REVIEW year (Chet Baker Sings shown 2019, Sinatra's Watertown 2022, Jarrett's Solo Concerts 2023). A min-year-across-sources rule changes only 22 of 351 and 64 albums have no source year at all, so era placement cannot be properly fixed without refetching Discogs master years — out of scope, flagged not silently patched. **The comp filter is miscalibrated in both directions**: it drops real LPs (Don Cherry's Complete Communion, in-catalog) while missing six box sets that reached the emitted list (The Final Tour #21, Jazz in Detroit #57, Bill Evans Treasures #95, Musical Prophet #107, Go West! #120, Round Trip #158). **One Pitchfork box review** (Chet Baker: The Legendary Riverside Albums, 8.3) is the sole quality signal behind two separately emitted albums (#11 and #39) — the box itself is correctly dropped as a comp, then its score is inherited by its contents. (4) Also outstanding: Miles Davis is 51 of 300 emitted / 19 of the top 50 (round 1's per-artist cap covered shelves and topPicks only, never the emitted list); 18 edition-duplicate pairs survive norm_key (Live Evil/Live-Evil, Head Hunters/Headhunters, We Insist twice on one shelf); the per-artist cap keys on the raw display string so "Pat Metheny"/"Pat Metheny Group" and "Miles Davis"/"Davis, Miles" each get a full allowance (reviewer flagged this independently as Minor #7). (5) Operational: superpowers 6.2.0's `review-package` writes to the per-plan subdir `.superpowers/sdd/2026-07-22-recs-pipeline/`, while Tasks 1-11a artifacts and the ledger remain at the flat `.superpowers/sdd/` path from the earlier skill version — both are live, neither should be "cleaned up".
- **Next**: Joseph's verdicts on the 11 items -> commit the Task 11b resume prompt BEFORE any execution (mid-flow scope decision rule) -> Task 11b as one TDD implementer + task review -> rerun -> his sign-off -> commit tuned constants + baked `recommendations.json` + `library.json` (`feat(recs): first baked recommendations`) -> SDD final whole-branch review on the most capable model, handed the full deferred-Minors list from the ledger (Tasks 1-11a) -> finishing-a-development-branch (merge to main) -> Plan 2 (UI).

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

## Phase C Close + Phase D Resume Prompt

(2026-07-23 generated after Phase C code completion, reddit run overnight; also in clipboard)

```
Close out Phase C of the recs pipeline (verify the overnight Reddit run), then start Phase D (Task 8 RYM assisted import — requires Joseph present at his logged-in Chrome).

Working directory: /Users/jinsoon/Work/Projects/personal/jazz_albums_recommends (branch feat/recs-pipeline)

State:
- Phases A+B COMPLETE (checkpoints Status). Phase C CODE COMPLETE + reviewed 2026-07-23: Task 6 fetch_pitchfork.py FULLY verified (cache/pitchfork.json = 374 reviews, bnm 17, years 2018-2026; steady-state api_calls: 0; spot-check 3/3 vs live). Task 7 fetch_reddit.py review-approved (RSS transport per amendment, 383 posts, cached claude -p haiku extraction, 429 cooldown-retry + loud listing aborts, 403 = hard stop never escalate, MIN_INTERVAL 90s). Commits af6eaf0, 6c7341e, 4279759, 3a1bdc8, 64ab916. Tests: 211 passing (python3 -m pytest scripts/recs/tests -q).
- OVERNIGHT: full reddit run launched detached 2026-07-23 ~19:00 (nohup + PYTHONUNBUFFERED, log scripts/recs/cache/reddit_run.log, was PID 99313, ETA ~04:30). All fetched threads/extractions are cache-permanent regardless of how it ended.

First actions (Task 7 live verify — blocks phase close):
1. tail -15 scripts/recs/cache/reddit_run.log. Healthy end = summary `posts: 383 | extracted: ... | unparseable: ... | distinct albums: ... | llm_calls: ... | api_calls: ... | cache_hits: ...` + skip-counter line + top-10 mentions table.
2. If it died mid-run or is still going: rerun controller-side in background (python3 -m scripts.recs.fetch_reddit, run_in_background — NEVER inside a subagent, its background dies on turn pause) — cache resumes; repeat until complete.
3. Steady-state: one more rerun → api_calls: 0 AND llm_calls: 0. (An intermediate pass may legitimately refetch run-transients once — rate_limited-skipped threads were never cached and get picked up then.)
4. Review counters honestly: rate_limited, comments_fetch_failed, unparseable, malformed_items, empty_norm — all reported, none silently dropped. Eyeball top-10 mentions = real albums attributed to real artists. If the top-10 contains junk (song titles, artist-only entries), STOP and surface to Joseph — do not tune the extraction prompt silently.
5. Then: mark Task 7 complete in .superpowers/sdd/progress.md; update checkpoints Status (Phase C COMPLETE) + append a short Log delta; run the post-completion checklist (next resume prompt + pbcopy).

Phase D (Task 8) — ONLY with Joseph present at his logged-in Chrome:
- Read the plan's Task 8 section (docs/superpowers/plans/2026-07-22-recs-pipeline.md). Protocol: agree final chart list with Joseph; navigate HIS logged-in Chrome to each rateyourmusic chart (pages 1-2 per slug); in-page JS extraction (selectors confirmed live at session start) to cache/rym_charts/<slug>.json; >= 10 s human pacing between pages; charts captured once, never re-fetched. Write validate_rym.py + tests/test_rym_validate.py FIRST (TDD, subagent-driven-development per ledger conventions), then the interactive capture session, then commit the validator only (cache stays untracked).
- RYM is aggressively anti-bot: this is an ASSISTED one-time capture in Joseph's real browser at human pace — never a crawler. If RYM blocks or Joseph is absent, STOP and ask whether to defer RYM and proceed to Phase E (Task 9 scoring can run without rym.json — per-source badges are optional — but the plan sequences RYM first; his call).

Execution mode: superpowers:subagent-driven-development. Ledger .superpowers/sdd/progress.md — tasks marked complete are DONE, never re-dispatch; scripts/task-brief + scripts/review-package helpers; record BASE commit before each dispatch; Minors go to the ledger, fixed only at the final whole-branch review.

Conventions: all cross-cutting contracts in docs/superpowers/plans/2026-07-22-recs-pipeline-checkpoints.md apply (branch feat/recs-pipeline, Conventional Commits + Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>, secrets never printed, caches untracked, completeness over silent drops, phase-gate checklist).

Parked for Task 11 taste gate (do NOT act now; itemized in ledger): lastfm artist_tags resolution-8 scope; non-jazz artists in Discogs pool via affinity; reddit extraction is shape-validated but not grounded (hallucinated artist/album pairs pass validate_items — consider spot-grounding top mentions at the taste gate).

Output: Phase C closed in ledger + checkpoints; Phase D validator committed + charts captured (or an explicit Joseph decision to defer RYM). Phase E next (Tasks 9-10 scoring + shelves).
```

### Correction note on the "Phase C Close + Phase D Resume Prompt" above

Superseded by **Phase C Close v2** below. The v1 prompt assumed a simple morning verify of the overnight run. Reality (2026-07-24 ~03:00): that run died to a machine reboot at 36/383, recovery exposed + fixed two extraction bugs (6c24dfb parser, bb4cc6b timeout), and a CLEAN run was relaunched. Use v2; do not use v1.

## Phase C Close v2 + Phase D Resume Prompt

(2026-07-24 ~03:15 generated after reboot-recovery + two extraction fixes + clean relaunch; also in clipboard; supersedes the prompt above)

```
Close Phase C of the recs pipeline: verify the CLEAN relaunched Reddit run and review two recovery fixes, then start Phase D (Task 8 RYM assisted import — requires Joseph present at his logged-in Chrome).

Working directory: /Users/jinsoon/Work/Projects/personal/jazz_albums_recommends (branch feat/recs-pipeline)

LEAVE THE RUN ALONE UNTIL IT FINISHES: extraction is slow (~250s per album-rich thread) and an active Claude session contends for `claude -p` account rate, pushing extractions past their timeout. If the run is still going when you start, do NOT run concurrent heavy Claude work — check state, let it finish, come back. Verify only once it is complete.

State:
- Phases A+B COMPLETE + live-verified. Task 6 (Pitchfork) COMPLETE + verified (cache/pitchfork.json = 374 reviews, steady api_calls: 0, 3/3 spot-check). Tests: 215 passing (python3 -m pytest scripts/recs/tests -q).
- Task 7 (Reddit) CODE COMPLETE but NOT yet verified. The 2026-07-23 ~19:00 overnight run died at 36/383 to a machine reboot (20:56, not a crash/rate-limit/403). Recovery on 2026-07-24 ~03:00 found a 33% false-`unparseable` rate and fixed TWO extraction bugs — both plain-code/config CORRECTNESS (not prompt tuning), TDD, 215 green, committed:
  - 6c24dfb: `_parse_llm_output` ran json.loads on whole stdout, so Haiku's valid array + trailing prose → false `unparseable`. New `_first_json_array` extracts the first decodable top-level JSON array (fences/prose tolerant, skips [link]/[comments] boilerplate); 4 regression tests from real Haiku output shapes.
  - bb4cc6b: LLM_TIMEOUT 120→300s. Album-rich threads make Haiku generate 100+ items; post 178in0e (12000-char) = 118 items measured 250s, old 120s cut off both call and retry. Raised per "completeness over speed"; PROMPT + 12000-char input cap left untouched (Joseph's tuning levers).
- 12 stale error files were deleted; clean run relaunched detached 2026-07-24 ~03:00 (nohup + caffeinate -i, both fixes live, was PID 90275, log scripts/recs/cache/reddit_run.log). Cache is permanent — any death is a free resume.

Before starting:
1. Read CLAUDE.md, then the checkpoints file docs/superpowers/plans/2026-07-22-recs-pipeline-checkpoints.md (Status + the 2026-07-24 Log entry), then .superpowers/sdd/progress.md (Task 7 + the 2026-07-24 RECOVERY note). Task 7 amendment note in docs/superpowers/plans/2026-07-22-recs-pipeline.md only if you need the RSS-transport rationale.
2. No .env gate for Phase C. Task 7's LLM step uses `claude -p --model haiku` (verify `claude --version` if you have to rerun).

First actions (Task 7 live verify — blocks phase close):
1. Check the run: `tail -20 scripts/recs/cache/reddit_run.log` and `pgrep -f scripts.recs.fetch_reddit`. Healthy end = a summary line `posts: 383 | extracted: ... | unparseable: ... | distinct albums: ... | llm_calls: ... | api_calls: ... | cache_hits: ...` + a skip-counter line + a top-10 mentions table.
2. If still running: let it finish (no concurrent heavy Claude work). If died (reboot/other): rerun controller-side in background, UNSUPERVISED — `nohup caffeinate -i python3 -m scripts.recs.fetch_reddit > scripts/recs/cache/reddit_run.log 2>&1 &` (NEVER inside a subagent — its background dies on turn pause). Cache resumes; repeat until the summary prints.
3. Steady-state: one more rerun → `api_calls: 0` AND `llm_calls: 0` (an intermediate pass may legitimately refetch run-transients / re-extract deleted-error threads once).
4. Confirm the fixes landed: `unparseable` should be LOW now (was 12/36 = 33% pre-fix). Spot-check a big album-rich thread recovered: `python3 -c "import json; d=json.load(open('scripts/recs/cache/reddit_extracted/178in0e.json')); print(type(d).__name__, len(d))"` → expect `list ~118`, not an error dict. Count all remaining error files: `python3 -c "import json,glob; print(sum(1 for f in glob.glob('scripts/recs/cache/reddit_extracted/*.json') if isinstance(json.load(open(f)),dict)))"`.
5. Residual honesty: a few of the very largest threads may STILL exceed 300s → still `unparseable`. Report the count; they are recoverable (delete those specific error files, re-run under light load) — never a silent drop. If more than a handful remain, surface to Joseph before closing.
6. Counters honest (rate_limited / comments_fetch_failed / unparseable / malformed_items / empty_norm — all reported, none silently dropped). Eyeball top-10 mentions = real albums by real artists. If top-10 has junk (song titles, artist-only entries), STOP + surface — do NOT tune the extraction prompt silently.
7. Review the two recovery commits (6c24dfb, bb4cc6b) with Joseph — made autonomously during overnight recovery; the timeout raise (120→300) especially is a completeness>speed judgment worth his explicit confirmation.
8. Then: mark Task 7 complete in .superpowers/sdd/progress.md; update checkpoints Status (Phase C COMPLETE) + append a short Log delta; run the post-completion checklist.

Phase D (Task 8 RYM assisted import) — ONLY with Joseph present at his logged-in Chrome:
- Read the plan's Task 8 section (docs/superpowers/plans/2026-07-22-recs-pipeline.md). Protocol: agree the final chart list with Joseph; navigate HIS logged-in Chrome to each rateyourmusic chart (pages 1-2 per slug); in-page JS extraction (confirm selectors live at session start) to cache/rym_charts/<slug>.json; >= 10 s human pacing between pages; charts captured once, never re-fetched. Write validate_rym.py + tests/test_rym_validate.py FIRST (TDD, subagent-driven-development), then the interactive capture, then commit the validator only (cache stays untracked).
- RYM is aggressively anti-bot: an ASSISTED one-time capture in Joseph's real browser at human pace — never a crawler. If RYM blocks or Joseph is absent, STOP and ask whether to defer RYM and proceed to Phase E (Task 9 scoring can run without rym.json — per-source badges optional — but the plan sequences RYM first; his call).

Execution mode: superpowers:subagent-driven-development. Ledger .superpowers/sdd/progress.md — tasks marked complete are DONE, never re-dispatch; scripts/task-brief + scripts/review-package helpers; record BASE commit before each dispatch; Minors go to the ledger, fixed only at the final whole-branch review.

Conventions: all cross-cutting contracts in the checkpoints file apply (branch feat/recs-pipeline, Conventional Commits + Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>, secrets never printed, caches untracked, completeness over silent drops, phase-gate checklist).

Parked for Task 11 taste gate (do NOT act now; itemized in ledger): lastfm artist_tags resolution-8 scope; non-jazz artists in the Discogs pool via affinity; reddit extraction is shape-validated but not grounded (hallucinated artist/album pairs pass validate_items — consider spot-grounding top mentions at the taste gate).

Output: Phase C closed in ledger + checkpoints; Phase D validator committed + charts captured (or an explicit Joseph decision to defer RYM). Phase E next (Tasks 9-10 scoring + shelves).

Post-completion checklist (every phase gate): update Status + append What/Why/Next to the Log in the checkpoints file; update .superpowers/sdd/progress.md; generate the next resume prompt, pbcopy it silently, append it to the checkpoints file, and tell Joseph it is safe to /clear ONLY when the window is worth shedding (~30%+) or he is stopping; a mid-flow scope decision commits its resume prompt immediately regardless of context level.
```

## Phase D Resume Prompt (mid-phase insurance)

(2026-07-27 ~13:30 generated at Phase C close, immediately after Joseph's "RYM now" scope decision; Phase D executes in the SAME session — this prompt is insurance if that session dies mid-phase; also in clipboard)

```
Continue Phase D of the recs pipeline (Task 8 RYM assisted import) — Phase C is CLOSED. Complete whatever Phase D work remains, then hand off to Phase E (Tasks 9-10) with a fresh prompt at that gate.

Working directory: /Users/jinsoon/Work/Projects/personal/jazz_albums_recommends (branch feat/recs-pipeline)

State:
- Phases A+B+C COMPLETE + live-verified (checkpoints Status + 2026-07-27 Log). Reddit final: 383/383 extracted, unparseable 0, distinct albums 2733, steady-state llm_calls 0 / api_calls 0; recovery commits 6c24dfb+bb4cc6b confirmed by Joseph. Tests: 215 passing (python3 -m pytest scripts/recs/tests -q).
- Phase D started 2026-07-27 with Joseph present at his logged-in Chrome. Check the ledger (.superpowers/sdd/progress.md, Task 8 entry) for exact state: the validator (scripts/recs/validate_rym.py + scripts/recs/tests/test_rym_validate.py) may already be committed; captured charts land in scripts/recs/cache/rym_charts/<slug>.json (untracked). Whatever exists is DONE — NEVER re-capture an existing chart file (RYM is aggressively anti-bot; each chart is captured once, ever).

Before starting:
1. Read CLAUDE.md, the plan's Task 8 section (docs/superpowers/plans/2026-07-22-recs-pipeline.md, ~lines 292-306), .superpowers/sdd/progress.md (Task 8), checkpoints Status + the 2026-07-27 Log entry.
2. No .env gate. The capture leg requires Joseph PRESENT at his logged-in Chrome; invoke the claude-in-chrome skill before any mcp__claude-in-chrome__ tool. If Joseph is absent, do validator-only work and stop before any browser step.

Task 8 protocol (plan-verbatim essentials):
- Validator FIRST if not yet committed (TDD, subagent-driven-development): validate_rym.py loads all cache/rym_charts/*.json -> asserts every entry has rank int, artist, album, rating 0-5 float, rating_count int > 0 -> writes normalized cache/rym.json {"charts": {slug: [{rank, norm_key, artist, title, year, rating, rating_count}]}} using common.norm_key; prints per-chart counts. tests/test_rym_validate.py: 2-entry fake file passes; missing rating fails naming chart+rank. Commit validator only (feat(recs): rym chart validator); cache stays untracked.
- Capture (Joseph present, HIS real Chrome, human pace): chart list as agreed with Joseph (recorded in ledger Task 8 entry; agree it first if not). Per slug: https://rateyourmusic.com/charts/top/album/all-time/g:<slug> pages 1-2 (top 80); confirm selectors live at session start; in-page JS extracts rank/artist/album/year/avg rating/rating count -> cache/rym_charts/<slug>.json; >= 10 s human pacing between pages; never bulk-crawl. If RYM blocks: STOP, ask Joseph whether to defer RYM and proceed to Phase E (Task 9 scoring runs without rym.json — per-source badges optional).
- After capture: python3 -m scripts.recs.validate_rym must pass, per-chart counts ~= 80; spot-check 2 entries per chart against the live page before closing the phase.

Execution mode: superpowers:subagent-driven-development. Ledger .superpowers/sdd/progress.md — tasks marked complete are DONE, never re-dispatch; scripts/task-brief + scripts/review-package helpers; record BASE commit before each dispatch; Minors go to the ledger, fixed only at the final whole-branch review.

Conventions: all cross-cutting contracts in the checkpoints file apply (branch feat/recs-pipeline, Conventional Commits + Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>, secrets never printed, caches untracked, completeness over silent drops, phase-gate checklist).

Parked for Task 11 taste gate (do NOT act now; itemized in ledger): lastfm artist_tags resolution-8 scope; non-jazz artists in the Discogs pool via affinity; reddit extraction shape-validated but not grounded (hallucinated pairs pass validate_items — consider spot-grounding top mentions at the taste gate).

Output: Phase D closed in ledger + checkpoints (validator committed; charts captured, or an explicit Joseph decision to defer RYM). Phase E next (Tasks 9-10 scoring + shelves).

Post-completion checklist (every phase gate): update Status + append What/Why/Next to the Log in the checkpoints file; update .superpowers/sdd/progress.md; generate the next resume prompt, pbcopy it silently, append it to the checkpoints file, and tell Joseph it is safe to /clear ONLY when the window is worth shedding (~30%+) or he is stopping; a mid-flow scope decision commits its resume prompt immediately regardless of context level.
```

## Phase E Resume Prompt

(2026-07-27 generated at Phase D close; also in clipboard)

```
Start Phase E of the recs pipeline: Tasks 9-10 (deterministic scoring + cache-traceable reasons + integrity gate, then authored editorial shelves). Phases A-D are COMPLETE.

Working directory: /Users/jinsoon/Work/Projects/personal/jazz_albums_recommends (branch feat/recs-pipeline)

State:
- Phases A-D COMPLETE + verified (checkpoints Status + Log). All SEVEN source caches are populated under scripts/recs/cache/ (all untracked/gitignored):
  spotify_library.json (1531 albums / 572 tracks / 50x3 top / 488 followed), taste_profile.json (styles source: catalog+lastfm), discogs.json (1381 releases), lastfm.json (similar 29 / tag_albums 12 / artist_tags 893), pitchfork.json (374 reviews), reddit.json (2733 distinct-album mentions from 383 posts), rym.json (6 charts x 80 = 480 entries: spiritual-jazz, hard-bop, post-bop, avant-garde-jazz, jazz-fusion, soul-jazz -- jazz-guitar intentionally ABSENT, not a real RYM slug).
- scripts/recs/: common.py, sync_spotify.py, build_taste_profile.py, fetch_discogs.py, fetch_lastfm.py, fetch_pitchfork.py, fetch_reddit.py, validate_rym.py (+ tests). Tests: 225 passing (python3 -m pytest scripts/recs/tests -q).
- Execution mode: superpowers:subagent-driven-development. Ledger .superpowers/sdd/progress.md -- tasks marked complete are DONE, never re-dispatch; use scripts/task-brief + scripts/review-package helpers; record BASE commit before each dispatch; Minors -> ledger, fixed only at the final whole-branch review.

Before starting:
1. Read CLAUDE.md, then docs/superpowers/plans/2026-07-22-recs-pipeline.md (Global Constraints + Tasks 9-10 IN FULL -- the scoring weights/constants, component math, reason templates, and integrity-check spec are all there and authoritative), then .superpowers/sdd/progress.md (every Task entry + deferred Minors + parked taste-gate questions), then this checkpoints file (Status + Log).
2. No .env gate, no browser, no LLM, no network for Phase E -- Task 9 scoring is pure deterministic computation over existing caches (12-Factor: own your control flow; NO model in scoring).

Goals (Phase E):
- Task 9: scripts/recs/build_recommendations.py per plan -- consumes all caches + src/data/albums.json + cache/taste_profile.json + scripts/recs/shelves.json; emits src/data/recommendations.json + src/data/library.json (commit the empty-shape stubs first, per the plan's Task 9 file list). Deterministic scoring with constants at top of file; <=3 cache-traceable reasons per album via a single render_reason(type,data) reused by the checker; and an INTEGRITY CHECK that, for every emitted reason, reloads the referenced cache record fresh and recomputes the exact render string -- any mismatch prints the offending album+reason and sys.exit(1). This is the zero-hallucination gate; NEVER soften it. TDD first (test_scoring.py): corroboration bonus cap, owned-candidate never emitted, mega-canon halves novelty, render_reason exact string, integrity checker catches a tampered reason (SystemExit), rym+discogs dedup merges into one candidate with both badges.
- Task 10: scripts/recs/shelves.json -- author the initial nine editorial shelves in the Paths voice (schema + list in plan Task 10); rerun build; every shelf >=5 items or investigate (loosen matcher or swap shelf).

RYM specifics for the Task 9 merge (from this session's capture): rym.json = {"charts": {slug: [ {rank, norm_key, artist, title, year, rating, rating_count} ]}}. Join key is norm_key. Plan's rym quality = (rating/5)*min(1, log10(rating_count)/4); chart reason template "#{rank} in RYM {chart} chart ({rating} from {count} ratings)". rating_count is RYM's abbreviated display value (e.g. 47000 parsed from "47k") -- exact below 1000, rounded above; immaterial under log10. Ratings are 0-5 floats (a handful integer-valued, e.g. 4.0). Do NOT expect a jazz-guitar chart.

Parked for the Task 11 taste gate (do NOT act now; itemized in ledger): lastfm artist_tags resolution-8 scope; non-jazz artists in the Discogs pool via affinity; reddit extraction is shape-validated but not grounded (hallucinated artist/album pairs pass validate_items -- consider spot-grounding top mentions); RYM rating_count is abbreviated-precision.

Conventions: all cross-cutting contracts in this checkpoints file apply (branch feat/recs-pipeline, Conventional Commits, secrets never printed, caches untracked, completeness over silent drops, phase-gate checklist). The Co-Authored-By trailer should name the model that actually authors the commit (this branch is mixed: Fable 5 on Tasks 1-7, Sonnet 5 on the Task 8 validator fix); Joseph may normalize/squash at the Phase F merge.

Output: build_recommendations.py + shelves.json committed + tests green; src/data/recommendations.json + library.json baked (first real run, integrity PASS). Phase F next (Task 11 end-to-end + human taste gate with Joseph -- review top 20 + shelves, tune constants).

Post-completion checklist (every phase gate): update Status + append What/Why/Next to the Log here; update .superpowers/sdd/progress.md; generate the next resume prompt, pbcopy it silently, append it here, and tell Joseph it is safe to /clear only when the window is worth shedding (~30%+) or he is stopping.
```

## Phase F Resume Prompt

(2026-07-27 generated at Phase E close; also in clipboard)

```
Start Phase F of the recs pipeline: Task 11 -- end-to-end verification + the HUMAN TASTE GATE with Joseph, then the SDD final whole-branch review, then merge. Phases A-E are COMPLETE.

Working directory: /Users/jinsoon/Work/Projects/personal/jazz_albums_recommends (branch feat/recs-pipeline)

Phase F NEEDS JOSEPH PRESENT for the taste gate (Step 2 onward). If he is absent, do only the autonomous Step-1 verification + prepare the review tables, then STOP and wait for him -- do NOT tune constants or commit baked data without his verdicts.

State:
- Phases A-E COMPLETE + verified (checkpoints Status + Log). All 7 source caches populated under scripts/recs/cache/ (untracked): spotify_library, taste_profile, discogs, lastfm, pitchfork, reddit, rym (6 charts x 80). 231 tests green (python3 -m pytest scripts/recs/tests -q).
- Task 9 build_recommendations.py: deterministic scoring (constants at top) + <=3 cache-traceable reasons via one render_reason() + a zero-hallucination integrity gate that reloads each referenced cache record FRESH and re-renders it, sys.exit(1) on any mismatch -- NEVER soften it. Task-review APPROVED (0 Critical/0 Important). Task 10 shelves.json: nine authored shelves, Paths voice. Commits: acb6be9 (docs baseline) -> 0961e94 (empty stubs) -> 14440b0 (feat scoring) -> a05bbc5 (feat shelves).
- Real run: 4850 candidates (catalog 206 / external 4644) -> 300 emitted; sources/emitted {1:186,2:60,3:40,4:13,5:1}; shelves blue-note-sound 12 / ecm-world 9 / spiritual-jazz 12 / strata-east-independents 1 / j-jazz 0 / guitar-after-wes 12 / organ-grease 12 / drummers-table 12 / after-midnight 12; integrity PASS.
- IMPORTANT: baked src/data/recommendations.json + library.json are ON DISK + integrity PASS but INTENTIONALLY UNCOMMITTED (dirty working tree). Only the EMPTY-shape stubs are committed. Task 11 Step 3 commits the tuned baked data -- that is the plan's design (bake after tuning, not before).
- Execution mode: superpowers:subagent-driven-development. Ledger .superpowers/sdd/progress.md -- tasks 1-10 marked complete are DONE, never re-dispatch. Deferred Minors + the four Task-9/10 taste-gate flags + the parked taste-gate questions are ALL itemized there.

Before starting:
1. Read CLAUDE.md, then docs/superpowers/plans/2026-07-22-recs-pipeline.md (Global Constraints + Task 11 IN FULL), then .superpowers/sdd/progress.md (every Task entry + deferred Minors + the four Task-9/10 taste-gate FLAGS + parked questions), then this checkpoints file (Status + the 2026-07-27 Phase E CLOSED Log entry).
2. No new .env/browser/LLM needed to re-score. A full fetcher rerun (2->7) is steady-state only if .env tokens are present; the caches are the frozen source of truth, so the essential verify is re-running Task 9 (build_recommendations) over the existing caches.

Task 11 protocol (plan Task 11):
- Step 1 (autonomous -- no Joseph needed): rerun `python3 -m scripts.recs.build_recommendations`; confirm the spec success criteria: >=100 candidates (have 4850), >=3 sources represented in the emitted set (have up to 5), integrity PASS, and note the 2 shelves <5. Build the two review tables for Joseph: (a) top 20 emitted albums with score + reasons + badges; (b) the nine shelves each with its items (title/artist/score) -- reuse the probe at scratchpad/probe_shelves.py pattern or write the tables straight from src/data/recommendations.json. Also surface the unmatched-saved-albums report (taste_profile.unmatched_saved_albums, 1394) count for his awareness.
- Step 2 (NEEDS JOSEPH -- the taste gate): paste the top-20 + nine-shelf tables in chat. Walk him through the FOUR taste-gate flags and get his decision on each: (1) TWO STARVED SHELVES strata-east-independents(1)/j-jazz(0) -- under-owned scenes never reach the emitted top-300; matcher-loosening cannot fix (confirmed). Options: (a) build change -- match shelves over the FULL candidate pool not just emitted top-300 (fills both, adds sub-top-300 albums to the albums dict, needs re-review), or (b) swap the shelf for a viable scene. (2) SINGLE-ARTIST DOMINANCE -- spiritual-jazz all Pharoah/Alice, organ-grease heavily Grant Green, after-midnight all Chet Baker; a max-N-per-artist-per-shelf cap (build change) would diversify. (3) drummers-table catches drummers-as-SIDEMEN (Miles/Coltrane records), not drummer-LED -- plan-consistent (players matcher = artist OR credits) but the blurb says "led"; leader-only matching needs a build change. (4) MOOD shelves can't be served by artist-level tags; a curated {albumIds:[...]} matcher type (like paths.json's late-night-tone path) is the honest fix for after-midnight -- build change. ALSO review the parked questions (lastfm artist_tags resolution-8 scope; non-jazz artists in the Discogs pool via affinity e.g. Deep Purple; reddit extraction shape-validated but not grounded -- hallucinated artist/album pairs pass validate_items, spot-ground the top mentions with him; rym rating_count is abbreviated-precision). Tune constants (weights AF/W_*, thresholds, EMIT_LIMIT, corroboration/mega-canon/novelty) in build_recommendations.py and matchers in shelves.json per his verdicts; rerun; repeat until he says "actually interesting". Any build change (full-pool shelves, per-artist cap, leader-only players, albumIds matcher) is a Task-9 code change -- do it TDD via a fresh implementer subagent + task review, not inline.
- Step 3: once Joseph signs off, commit the tuned constants + shelves + the baked src/data/recommendations.json + src/data/library.json: `feat(recs): first baked recommendations`.

After Task 11 -- close the branch:
- SDD FINAL WHOLE-BRANCH REVIEW (this is where it happens, per the skill -- reviews Tasks 1-11 before merge): run scripts/review-package $(git merge-base main HEAD) HEAD, dispatch the final code-reviewer (superpowers:requesting-code-review code-reviewer.md) on the MOST CAPABLE model, and hand it the FULL deferred-Minors list from the ledger (every task's Minors -- Tasks 1-10) so it triages which must be fixed before merge. If it returns findings, dispatch ONE fix subagent with the complete list (not one fixer per finding). The known cleanup items for the merge: two Task-8 commits (2f88c50+a07b2d5) may want squashing; the Co-Authored-By trailer is mixed across the branch (Fable 5 Tasks 1-7, Sonnet 5 Task 8 fix, Opus 4.8 Tasks 9-10 + docs) -- Joseph may normalize/squash.
- Then superpowers:finishing-a-development-branch (merge feat/recs-pipeline -> main). -> Plan 2 (the /discover UI, Home row, badges) is written only after this branch merges with real baked data.

Execution mode: superpowers:subagent-driven-development. Ledger .superpowers/sdd/progress.md -- complete tasks are DONE; scripts/task-brief + scripts/review-package helpers; record BASE before each dispatch; Minors -> ledger, fixed at the final whole-branch review.

Conventions: all cross-cutting contracts in this checkpoints file apply (branch feat/recs-pipeline, Conventional Commits, secrets never printed, caches untracked, completeness over silent drops, phase-gate checklist). Co-Authored-By trailer names the model that actually authors each commit.

Output: Task 11 tuned constants + baked recommendations.json + library.json committed (integrity PASS, Joseph-approved); final whole-branch review clean; branch merged to main. Then Plan 2 (UI).

Post-completion checklist (branch close): update Status + append What/Why/Next to the Log here; update .superpowers/sdd/progress.md; this is the last phase of Plan 1, so the next handoff is into Plan 2 (UI) -- generate that resume prompt, pbcopy it silently, append it here.
```

## Task 11b Resume Prompt (Phase F mid-phase)

(2026-07-27 generated the moment Joseph returned his taste-gate round-2 verdict "do 1,2,4,5,6,7,10,11 as one task"; committed BEFORE any execution per the mid-flow scope-decision rule; also in clipboard)

```
Continue Phase F of the recs pipeline: implement Task 11b (taste-gate round 2 build changes), then rerun and present round-3 tables to Joseph. Phases A-E are COMPLETE and Task 11a is CLOSED.

Working directory: /Users/jinsoon/Work/Projects/personal/jazz_albums_recommends (branch feat/recs-pipeline)

State:
- Task 11a COMPLETE (commits 899c348..8b50632, task review Needs-fixes on 2 Important -> fix round 1 -> scoped re-review "all findings addressed"). 243 tests green (python3 -m pytest scripts/recs/tests -q), build exits 0 with integrity PASS, all nine shelves at 12, determinism byte-identical after masking "generated".
- Current real run: candidates 4684 (catalog 205 / external 4479) | emitted 300 | excluded_comps 166 | albums 351 (51 shelf-only) | sources per emitted {1:186, 2:59, 3:41, 4:13, 5:1}.
- Baked src/data/{recommendations,library}.json are ON DISK, integrity PASS, INTENTIONALLY UNCOMMITTED. Only empty-shape stubs are committed. They get committed at Task 11 Step 3 after Joseph signs off -- that is the plan's design, do not commit them early.
- Ledger: .superpowers/sdd/progress.md (flat path, from the earlier skill version). Task briefs/reports for Tasks 1-11a are also at that flat path. superpowers 6.2.0's review-package script writes to the per-plan subdir .superpowers/sdd/2026-07-22-recs-pipeline/. BOTH paths are live -- do not "clean up" either.

Joseph's taste-gate round-2 verdict (2026-07-27): implement items 1, 2, 4, 5, 6, 7, 10, 11 as ONE task. Item 3 (year/era accuracy) is DEFERRED -- fixing it properly needs a Discogs master-year refetch, out of scope. Item 8 folds into item 10. Item 9 (library topArtists shows Jacqueline du Pre and Barenboim) is LEFT AS IS deliberately -- it is truthful about his listening.

Task 11b scope, all in scripts/recs/build_recommendations.py + scripts/recs/shelves.json + scripts/recs/tests/test_scoring.py:

1. PER-ARTIST CAP ON THE EMITTED LIST. Miles Davis is currently 51 of 300 emitted and 19 of the top 50. Apply a greedy cap of 4 per artist when selecting the emitted 300, same pattern as the existing SHELF_PER_ARTIST / TOP_PICKS_PER_ARTIST caps, new constant EMIT_PER_ARTIST = 4.
2. EDITION-DUPLICATE MERGE. 18 near-duplicate pairs survive norm_key: "Live Evil"/"Live-Evil", "Head Hunters"/"Headhunters", "Relaxin'"/"Relaxin' with the Miles Davis Quintet", three spellings of Jack Johnson, "In New York"/"Chet Baker In New York", "We Insist"/"We Insist! Max Roach's Freedom Now Suite" (both on one shelf). Merge CONSERVATIVELY: same artist AND equal titles after stripping punctuation/whitespace, leading articles, and a leading copy of the artist name. Keep the higher-scored record, union its source badges and reasons. DO NOT use substring containment -- it would wrongly merge Joe Pass "Virtuoso" with "Virtuoso #3", and "Go!" with "The History Of Wes Montgomery" (the substring "go" appears in "montgomery").
4. ORGAN GREASE SHELF. Currently matched on soul-jazz tags and contains almost no organ (Somethin' Else, Green Street which is a guitar trio, two Kamasi Washington). Switch it to the `leaders` matcher with an organist list: Jimmy Smith, Jack McDuff, Larry Young, Big John Patton, Baby Face Willette, Lonnie Smith, Charles Earland, Shirley Scott, Richard "Groove" Holmes.
5. CAP-KEY CANONICALIZATION. All three per-artist caps currently key on the raw display string, so variants each get a full allowance: the ECM shelf holds five Metheny records ("Pat Metheny" x3 + "Pat Metheny Group" x2) and four Jarrett. The pool also holds "Miles Davis" and "Davis, Miles" as separate spellings (the task reviewer flagged this independently as Minor 7). Canonicalize the cap key: convert "Last, First" to "First Last", and strip trailing ensemble words (Group, Trio, Quartet, Quintet, Sextet, Septet, Octet, Band, Orchestra, Ensemble). Use it for all three caps.
6. SHELF ORDERING. "Guitar After Wes" opens with a Chet Baker record and a Paul Desmond record -- correct by the rules (Kenny Burrell plays on Chet, Jim Hall on Easy Living) and genuinely part of the lineage, but it reads wrong. Within a shelf, sort leader-matches ahead of credit-matches, then by score. Do not exclude the credit-matches.
7. SINGLES FILTER. The pool contains 78-rpm singles, e.g. Louis Armstrong "Blueberry Hill / Baby, Won't You Say You Love Me" on the After Midnight shelf. Drop candidates whose title contains " / " (A-side/B-side form). Note this also catches the multi-disc box "Jazz in Detroit / Strata Concert Gallery / 46 Selden", which is a correct drop under item 10 anyway. Print every dropped title so the exclusion is auditable -- completeness over silent drops.
10. COMP FILTER RECALIBRATION, BOTH DIRECTIONS. It currently drops real LPs while missing box sets.
   (a) FALSE POSITIVES to allowlist by exact norm_key: Don Cherry "Complete Communion" (1966 Blue Note, and in the site catalog), Chet Baker "Plays the Best of Lerner & Loewe" AND "Chet Baker Plays the Best of Lerner and Loewe" (both pool entries -- the title means the best songs OF Lerner and Loewe), George Russell "Ezz-thetics (Keepnews Collection) [Bonus Track Version]" (caught by "collection" from the reissue-series name), Rashied Ali "Duo Exchange: Complete Sessions".
   (b) MISSES -- six box sets currently in the emitted list: Miles Davis "The Final Tour: The Bootleg Series, Vol. 6" (#21), Charles Mingus "Jazz in Detroit / Strata Concert Gallery / 46 Selden" (#57), Bill Evans "Treasures: Solo, Trio & Orchestra Recordings From Denmark (1965-1969)" (#95), Eric Dolphy "Musical Prophet: The Expanded 1963 New York Studio Sessions" (#107), Sonny Rollins "Go West!: The Contemporary Records Albums" (#120), Ornette Coleman "Round Trip: Ornette Coleman on Blue Note" (#158). Add narrow title patterns ("bootleg series", "box set", "the <label> recordings/albums", "the expanded ... sessions") and, where no safe pattern exists, an explicit denylist by norm_key. Prefer a denylist entry over a broad pattern -- a pattern that also kills real LPs is worse than a missed box.
   Print the full exclusion list grouped by reason (comp-artist / comp-title / allowlisted / denylisted / single) to stderr.
11. PITCHFORK BOX-SCORE PROPAGATION. One Pitchfork review of the box "Chet Baker: The Legendary Riverside Albums" (8.3) is the sole quality signal behind two separately emitted albums -- "Chet Baker Sings - It Could Happen to You" (#11) and "Chet" (#39 on the guitar shelf). The box itself is correctly dropped as a comp, then its score is inherited by its contents as if each had been reviewed. Deterministic rule: when a single review URL maps to MORE THAN ONE album record AND all of those records carry the SAME score, treat it as a box review and do not use it as a quality signal for any of them. If the scores differ it is a genuine multi-album review -- keep it. Report how many reviews and albums this affects. Note that dropping the pitchfork signal also drops that album's pitchfork-derived year; falling back to another source or to null is correct, not a regression.

NOT in scope, do not do: item 3 (year/era accuracy -- deferred, needs a refetch), item 9 (library topArtists -- left as is), any change to the scoring weights W_AFFINITY/W_QUALITY/W_NOVELTY, the AF dict, or existing thresholds unless one of the eight items above requires it.

Execution mode: superpowers:subagent-driven-development. Fresh implementer subagent + task-reviewer subagent + fix loop. Record BASE (git rev-parse HEAD) before dispatching. Use the flat-path ledger .superpowers/sdd/progress.md. Minors -> ledger, fixed only at the final whole-branch review. Never dispatch parallel implementers.

Hard invariants the implementer must not break:
- The zero-hallucination integrity gate: every emitted reason is re-derived by reloading the referenced cache record FRESH and re-rendering through the SAME render_reason() + derivation helpers used at generation, sys.exit(1) on any mismatch. NEVER soften it. It now covers emitted u shelf-only albums.
- Deterministic build, constants at top of file, no LLM anywhere in scoring, no network.
- Completeness over silent drops: every exclusion category counted and printed.
- ruff-clean (auto-format hook), flat code, early returns.
- Commit ONLY the script/shelves/test files. src/data/{recommendations,library}.json stay modified-but-uncommitted until Joseph signs off.

After the task review comes back clean:
1. Rerun python3 -m scripts.recs.build_recommendations; confirm integrity PASS, note the new emitted/shelf counts and every exclusion count.
2. Build round-3 review tables for Joseph (top 20 with score + reasons + badges; the nine shelves with items). A working probe pattern is at scratchpad/tables.py: the albums dict is ordered emitted-first (first EMIT_LIMIT keys, score-descending) then shelf-only.
3. Present them and get his sign-off. Expect a round 4 -- do not assume this converges in one pass.
4. On sign-off: commit tuned constants + shelves + baked src/data/recommendations.json + src/data/library.json as `feat(recs): first baked recommendations`.
5. Then the SDD FINAL WHOLE-BRANCH REVIEW: scripts/review-package on $(git merge-base main HEAD)..HEAD, dispatch the final code-reviewer on the MOST CAPABLE model, hand it the FULL deferred-Minors list from the ledger (Tasks 1-11b) to triage. Known merge cleanup: the two Task-8 commits (2f88c50 + a07b2d5) may want squashing, and the Co-Authored-By trailer is mixed across the branch (Fable 5 Tasks 1-7, Sonnet 5 Task 8 fix + 11a fix, Opus 4.8 Tasks 9-10, Opus 5 Phase F docs) -- Joseph's call whether to normalize.
6. Then superpowers:finishing-a-development-branch (merge to main). Plan 2 (the /discover UI) is written only after this branch merges with real baked data.

Already closed, do NOT re-open: reddit grounding (verified 2026-07-27 -- across all 100 emitted albums with a reddit reason, 560 cited posts, the album title appears verbatim 560/560 and the artist name 546/560; the 14 exceptions were read individually and are contextual, not misattributions).

Conventions: all cross-cutting contracts in docs/superpowers/plans/2026-07-22-recs-pipeline-checkpoints.md apply (branch feat/recs-pipeline, Conventional Commits, secrets never printed, caches untracked, completeness over silent drops, phase-gate checklist). Co-Authored-By names the model that actually authors each commit. No emojis anywhere.

Post-completion checklist (every phase gate): update Status + append a What/Why/Next entry to the Log in the checkpoints file; update .superpowers/sdd/progress.md; generate the next resume prompt, pbcopy it silently, append it to the checkpoints file, and tell Joseph it is safe to /clear only when the window is worth shedding or he is stopping for the session; a mid-flow scope decision commits its resume prompt immediately, before any execution, regardless of context level.
```

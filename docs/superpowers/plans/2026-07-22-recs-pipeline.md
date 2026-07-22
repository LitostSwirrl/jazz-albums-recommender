# Recommendation Pipeline Implementation Plan (Plan 1 of 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Offline Python pipeline that turns Joseph's Spotify library + five external sources into `src/data/recommendations.json` + `src/data/library.json` with deterministic scores and cache-traceable reasons.

**Architecture:** New `scripts/recs/` Python package; every stage reads/writes disk caches under `scripts/recs/cache/` (gitignored) and is independently re-runnable; final build stage emits baked JSON consumed later by the React UI (Plan 2). No LLM in scoring — one LLM extraction step (Reddit text → structured mentions) only.

**Tech Stack:** Python 3.14, stdlib + `requests` (already used across scripts/) + `pytest` for pure-logic tests. `claude -p` CLI (haiku) for Reddit extraction. Browser automation (in-session, Joseph's logged-in Chrome) for the one-time RYM import.

**Spec:** `docs/superpowers/specs/2026-07-22-taste-recommendation-engine-design.md`

## Global Constraints

- Zero hallucinated data: every emitted reason must trace to a cached source record; integrity check fails the build otherwise.
- Never print secrets. All tokens live in `.env` (gitignored); `.env.example` documents key names only.
- Deterministic scoring: constants at top of `build_recommendations.py`; LLM used only for Reddit text extraction.
- Completeness over silent drops: unmatched/skipped items always reported with counts.
- Spotify: only non-deprecated endpoints (`/me/albums`, `/me/tracks`, `/me/top/*`, `/me/following`); PKCE with redirect `http://127.0.0.1:8888/callback`; scopes `user-library-read user-top-read user-follow-read`.
- Rate limits: Discogs ≤ 60 req/min (authenticated); Last.fm ≤ 4 req/s; Pitchfork ≥ 3 s between page fetches; Reddit app-only OAuth standard limits.
- External album ids use `ext-` slug prefix; catalog ids stay as-is.
- Python style: ruff-clean (auto-hook), flat code, early returns.

## USER SETUP GATE (blocks marked tasks)

| Item | Blocks |
|---|---|
| Spotify dashboard: add redirect URI `http://127.0.0.1:8888/callback` | Task 2 |
| `DISCOGS_TOKEN` in `.env` (free personal token) | Task 4 |
| `LASTFM_API_KEY` in `.env` (free API key) | Task 5 |
| `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` in `.env` (script app) | Task 7 |
| Joseph present with RYM-logged-in Chrome | Task 8 |

Tasks 1, 3 (after 2), 9, 10 need no user setup.

---

### Task 1: Package scaffold + `common.py` core helpers

**Files:**
- Create: `scripts/recs/__init__.py` (empty)
- Create: `scripts/recs/common.py`
- Create: `scripts/recs/tests/__init__.py` (empty)
- Test: `scripts/recs/tests/test_common.py`
- Modify: `.gitignore` (append block)
- Create: `.env.example`

**Interfaces (Produces):**
- `common.ROOT: Path` (repo root), `common.CACHE: Path` (`scripts/recs/cache/`)
- `common.load_env() -> None` — parses `ROOT/.env` `KEY=VALUE` lines into `os.environ` (no override, skips comments/blanks)
- `common.norm(s: str) -> str` — lowercase, NFKD accent-strip, drop punctuation, collapse whitespace, strip leading `the `
- `common.norm_title(s: str) -> str` — `norm()` after removing trailing `(...)`/`[...]` groups whose text matches edition words (remaster|deluxe|edition|expanded|reissue|anniversary|bonus|mono|stereo|version|remix|rvg|ojc)
- `common.norm_key(artist: str, title: str) -> str` — `f"{norm(artist)}::{norm_title(title)}"`
- `common.spotify_album_id(url: str) -> str | None`
- `common.slugify(s: str) -> str` — norm + hyphens
- `common.cached_get_json(bucket: str, url: str, *, params=None, headers=None, min_interval=1.0, as_text=False)` — GET with per-bucket disk cache (`CACHE/http/<bucket>/<sha1>.json`) and per-bucket monotonic throttle; raises on HTTP ≥ 400 after printing url; honors `Retry-After` on 429 (sleep + one retry)
- `common.load_json(path) / common.save_json(path, obj)` — UTF-8, `ensure_ascii=False`, indent 1

**Steps:**

- [ ] **Step 1: Write failing tests** — `scripts/recs/tests/test_common.py`:

```python
from scripts.recs import common

def test_norm_basic():
    assert common.norm("The Jazz Messengers") == "jazz messengers"
    assert common.norm("Météo") == "meteo"

def test_norm_title_strips_editions():
    assert common.norm_title("Blue Train (Remastered 2003)") == "blue train"
    assert common.norm_title("Speak No Evil [RVG Edition]") == "speak no evil"

def test_norm_title_keeps_real_parens():
    assert common.norm_title("Money Jungle (Provocative in Blue)") != "money jungle"

def test_norm_key():
    assert common.norm_key("The Bill Evans Trio", "Portrait in Jazz (OJC)") == "bill evans trio::portrait in jazz"

def test_spotify_album_id():
    assert common.spotify_album_id("https://open.spotify.com/album/2e2E6QiOO95idJELO2MnKb") == "2e2E6QiOO95idJELO2MnKb"
    assert common.spotify_album_id("") is None
```

- [ ] **Step 2:** `python3 -m pytest scripts/recs/tests/test_common.py -q` → FAIL (module missing). If pytest absent: `python3 -m pip install pytest`.
- [ ] **Step 3:** Implement `common.py` per Interfaces above (stdlib: `unicodedata`, `hashlib`, `re`, `time`, `json`, `pathlib`, plus `requests`). Throttle: module-level `dict bucket -> last_ts`, sleep to honor `min_interval`.
- [ ] **Step 4:** Tests pass. Run from repo root so `scripts.recs` imports resolve.
- [ ] **Step 5:** `.gitignore` append:

```
# recs pipeline
scripts/recs/cache/
scripts/recs/.spotify_token.json
```

`.env.example` (names only): `VITE_SPOTIFY_CLIENT_ID=`, `SPOTIFY_CLIENT_ID=`, `SPOTIFY_CLIENT_SECRET=`, `DISCOGS_TOKEN=`, `LASTFM_API_KEY=`, `REDDIT_CLIENT_ID=`, `REDDIT_CLIENT_SECRET=`, `UMAMI_API_KEY=`, `UMAMI_WEBSITE_ID=`
- [ ] **Step 6:** Commit `feat(recs): scaffold pipeline package with normalization + cache helpers`

---

### Task 2: Spotify sync (`sync_spotify.py`) — GATE: redirect URI added

**Files:**
- Create: `scripts/recs/sync_spotify.py`

**Interfaces:**
- Consumes: `common.load_env`, `common.save_json`
- Produces: `cache/spotify_library.json`:

```json
{
  "fetched_at": "2026-07-22T12:00:00+08:00",
  "saved_albums": [{"spotify_id": "...", "title": "...", "artists": ["..."], "year": 1965, "added_at": "..."}],
  "saved_tracks": [{"spotify_id": "...", "title": "...", "artists": ["..."], "album": "...", "album_spotify_id": "...", "added_at": "..."}],
  "top_artists": {"short_term": [{"rank": 1, "name": "...", "spotify_id": "...", "genres": ["..."]}], "medium_term": [], "long_term": []},
  "top_tracks": {"short_term": [{"rank": 1, "title": "...", "artists": ["..."], "album_spotify_id": "..."}], "medium_term": [], "long_term": []},
  "followed_artists": [{"name": "...", "spotify_id": "..."}]
}
```

**Steps:**

- [ ] **Step 1: PKCE auth.** `pkce_pair()`: verifier = urlsafe-b64(secrets.token_bytes(64)) stripped of `=`; challenge = urlsafe-b64(sha256(verifier)) stripped. Authorize URL `https://accounts.spotify.com/authorize` with `client_id` (env `SPOTIFY_CLIENT_ID`), `response_type=code`, `redirect_uri=http://127.0.0.1:8888/callback`, `scope=user-library-read user-top-read user-follow-read`, `code_challenge_method=S256`, `code_challenge`. Open via `webbrowser.open`; capture `?code=` with stdlib `http.server` one-shot handler on `127.0.0.1:8888`; exchange at `https://accounts.spotify.com/api/token` (`grant_type=authorization_code`, `code_verifier`). Persist `{access_token, refresh_token, expires_at}` to `scripts/recs/.spotify_token.json`. On later runs: refresh via `grant_type=refresh_token`, persist rotated refresh token. Never print tokens.
- [ ] **Step 2: Pulls.** `api_get(path, params)` with bearer; on 401 refresh once; on 429 honor `Retry-After`. Paginate: `/me/albums` + `/me/tracks` (`limit=50`, offset until `total`); `/me/top/artists` + `/me/top/tracks` for `short_term|medium_term|long_term` (`limit=50`); `/me/following?type=artist&limit=50` (cursor `after`). Map to the schema above; write `cache/spotify_library.json`; print summary counts.
- [ ] **Step 3: Verify (real run, needs Joseph's one-time browser consent):** `python3 -m scripts.recs.sync_spotify` → browser opens once → expected output like `saved_albums: N / saved_tracks: N / top_artists: 50+50+50 / followed: N`. Second run must NOT open browser (refresh token path).
- [ ] **Step 4:** Commit `feat(recs): spotify library sync via PKCE`

---

### Task 3: Taste profile (`build_taste_profile.py`)

**Files:**
- Create: `scripts/recs/build_taste_profile.py`
- Test: `scripts/recs/tests/test_taste.py`

**Interfaces:**
- Consumes: `cache/spotify_library.json`, `src/data/albums.json`, `common.norm_key`, `common.spotify_album_id`
- Produces: `cache/taste_profile.json`:

```json
{
  "artists": [{"name": "...", "norm": "...", "score": 37.2, "rank": 1, "saved_albums": 4, "saved_tracks": 11, "followed": true}],
  "labels": [{"name": "Blue Note", "count": 12}],
  "styles": [{"tag": "hard bop", "weight": 0.18}],
  "owned": {"spotify_album_ids": ["..."], "catalog_ids": ["..."], "norm_keys": ["artist::title"]},
  "unmatched_saved_albums": [{"title": "...", "artists": ["..."]}]
}
```

- Pure functions for tests: `affinity_scores(lib: dict) -> dict[str, dict]`, `match_owned(saved_albums: list, catalog: list) -> tuple[owned: dict, unmatched: list]`

**Constants:** `W_SAVED_ALBUM=5.0, W_SAVED_TRACK=1.0, W_FOLLOWED=2.0, RANGE_WEIGHT={"short_term":1.5,"medium_term":1.25,"long_term":1.0}`; top-artist points `= (51-rank)/50*10*RANGE_WEIGHT[r]`. Catalog match order: spotify id (from `spotifyUrl`) → exact `norm_key` → same `norm(artist)` + `difflib.SequenceMatcher` title ratio ≥ 0.92. Styles from matched catalog albums' `genres[]` (weight = share), enriched with Last.fm artist tags when `cache/lastfm/` exists (Task 5 rerun).

**Steps:**

- [ ] **Step 1: Failing tests** — `test_taste.py` with a tiny inline fake library + 3-album fake catalog:

```python
from scripts.recs import build_taste_profile as tp

FAKE_LIB = {
  "saved_albums": [{"spotify_id": "AAA", "title": "Idle Moments", "artists": ["Grant Green"], "year": 1964, "added_at": ""}],
  "saved_tracks": [{"spotify_id": "t1", "title": "x", "artists": ["Grant Green"], "album": "y", "album_spotify_id": "", "added_at": ""}] * 3,
  "top_artists": {"short_term": [{"rank": 1, "name": "Grant Green", "spotify_id": "g", "genres": []}], "medium_term": [], "long_term": []},
  "top_tracks": {"short_term": [], "medium_term": [], "long_term": []},
  "followed_artists": [{"name": "Grant Green", "spotify_id": "g"}],
}
FAKE_CATALOG = [
  {"id": "idle-moments", "title": "Idle Moments", "artist": "Grant Green", "spotifyUrl": "https://open.spotify.com/album/AAA", "label": "Blue Note", "genres": ["hard bop"]},
  {"id": "matador", "title": "The Matador", "artist": "Grant Green", "spotifyUrl": "", "label": "Blue Note", "genres": ["hard bop"]},
]

def test_affinity_weights():
    scores = tp.affinity_scores(FAKE_LIB)
    g = scores["grant green"]
    assert g["saved_albums"] == 1 and g["saved_tracks"] == 3 and g["followed"]
    assert g["score"] == 5.0 + 3.0 + (50/50*10*1.5) + 2.0  # 25.0

def test_match_owned_by_spotify_id():
    owned, unmatched = tp.match_owned(FAKE_LIB["saved_albums"], FAKE_CATALOG)
    assert owned["catalog_ids"] == ["idle-moments"] and unmatched == []

def test_unmatched_reported():
    lib = [{"spotify_id": "ZZZ", "title": "Nonexistent", "artists": ["Nobody"], "year": 0, "added_at": ""}]
    owned, unmatched = tp.match_owned(lib, FAKE_CATALOG)
    assert len(unmatched) == 1
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement (pure functions + `main()` that loads real files, writes profile, prints: totals, top-15 artists table, label counts, unmatched list). **Step 4:** Tests pass; then real run `python3 -m scripts.recs.build_taste_profile` — eyeball top-15 sanity. **Step 5:** Commit `feat(recs): taste profile with affinity scores and ownership matching`

---

### Task 4: Discogs fetcher (`fetch_discogs.py`) — GATE: DISCOGS_TOKEN

**Files:** Create: `scripts/recs/fetch_discogs.py`

**Interfaces:**
- Consumes: `cache/taste_profile.json`, `common.cached_get_json` (`min_interval=1.1`, header `Authorization: Discogs token=<DISCOGS_TOKEN>`, UA `SmackCatsRecs/1.0`)
- Produces: `cache/discogs.json`:

```json
{
  "releases": [{"norm_key": "...", "artist": "...", "title": "...", "year": 1972, "labels": ["Strata-East"], "rating": 4.42, "rating_count": 812, "haves": 5400, "wants": 3900, "credits": ["Ron Carter", "..."], "discogs_release_id": 123, "via": "artist:Charles Tolliver"}]
}
```

**Bounds (explicit, printed at end):** top 40 affinity artists × up to 12 main-role masters each; label sweep for every label with affinity count ≥ 3 plus this fixed scene list: `Blue Note, Impulse!, ECM Records, Strata-East, CTI Records, Black Jazz Records, India Navigation, Prestige, Riverside, SteepleChase, Enja, Three Blind Mice` — up to 60 releases per label (main role, year ≤ filter none). Release detail fetched only for entries not already owned (`norm_key ∉ owned.norm_keys`). Everything cached; a rerun costs zero API calls.

**Flow:** search `/database/search?q=<artist>&type=artist` → take first exact-norm name match → `/artists/{id}/releases?sort=year&per_page=100` (role `Main`) → pick up to 12 masters spread across years → `/masters/{id}` → `main_release` → `/releases/{id}` → community rating/haves/wants + labels + `extraartists`+`tracklist` credits names. Labels: `/database/search?q=<label>&type=label` → `/labels/{id}/releases?per_page=100` (role Main) → same release-detail path for top 60 by year spread.

**Steps:**
- [ ] **Step 1:** Implement per above; print progress every 10 releases; final summary `releases: N (artists: A, labels: L) | api_calls: C | cache_hits: H`.
- [ ] **Step 2:** Verify: run twice — second run prints `api_calls: 0`. Spot-check 3 known albums' ratings against discogs.com pages.
- [ ] **Step 3:** Commit `feat(recs): discogs fetcher (artist + label sweeps, community data, credits)`

---

### Task 5: Last.fm fetcher (`fetch_lastfm.py`) — GATE: LASTFM_API_KEY

**Files:** Create: `scripts/recs/fetch_lastfm.py`

**Interfaces:**
- Consumes: `cache/taste_profile.json`; base `https://ws.audioscrobbler.com/2.0/` (`format=json`, `min_interval=0.3`)
- Produces: `cache/lastfm.json`:

```json
{
  "similar": {"grant green": [{"name": "Kenny Burrell", "match": 0.87}]},
  "tag_albums": {"spiritual jazz": [{"artist": "...", "title": "...", "norm_key": "..."}]},
  "artist_tags": {"kenny burrell": ["jazz", "guitar", "hard bop"]}
}
```

**Bounds:** `artist.getsimilar` (limit 30) for top 30 affinity artists; `tag.gettopalbums` (limit 100) for tags: `spiritual jazz, hard bop, post-bop, soul jazz, jazz fusion, avant-garde jazz, free jazz, modal jazz, jazz guitar, organ trio, japanese jazz, ecm`; `artist.gettoptags` for every artist appearing in similar/tag results (deduped).

**Steps:**
- [ ] **Step 1:** Implement; summary `similar: 30 artists | tag_albums: 12 tags × ~100 | artist_tags: N`.
- [ ] **Step 2:** Verify rerun = 0 api calls; spot-check `similar["grant green"]` contains plausible names. Rerun Task 3 (`build_taste_profile`) → styles now include Last.fm enrichment (profile prints `styles source: catalog+lastfm`).
- [ ] **Step 3:** Commit `feat(recs): lastfm fetcher (similarity edges, tag albums, artist tags)`

---

### Task 6: Pitchfork fetcher (`fetch_pitchfork.py`)

**Files:** Create: `scripts/recs/fetch_pitchfork.py`

**Interfaces:**
- Produces: `cache/pitchfork.json`: `{"reviews": [{"norm_key": "...", "artist": "...", "title": "...", "score": 8.3, "bnm": true, "year": 2025, "url": "https://pitchfork.com/reviews/albums/..."}]}`

**Flow:** listing pages `https://pitchfork.com/reviews/albums/?genre=jazz&page=N` for N=1.. until page yields no new review links or published date < 2018 (cap 40 pages, `min_interval=3.0`, UA a normal browser string). Collect review URLs; per review page parse JSON-LD `<script type="application/ld+json">` (`@type` Review → `reviewRating.ratingValue`) with fallback regex `"score":\s*"?(\d+\.\d)`; BNM from `"isBestNewMusic":\s*true` or badge markup.

**Fail-loud:** after parse, `assert len(reviews) >= 50`, and every review has artist+title+score — otherwise dump one raw HTML sample path to cache and exit 1 (site markup changed; fix parser, don't return zeros).

**Steps:**
- [ ] **Step 1:** Implement. **Step 2:** Verify: summary `reviews: N (bnm: B, years 2018–2026)`; rerun = 0 fetches; spot-check 3 scores against live pages. **Step 3:** Commit `feat(recs): pitchfork jazz reviews fetcher (fail-loud parser)`

---

### Task 7: Reddit fetcher (`fetch_reddit.py`) — GATE: REDDIT creds

**Files:** Create: `scripts/recs/fetch_reddit.py`

**Interfaces:**
- Produces: `cache/reddit_threads/<post_id>.json` (raw), `cache/reddit_extracted/<post_id>.json` (LLM output), `cache/reddit.json` aggregate: `{"mentions": [{"norm_key": "...", "artist": "...", "title": "...", "count": 7, "post_ids": ["..."]}]}`

**Flow:** app-only OAuth: POST `https://www.reddit.com/api/v1/access_token` (HTTP basic `CLIENT_ID:SECRET`, `grant_type=client_credentials`, UA `SmackCatsRecs/1.0 by <reddit-user>`); then `https://oauth.reddit.com`: `/r/jazz/top?t=year&limit=100`, `/r/jazz/top?t=all&limit=100`, `/r/jazzguitar/top?t=all&limit=100`, `/r/jazz/search?q=best+albums&restrict_sr=1&sort=top&limit=100`. For each post: `/comments/{id}?limit=100&depth=1`; concat title + selftext + top-level comment bodies (truncate 12k chars).

**LLM extraction (per post, cached by post id — never re-extracted):**

```bash
claude -p --model haiku "Extract every specific music album recommendation from this Reddit thread text. Return ONLY a JSON array, no prose, no code fences: [{\"artist\": \"...\", \"album\": \"...\"}]. Rules: include only concrete album titles attributed to a specific artist; skip artist-only mentions; skip song titles. Text follows:\n\n<TEXT>"
```

via `subprocess.run([...], input=text, capture_output=True)`; parse stdout as JSON, on parse failure retry once with `Return valid JSON only.` appended, then record `{"error": "unparseable"}` and continue (reported in summary). Aggregation (plain code): norm_key → count distinct posts.

**Steps:**
- [ ] **Step 1:** Implement fetch + extraction + aggregate. **Step 2:** Verify: summary `posts: P | extracted: E | unparseable: U | distinct albums: N | top 10 mentions:` table — eyeball top 10 are real albums. Rerun = 0 fetches, 0 LLM calls. **Step 3:** Commit `feat(recs): reddit mining with cached LLM extraction`

---

### Task 8: RYM one-time assisted import — GATE: Joseph + logged-in Chrome

**Files:** Create: `scripts/recs/validate_rym.py`; data lands in `cache/rym_charts/<chart-slug>.json`

**Session protocol (interactive, done together):**
1. Agree final chart list (default: `spiritual-jazz, hard-bop, post-bop, avant-garde-jazz, jazz-fusion, soul-jazz, jazz-guitar?` — RYM descriptor/genre slugs verified live; Japan filter chart if available).
2. For each chart: navigate Joseph's logged-in Chrome to `https://rateyourmusic.com/charts/top/album/all-time/g:<slug>` pages 1–2 (top 80); run an in-page JS extraction snippet (selectors confirmed live at session start; capture rank, artist, album, year, avg rating, rating count); save each page's JSON array to `cache/rym_charts/`.
3. Human pacing between pages (≥ 10 s); never bulk-crawl; charts are captured once and never re-fetched.

**Validator (`validate_rym.py`):** loads all chart files → asserts every entry has rank int, artist, album, rating 0–5 float, rating_count int > 0 → writes normalized `cache/rym.json`: `{"charts": {"spiritual-jazz": [{"rank": 1, "norm_key": "...", "artist": "...", "title": "...", "year": 1971, "rating": 4.35, "rating_count": 12400}]}}`; prints per-chart counts.

**Steps:**
- [ ] **Step 1:** Write `validate_rym.py` (+ inline test in `tests/test_rym_validate.py` with a 2-entry fake file: valid passes, missing rating fails with named chart+rank).
- [ ] **Step 2:** Run session with Joseph; validator passes; per-chart counts ≈ 80. **Step 3:** Commit validator only (`feat(recs): rym chart validator`); cache stays untracked.

---

### Task 9: Scoring + reasons + integrity (`build_recommendations.py`)

**Files:**
- Create: `scripts/recs/build_recommendations.py`
- Create: `scripts/recs/shelves.json` — 2-shelf stub so the build runs (`blue-note-sound` label shelf + `spiritual-jazz` tag shelf, schema per Task 10); Task 10 replaces it with the full authored set
- Test: `scripts/recs/tests/test_scoring.py`
- Create (initial empty-shape outputs, committed): `src/data/recommendations.json` = `{"generated": null, "topPicks": [], "shelves": [], "albums": {}}`, `src/data/library.json` = `{"generated": null, "counts": {}, "topArtists": [], "ownedCatalogIds": []}`

**Interfaces:**
- Consumes: all caches + `src/data/albums.json` + `cache/taste_profile.json` + `scripts/recs/shelves.json` (Task 10)
- Produces final schemas (the Plan-2 UI contract):

```json
// src/data/recommendations.json
{
  "generated": "2026-07-30T...",
  "topPicks": ["<albumKey>", "... 8 total"],
  "shelves": [{"id": "spiritual-jazz", "title": "...", "blurb": "...", "type": "scene", "items": ["<albumKey>", "... ≤12"]}],
  "albums": {
    "<albumKey>": {
      "id": "ext-charles-tolliver-live-at-slugs" ,
      "title": "...", "artist": "...", "year": 1972,
      "coverUrl": "https://... or null", "inCatalog": false, "catalogId": null,
      "spotifyUrl": "https://open.spotify.com/search/... or direct",
      "score": 78.4,
      "reasons": [{"type": "label", "detail": "On Strata-East — you have 6 albums from this label", "src": "discogs", "ref": "release:123"}],
      "badges": {"rym": {"chart": "spiritual-jazz", "rank": 4, "rating": 4.35}, "discogs": {"rating": 4.42, "haves": 5400}, "pitchfork": {"score": 8.6, "bnm": true}, "reddit": {"mentions": 7}}
    }
  }
}
// src/data/library.json
{"generated": "...", "counts": {"savedAlbums": 0, "savedTracks": 0, "matchedCatalog": 0}, "topArtists": [{"name": "...", "artistId": "grant-green-or-null", "score": 37.2}], "ownedCatalogIds": ["..."]}
```

**Scoring constants (top of file, tuned at Task 11):**

```python
W_AFFINITY, W_QUALITY, W_NOVELTY = 0.45, 0.40, 0.15
AF = {"artist": 0.35, "sideman": 0.20, "label": 0.15, "similar": 0.20, "tags": 0.10}
CORROBORATION_BONUS = 0.05          # per source beyond first, cap +0.15
MEGA_CANON_HAVES = 25000            # discogs haves above this → novelty 0.5
NEW_TO_SITE_BONUS = 0.1
SHELF_SIZE = 12
TOP_PICKS = 8
EMIT_LIMIT = 300
```

Component math: `artist` = normalized affinity of candidate's artist (affinity/max_affinity, 0 if unknown); `sideman` = `min(1, |credits ∩ top50_affinity_artists| / 5)`; `label` = `min(1, owned_label_count/8)` for candidate's best label; `similar` = max Last.fm `match` from any top-30 artist to candidate artist; `tags` = Jaccard(candidate tags, top-15 profile style tags). Quality per source: rym `(rating/5)*min(1, log10(rating_count)/4)`; discogs `(rating/5)*min(1, log10(haves)/4)`; pitchfork `score/10 (+0.05 bnm)`; reddit `min(1, count/8)`; quality = mean(present) + bonus. Novelty: owned → excluded before scoring; else 1.0, halved if mega-canon, `+NEW_TO_SITE_BONUS` if not in catalog, clamp [0,1]. Final `score = round(100*(0.45*A + 0.40*Q + 0.15*N), 1)`.

**Reasons — thresholds and exact render strings (one function `render_reason(type, data) -> str`, reused by the checker):**

| type | emit when | template |
|---|---|---|
| artist | affinity rank ≤ 30 | `{artist} is your #{rank} artist` |
| sideman | shared ≥ 2 | `{name1} and {name2} appear on albums you saved` |
| label | owned label count ≥ 3 | `On {label} — you have {n} albums from this label` |
| similar | match ≥ 0.4 | `Last.fm: similar to {top_artist} (your #{rank})` |
| chart | in any RYM chart | `#{rank} in RYM {chart} chart ({rating} from {count} ratings)` |
| pitchfork | score ≥ 7.5 | `Pitchfork {score}{", Best New Music" if bnm} ({year})` |
| reddit | mentions ≥ 3 | `Mentioned in {n} r/jazz threads` |

Max 3 reasons per album, ordered by component contribution. Every reason stores `src` + `ref` (cache record locator).

**Integrity check (same file, runs at end of every build):** for each emitted reason, reload the referenced cache record fresh and recompute `render_reason` — string must match exactly; any mismatch → print offending album+reason and `sys.exit(1)`. Also prints 10 random sample recs with reasons for eyeball review.

**Steps:**
- [ ] **Step 1: Failing tests** — `test_scoring.py` with small fixtures: (a) corroboration bonus adds 0.05/source capped; (b) owned candidate never emitted; (c) mega-canon halves novelty; (d) `render_reason("label", ...)` exact string; (e) integrity checker catches a tampered reason (mutate detail string → expect SystemExit); (f) dedup: same album from rym+discogs merges into one candidate with both badges.
- [ ] **Step 2:** FAIL → implement → PASS.
- [ ] **Step 3:** Real run `python3 -m scripts.recs.build_recommendations` → summary: `candidates: N (catalog: C, external: E) | emitted: 300 | sources per emitted: histogram | shelves: id → count | integrity: PASS`. Cover resolution for externals: Discogs release thumb if present else null (UI ladder handles null).
- [ ] **Step 4:** Commit `feat(recs): deterministic scoring with cache-traceable reasons + integrity gate`

---

### Task 10: Shelves (`scripts/recs/shelves.json`) — authored, committed

**Files:** Create: `scripts/recs/shelves.json`

**Schema:** `[{"id": "blue-note-sound", "title": "The Blue Note Sound", "blurb": "1-2 sentences, existing Paths voice", "type": "label", "matcher": {"labels": ["Blue Note"]} | {"tags": ["spiritual jazz", "astral jazz"]} | {"players": ["Grant Green", "..."]}}]`

Initial nine (drafted by Claude in Paths voice, Joseph tweaks at taste gate): The Blue Note Sound (label), The ECM World (label: ECM Records), Spiritual Jazz (tags), Strata-East & the Independents (labels: Strata-East, Black Jazz Records, India Navigation, Tribe), J-Jazz (tags: japanese jazz + labels: Three Blind Mice), Guitar After Wes (players: guitar lineage from paths.json + tags: jazz guitar), Organ Grease (tags: organ trio, soul jazz), Drummer's Table (players: drummer-leaders list), After Midnight, Continued (tags: ballads, late night — mood).

Matcher evaluation lives in Task 9's build (labels: candidate label ∈ list; tags: intersection ≥ 1; players: candidate artist ∈ list OR credits ∩ list ≥ 1). Shelf < 5 items → build prints WARNING (not failure).

**Steps:**
- [ ] **Step 1:** Author file; rerun build; every shelf ≥ 5 or warning investigated (loosen matcher or swap shelf). **Step 2:** Commit `feat(recs): editorial shelf definitions v1`

---

### Task 11: End-to-end + human taste gate

- [ ] **Step 1:** Full pipeline run in order (2→3→4→5→6→7→validate_rym→9). Verify success criteria from spec: ≥100 candidates, ≥3 sources represented in emitted set, every shelf ≥5, integrity PASS, unmatched-albums report reviewed with Joseph.
- [ ] **Step 2:** Joseph reviews top 20 + shelves (paste summary table in chat). Tune constants (weights, thresholds) per his verdicts; rerun; repeat until "actually interesting".
- [ ] **Step 3:** Commit final tuned constants + baked `src/data/recommendations.json` + `library.json`: `feat(recs): first baked recommendations`. → Proceed to Plan 2 (UI).

---

## Self-check before execution

Spec coverage: Stage 1→Task 2, Stage 2→Task 3, Stage 3→Tasks 4–8, Stage 4→Task 9, Stage 5→Task 10, verification→Task 11, setup gate→table above, outputs schema→Task 9. UI intentionally deferred to Plan 2 (same spec, separate plan).

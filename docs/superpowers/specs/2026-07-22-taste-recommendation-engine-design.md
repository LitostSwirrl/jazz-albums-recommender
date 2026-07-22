# Taste-Based Recommendation Engine — Design Spec

Date: 2026-07-22
Status: approved (brainstorm 2026-07-22)

## Goal

Pivot the site's primary value from curated-editorial reference to personal recommendation:
surface awesome, relevant albums Joseph does not already have, grounded in his real Spotify
library and externally validated by rating/discussion sources. Categorization survives but as
interesting editorial topics (scenes, labels, player lineages, moods) — not textbook genre names.

## Decisions (locked during brainstorm)

- **Scope**: jazz + adjacent (soul-jazz, fusion, ECM-ish, spiritual, J-jazz, jazz-adjacent
  hip-hop where taste supports it). Site keeps its jazz identity.
- **Old features** (timelines, historical context, influence graph): untouched now; pruning is
  a separate phase-2 effort.
- **Data flow**: offline local sync script + baked JSON. No backend, no in-browser OAuth.
  Taste data becomes part of the public static site — accepted.
- **Topic flavors**: scene & label lineages, player-first lineages, mood & moment.
  Explicitly NOT computed taste-clusters — topics are editorial containers; taste personalizes
  contents, not containers.
- **Approach**: source-backed expansion (candidates from catalog remainder + external
  discovery), deterministic interpretable scoring, no LLM in the scoring loop.
- **Sources v1**: Discogs + Last.fm backbone; RYM one-time assisted chart import;
  Pitchfork jazz-review scrape; Reddit discussion mining with LLM extraction step.

## Architecture

Offline Python pipeline in a new `scripts/recs/` directory (existing flat `scripts/` pile stays
untouched). Every stage caches to `scripts/recs/cache/` (gitignored) and is independently
re-runnable. Outputs are baked JSON in `src/data/`, consumed by the static React site.

### Stage 1 — `sync_spotify.py`

- OAuth authorization-code + PKCE against the existing Spotify app
  (`SPOTIFY_CLIENT_ID` in `.env`). Redirect URI `http://127.0.0.1:8888/callback`
  (loopback IP, per current Spotify policy). One-time browser consent; refresh token cached in
  gitignored `scripts/recs/.spotify_token.json`; later runs are hands-free.
- Scopes: `user-library-read user-top-read user-follow-read`.
- Pulls (paginated, all pages): saved albums (`/me/albums`), saved tracks (`/me/tracks`),
  top artists + top tracks (`/me/top/*`, all three time ranges), followed artists
  (`/me/following?type=artist`).
- Uses only non-deprecated endpoints (no audio-features, no Spotify recommendations,
  no related-artists).
- Output: `cache/spotify_library.json`.

### Stage 2 — `build_taste_profile.py`

Deterministic reduction to `cache/taste_profile.json`:

- **Artist affinity scores**: saved album = heaviest weight; saved tracks accumulate per
  artist; top-artist rank boosts (short/medium/long term, recency-weighted); followed = small
  boost.
- **Label affinity**: from labels of matched saved albums.
- **Era/style distribution**: from catalog matches on first run; enriched with Last.fm tags
  for non-catalog artists after Stage 3 has run once (stages are cache-driven and
  re-runnable; profile rebuild is cheap).
- **Ownership set**: Spotify album IDs + normalized `(artist, title)` pairs. Catalog matching
  via existing `spotifyUrl` (direct ID match) then normalized fuzzy artist+title.
- **Unmatched report**: saved albums that match nothing are listed in a printed report —
  never silently dropped.

### Stage 3 — `fetch_sources.py` (+ per-source modules)

All HTTP cached to disk; polite rate limiting per source.

- **Discogs** (`DISCOGS_TOKEN`, 60 req/min): releases + community rating / have / want for
  high-affinity artists and labels; label discographies (feeds scene/label shelves);
  personnel credits (feeds player lineages and sideman-overlap scoring).
- **Last.fm** (`LASTFM_API_KEY`): `artist.getSimilar` for top-affinity artists (similarity
  edges), `tag.getTopAlbums` for shelf tags, `album.getInfo` for tags.
- **Pitchfork** (no API): polite scrape of the jazz reviews index — artist, album, score,
  Best New Music flag, review URL, date. Cached; runs rarely.
- **Reddit** (`REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET`, app-only OAuth): top + "best albums"
  threads from r/jazz and r/jazzguitar. One LLM extraction step (Claude via `claude -p`,
  haiku-tier model) converts thread text to structured album mentions; the model only extracts — counting,
  dedup, and aggregation are plain code (12-factor: LLM for judgment only).
- **RYM** (one-time assisted import, separate script + browser session): drive Joseph's own
  logged-in browser through selected genre charts (candidate list: spiritual jazz, hard bop,
  post-bop, avant-garde jazz, jazz fusion, soul jazz, J-jazz; finalized at import time).
  Capture rank, artist, album, year, avg rating, rating count, genres per entry into
  `cache/rym_charts/*.json`. Never re-fetched. Known ToS friction — accepted, low-volume,
  personal use.

### Stage 4 — `build_recommendations.py`

- **Candidate pool** = (catalog albums not owned) ∪ (external albums from all sources).
  Dedup across sources by normalized artist+title (MusicBrainz ID where available).
  External ids get an `ext-` slug prefix to avoid catalog collisions.
- **Score** = weighted sum of three components (initial weights 0.45 / 0.40 / 0.15,
  constants at top of file, tuned during the human taste gate):
  - **Affinity**: shared-artist (owned artist), sideman overlap (Discogs credits ∩ affinity
    artists), label affinity, max Last.fm similarity edge to a top artist, tag overlap with
    taste distribution.
  - **Quality**: per-source min-max normalized rating × log(rating-count) confidence,
    averaged across sources present; corroboration bonus per additional source (capped).
  - **Novelty**: owned albums excluded outright; mega-canonical penalty (e.g. Discogs
    haves > 25k); small bonus for albums genuinely new to the site.
- **Reasons**: every candidate carries machine-generated `reasons[]` built strictly from
  cached source records — e.g. `{type: "sideman", detail: "Ron Carter appears on 11 albums
  you saved"}`, `{type: "chart", detail: "#4 RYM spiritual jazz chart"}`. UI renders these
  verbatim. No generated prose.
- **Integrity check** (post-build, automated): every reason on every emitted recommendation
  must trace back to a real record in cache; build fails loudly otherwise. Spot-check
  sampling printed for manual review.

### Stage 5 — shelves

- `scripts/recs/shelves.json` (committed, hand-authored with Joseph during implementation).
  Each shelf: `id`, editorial `title` + `blurb` (existing Paths voice), `type`
  (`scene | label | lineage | mood`), and a `matcher` (label list / tag list / player list).
- Build fills each shelf with that shelf's top-scoring candidates (initial N = 12).
  Editorial containers, personalized contents.
- Initial candidates (finalized during implementation): The Blue Note Sound, The ECM World,
  Spiritual Jazz, Strata-East & the Independents, J-Jazz, Guitar After Wes, organ trios,
  drummer-led dates, After Midnight extension.

### Outputs (baked into `src/data/`)

- `recommendations.json` — top ~300 candidates: id, title, artist, year, cover URL, score,
  reasons, source badges (RYM rank, Discogs rating, Pitchfork score, Reddit mentions),
  shelf assignments, spotify link (direct or search URL), `inCatalog` flag.
- `library.json` (slim) — owned catalog ids, owned Spotify album ids count, totals,
  top ~20 artists with counts. Powers badges and the profile strip.
- Both committed with an empty-shape default (`{"generated": null, ...}`) so the site builds
  before the first pipeline run.

## Site changes (React)

- **New lazy route `/discover`** (nav label "Discover"; naming can change): profile summary
  strip (library size, top artists), then shelves as horizontal carousels reusing existing
  Home carousel components.
  - Catalog albums → existing card, links to internal album page, shows top "why" chip.
  - External albums → new lighter card variant: cover (existing AlbumCover fallback ladder),
    title / artist / year, top "why" chip, source badges, external Spotify link.
    No internal pages for external albums in v1.
- **Home**: one "Picked for you" row (top 8 overall), dynamically imported below the fold.
  Nothing else on Home moves.
- **Library badge**: subtle "In your library" state on catalog album cards + album page.
- **Types**: new `src/types/recommendations.ts` interfaces (Recommendation, Reason, Shelf,
  LibrarySummary).
- **States**: empty `recommendations.json` → setup-instructions empty state; loading
  skeletons and error handling per house rules. Data loads lazily (dynamic import), matching
  the slim-eager / detail-lazy architecture.
- Optional: Umami event on rec card click-out (uses existing analytics util) — feeds the
  later taste evaluation.

## Explicitly out of scope

- Feedback buttons / persisted user state on recs
- Computed taste clusters
- Backend or in-browser Spotify OAuth
- Auto-promotion of external albums into the full catalog (manual enrichment later)
- Pruning timelines / context / influence graph (separate phase-2 effort)
- Runtime LLM anything

## One-time setup (Joseph, ~15 min, before relevant phases)

1. Spotify developer dashboard: add redirect URI `http://127.0.0.1:8888/callback` to the
   existing app.
2. Discogs: create free personal access token → `DISCOGS_TOKEN` in `.env`.
3. Last.fm: create free API key → `LASTFM_API_KEY` in `.env`.
4. Reddit: create script-type app → `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` in `.env`.
5. RYM: be present with logged-in browser for the one-time chart import session.

`.env.example` gains the new key names (no values). `scripts/recs/cache/` and
`.spotify_token.json` added to `.gitignore`.

## Verification / success criteria

1. Pipeline runs end-to-end; each stage prints summary stats; unmatched-albums report
   reviewed (completeness over silent drops).
2. Reasons-integrity check passes on every build (all reasons trace to cached records).
3. ≥100 scored candidates spanning ≥3 sources; every shelf holds ≥5 items.
4. `npm run build` passes; `/discover` and Home row render all four UI states correctly.
5. Human taste gate: Joseph reviews the top 20 overall — they must actually be interesting.
   Scoring weights tuned here if not.

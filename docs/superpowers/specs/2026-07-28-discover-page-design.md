# /discover — minimal recommendations page (design)

Date: 2026-07-28
Status: approved by Joseph, ready for an implementation plan

## Purpose

Plan 1 built a recommendation pipeline and merged it to main. Its output —
`src/data/recommendations.json` — currently has **no consumer**: nothing under
`src/` imports it, so nothing about the live site changed when it merged.

This is the minimal page that makes it visible. Joseph explicitly chose a
minimal `/discover` over the fuller Plan 2 (discover page plus a Home row plus
per-source badges) to get the recommendations in front of his eyes sooner,
having found across three taste-gate rounds that seeing the output changes what
he wants from it. Badges and the Home row are a later iteration and are out of
scope here.

**The page's job:** answer "what do I play next". Not "browse nine scenes", and
not "show me the evidence" — those were the alternatives considered and
rejected. The eight top picks lead; the nine shelves sit below as secondary
browsing.

## Data reality this design is built around

Measured against the merged `recommendations.json` (358 albums), not assumed:

| Fact | Number | Consequence |
|---|---|---|
| Albums with a cover URL | 65 of 358 | A cover-led grid would be 82% empty. Part A fixes this. |
| Albums with a Spotify link | 358 of 358 | Every card has a working action. No dead cards. |
| Albums with a site album page | 65 of 358 | Only in-catalog albums can link to `/album/:id`. |
| Albums with no reasons at all | 32 | Cards must render without reasons. |
| Albums with no year | 53, and the rest are unreliable | Year is dropped from this page entirely. |

Two further constraints inherited from Plan 1 and recorded in its checkpoints:

- **The integrity guarantee covers reason sentences only.** Badges, scores,
  years, titles and artist names are not verified by the pipeline's gate. Do not
  present any of them as though they were.
- **`score` is deliberately unclamped** and can exceed 100. It must never be
  rendered as a percentage, a progress bar, or at all on this page.

## Part A — cover resolver

New standalone script `scripts/fetch_rec_covers.py`. It does not modify the
recs pipeline, and no cover refresh ever requires re-baking
`recommendations.json`.

**Input:** every album in `src/data/recommendations.json` with a falsy
`coverUrl` (293 today).

**Resolution:** the iTunes Search API (`entity=album`), queried on artist plus
title. No authentication required.

**Acceptance is strict, and this is the load-bearing rule.** A result is
accepted only when the normalized artist *and* the normalized core title both
match the album we asked for. Normalization strips punctuation, case, and the
parenthetical and bracketed suffixes the API appends — so
`Waltz for Debby (Original Jazz Classics)` matches `Waltz for Debby`, while
`Theo Parrish's Black Jazz Signature` correctly rejects `First Floor`. That
false positive was observed in a live probe; taking the first search result
would have shipped the wrong album art. **When nothing matches, the album gets
no cover.** A plausible substitute is a false claim about a record, which is the
same class of error the whole pipeline exists to prevent.

**Output:**
- `src/data/recCoverManifest.json` — `{albumId: coverUrl}`, only for accepted
  matches. This mirrors the existing `src/data/coverManifest.json` pattern.
- A failures list naming every album that got no cover and why (no result vs
  rejected as a mismatch).

**Behaviour:** results cached per album id so reruns are free; requests paced
about 1.2s apart. The API returns `artworkUrl100`; rewrite the trailing
`100x100bb` segment to `600x600bb` — the mzstatic convention the site already
relies on for its 179 existing mzstatic covers, which the cover-fetch script's
own notes record as served direct and reliable. The run
prints resolved / rejected-as-mismatch / no-result counts plus a sample of
accepted matches for a human to eyeball, and never silently drops an album.

**Expected outcome, from a 30-album probe:** 15 of 15 resolved on well-known
records, 9 of 15 on the obscure tail (J-Jazz, Strata-East). Blended, roughly 235
of 293 resolved, leaving about 58 albums with no cover. That number is an
estimate; the script reports the real one.

## Part B — the page

**Route.** `/discover`, registered in `src/App.tsx` and lazy-loaded exactly like
the existing routes. `recommendations.json` and `recCoverManifest.json` are
static imports *inside* the route module, so Vite places them in that route's
chunk and they never enter the eager bundle. No runtime fetch is needed. A nav
entry is added to the header.

**Structure, top to bottom:**

1. Header — page title and one line of framing.
2. **Tonight** — the eight `topPicks` as large, cover-led cards. Each shows up
   to two of its reasons in small type. The reasons are what separate this page
   from an arbitrary list, and they are the only claims the pipeline actually
   guarantees.
3. **Nine shelves** — one horizontal scrolling row each, reusing the existing
   carousel components rather than new ones, each headed by its title and
   editorial blurb. Shelf cards are lean: cover, title, artist. No reasons, so a
   row of twelve stays scannable.

**Cards.** Cover art where the manifest or the album record supplies one. Where
neither does, a typographic fallback occupies the same footprint — title set
large, artist beneath — so a row keeps its rhythm rather than showing a broken
image. The fallback is a designed state, not an error state.

**Links.** In-catalog albums (`inCatalog: true`) link to `/album/:catalogId`.
All others open their Spotify URL in a new tab. Never construct an
`/album/ext-…` link; those pages do not exist.

**Never rendered:** `score`, and `year`.

## UI states

All four are required, per the project's standards:

- **Loading** — the route chunk is code-split, so the existing Suspense boundary
  covers it; a skeleton consistent with the site's other lazy routes.
- **Error** — if the data fails to import or is malformed, a plain message. Do
  not swallow it.
- **Empty** — if `topPicks` or `shelves` is empty, say so rather than rendering
  an empty page. Not expected, but the page must not assume.
- **Success** — as described above.

## Out of scope

Per-source badges; a Home page recommendations row; a browse-all-300 view; any
change to the recs pipeline or its baked output; self-hosting cover images;
fixing the year field.

**Related decision deferred, not forgotten:** 8 non-jazz albums (4 Deep Purple,
2 Ulver, 2 Jacqueline du Pré) sit in the emitted 300 because Joseph's real
listening affinity ranks those artists highly and nothing in the pipeline gates
genre. None appear in `topPicks` or on any shelf, so **this page will not show
them.** They become visible the moment a browse-all view ships, which is when
the policy call is due.

## Verification

1. `npm run typecheck` and `npm run lint` clean.
2. `npm run build` succeeds, and the build output confirms the recommendations
   JSON is in the `/discover` chunk, not the main bundle. This is checked, not
   assumed.
3. The page is opened and inspected: eight top picks, all nine shelves, cover
   fallbacks looking deliberate, no dead links, no console errors.
4. `npm run deploy` to Firebase, and the live URL confirmed.

## Standards

TypeScript strict, no `any`. `interface` over `type` except unions. Early
returns, flat structure. Tailwind for all styling. Dark monochrome editorial
aesthetic, warm-gray palette, Space Grotesk and Inter — no serifs. No emojis
anywhere.

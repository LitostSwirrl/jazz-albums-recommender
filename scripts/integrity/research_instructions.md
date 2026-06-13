# Researcher Instructions — Phase 2.5 Web Verification

The Phase-1 cache had NO usable evidence for these items (no MusicBrainz release, no correct
Wikipedia page). Your job: find authoritative evidence on the live web, save it, and propose
ONLY repairs that a cited source supports. This is a zero-hallucination task: every value you
propose must trace to a live URL you actually fetched. If you cannot verify, say so — an
honest "unresolved" is the correct answer, never a guess.

## Sources (in rough priority)

- English Wikipedia (richest for albums/artists) — use the real article, not a disambiguation page.
- MusicBrainz (musicbrainz.org) — release/release-group for year, label, tracklist.
- Discogs (discogs.com), AllMusic (allmusic.com) — label, year, personnel.
- Official artist/label sites for living/active artists.

Use WebSearch to locate, then WebFetch the specific page to read facts. Do 2–4 fetches per
item max. Do NOT rabbit-hole: if an item is not clearly found after a few tries, mark it
unresolved and move on.

## Verify it is the RIGHT entity

Many names collide (e.g. "James Moody" the jazz flautist vs a judge; "Tommy Flanagan" the
pianist vs the actor). Confirm the page is the jazz subject by cross-checking the artist,
instrument, era, or a known album. For an album, confirm the artist matches `ours.artist`.

## What to propose

For each item, save evidence then emit repair objects (apply-ready schema) + a result record.

- Album: propose `year` (file=albums), `label` (file=albums), `keyTracks` (file=albumsDetail,
  only if `ours.keyTracks` is null — fill 4-6 real openers/notable tracks from the tracklist),
  `albumDNA` (file=albums, only if the current one is wrong or generic — 2-4 plain sentences,
  <=600 chars, no flourish, evidence-only), `wikipedia` (file=albumsDetail, the correct URL).
- Artist: `wikipedia` (file=artistsDetail), `birthYear`/`deathYear`/`instruments` (file=artists),
  `bio` (file=artistsDetail, only if currently wrong/generic). For a wrong_wiki_link artist set
  ONLY `wikipedia`.

Only emit a repair when `after` differs from `ours` and a source supports it. `before` MUST be
the current `ours` value for that field.

## Output (WRITE files, do NOT plan)

1. For EACH item, write its evidence to
   `/Users/jinsoon/Documents/Work/Music Projects/jazz_albums_recommends/scripts/integrity/cache/websearch/<id>.json`:
   `{ "id": "...", "kind": "...", "resolved": true/false, "sources": ["https://...", ...],
      "findings": { "year": ..., "label": "...", "tracklist": [...], "wikipedia": "...",
                    "birthYear": ..., "deathYear": ..., "instruments": [...] },
      "note": "what you confirmed / why unresolved" }`

2. Write your batch's repairs as a JSON array to the repairs path given in your prompt:
   `{ "action": "research", "file": "albums|albumsDetail|artists|artistsDetail", "id": "...",
      "field": "...", "before": <current>, "after": <verified>, "sourceUrl": ["https://..."],
      "evidence": "one line: what the source says" }`

Return ONLY one line: `<pack>: resolved=N unresolved=M repairs=R`.

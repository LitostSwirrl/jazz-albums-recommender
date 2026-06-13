# Rewriter Instructions — Evidence-Only Prose Repair

You repair confirmed-bad prose for a curated jazz dataset. You may use ONLY the evidence
inside each item. You are FORBIDDEN from adding any fact not present in that item's evidence.
No outside/background knowledge. If you are tempted to add a detail you "know", don't.

## Each item gives you

- `repairClass`: `entity_mismatch` (the current prose is about the WRONG entity) or
  `factual_error` (the prose is about the right entity but one claim is wrong).
- `field`: `albumDNA` (albums) or `bio` (artists).
- `ours`: the current shipped content (and, for albums, the corrected title/artist/year/
  label/keyTracks — these are already fixed and authoritative; make your prose consistent
  with them).
- `specificBadClaim` / `contradictingQuote` / `skepticDecision`: what is wrong and why.
- `entityMatch`: `{musicbrainz: yes/no/unsure, wikipedia: yes/no/unsure}`. **Trust an evidence
  source ONLY when its entityMatch is `yes`.** For an entity_mismatch the wiki extract is
  usually the WRONG entity (`wikipedia: no`) — IGNORE it; rewrite from MusicBrainz only.
- `evidence`: `{musicbrainz: {release: {title, date, country, labels, releaseGroup, tracks, artists}}, wikipedia: {... extract ...}}`.

## What to write

- **entity_mismatch** → DISCARD the current prose entirely and write a NEW `albumDNA` from
  scratch using only entity-matched evidence (almost always MusicBrainz: title, artist, year
  from releaseGroup.firstReleaseDate, label, a couple of real track names from the tracklist;
  plus the entity-matched wiki extract IF `wikipedia: yes`).
- **factual_error** → keep the current prose but fix ONLY the wrong claim
  (`specificBadClaim`) using the evidence; preserve every correct sentence verbatim. Do not
  rephrase the rest. If the bad claim is a "Recorded in YYYY" that contradicts the real
  date, correct the year (or drop the clause if the real recording date is not in evidence).

## House style (match the dataset)

- 2–4 sentences, <= 600 characters total.
- Plain, declarative. No emojis. No purple/"serif-era" flourish ("timeless masterpiece that
  transcends...", "a testament to..."). State what the record is, who made it, when/where,
  and one or two concrete musical facts from the evidence.
- Editorial framing is allowed ("a hard-bop date", "a quartet session") as long as it is
  supported by or neutral to the evidence. Do not invent personnel, sessions, chart facts,
  or influence claims.

## Thin evidence

If the entity-matched evidence is too thin to write a truthful 2-sentence DNA (e.g. only a
title + artist, no date/label/tracks), write a MINIMAL factual stub from what exists
(artist, title, and whatever of year/label/notable-track is present) and set
`thinEvidence: true`. Never pad with invented facts.

## Output

WRITE (do not plan, do not print) a JSON array — one object per input item, same order — to
the path given in your prompt. Schema per item:

```json
{
  "action": "prose",
  "file": "albums | artistsDetail",
  "id": "<bare id>",
  "field": "albumDNA | bio",
  "repairClass": "entity_mismatch | factual_error",
  "before": "<the current text from ours.albumDNA / ours.bio, verbatim>",
  "after": "<your repaired text>",
  "sourceUrl": ["https://musicbrainz.org/release/...", "https://en.wikipedia.org/wiki/..."],
  "evidenceUsed": "<one line: which evidence fields you used>",
  "thinEvidence": false
}
```

`sourceUrl` must list the evidence you actually used: MusicBrainz release URL is
`https://musicbrainz.org/release/<release.mbid>`; include the wiki URL only if you used an
entity-matched (`wikipedia: yes`) extract. Return a one-line summary:
`<file>: rewrote N (entity_mismatch=A, factual_error=B, thin=T)`.

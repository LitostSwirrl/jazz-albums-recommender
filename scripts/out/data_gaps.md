# Data Gaps — S3 re-audit (2026-04-14)

## Summary

- **Audit candidates:** 9 albums flagged by `audit_album_descriptions.py`
  (cross-artist contamination + own-artist absent + Wikipedia low overlap).
- **True corruptions rewritten:** 10 (the original 7 from the first audit
  pass + 3 more from the principled re-audit).
- **False-positive candidates left untouched:** 6 (editorial-style DNA that
  legitimately omits the leader's name but is topically correct — see
  below).
- **Spot-check accuracy:** 50/50 sampled albums have own-artist name
  present in DNA after rewrites.

## Root cause of the underlying corruption

The original `description` field was populated by Wikipedia article scrapes
keyed on title alone, with no validation that the resolved article was
about the right artist. Disambiguation collisions then silently substituted
unrelated articles:

- "In Private" → Dusty Springfield's 1989 single (instead of Art Tatum's
  Pablo collection)
- "Broken Circles" → the Levellers' 1991 album (instead of Joel Ross's)
- "Jazz Street" → Wings' "Red Rose Speedway" (Wikipedia scraper went off
  the rails)
- "Lullabies" → Vijay Iyer's 2020 album (instead of Dave Brubeck's
  posthumous Verve release)
- "Volume 1 (1923-1929)" → Mingus Ah Um (no idea how)
- Sun Ra "Solo Piano at WKCR, 1977" → Charlie Parker's biography
- Louis Armstrong "Armstrong Alumni Allstars" → generic Wikipedia jazz
  history article
- Christian Sands "Christmas Stories" → essay about Christmas in
  literature/film
- Eric Dolphy "Screamin' the Blues" → correctly identified as Oliver
  Nelson's record (Dolphy was a sideman); the dataset's artist attribution
  is the historical question, not the description
- "Various Artists" "The Real Book" → Leonard Cohen's "Various Positions"
  (matched on the word "Various")

## Audit limitation surfaced (relevant if scaling up)

The principled audit (cross-artist mention + own-artist absent +
word-bounded matching against the 315-artist index) over-flags
**editorial-style descriptions** that legitimately omit the leader's name
but discuss the album's actual personnel. Examples below.

The strongest known-correct discriminator between corruption and editorial
style requires a *personnel/collaborator graph* the dataset doesn't have.
Wikipedia first-paragraph jaccard fails because formal Wikipedia openings
share few tokens with editorial prose even when topic matches.

**Practical conclusion:** the audit produces a candidate list. Final triage
needs human eyes for borderline cases. Documented in the script docstring.

## Editorial-style DNA flagged but kept (no rewrite)

These albums' DNA reads as editorial copy that names the album's actual
personnel but doesn't name the leader explicitly. The content is topically
correct; the audit flags them because the leader's name is absent. A
future SEO-pass might add the leader's name to each opening sentence.

- **Bitches Brew** (`bitches-brew`) / Miles Davis — DNA names Wayne
  Shorter, Chick Corea, Joe Zawinul, John McLaughlin, Dave Holland (the
  actual Bitches Brew lineup) but not Davis.
- **Kind of Blue** (`kind-of-blue`) / Miles Davis — names Bill Evans,
  Cannonball Adderley, Gil Evans (correct sidemen) but not Davis.
- **Free Jazz: A Collective Improvisation** (`free-jazz`) / Ornette Coleman
  Double Quartet — DNA says "by American jazz saxophonist Ornette Coleman"
  (correct content); flagged because dataset's artist field is "Ornette
  Coleman Double Quartet" (the ensemble) not "Ornette Coleman" (the
  leader).
- **The Newest Sound Around** (`the-newest-sound-around`) / Ran Blake &
  Jeanne Lee — DNA names both Ran Blake and Jeanne Lee separately;
  flagged because dataset's artist field is the combined string.
- **Your Queen Is a Reptile** (`your-queen-is-a-reptile`) / Sons of Kemet
  — DNA names Shabaka Hutchings (Sons of Kemet's leader) but not the
  group.
- **Pimp Master** (`pimp-master`) / Soil & "Pimp" Sessions — DNA describes
  the album's musical character correctly without naming the band.

## Album metadata questions surfaced during the rewrite

These are NOT description corruptions — the new albumDNA reads cleanly —
but the audit surfaced metadata questions a human curator may want to
revisit. The dataset values were preserved (S3 scope excludes year/label
edits).

- **In Private** (`in-private`) / Art Tatum — dataset says `year: 1991`,
  `label: Fresh Sound Records`. Per the S3 spec brief, the authoritative
  release is the 1976 Pablo Records solo piano collection (Fresh Sound
  reissued it in 1991). Curated albumDNA now cites both. The
  `era: hard-bop` tag is wrong for Tatum (his career ended 1956 — swing
  era).
- **Lullabies** (`lullabies`) / Dave Brubeck — Brubeck died in 2012;
  dataset's `year: 2020 / label: Verve` is a posthumous release.
- **Jazz Street** (`jazz-street`) / Jaco Pastorius — Pastorius died 1987;
  dataset's `year: 1989 / label: Timeless Records` is a posthumous live
  release.
- **Screamin' the Blues** (`screamin-the-blues`) — dataset attributes the
  album to Eric Dolphy. It is historically credited to Oliver Nelson, with
  Dolphy as sideman.
- **Volume 1 (1923-1929)** (`volume-1-1923-1929`) / Jelly Roll Morton —
  dataset's `year: 2010 / label: Neatwork` is a modern reissue collection
  of historic 1923-1929 recordings.
- **The Real Book** (`real-book`) / Various Artists — this is a fake-book
  (jazz lead-sheet compilation), not a commercial album. Schema fits
  awkwardly.
- **Solo Piano at WKCR, 1977** (`solo-piano-at-wkcr-1977`) / Sun Ra —
  dataset's `label: "Unknown"` (literal string) and era/genre tags
  conflict (genres list "swing", era is "fusion"). The recording date is
  1977; the Corbett vs. Dempsey release is 2019.
- **Armstrong Alumni Allstars** (`armstrong-alumni-allstars`) / Louis
  Armstrong — Armstrong died 1971. The album is a 2001 G.H.B. Records
  release by an "alumni" group (not Armstrong himself). The DNA opening
  reflects this awkwardness.

## Spotify URL coverage

See `scripts/out/spotify_fill_report.md` (created by the fill pass).

## Artist images

See `scripts/out/artist_images_report.md` (created by the repair pass).

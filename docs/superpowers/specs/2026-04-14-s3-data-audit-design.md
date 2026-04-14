# S3 — Data Audit & Album DNA

**Parent:** `2026-04-14-overhaul-master.md`
**Scope:** Album schema migration (description + significance → `albumDNA`), full re-audit of 1000 album descriptions against trusted sources, fill 54 missing Spotify URLs, repair missing and broken artist images.

All work is Python data-pipeline + a small React/TS touch-up for the type change and Album page. No new features, no visual redesign.

## 1. Album DNA schema migration

### Problem
`src/data/albums.json` has two prose fields per album: `description` (neutral "what this album is") and `significance` (editorial "why it matters"). The frontend renders them under separate headings — "About this Album" and "Why It Matters". Two fields means two ways to drift, and at least one case (Art Tatum's "In Private") has a `description` that is literally a Wikipedia paragraph about a completely unrelated Dusty Springfield single. User wants a single, combined block called "Album DNA."

### Decision (from S1 brainstorming)
**Full schema migration.** Collapse both fields into one `albumDNA` field. Remove `description` and `significance` entirely. Rollback via git if needed.

### Steps
1. Write `scripts/migrate_to_album_dna.py` that:
   - Loads `src/data/albums.json`.
   - For each album, produces `albumDNA` by combining `description` + `significance` into one coherent paragraph. **Do NOT just concatenate with a space** — rewrite so the combined prose reads as a single thought (this is an LLM-style rewrite; for a mechanical pass, concat with a sentence-boundary check, then re-audit in step 2 handles quality).
   - Writes back with only the new field. Removes `description` and `significance`.
   - Preserves all other fields untouched.
2. Update `src/types/` (find the Album interface — likely `src/types/Album.ts` or `src/types/index.ts`). Rename `description` + `significance` → `albumDNA: string`.
3. Update `src/pages/Album.tsx`:
   - Find the "About this Album" heading block and the "Why It Matters" heading block.
   - Replace with one "Album DNA" heading and a single paragraph rendering `album.albumDNA`.
   - Preserve existing Tailwind classes and spacing — match the surrounding section style.
4. Grep for any other consumers of `.description` or `.significance` in `src/` and fix them.

### Verification
- `npm run typecheck` passes (will catch any missed `.description` / `.significance` reads).
- `npm run dev` — load an album page, confirm one "Album DNA" section, no empty / duplicate sections.
- Data file: `python3 -c "import json; d=json.load(open('src/data/albums.json')); print(len(d), sum(1 for a in d if 'albumDNA' in a))"` — both numbers equal 1000.

## 2. Re-audit all 1000 album descriptions

### Problem
At least the Art Tatum / Dusty Springfield case (sample inspected during S1) shows that album `description` fields have been contaminated with text about unrelated subjects. Pattern likely caused by a prior Wikipedia-scraping pass that resolved to the wrong article for disambiguation-collision titles. Unknown how many other albums are affected. Must re-audit all 1000.

### Audit pass (detect corruptions)
Write `scripts/audit_album_descriptions.py` that, for each album:
1. Tokenize the `albumDNA` text (post-migration).
2. Check whether the artist name appears in the description. If not, flag. (Not every legitimate description mentions the artist — so this is suggestive, not definitive.)
3. Hit MusicBrainz `/release-group` or `/release` endpoint with title + artist and compare first-sentence noun phrases of the current description against MusicBrainz `annotation` field (if present) and Wikipedia abstract (via `wikipedia` Python package or direct REST).
4. Score mismatch confidence. Flag anything > 0.7 mismatch confidence as "suspected corruption."
5. Write flagged items to `scripts/out/suspected_corruptions.json` for the rewrite pass.

**Target:** catch the obvious Art Tatum-class errors. Don't pretend the audit is 100% — false negatives possible. After the rewrite pass, spot-check 50 random albums manually and report accuracy.

### Rewrite pass (regenerate clean albumDNA)
For every flagged album AND every album with very short `albumDNA` (< 60 chars), regenerate:
1. Fetch Wikipedia article via disambiguated query `"{title}" "{artist}" album`. Use the Python `wikipedia` package with auto-suggest OFF; fallback to MediaWiki search API with `srsearch="{title}" "{artist}" album`.
2. Fetch MusicBrainz release-group for release metadata + annotation.
3. Compose a 2–4 sentence `albumDNA` that combines: one sentence on what the album is (year, label, personnel or style hook), one sentence on significance or reception.
4. If no Wikipedia article exists, fall back to MusicBrainz annotation alone; if neither available, leave the existing `albumDNA` but flag the album in a `data_gaps.md` report for manual curation later.

Write the result back to `src/data/albums.json`. Preserve existing `albumDNA` for albums that passed the audit — do not over-write cleanly-written entries.

### Verification
- Spot-check 50 random albums: does the `albumDNA` discuss the correct album, by the correct artist, factually? Report accuracy rate.
- Re-inspect "In Private" by Art Tatum specifically: description must be about the 1976 solo piano recording (Pablo Records), not Dusty Springfield.
- `scripts/out/data_gaps.md` written with any albums lacking a trustworthy source.

## 3. Fill 54 missing Spotify URLs

### Problem
946/1000 albums have `spotifyUrl`. 54 missing. User is a Spotify user; every album needs a Spotify link where possible.

### Approach
Existing script pattern: `scripts/fill_spotify_urls.py` and `scripts/find_missing_spotify.py`. Reuse/extend.

### Steps
1. Identify the 54 missing: `python3 -c "import json; d=json.load(open('src/data/albums.json')); missing=[a for a in d if not a.get('spotifyUrl')]; print(len(missing)); [print(a['id'], a['title'], a['artist']) for a in missing]"`
2. For each, query Spotify Search API (`GET /v1/search?type=album&q="{title}" artist:"{artist}"`). Spotify Client Credentials flow; no user OAuth required. Store Client ID/Secret in env vars (user's recent commit `98437a2` scrubbed hardcoded secrets — do NOT regress).
3. Match the top result; verify artist name similarity ≥ 0.85 using `difflib.SequenceMatcher` before writing the URL.
4. For albums that return no confident match, leave `spotifyUrl` null and list them in the data-gaps report (user can hand-curate).

### Verification
- Count after run: ≥ 990/1000 have `spotifyUrl` (expect most 54 to resolve; a few obscure titles may not). Report the final count and the unresolved list.
- Spot-check 10 random URLs in a browser: all load the correct album.

## 4. Repair artist images

### Problem
14/315 artists have no `imageUrl`. Additionally, some existing URLs are broken — Art Tatum has a populated `imageUrl` pointing at `upload.wikimedia.org/wikipedia/commons/e/ef/Art_Tatum%2C_Vogue_Room_1948_%28Gottlieb%29.jpg`, which may be dead or return 403. User reported Art Tatum's photo is "not that hard to find" — confirming the current one doesn't render.

### Two-phase repair
**Phase A — verify existing URLs:**
1. Write `scripts/verify_artist_images.py` that HTTP HEADs every `imageUrl` in `artists.json`.
2. Flag any that return non-2xx or a non-image Content-Type.
3. Also flag any missing `imageUrl` field.

**Phase B — re-source:**
For each flagged artist:
1. Query Wikidata for the artist's entity (use `wikipedia` Python package to resolve Wikipedia article → Wikidata QID, or hit Wikidata search API with the artist name).
2. Fetch the `P18` (image) property — this returns a Commons filename.
3. Build the canonical `upload.wikimedia.org` URL: `https://upload.wikimedia.org/wikipedia/commons/{hash}/{filename}`. Use MediaWiki `imageinfo` API to get the direct URL reliably (don't hash manually).
4. HTTP HEAD the result to confirm it loads.
5. Write back to `artists.json`.
6. For artists with no Wikidata P18, fall back to scraping the Wikipedia article infobox for the first image. Known-risky — add to data-gaps report if automated path fails.

### Verification
- Every `imageUrl` in `artists.json` returns 200 + image/* content type.
- Art Tatum specifically: new URL loads a portrait.
- Run count: artists with populated + verified `imageUrl` ≥ 310/315. Remaining gaps listed.

## 5. Out of scope for S3

- No UI redesign of the Album page beyond replacing the two-heading block with one.
- No schema changes to `artists.json`, `connections.json`, `eras.json`.
- No analytics wiring — that's S4.
- Do not deprecate or merge duplicate albums even if the audit surfaces them; flag them in the gaps report.

## Completion checklist

- [ ] `scripts/migrate_to_album_dna.py` run; `albums.json` has `albumDNA` field, no `description` / `significance` fields, 1000/1000 records
- [ ] `src/types/` updated; `src/pages/Album.tsx` renders single "Album DNA" block; `npm run typecheck` passes
- [ ] Audit script run; suspected-corruption count reported in log
- [ ] Rewrite pass done; spot-check of 50 random albums reports accuracy rate (target ≥ 95%)
- [ ] "In Private" by Art Tatum specifically re-verified — not about Dusty Springfield
- [ ] Missing Spotify count reduced from 54 to the minimum achievable; data-gaps report lists unresolved
- [ ] Artist image audit complete; all populated URLs verified returning 200
- [ ] Art Tatum specifically has a working image
- [ ] `scripts/out/data_gaps.md` written for user follow-up
- [ ] `npm run typecheck` and `npm run build` pass
- [ ] `npm run dev` — visually confirm an album page and the Art Tatum artist page
- [ ] Commit(s) pushed; deploy via `npm run deploy`
- [ ] Log entry appended to `docs/superpowers/logs/2026-04-14-overhaul-log.md`
- [ ] S4 kickoff prompt written into the log

## Memory entries to create/update

At end of session:
1. **Update** `project_spotify_history.md` (currently states "253/1000 albums missing URLs"). Replace with current accurate count and note the 2026-04-14 batch-fill.
2. **Create or update** a memory capturing: "Album schema uses `albumDNA` field (one combined prose block). Old `description` and `significance` fields no longer exist as of 2026-04-14."
3. Update `MEMORY.md` index accordingly.

## S4 kickoff prompt

Write this as the final step of S3, appended to the log file under "## Next session":

```
I'm continuing the jazz site v2 overhaul. S3 is done (data audit & Album DNA).

Please read these files in order, then execute S4:
1. docs/superpowers/specs/2026-04-14-overhaul-master.md
2. docs/superpowers/specs/2026-04-14-s4-analytics-install-design.md
3. docs/superpowers/logs/2026-04-14-overhaul-log.md (for what S2 and S3 shipped)

Follow the spec exactly. At the end, update memory, append a log entry, and note that feature triage is now deferred until 2–4 weeks of analytics data accumulate. Don't ask for clarifications unless truly stuck.
```

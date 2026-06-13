# 2026-06-13 — Data Integrity Campaign (Sessions Log)

Goal: 0% hallucinated/mismatched content across artist bios and album
descriptions. Replace heuristic auditing with positive verification of every
item against fetched external evidence. Campaign state lives in
`data-integrity-checkpoints.md` (root); this log records the why per session.

## Session 1 (2026-06-13)

### Phase 0 — Research
- **What**: Mapped the disease and prior waves. Root cause (documented in
  `scripts/audit_album_descriptions.py` + `scripts/out/data_gaps.md`): prose
  scraped from Wikipedia by title-search alone → disambiguation collisions
  substituted unrelated articles. Wave 1 (2026-04-14) repaired 10 albumDNA
  corruptions; wave 2 (2026-06-12) found 5 MORE plus 10 factual errors in a
  38-claim spot-check. Each heuristic pass keeps finding more → heuristics
  can't reach 0%.
- **Why the new design**: the existing audit only cross-matches against the
  315-artist index (misses non-jazz contaminants like King Princess), never
  audited the 315 bios or 975 keyTracks lists, and the 619 stored wikipedia
  links are themselves title-search era (confirmed live: the Bix Beiderbecke
  "Singin' the Blues" link points to the 1956 pop song article; opensearch for
  "First Impressions" returns Olivia Newton-John).
- **Key asset**: 569 albums embed a MusicBrainz release MBID in their
  coverartarchive coverUrl — authoritative anchor for tracklist/date/label/
  artist credit.
- **Architecture** (12-factor: deterministic control flow, model only for
  judgment): Phase 1 fetch+cache evidence (Python, resumable) → Phase 2 judge
  agents over evidence packs (strict JSON verdicts, verbatim quotes, adversarial
  re-check of non-clean) → Phase 3 scripted repairs from evidence (auditable
  repairs JSON + sourceUrls) → Phase 4 re-verify + report. Editorial opinion is
  NOT a flag (April lesson: 6/9 candidates were editorial-style false
  positives).

### Phase 1 — Ground-truth fetch & cache
- **What**: `scripts/integrity/fetch_ground_truth.py` — per-entity JSON cache
  (gitignored) of Wikipedia full-text extracts (artists + albums) and
  MusicBrainz releases (embedded MBID for 569; confident release-group search +
  earliest-release tracklist for the rest). Evidence packs builder
  (`build_evidence_packs.py`), judge spec (`judge_instructions.md`), verdict
  aggregator (`merge_verdicts.py`).
- **Why**: judges must see resolution metadata (stored_url vs opensearch) so
  wrong-entity evidence gets discarded instead of trusted — auto-trusting
  title-matched pages is the original disease.
- **Incident**: first full run mass-429'd on Wikipedia (6 workers, no throttle;
  3-item smoke passed, 1293/1315 errored). Fix: 2 req/s gate + Retry-After
  backoff, workers 3, `--refresh-errors` re-run. Lesson recorded: smoke tests
  don't surface rate limits; throttle from the start.
- **Result**: 315 + 1000 + 1000 cached, 0 errors. 909/1000 albums with confident
  MB release (tracklist+date+label evidence); 91 low-confidence MB; 292 albums +
  5 artists without wiki page evidence (the 5: david-murray, jiro-inagaki,
  latin-jazz-quintet, leon-thomas, yuki-arimasa -- resolution misses for at least
  Murray/Thomas, queued for Phase 2.5 web research). Confirmed in evidence: the
  shipped Bix "Singin' the Blues" wikipedia link resolves to "1956 song performed
  by Guy Mitchell" -- the wrong-entity link class is real and will be caught by
  wikiLinkVerdict.
- **Next**: Phase 2 -- dispatch judge agents per pack (53), merge verdicts,
  adversarial re-check of non-clean, Phase 2.5 research for no_evidence items.

### Phase 2 -- Verification verdicts (first pass)
- **What**: 54 judge subagents (53 packs + 1 gap pack for 14 items individual
  judges skipped) judged all 1315 items against cached evidence per
  `judge_instructions.md`. Deterministic merge (`merge_verdicts.py`) ->
  `out/verdicts.json` (1315/1315, 0 missing, 0 malformed).
  Categorizer (`categorize_verdicts.py`) -> `out/repair_worklist.json`.
- **Verdict mix**: clean 733, factual_error 253, unverifiable 220,
  entity_mismatch 67, no_evidence 42. Plus 104 wrong wiki links, 78 keyTracks
  mismatches.
- **Key finding (answers the user's worry directly)**: the "unrelated /
  hallucinated" disease is real but BOUNDED. **Zero artist bios are
  entity-mismatched** -- no bio is about the wrong person. All 67 entity_mismatch
  cases are ALBUM descriptions where the title-search scraper grabbed the wrong
  article: a different-artist pop song (singin-the-blues-beiderbecke -> 1956 Guy
  Mitchell song, Wikipedia itself disclaims the Bix link), a song/composition
  article instead of the album (aint-misbehavin, nuages), or a different album by
  the same artist (the-joint-is-jumpin -> "A Handful of Keys"). 63/67 carry
  verbatim evidence quotes; judge quality spot-checked good.
- **Two merge bugs found + fixed (not re-judges)**: (1) album and artist id
  namespaces overlap -- 9 self-titled albums share a slug with their artist
  (Weather Report the band vs the album); merge now keys by `kind:id`. (2) a
  keyTracks-only mismatch is valid factual_error evidence; validation relaxed to
  accept `keyTracksVerdict=="mismatch"`. After fixes: 1315/1315 clean merge.
- **Incidents**: mid-run session-limit killed 7 album judges (verified on disk:
  5 had already written; re-dispatched the rest in waves of 8). 14 items were
  silently skipped by their judges (judge wrote 24 of 25) -- caught by the
  completeness check, collected into one gap pack, re-judged.
- **Repair worklist buckets**: entity_mismatch_albums 67, prose_factual 134,
  artist_stub_fields 57 (birthYear/deathYear/instruments placeholders rendering
  as "0-1937" on the Artist page), keytracks_mismatch 78, field_year 46 (reissue
  dates), field_label 35, field_artist 13, wrong_wiki_link 104, no_evidence 42,
  unverifiable_prose 220. 602 distinct items touched; most mechanical+verifiable.
- **Why defer repairs to a fresh session**: the judgment-call rewrites need an
  adversarial re-check gate, and the conversation had grown long (~56 agents).
  Checkpointed at this clean gate per ACE (keep utilization 40-60%).
- **Next**: Phase 3 -- adversarial re-check of the 201 judgment calls, mechanical
  fixes from cache, rewrite survivors, Phase 2.5 research for no_evidence.

### Phase 3 -- Repairs (recheck + mechanical + rewrite + research)
- **What**: Repaired the flagged set end to end. Four sub-steps, all evidence-driven,
  applied to `src/data` via one idempotent script. Net: **584 fixes across 261 albums +
  74 artists**, `out/repairs.json` (every fix: action/before/after/sourceUrl), `out/gaps.md`.
- **(a) Adversarial recheck (the gate)**: 11 skeptic subagents re-judged the 201 judgment
  calls (67 entity_mismatch + 134 prose_factual), each told to REFUTE the flag from that
  item's evidence alone. **180 upheld, 21 overturned, 0 reclassified** -> confirmed
  prose-repair set = 64 entity_mismatch albums + 97 factual_error albums + 19 factual_error
  bios. Overturns were correct triage (e.g. money-jungle/little-girl-blue year claims that
  the entity-matched Wikipedia actually supports; icp-orchestra omission = editorial, not
  error). A 30-item spot-check of `unverifiable_prose` found **0 hidden mismatches** ->
  bucket accepted as-is. Artifacts: `out/verdicts_recheck/`, `out/recheck_result.json`.
- **(b) Mechanical fixes (deterministic, cache-traceable)**: 308 fixes -- 100 wrong wiki
  links dropped, 60 keyTracks recomputed from MB tracklists, 44 deathYear + 36 birthYear +
  40 instruments from wiki leads, 15 labels (junk-only), 12 years (clear reissue gaps).
  Built proposals first, audited, then applied. Several bugs caught in audit before apply:
  group-vs-person date logic (MJQ was grabbing a member's tenure year "1952-1955"; fixed by
  detecting a birth-death paren before the first copula verb), substring instrument matches
  ("organ" in "organization"), collaborator-instrument leakage (restricted to the role
  clause), and field_label regressions (taking the embedded *reissue* label would have
  turned Prestige into OJC -- restricted to junk labels only). field_artist (13) NOT
  auto-fixed -> gaps. `build_mechanical_repairs.py` MUST run against pristine data (it diffs).
- **(c) Prose rewrites (evidence-only)**: 12 rewriter subagents + 1 recovery pass (agents
  dropped 10 items via list-truncation) rewrote all 180 confirmed items. entity_mismatch =
  full rewrite from entity-matched evidence (MB only when the wiki was the wrong entity);
  factual_error = surgical fix of just the bad claim. House style, sourceUrl per rewrite.
  7 thin-evidence stubs (no full DNA possible) flagged in gaps; spot-check found no
  hallucinations (verified "Birk's Works", "BLP 1543", etc. are in the cached evidence).
  `out/repairs_prose.json`.
- **(d) Phase 2.5 web research**: 7 subagents (WebSearch+WebFetch) resolved **40/49**
  no_evidence + name-collision items -> 105 repairs (`out/repairs_research.json`,
  `cache/websearch/`). All 7 problem artists fixed (correct disambiguated Wikipedia URLs +
  dates/instruments for Flanagan/Moody/Williams). 9 unresolved, of which **5 are catalog
  data errors** the research refused to invent toward: blue-note-4000 (a catalog range, not
  an album), investigations (no such Mehldau album), new-orleans-joys (a Morton tune, not a
  Kid Ory album), the-art-of-the-trio-vol-4-nat-king-cole (actually a Brad Mehldau album --
  wrong artist), a-smooth-one-woody-herman (mislabeled track). All in gaps.md as
  deletion/reattribution candidates.
- **Why these choices**: zero-hallucination throughout -- mechanical values trace to a
  cached field, prose/research carry sourceUrls, and every "can't verify" is named rather
  than guessed. Subagents WRITE to files (verdicts/prose/research) so 180+105 outputs never
  flood the orchestrator context (1M window stayed well under the 55% checkpoint line, so
  Phase 3 ran in one session). apply_repairs.py collapses (file,id,field) collisions into a
  single net fix (mystic-brew/real-book sit in both wrong_wiki_link and no_evidence -> the
  research URL wins over the mechanical drop) and is idempotent (re-run applies 0).
- **State after apply**: 1000/1000 albumDNA non-empty, 0/315 empty bios, all 57 flagged
  stub artists resolved (2 birthYear==0 remain OUTSIDE the flagged scope -- not Phase 3
  items). Data NOT yet built/committed -- that is Phase 4.
- **Next**: Phase 4 -- re-verify every repaired item with fresh judges, `out/integrity_report.md`,
  `npm run build`, conventional commit.

## Phase 4 -- re-verify, additional fixes, report, build, commit (2026-06-13)

- **What**: Re-verified every repaired item with FRESH blind judges, fixed what they
  legitimately caught, and produced the final integrity report. Built 14 blind re-verify
  packs (335 repaired items = current post-repair content + cached MB/wiki + websearch
  evidence) and ran them through fresh judge subagents (Workflow fan-out, file-output).
  **Wave 1 result: entity_mismatch = 0** -- the core wrong-entity disease is gone. 251
  clean, 18 acceptable-unverifiable, 13 within-gap, 53 actionable. Triaged the 53 against
  cached evidence -> **60 more evidence-backed fixes** (28 `label='Various'` -> attested
  original label, 23 reissue/remaster years -> original release year, 3 birthYears, 2
  fabricated keyTracks, 4 anachronistic compilation/track prose). Wave 2 re-judged the 42
  fixed items: 39 clean, 2 acceptable, 1 within-gap, **0 regressions**. A full-dataset sweep
  found 5 Phase-2 factual errors that slipped Phase 3: 3 fixed + wave-3 clean (earth-jones
  label->Palo Alto; gateway keyTracks were a WRONG-entity 2015 album's metal tracks ->
  replaced with the real 1976 ECM tracklist fetched live from Wikipedia; marcus-miller
  instruments trumpet->bass), 2 documented (juju recorded-1967/released-1968, township-jive
  title variant). Phase 4 added 63 fixes; **646 cumulative repairs**.
- **Final accounting (1315 items)**: clean **1014**, acceptable-unverifiable **217**,
  documented-gap **84**, unresolved **0** (0 entity-mismatch, 0 evidence-contradicting
  factual error). Report at `out/integrity_report.md`; machine summary `out/full_accounting.json`.
  `npm run build` passes (TypeScript strict, 575 modules, no errors).
- **Why these choices**: judges ran BLIND (no gap hints) so they verified honestly; gap
  reconciliation was deterministic on my side against `_gap_ids.json`, conservative (any flag
  not provably a documented gap -> regression for review). Fixed only high-confidence,
  cache-traceable defects; the original-vs-reissue label trap was respected (preferred the
  attested original, documented the 7 reissue-only cases rather than enshrine a MoFi/OJC/
  Analogue-Productions reissue label). Did NOT overclaim "0% hallucination": the 217
  unverifiable are not-contradicted (not proven clean; 196 rest on Phase-2 + the 30-item
  spot-check), and 84 gaps await human catalog decisions -- all named.
- **Artifacts**: `reconcile_reverify.py`, `consolidate_final.py`, `full_accounting.py`,
  `build_reverify_packs.py`, `build_reverify_fixes.py`, `build_gap_ids.py`;
  `out/verdicts_reverify{,2,3}/`, `out/repairs_reverify.json` (63), `out/final_status.json`,
  `out/full_accounting.json`, `out/integrity_report.md`.
- **Next**: campaign COMPLETE. Optional future work is the human-review queue in
  `gaps.md` + the Phase-4 `p4_*` gap entries (catalog deletions/reattributions, attribution
  decisions, original-vs-reissue label/year picks).

# Data Integrity Campaign -- Cross-Session Checkpoints

> Multi-session continuation file. After each phase completes, the agent appends the
> next phase's resume prompt here and pbcopy's it silently. User pastes it into a
> fresh session after /clear.
>
> Rules: append-only -- never modify historical prompts. Every prompt must be
> self-contained (a new session sees only CLAUDE.md + the pasted prompt).

## Goal

**0% hallucinated/mismatched content** across artist bios and album descriptions.
The known disease: content originally scraped from Wikipedia by title-search alone,
so disambiguation collisions substituted unrelated articles (Dusty Springfield for
Art Tatum, Diana Ross for Joel Ross, the 1956 pop song "Singing the Blues" for Bix
Beiderbecke's 1927 recording). Two prior repair waves (2026-04-14, 2026-06-12) each
found more, because the existing audit is heuristic-only. This campaign replaces
heuristics with positive verification of every item against fetched external
evidence.

**Success criterion** -- every one of these items ends in exactly one of three states:
(a) verified clean against external evidence, (b) rewritten from evidence and
re-verified clean, or (c) unverifiable claims removed, remainder verified, item
listed in the gaps report. Nothing skipped, gaps named.

Verification targets:
- `albums.json` -- albumDNA prose (1000) + year/label fields
- `albumsDetail.json` -- keyTracks (975), wikipedia links (619)
- `artistsDetail.json` -- bio (315), wikipedia links (272; 43 missing)
- `artists.json` -- birthYear/deathYear/instruments (315)

## Status

- **Phase 0 -- Research + plan**: complete (2026-06-13)
- **Phase 1 -- Ground-truth fetch & cache**: complete (2026-06-13) -- 315 artists
  + 1000 albums cached, 0 fetch errors; 909/1000 confident MB releases; packs
  built (53 files); gaps: 91 low-confidence MB, 292 albums / 5 artists no wiki page
- **Phase 2 -- Verification verdicts (first pass)**: complete (2026-06-13) --
  1315/1315 judged, 0 missing/malformed. clean 733, factual_error 253,
  unverifiable 220, entity_mismatch 67, no_evidence 42; 104 wrong wiki links, 78
  keyTracks mismatches. Artifacts: out/verdicts.json, out/verdict_summary.md,
  out/repair_worklist.json. KEY FINDING: 0 artist bios entity-mismatched; the
  disease is 67 album descriptions + a prose-error subset.
- **Phase 3 -- Repairs (adversarial recheck + fixes + rewrite)**: complete (2026-06-13) --
  584 evidence-backed fixes applied to src/data across 261 albums + 74 artists. Adversarial
  recheck upheld 180/201 judgment calls (21 demoted, 0 reclassified); spot-check of
  unverifiable_prose found 0 hidden mismatches. Breakdown: 308 mechanical (cache-traceable),
  180 prose rewrites (evidence-only), 105 research (Phase 2.5 web). apply_repairs.py is
  idempotent (collapses field collisions; re-run applies 0). 1000/1000 albumDNA non-empty,
  0 empty bios, all 57 flagged stub artists resolved. Artifacts: out/repairs.json,
  out/repairs_{mechanical,prose,research}.json, out/recheck_result.json, out/gaps.md.
  Data NOT yet built or committed (Phase 4).
- **Phase 4 -- Re-verify + final report + commit**: complete (2026-06-13) -- **CAMPAIGN
  COMPLETE.** Fresh blind judges re-verified all 335 repaired items (wave 1): entity_mismatch
  = 0. Triaged 53 actionable -> 60 evidence-backed fixes; wave 2 confirmed the 42 fixed items
  (39 clean, 2 acceptable, 1 within-gap, 0 regressions). A full-dataset sweep caught 5 Phase-2
  errors that slipped Phase 3: 3 fixed + wave-3 clean (earth-jones, gateway, marcus-miller), 2
  documented. Phase 4 added 63 fixes (646 cumulative repairs). **Final (1315 items): clean
  1014, acceptable-unverifiable 217, documented-gap 84, unresolved 0** (0 entity-mismatch, 0
  evidence-contradicting factual error). `npm run build` passes. Did NOT overclaim 0%
  hallucination: 217 unverifiable are not-contradicted (196 rest on Phase-2 + 30-item
  spot-check), 84 gaps named for human review. Report: `out/integrity_report.md`.

## Cross-cutting contracts (shared by every session)

- **Project root**: `/Users/jinsoon/Documents/Work/Music Projects/jazz_albums_recommends`
- **Read order (new session)**: CLAUDE.md -> this file's Status + contracts -> the
  phase's resume prompt -> referenced outputs under `scripts/integrity/out/`
- **Campaign workspace**: `scripts/integrity/` (scripts + `cache/` gitignored +
  `out/` tracked). Prior-wave artifacts for reference: `scripts/out/data_gaps.md`,
  `scripts/out/corruption_repairs.json`, `scripts/out/accuracy_corrections.json`,
  `scripts/audit_album_descriptions.py` (docstring documents the heuristic's limits).
- **Ground-truth anchors**: 569 albums carry a MusicBrainz release MBID inside their
  coverartarchive.org coverUrl -- authoritative for tracklist/date/label/artist.
  Wikipedia URLs in the dataset are title-search era -- NEVER trust them as anchors;
  they are themselves verification subjects.
- **Rate limits**: MusicBrainz strictly 1 req/s, single thread. Wikipedia API:
  parallel <= 6 workers, descriptive User-Agent.
- **Triage rule (April lesson)**: editorial opinion is NOT a hallucination. Only
  factual claims are flagged: names, dates, labels, personnel, track titles, places,
  chart/award facts. Prose that names sidemen but omits the leader is legitimate
  editorial style.
- **Zero-hallucination repair rule**: every rewrite carries a sourceUrl into the
  repairs JSON; rewrites compose ONLY from fetched evidence + the dataset's own
  structured fields. A judge/rewriter that lacks evidence says so -- it never guesses.
  Verdicts quoting evidence must quote verbatim.
- **House style for rewrites**: albumDNA = 2-4 sentence editorial prose, <= ~600
  chars, no emojis; bio = 2-4 sentence narrative arc (see abbey-lincoln in
  artistsDetail.json for register).
- **JSON hygiene**: data files are UTF-8, 2-space indent, `ensure_ascii=False`,
  trailing newline; key order preserved (apply scripts edit in place, never re-sort).
- **After every phase**: the 5-step handoff (TaskUpdate -> log append -> next resume
  prompt -> pbcopy + append here -> announce safe-to-/clear). Session logs live at
  `docs/superpowers/logs/2026-06-13-data-integrity-log.md`.

## Phase 2 Resume Prompt

(2026-06-13 generated, after Phase 1 completed)

```
Continue Phase 2 of the data-integrity campaign: judge all 1315 items against cached evidence.

Working directory: /Users/jinsoon/Documents/Work/Music Projects/jazz_albums_recommends

State:
- Phase 0+1 complete (2026-06-13). Ground truth cached under scripts/integrity/cache/
  (gitignored): artists/ 315, albums_mb/ 1000 (909 confident releases), albums_wiki/
  1000 (292 no page). Zero fetch errors. Stats: scripts/integrity/out/fetch_summary.json.
- Evidence packs: scripts/integrity/out/packs/ -- 13 artists_NN.json + 40 albums_NN.json
  (<=25 items each) + index.json mapping pack -> item ids.
- Campaign contracts: data-integrity-checkpoints.md (root), section "Cross-cutting
  contracts". Session log: docs/superpowers/logs/2026-06-13-data-integrity-log.md.

Before starting:
1. Read data-integrity-checkpoints.md (Status + contracts)
2. Read scripts/integrity/judge_instructions.md -- the judge spec; dispatch it by path
3. TaskList: task #2 (verdicts) should be in_progress; #3, #4 pending

Goals:
- mkdir scripts/integrity/out/verdicts. For every pack in packs/index.json, dispatch a
  judge subagent (general-purpose): prompt = follow scripts/integrity/judge_instructions.md
  exactly; input pack <pack path>; WRITE verdict JSON array to
  scripts/integrity/out/verdicts/<pack_name> (do not plan, write the file); judge ONLY
  ours-vs-evidence, never from background knowledge; return a one-line count summary.
  Parallel waves of ~8.
- python3 scripts/integrity/merge_verdicts.py must exit 0 (every item exactly one valid
  verdict). Re-dispatch missing/malformed packs until it does.
- Adversarial re-check: every non-clean verdict gets one independent skeptic agent that
  tries to REFUTE it from the same pack evidence (batch the non-clean items into recheck
  packs; output scripts/integrity/out/verdicts_recheck/). A non-clean verdict survives
  only if upheld; demotions applied deterministically (small merge script), then re-run
  merge_verdicts.py.
- Phase 2.5: items with verdict no_evidence, or entityMatch unsure/no on all evidence:
  targeted web-research agents (WebSearch + WebFetch; musicbrainz.org, discogs.com,
  artist sites, AllMusic) to fetch real evidence; save as
  scripts/integrity/cache/websearch/<id>.json with source URLs; re-judge those items.
  Known cases: artists david-murray, jiro-inagaki, latin-jazz-quintet, leon-thomas,
  yuki-arimasa (resolution misses -- David Murray and Leon Thomas certainly have pages).
- Deliverables: out/verdicts.json + out/verdict_summary.md, with honest counts per class.

Conventions: triage rule (editorial opinion is NOT a flag; absence is not contradiction;
verbatim evidence quotes required for factual_error), zero-hallucination rule, JSON
hygiene -- all in the checkpoints file contracts section.

Post-completion checklist (5 steps):
1. TaskUpdate #2 -> completed
2. Append What/Why/Next entry to docs/superpowers/logs/2026-06-13-data-integrity-log.md
3. Write Phase 3 resume prompt (committed scope: repairs from verdicts)
4. pbcopy it silently + append to data-integrity-checkpoints.md; update its Status block
5. Announce: Phase 2 complete, resume prompt in clipboard, safe to /clear
```

## Phase plan (emergent -- refine as phases complete)

1. **Ground-truth fetch & cache** -- `scripts/integrity/fetch_ground_truth.py`.
   Per artist: Wikipedia full-text extract (resolve the 43 missing via opensearch;
   validated resolution metadata stored, not auto-trusted). Per album: MB release
   by embedded MBID (569) or MB release-group search (rest) + Wikipedia article for
   stored/searched title. Cache one JSON per entity under `scripts/integrity/cache/`.
   Resumable, idempotent. Output `out/fetch_summary.json` coverage stats.
2. **Verification verdicts** -- build evidence packs (our content vs trimmed
   evidence), fan out parallel judge subagents (~25 items each, strict JSON verdict
   schema: clean | entity_mismatch | factual_error | unverifiable | no_evidence,
   with verbatim evidence quotes for non-clean). Adversarial second pass re-checks
   every non-clean verdict before it may drive a repair. Output
   `out/verdicts.json` + `out/verdict_summary.md`.
3. **Repairs** -- rewrite flagged DNA/bios from cached evidence (house style), fix
   keyTracks from MB tracklists, fix-or-drop bad wikipedia links, trim unverifiable
   claims. One auditable repairs JSON + one apply script (pattern:
   `scripts/apply_corruption_repairs.py`).
4. **Re-verify + report + commit** -- fresh judges re-verify every repaired item;
   `out/integrity_report.md` with honest counts (clean / repaired / gaps); npm run
   build passes; conventional commit.

---

## Phase 3 Resume Prompt

(2026-06-13 generated, after Phase 2 first-pass judging completed)

```
Continue Phase 3 of the data-integrity campaign: adversarially re-check the judgment-call verdicts, apply mechanical fixes, and rewrite confirmed-bad content from cached evidence.

Working directory: /Users/jinsoon/Documents/Work/Music Projects/jazz_albums_recommends

State (Phase 0-2 complete, 2026-06-13):
- Ground truth cached under scripts/integrity/cache/ (gitignored): artists/ 315,
  albums_mb/ 1000 (909 confident MB releases w/ tracklist+date+label), albums_wiki/ 1000.
- scripts/integrity/out/verdicts.json -- 1315/1315 verdicts, keyed "kind:id" (e.g.
  "album:kind-of-blue", "artist:miles-davis"; each value has .verdict .confidence
  .entityMatch .wikiLinkVerdict .keyTracksVerdict .keyTracksUnmatched .fieldIssues
  .wrongClaims .notes .kind). Mix: clean 733, factual_error 253, unverifiable 220,
  entity_mismatch 67, no_evidence 42.
- scripts/integrity/out/repair_worklist.json -- non-clean items bucketed by repair ACTION:
  entity_mismatch_albums 67, prose_factual 134, artist_stub_fields 57, field_year 46,
  field_label 35, field_artist 13, keytracks_mismatch 78, wrong_wiki_link 104,
  no_evidence 42, unverifiable_prose 220. (Buckets overlap; 602 distinct items.)
- KEY FINDING: 0 artist bios are entity-mismatched. The "hallucinated/unrelated" disease
  is 67 ALBUM descriptions (wrong-entity prose) + the prose_factual subset. Mechanical
  buckets (stub fields, keyTracks, year, label, wiki links) are data errors, not prose.
- Evidence packs at scripts/integrity/out/packs/ still hold each item's trimmed evidence
  (our content + MB release + wiki extract), keyed by bare id within artists_NN/albums_NN.

Before starting:
1. Read data-integrity-checkpoints.md (Status + Cross-cutting contracts -- esp. the
   zero-hallucination repair rule, house style, JSON hygiene, triage rule)
2. Read scripts/integrity/out/verdict_summary.md (the non-clean list + buckets)
3. Read one prior apply script for the pattern: scripts/apply_corruption_repairs.py
4. TaskList: task #3 (repairs) -> in_progress; #4 pending. THIS IS A MULTI-PHASE PHASE --
   invoke the checkpointing skill; checkpoint between sub-steps (b) and (c) if context
   passes ~55%. Re-verify (Phase 4) is a SEPARATE later session.

Goals, in order:
(a) ADVERSARIAL RE-CHECK (gate before any prose rewrite). Build recheck packs from the
    201 judgment-call verdicts (entity_mismatch_albums 67 + prose_factual 134). For each,
    a skeptic subagent gets ONLY that item's pack evidence + the verdict's claim, and must
    try to REFUTE the flag (default: uphold only if the evidence still clearly supports it;
    a wrong-entity call must point to evidence the prose describes a different entity).
    Output scripts/integrity/out/verdicts_recheck/. Deterministically demote any verdict the
    skeptic overturns (record demotions). Survivors are the confirmed prose-repair set.
    Also spot-check a ~30-item random sample of unverifiable_prose for hidden mismatches; if
    the false-negative rate is ~0, accept the bucket as "leave as-is".
(b) MECHANICAL FIXES (deterministic, from cache -- NO LLM judgment, every value traceable
    to a cached MB/wiki field; emit a repairs JSON with sourceUrl per fix, then an apply
    script that edits src/data in place preserving key order + JSON hygiene):
    - artist_stub_fields (57): fill birthYear/deathYear from the cached wiki lead
      (artists/<id>.json .page.extract first sentence dates) and instruments from the
      short description / lead. These render as "0-1937" on the Artist page TODAY -- visible
      bug. Leave a field null only if the wiki lead genuinely lacks it (list in gaps).
    - keytracks_mismatch (78): for each, recompute keyTracks from the cached MB tracklist
      (albums_mb/<id>.json .release.tracks); keep our tracks that match, replace absent ones
      with real opener/notable tracks from MB. Only when MB has a real tracklist.
    - field_year (46): replace album year with MB releaseGroup.firstReleaseDate year when
      the verdict shows ours is a reissue/comp date contradicted by MB. Keep prose's
      "Recorded in YYYY" consistent.
    - field_label (35): correct label from MB labels[].name.
    - wrong_wiki_link (104): for each, the stored wikipedia link is about a different entity.
      If the cache resolved a correct page (resolution stored_url but wrong) -> drop the link
      (set null) unless Phase 2.5/opensearch found the right one; never ship a wrong link.
    - field_artist (13): DO NOT auto-fix -- these are attribution questions (sideman vs
      leader). List them for human review in the gaps report.
(c) PROSE REWRITES (the core fix). For each confirmed entity_mismatch album + confirmed
    prose_factual album, rewrite albumDNA from cached evidence ONLY (MB release fields +
    entity-matched wiki extract), house style (2-4 sentences, <=600 chars, no emojis, no
    serifs-era flourish). Every rewrite carries sourceUrl(s) in the repairs JSON. If
    evidence is too thin to write a truthful DNA, write a minimal factual stub from MB
    (artist/title/year/label/notable tracks) and list it as a thin-evidence gap -- never
    invent. Compose deterministically where possible; use rewriter subagents that are
    handed the evidence and forbidden from adding outside facts.
(d) PHASE 2.5 RESEARCH (42 no_evidence + the 5 artist resolution misses: david-murray,
    jiro-inagaki, latin-jazz-quintet, leon-thomas, yuki-arimasa). Targeted web research
    (WebSearch + WebFetch: musicbrainz.org, discogs.com, allmusic.com, artist sites). Save
    evidence + source URLs to scripts/integrity/cache/websearch/<id>.json. Then fix or, if
    genuinely unresolvable, list in the gaps report (honest "could not verify").

Deliverables: scripts/integrity/out/repairs.json (every fix with action + before + after +
sourceUrl), apply script(s) editing src/data/{albums,albumsDetail,artists,artistsDetail}.json,
scripts/integrity/out/gaps.md (field_artist review list + thin-evidence stubs + unresolved).
Do NOT run the Phase 4 re-verify here.

Conventions: zero-hallucination repair rule, house style, triage rule, JSON hygiene -- all
in the checkpoints contracts section. Mechanical fixes must be traceable to a cached field;
prose rewrites must cite evidence; never invent; report gaps honestly.

Post-completion checklist (5 steps):
1. TaskUpdate #3 -> completed
2. Append What/Why/Next to docs/superpowers/logs/2026-06-13-data-integrity-log.md
3. Write Phase 4 resume prompt (committed scope: re-verify every repaired item with fresh
   judges, integrity_report.md, npm run build, conventional commit)
4. pbcopy it silently + append to data-integrity-checkpoints.md; update its Status block
5. Announce: Phase 3 complete, resume prompt in clipboard, safe to /clear
```

---

## Phase 4 Resume Prompt

(2026-06-13 generated, after Phase 3 repairs completed)

```
Continue Phase 4 (final) of the data-integrity campaign: re-verify every repaired item with fresh judges, write the integrity report, build, and commit.

Working directory: /Users/jinsoon/Documents/Work/Music Projects/jazz_albums_recommends

State (Phases 0-3 complete, 2026-06-13):
- Phase 3 applied 584 evidence-backed repairs to src/data across 261 albums + 74 artists, all idempotent via scripts/integrity/apply_repairs.py. Deliverables under scripts/integrity/out/:
  - repairs.json -- every applied fix (action/file/id/field/before/after/sourceUrl). repairs_{mechanical,prose,research}.json -- by source.
  - recheck_result.json -- the 180 confirmed-bad (adversarial recheck) + 21 demotions; recheck_summary.md.
  - gaps.md -- the intentional NON-fixes / human-review queue (see below).
- Ground-truth cache under scripts/integrity/cache/ (gitignored): artists/ 315, albums_mb/ 1000, albums_wiki/ 1000, websearch/ 49 (Phase 2.5). Evidence packs at scripts/integrity/out/{packs,recheck_packs,rewrite_packs,research_packs}/.
- src/data is MODIFIED but NOT committed and NOT built. All 4 files valid JSON; 1000/1000 albumDNA non-empty; 0 empty bios; all 57 flagged stub artists resolved (2 birthYear==0 remain OUTSIDE the flagged scope -- not campaign items).
- gaps.md (DO NOT treat as failures -- intentional, named): 5 catalog data errors / deletion-reattribution candidates (blue-note-4000, investigations, new-orleans-joys-kid-ory, the-art-of-the-trio-vol-4-nat-king-cole [wrong artist = Brad Mehldau], a-smooth-one-woody-herman); 13 field_artist attribution reviews; 17 year_disputed; 16 label_review; 10 weak_mb_match; 16 keyTracks-not-fixed; 5 instrument_review; 7 thin-evidence prose stubs; 4 unverifiable compilations.

Before starting:
1. Read data-integrity-checkpoints.md (Status + Cross-cutting contracts -- triage rule, zero-hallucination rule, house style, JSON hygiene).
2. Read scripts/integrity/out/gaps.md (so re-verify does NOT re-flag intentional gaps).
3. Read scripts/integrity/judge_instructions.md (the Phase 2 judge spec -- reuse it) + one recheck pack (scripts/integrity/out/recheck_packs/recheck_00.json) for the evidence shape.
4. TaskList: create Phase 4 tasks. This is the final phase. Invoke the checkpointing skill only if you split it; otherwise run straight through (1M context).

Goals, in order:
(a) RE-VERIFY every repaired item with FRESH judges (the proof that the repairs worked). Build re-verify packs: for each repaired entity (ids in repairs.json: ~261 albums + ~74 artists), bundle the CURRENT post-repair content from src/data + that item's cached evidence (reuse recheck/rewrite/research packs + cache/{artists,albums_mb,albums_wiki,websearch}). Dispatch fresh judge subagents in parallel waves (~25 items/pack) following judge_instructions.md; have them WRITE verdicts to files and return one-line summaries (keeps orchestrator context clean). Question per item: does the repaired content now MATCH the evidence (clean), or is there a REMAINING mismatch/error (regression)? Items in gaps.md are expected non-clean -- exclude them or mark "known gap", never count as failures. Deterministically merge; any genuine regression gets ONE more evidence-only rewrite (reuse rewriter_instructions.md) + re-apply (apply_repairs.py is idempotent); loop until the repaired set is clean or the residue is a documented gap. Save to scripts/integrity/out/verdicts_reverify/.
(b) INTEGRITY REPORT: scripts/integrity/out/integrity_report.md with honest counts -- total items (1315), clean-from-Phase-2, repaired-and-now-clean, still-gapped (by gaps.md category). State the outcome against the success criterion (every item ends: verified clean | rewritten & re-verified | unverifiable-claims-removed-and-listed). Name what remains unresolved; do not overclaim "0% hallucination" if gaps remain -- report the residual honestly.
(c) BUILD: npm run build must pass (TypeScript strict, no any). Fix only data-shape issues the build surfaces (e.g. a null where the type wants a string); do NOT change app code beyond what the data change requires.
(d) COMMIT: conventional commit of src/data + scripts/integrity/ (out/ tracked, cache/ gitignored) + docs/superpowers/logs/2026-06-13-data-integrity-log.md + data-integrity-checkpoints.md. Suggested message: "fix(data): zero-hallucination repair wave -- 584 evidence-backed fixes across 261 albums + 74 artists". Branch off main first if the repo requires it. Do NOT push unless asked.

Conventions: triage rule (editorial opinion is NOT a flag; absence is not contradiction), zero-hallucination (verbatim evidence quotes for any new flag), JSON hygiene (UTF-8, 2-space indent, ensure_ascii=False, trailing newline, key order preserved -- apply scripts edit in place). Re-verify judges ours-vs-evidence ONLY, never background knowledge, and never re-flags a documented gap.

Post-completion checklist:
1. TaskUpdate Phase 4 -> completed.
2. Append What/Why/Next to docs/superpowers/logs/2026-06-13-data-integrity-log.md.
3. Update data-integrity-checkpoints.md Status -> campaign COMPLETE; record final integrity_report numbers.
4. Announce the campaign outcome (clean / repaired / residual-gap counts) and that the commit is made.
```

---

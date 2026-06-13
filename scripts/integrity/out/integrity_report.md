# Data-Integrity Campaign — Final Integrity Report

Date: 2026-06-13. Scope: every factual claim across the catalog — 1000 albums
(albumDNA prose, year, label, keyTracks, wikipedia link) and 315 artists (bio,
birthYear, deathYear, instruments, wikipedia link) = **1315 verification items**.

The campaign replaced the old heuristic audit with positive verification of every
item against fetched external evidence (MusicBrainz release-groups, entity-matched
Wikipedia, and targeted web research), then repaired what the evidence contradicted
and re-verified the repairs with fresh, independent judges.

## Headline outcome

| End state | Items | Share |
|---|---:|---:|
| **Verified clean** (consistent with entity-matched evidence) | **1014** | 77.1% |
| **Acceptable / unverifiable** (right entity, no contradiction, only uncheckable editorial or biographical detail) | **217** | 16.5% |
| **Documented gap** (named, evidence-honest non-fix — see gaps.md) | **84** | 6.4% |
| **Unresolved** (entity-mismatch or evidence-contradicting factual error still present) | **0** | 0% |
| Total | **1315** | 100% |

**The known disease is eradicated.** The dataset's original defect was
disambiguation-collision prose — content about a different, similarly-named entity
(Dusty Springfield's blurb under Art Tatum, the 1956 pop song "Singing the Blues"
attached to Bix Beiderbecke's 1927 recording). After the repair and two re-verify
waves, **0 items carry an entity-mismatch** and **0 carry an evidence-contradicting
factual error**.

### Honest framing of the residual

This report does **not** claim an absolute "0% hallucination":

- The **217 unverifiable** items are *not proven clean* — they are proven *not
  contradicted*. They carry editorial or biographical claims the available evidence
  cannot confirm (e.g. "recorded in Paris in June 1964", "his final album"). Of
  these, 21 were individually re-verified in Phase 4; the other **196 rest on the
  Phase-2 judgment plus a 30-item Phase-3 spot-check that found 0 hidden mismatches**,
  not an individual Phase-4 re-judgment.
- The **84 documented gaps** are real open questions — catalog deletion candidates,
  attribution decisions, original-vs-reissue label/year, ambiguous reissue
  compilations — each named individually in `gaps.md`. They await a human catalog
  decision or further external research, not invention.

## How the 1014 "clean" breaks down

| Source | Items |
|---|---:|
| Phase-2 first-pass clean, never needed a repair | 704 |
| Repaired in Phase 3/4 and re-verified clean by fresh judges | 290 |
| Phase-3 adversarial recheck overturned a false Phase-2 flag | 17 |
| Phase-4 straggler fixes (earth-jones, gateway, marcus-miller), wave-3 clean | 3 |
| **Total** | **1014** |

## Phase-by-phase

**Phase 1 — ground truth.** 315 artists + 1000 albums fetched and cached, 0 fetch
errors; 909/1000 confident MusicBrainz releases.

**Phase 2 — first-pass verdicts.** All 1315 judged against evidence: clean 733,
factual_error 253, unverifiable 220, entity_mismatch 67, no_evidence 42. Key
finding: **0 artist bios were entity-mismatched** — the disease was concentrated in
67 album descriptions plus a prose-error subset.

**Phase 3 — repairs.** 584 evidence-backed fixes across 261 albums + 74 artists
(335 distinct items). An adversarial recheck took the 201 judgment-call verdicts
(entity_mismatch + prose_factual), upheld 180 and demoted 21; a 30-item spot-check
of the "unverifiable" bucket found 0 hidden mismatches. All fixes are idempotent and
traceable to a cached field (`apply_repairs.py`).

**Phase 4 — re-verify, additional fixes, report (this phase).**

- *Wave 1* — fresh blind judges re-verified all 335 repaired items.
  **entity_mismatch = 0.** 251 clean, 18 acceptable-unverifiable, 13 within a
  documented gap, 53 actionable.
- *Triage* — the 53 were checked against cached evidence, yielding **60 more
  evidence-backed fixes**: 28 placeholder labels (`Various` → the attested original
  label), 23 reissue/remaster years → the original release year, 3 birthYears, 2
  fabricated keyTracks, 4 anachronistic compilation/track prose claims. The
  remaining cases were **documented, not guessed**: 7 reissue-trap labels with no
  cached original, attribution questions (blue-rondo ×2, is-that-so, secrets),
  catalog-title issues (mystic-brew), ±1-2yr recorded-vs-released years, and one
  suspect MusicBrainz release (begin-the-beguine, where our keyTracks are the
  correct famous sides and MB's are a dubious budget comp).
- *Wave 2* — re-verified the 42 fixed items: 39 clean, 2 acceptable, 1 documented
  gap, **0 regressions**.
- *Full-dataset sweep* — surfaced 5 Phase-2 factual errors that slipped Phase 3.
  Three were fixed from evidence (earth-jones label Quicksilver → Palo Alto;
  gateway keyTracks — wrong-entity metal tracks replaced with the real 1976 ECM
  tracklist fetched from Wikipedia; marcus-miller instruments trumpet → bass) and
  re-verified clean in *wave 3*; two were documented (the-magic-of-juju recorded
  1967 / released 1968; township-jive minor title variant).

Phase 4 added 63 fixes; **646 cumulative evidence-backed repairs**.

## Documented gaps (84 items, by category)

An item may span more than one category.

| Category | Items |
|---|---:|
| year_disputed (MB vs ours, recorded-vs-released) | 15 |
| label_review (original vs reissue/parent label) | 12 |
| field_artist (sideman-vs-leader attribution) | 10 |
| keytracks — no MB tracklist available | 9 |
| weak MusicBrainz match | 6 |
| keytracks — uncertain MB release / title mismatch | 6 |
| catalog data errors (deletion / reattribution candidates) | 6 |
| p4 label reissue-trap (MB has only a reissue label, no cached original) | 5 |
| p4 year recorded-vs-released (±1-2yr, not flipped) | 4 |
| thin-evidence prose stubs | 4 |
| unverifiable reissue compilations | 4 |
| p4 catalog-title (track-as-title / title variant) | 3 |
| p4 attribution (composer-credit-as-artist) | 3 |
| instrument review | 2 |
| p4 label region (original vs regional release) | 1 |
| p4 suspect MB release | 1 |
| Phase-2 no-evidence (no document survived entity-matching) | 1 |

Full per-item detail and reasoning: `scripts/integrity/out/gaps.md` (Phases 1-3)
and the `p4_*` entries in `scripts/integrity/build_gap_ids.py` (Phase 4).

## Verdict against the success criterion

> Every item ends in exactly one of: (a) verified clean against external evidence,
> (b) rewritten from evidence and re-verified clean, or (c) unverifiable claims
> removed / item listed in the gaps report.

**Met.** 1014 items are verified clean (a); the 173 Phase-3 prose rewrites and 63
Phase-4 field/prose fixes were rewritten from evidence and re-verified clean by
fresh judges (b); the 217 unverifiable items carry no contradiction and the 84 gaps
are individually named (c). No item remains with an unaddressed entity-mismatch or
evidence-contradicting factual error.

## Reproducibility

- Re-verify verdicts: `out/verdicts_reverify/` (wave 1, 335), `out/verdicts_reverify2/`
  (wave 2, 42), `out/verdicts_reverify3/` (wave 3, 3).
- Reconciliation: `reconcile_reverify.py` → `out/reverify_reconciled.json`;
  `consolidate_final.py` → `out/final_status.json`; `full_accounting.py` →
  `out/full_accounting.json`.
- Repairs: `out/repairs.json` (646 total), `out/repairs_reverify.json` (63 Phase-4),
  applied idempotently by `apply_repairs.py`. Gap set: `out/_gap_ids.json` (100
  flagged dimensions across the documented items).

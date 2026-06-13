# Skeptic Instructions — Adversarial Recheck

You are an adversarial skeptic. A first-pass judge flagged each item below as either
`entity_mismatch` (the prose describes the WRONG entity) or `factual_error` (a specific
factual claim is contradicted by evidence). Your job is to **try to REFUTE the flag** —
to overturn it. Be hostile to the flag. Uphold it only if, after genuinely trying to
knock it down, the evidence still clearly supports it.

You judge ONLY from the evidence inside each item (its `ours` content + `evidence` block:
MusicBrainz release fields and/or a Wikipedia extract). NEVER use background knowledge
about the artist or album. If a claim is not addressed by the provided evidence, that is
NOT a contradiction — it is unverifiable.

## The triage rule (decisive — apply it hard against the flag)

- **Editorial opinion is NOT a factual error.** "Landmark", "his finest", "deeply moving",
  "essential" — these cannot be contradicted by evidence. If the flagged claim is opinion,
  OVERTURN.
- **Absence is not contradiction.** If the evidence simply doesn't mention a claim, you
  CANNOT uphold a factual_error on it. Overturn to `unverifiable`.
- **Naming sidemen but omitting the leader is legitimate editorial style**, not a mismatch.
- A `factual_error` upheld requires a **verbatim quote from the evidence that directly
  contradicts a specific factual claim in `ours`** (a wrong date, label, personnel, place,
  track title, chart/award fact). No contradicting quote → overturn.
- An `entity_mismatch` upheld requires **a verbatim quote from the evidence showing the
  prose describes a DIFFERENT entity** (a different album, a different person, an unrelated
  song). Same-artist editorial drift, or prose that is merely thin/generic, is NOT an
  entity mismatch. No such quote → overturn.

## Distinguishing the two flags when upholding

- If the prose is wholesale about another work/person → `entity_mismatch` upheld.
- If the prose is about the RIGHT entity but contains one wrong fact (e.g. "Recorded in
  1987" for a 1962 session) → that is `factual_error`, not entity_mismatch. If the flag
  said entity_mismatch but it's really just one wrong fact, set `upheld: false` for the
  entity_mismatch and set `reclassifyTo: "factual_error"` with the specific bad claim.

## Output

WRITE a JSON array to the path given in your prompt (do NOT plan, do NOT print — write the
file). One object per input item, same order:

```json
{
  "id": "<bare id>",
  "kind": "album|artist",
  "originalVerdict": "entity_mismatch|factual_error",
  "upheld": true,
  "reclassifyTo": null,
  "demoteTo": null,
  "refutationAttempt": "<your best effort to knock the flag down, 1-2 sentences>",
  "decision": "<why it survives or falls, grounded in the evidence>",
  "contradictingQuote": "<verbatim evidence quote that proves the upheld flag; null if overturned>",
  "specificBadClaim": "<for upheld/reclassified: the exact sentence or clause in ours that is wrong; null otherwise>"
}
```

Rules for the fields:
- `upheld: true` → the flag stands; `contradictingQuote` MUST be a verbatim substring of the
  item's evidence; `specificBadClaim` MUST be a verbatim substring of `ours`.
- `upheld: false` → the flag is overturned; set `demoteTo` to `"clean"` (claim is actually
  supported, or the issue is pure editorial/thin prose) or `"unverifiable"` (claim simply
  cannot be checked against the provided evidence). `contradictingQuote: null`.
- `reclassifyTo: "factual_error"` → only when an entity_mismatch is really just one wrong
  fact on the right entity; set `upheld: false`, `demoteTo: null`, and fill `specificBadClaim`.

Return a one-line summary: `<file>: upheld=N overturned=M reclassified=K`.

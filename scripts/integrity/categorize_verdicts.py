#!/usr/bin/env python3
"""
Phase 2 -> Phase 3 bridge: bucket every non-clean verdict into a repair worklist
keyed by the repair ACTION it needs, so Phase 3 can execute deterministically.

Buckets (an item can appear in more than one — e.g. entity_mismatch + wrong wiki
link):
  entity_mismatch_albums   rewrite albumDNA from evidence (gate: adversarial recheck)
  prose_factual            right entity, prose makes a contradicted claim — recheck + correct/trim
  artist_stub_fields       birthYear/deathYear/instruments are placeholders (0/null/[]) — fill from wiki
  field_year               album year is a reissue/comp date — correct from MB first-release-date
  field_label              album label contradicted — correct from MB
  field_artist             artist credit contradicted — investigate (attribution question)
  keytracks_mismatch       a listed keyTrack is absent from the real tracklist — fix from MB
  wrong_wiki_link          shipped wikipedia link is about a different entity — drop/replace
  no_evidence              nothing to verify against — Phase 2.5 web research
  unverifiable_prose       entity ok, claim uncheckable — review; trim only if risky

Output: scripts/integrity/out/repair_worklist.json + appends a breakdown to
verdict_summary.md.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
V = json.loads((OUT / "verdicts.json").read_text(encoding="utf-8"))


def has_field(v, name):
    return any(fi.get("field") == name for fi in v.get("fieldIssues") or [])


buckets: dict[str, list[str]] = {
    k: []
    for k in [
        "entity_mismatch_albums",
        "prose_factual",
        "artist_stub_fields",
        "field_year",
        "field_label",
        "field_artist",
        "keytracks_mismatch",
        "wrong_wiki_link",
        "no_evidence",
        "unverifiable_prose",
    ]
}

for key, v in V.items():
    verdict = v["verdict"]
    kind = v["kind"]
    if verdict == "entity_mismatch" and kind == "album":
        buckets["entity_mismatch_albums"].append(key)
    if verdict == "factual_error":
        if v.get("wrongClaims"):
            buckets["prose_factual"].append(key)
        if kind == "artist" and (
            has_field(v, "birthYear")
            or has_field(v, "deathYear")
            or has_field(v, "instruments")
        ):
            buckets["artist_stub_fields"].append(key)
        if has_field(v, "year"):
            buckets["field_year"].append(key)
        if has_field(v, "label"):
            buckets["field_label"].append(key)
        if has_field(v, "artist"):
            buckets["field_artist"].append(key)
    if v.get("keyTracksVerdict") == "mismatch" and v.get("keyTracksUnmatched"):
        buckets["keytracks_mismatch"].append(key)
    if v.get("wikiLinkVerdict") == "wrong_entity":
        buckets["wrong_wiki_link"].append(key)
    if verdict == "no_evidence":
        buckets["no_evidence"].append(key)
    if verdict == "unverifiable":
        buckets["unverifiable_prose"].append(key)

(OUT / "repair_worklist.json").write_text(
    json.dumps(buckets, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
)

lines = ["", "## Repair worklist (Phase 3 buckets)", ""]
for name, ids in buckets.items():
    lines.append(f"- **{name}**: {len(ids)}")
summary = (OUT / "verdict_summary.md").read_text(encoding="utf-8")
if "## Repair worklist" not in summary:
    (OUT / "verdict_summary.md").write_text(
        summary + "\n".join(lines) + "\n", encoding="utf-8"
    )

print("repair_worklist.json written")
for name, ids in buckets.items():
    print(f"  {name}: {len(ids)}")
total_items = len({k for ids in buckets.values() for k in ids})
print(f"distinct items needing some repair: {total_items}")
print(f"verdict mix: {dict(Counter(v['verdict'] for v in V.values()))}")

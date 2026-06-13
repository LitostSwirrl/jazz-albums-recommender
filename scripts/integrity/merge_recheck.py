"""Merge adversarial-recheck verdicts -> confirmed prose-repair set + demotions.

Reads scripts/integrity/out/verdicts_recheck/recheck_*.json (skeptic verdicts) and the
spotcheck. Upheld flags = confirmed prose-repair set. Overturned = demoted (recorded).
Reclassified entity_mismatch->factual_error stays a repair under the new class.

Outputs:
  scripts/integrity/out/recheck_result.json
  scripts/integrity/out/recheck_summary.md
"""

import glob
import json

OUT = "scripts/integrity/out"
RC = f"{OUT}/verdicts_recheck"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(o, p):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
        f.write("\n")


rows = []
for f in sorted(glob.glob(f"{RC}/recheck_*.json")):
    rows.extend(load(f))

upheld, demoted, reclassified = [], [], []
for r in rows:
    orig = r.get("originalVerdict")
    rec = {
        "id": r["id"],
        "kind": r["kind"],
        "originalVerdict": orig,
        "contradictingQuote": r.get("contradictingQuote"),
        "specificBadClaim": r.get("specificBadClaim"),
        "decision": r.get("decision"),
    }
    if r.get("upheld") is True:
        rec["repairClass"] = orig  # entity_mismatch | factual_error
        upheld.append(rec)
    elif r.get("reclassifyTo"):
        rec["repairClass"] = r["reclassifyTo"]
        reclassified.append(rec)
    else:
        demoted.append(
            {
                "id": r["id"],
                "kind": r["kind"],
                "from": orig,
                "to": r.get("demoteTo"),
                "reason": r.get("decision"),
            }
        )

repairs_set = upheld + reclassified  # all items needing a prose repair

# split for the rewrite stage
em_albums = [
    x
    for x in repairs_set
    if x["repairClass"] == "entity_mismatch" and x["kind"] == "album"
]
pf_albums = [
    x
    for x in repairs_set
    if x["repairClass"] == "factual_error" and x["kind"] == "album"
]
pf_artists = [
    x
    for x in repairs_set
    if x["repairClass"] == "factual_error" and x["kind"] == "artist"
]
other = [x for x in repairs_set if x not in em_albums + pf_albums + pf_artists]

# spotcheck
sc = load(f"{RC}/spotcheck_unverifiable.json")
sc_hits = [x for x in sc if x.get("hiddenProblem") not in (None, "none")]

result = {
    "total_rechecked": len(rows),
    "upheld": len(upheld),
    "reclassified": len(reclassified),
    "demoted": len(demoted),
    "confirmed_prose_repairs": {
        "entity_mismatch_albums": [x["id"] for x in em_albums],
        "factual_error_albums": [x["id"] for x in pf_albums],
        "factual_error_artists": [x["id"] for x in pf_artists],
        "other": [f"{x['kind']}:{x['id']}" for x in other],
    },
    "demotions": demoted,
    "spotcheck": {"sampled": len(sc), "hidden_problems": len(sc_hits), "hits": sc_hits},
    "detail": repairs_set,
}
dump(result, f"{OUT}/recheck_result.json")

lines = [
    "# Adversarial Recheck Result",
    "",
    f"- total rechecked: {len(rows)} (expected 201)",
    f"- upheld (confirmed bad): {len(upheld)}",
    f"- reclassified: {len(reclassified)}",
    f"- overturned/demoted: {len(demoted)}",
    "",
    "## Confirmed prose-repair set",
    f"- entity_mismatch albums (full rewrite): {len(em_albums)}",
    f"- factual_error albums (targeted fix): {len(pf_albums)}",
    f"- factual_error artist bios (targeted fix): {len(pf_artists)}",
    f"- other: {len(other)}",
    "",
    "## Demotions (left the prose-repair set)",
]
for d in demoted:
    lines.append(f"- {d['kind']}:{d['id']}  {d['from']} -> {d['to']}")
lines += [
    "",
    "## Spot-check of unverifiable_prose (false-negative audit)",
    f"- sampled: {len(sc)}",
    f"- hidden problems found: {len(sc_hits)}",
]
for h in sc_hits:
    lines.append(f"  - {h['id']}: {h['hiddenProblem']} — {h.get('note')}")
lines.append("")
with open(f"{OUT}/recheck_summary.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(
    f"rechecked {len(rows)} | upheld {len(upheld)} | reclass {len(reclassified)} | demoted {len(demoted)}"
)
print(
    f"  -> em_albums {len(em_albums)} | pf_albums {len(pf_albums)} | pf_artists {len(pf_artists)} | other {len(other)}"
)
print(f"spotcheck hidden problems: {len(sc_hits)}/{len(sc)}")
assert len(rows) == 201, f"expected 201 rechecked, got {len(rows)}"

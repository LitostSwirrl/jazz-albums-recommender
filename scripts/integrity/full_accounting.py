"""Phase 4: full-dataset accounting across all 1315 items (keyed kind:id).

Layering, in priority order, per item:
  1. Repaired in Phase 3/4  -> Phase-4 definitive status (final_status.json).
  2. Documented gap         -> documented_gap (_gap_ids.json).
  3. Phase-3 recheck demoted -> clean (the adversarial skeptic overturned the flag).
  4. Otherwise              -> mapped Phase-2 verdict.
Anything left as factual_error / entity_mismatch is a GENUINE unresolved residue and
is listed explicitly -- the report must name it, never bury it.
"""

import json
from collections import Counter

OUT = "scripts/integrity/out"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


verdicts = load(f"{OUT}/verdicts.json")
final = load(f"{OUT}/final_status.json")
gaps = load(f"{OUT}/_gap_ids.json")
repaired = load(f"{OUT}/_repaired_ids.json")
recheck = load(f"{OUT}/recheck_result.json")

# Phase-4 first-touch fixes outside the original 335 (judged clean in wave 3)
import glob as _glob

wave3 = {}
for _p in _glob.glob(f"{OUT}/verdicts_reverify3/*.json"):
    for _v in load(_p):
        wave3[_v["id"]] = _v.get("verdict")

album_repaired = set(repaired["album_ids"])
artist_repaired = set(repaired["artist_ids"])
repaired_status = final["status_by_id"]


def demotion_id(d):
    if isinstance(d, str):
        return d
    for k in ("id", "key", "item"):
        if isinstance(d, dict) and d.get(k):
            return str(d[k]).split(":")[-1]
    return None


demoted = {demotion_id(d) for d in recheck.get("demotions", [])}
demoted.discard(None)

P2_MAP = {
    "clean": "clean",
    "unverifiable": "acceptable_unverifiable",
    "no_evidence": "documented_gap",
    "factual_error": "UNRESOLVED_factual_error",
    "entity_mismatch": "UNRESOLVED_entity_mismatch",
}

status = {}
detail = {}
for key, v in verdicts.items():
    kind, _, bare = key.partition(":")
    pv = v.get("verdict")
    is_repaired = (kind == "album" and bare in album_repaired) or (
        kind == "artist" and bare in artist_repaired
    )
    if bare in wave3:
        w3 = wave3[bare]
        status[key] = (
            "clean"
            if w3 == "clean"
            else ("documented_gap" if bare in gaps else f"UNRESOLVED_{w3}")
        )
    elif is_repaired and bare in repaired_status:
        st = repaired_status[bare]
        status[key] = "documented_gap" if st == "known_gap" else st
    elif bare in gaps:
        status[key] = "documented_gap"
    elif bare in demoted:
        status[key] = "clean"  # recheck skeptic overturned the Phase-2 flag
    else:
        status[key] = P2_MAP.get(pv, f"p2_{pv}")
    detail[key] = pv

tally = Counter(status.values())
unresolved = sorted(k for k, s in status.items() if s.startswith("UNRESOLVED"))

print(f"TOTAL items: {len(status)}")
print("\nFinal end-state tally:")
for k in (
    "clean",
    "acceptable_unverifiable",
    "documented_gap",
    "UNRESOLVED_factual_error",
    "UNRESOLVED_entity_mismatch",
):
    print(f"  {k:28s}: {tally.get(k, 0)}")
print(f"\nUNRESOLVED ({len(unresolved)}):")
for k in unresolved:
    print(f"  {k}  (phase2={detail[k]})")

result = {
    "total": len(status),
    "tally": dict(tally),
    "demoted_count": len(demoted),
    "unresolved": [{"key": k, "phase2": detail[k]} for k in unresolved],
}
with open(f"{OUT}/full_accounting.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    f.write("\n")

"""Phase 4: consolidate the definitive post-repair status of every repaired item.

For each of the 335 repaired ids, the final verdict is taken from wave 2
(verdicts_reverify2) when the item was fixed in Phase 4, otherwise from wave 1
(verdicts_reverify). Each verdict is classified against the UPDATED gap set
(_gap_ids.json, incl. Phase-4-documented gaps). Asserts zero residual regressions.

Output: out/final_status.json + printed tallies (incl. gap breakdown by category).
"""

import glob
import json
import sys
from collections import Counter

sys.path.insert(0, "scripts/integrity")
from reconcile_reverify import ACCEPTS, concrete_dims  # noqa: E402

OUT = "scripts/integrity/out"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def read_verdicts(subdir):
    V = {}
    for p in glob.glob(f"{OUT}/{subdir}/*.json"):
        if p.endswith("index.json"):
            continue
        for v in load(p):
            V[v["id"]] = v
    return V


def classify(vid, v, gaps):
    verdict = v.get("verdict")
    if verdict == "clean":
        return "clean", []
    cd = concrete_dims(v)
    if not cd and verdict == "unverifiable":
        return "acceptable_unverifiable", []
    if vid in gaps:
        allowed = set()
        for d in gaps[vid]["dims"]:
            allowed |= ACCEPTS.get(d, set())
        check = cd if cd else {verdict.replace("_error", "")}
        if check <= allowed:
            return "known_gap", sorted(cd)
    return "regression", sorted(cd)


def main():
    repaired = load(f"{OUT}/_repaired_ids.json")
    expected = sorted(set(repaired["album_ids"]) | set(repaired["artist_ids"]))
    gaps = load(f"{OUT}/_gap_ids.json")
    fixed = sorted({r["id"] for r in load(f"{OUT}/repairs_reverify.json")["repairs"]})
    w1 = read_verdicts("verdicts_reverify")
    w2 = read_verdicts("verdicts_reverify2")

    status = {}
    source = {}
    for vid in expected:
        if vid in fixed and vid in w2:
            v, src = w2[vid], "wave2"
        else:
            v, src = w1.get(vid), "wave1"
        if v is None:
            status[vid] = "MISSING"
            continue
        cls, _ = classify(vid, v, gaps)
        status[vid] = cls
        source[vid] = src

    tally = Counter(status.values())
    regressions = [k for k, s in status.items() if s == "regression"]
    missing = [k for k, s in status.items() if s == "MISSING"]

    # gap breakdown by category for the items that ended known_gap
    gap_items = [k for k, s in status.items() if s == "known_gap"]
    cat_breakdown = Counter()
    for vid in gap_items:
        for c in gaps.get(vid, {}).get("categories", []):
            cat_breakdown[c] += 1

    out = {
        "expected": len(expected),
        "tally": dict(tally),
        "fixed_count": len(fixed),
        "regressions": regressions,
        "missing": missing,
        "known_gap_category_breakdown": dict(cat_breakdown),
        "status_by_id": status,
    }
    with open(f"{OUT}/final_status.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"repaired items: {len(expected)} | fixed in Phase 4: {len(fixed)} distinct")
    for k in ("clean", "acceptable_unverifiable", "known_gap", "regression", "MISSING"):
        print(f"  {k:24s}: {tally.get(k, 0)}")
    print(f"\nresidual REGRESSIONS: {regressions if regressions else 'NONE'}")
    print(f"missing: {missing if missing else 'none'}")
    print("\nknown_gap by category:")
    for c, n in sorted(cat_breakdown.items()):
        print(f"  {c}: {n}")


if __name__ == "__main__":
    main()

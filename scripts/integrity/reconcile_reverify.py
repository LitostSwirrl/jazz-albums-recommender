"""Phase 4: merge re-verify verdicts and reconcile against documented gaps.

Reads every verdict file in out/verdicts_reverify/, validates completeness against
the 335 repaired ids, then classifies each item by its CONCRETE flagged dimensions
(field:X from fieldIssues, keytracks, wikilink, prose from wrongClaims). The generic
verdict label is NOT a dimension -- a factual_error whose only concrete issue is a
documented gap field is a KNOWN_GAP, not a regression.

  PASS         -- verdict == clean.
  ACCEPTABLE_UNVERIFIABLE -- verdict unverifiable with NO concrete contradiction
                  (no fieldIssues, no wrongClaims): right entity, no false claim,
                  only uncheckable editorial/biographical detail. Valid end state.
  KNOWN_GAP    -- non-clean; every concrete dimension is within this id's documented
                  gap dimensions. Expected, not a failure.
  REGRESSION   -- a concrete contradiction NOT covered by a documented gap. Actionable.

Output: out/reverify_reconciled.json + a printed summary.
"""

import glob
import json
import os

OUT = "scripts/integrity/out"
VDIR = f"{OUT}/verdicts_reverify"

ACCEPTS = {
    "field:artist": {"field:artist"},
    "field:year": {"field:year"},
    "field:label": {"field:label"},
    "field:instruments": {"field:instruments"},
    "field:title": {"field:title", "prose"},
    "prose": {"prose"},
    "keytracks": {"keytracks"},
    "weak_match": {
        "unverifiable",
        "no_evidence",
        "field:year",
        "field:label",
        "keytracks",
    },
    "thin_prose": {"unverifiable", "no_evidence", "prose"},
    "unverifiable_comp": {"unverifiable", "no_evidence"},
    "catalog_error": {
        "entity",
        "unverifiable",
        "no_evidence",
        "prose",
        "keytracks",
        "field:year",
        "field:label",
        "field:artist",
        "field:title",
        "wikilink",
    },
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def concrete_dims(v: dict) -> set[str]:
    """Concrete contradiction dimensions only (verdict label is NOT a dimension)."""
    dims: set[str] = set()
    for fi in v.get("fieldIssues") or []:
        f = fi.get("field")
        if f:
            dims.add(f"field:{f}")
    if v.get("keyTracksVerdict") == "mismatch":
        dims.add("keytracks")
    if v.get("wikiLinkVerdict") == "wrong_entity":
        dims.add("wikilink")
    if v.get("wrongClaims"):
        dims.add("prose")
    return dims


def main() -> int:
    repaired = load(f"{OUT}/_repaired_ids.json")
    expected = set(repaired["album_ids"]) | set(repaired["artist_ids"])
    gaps = load(f"{OUT}/_gap_ids.json")

    verdicts: dict[str, dict] = {}
    dupes, malformed = [], []
    for path in sorted(glob.glob(f"{VDIR}/*.json")):
        if os.path.basename(path) == "index.json":
            continue
        try:
            arr = load(path)
        except Exception as e:  # noqa: BLE001
            malformed.append(f"{os.path.basename(path)}: {e}")
            continue
        if not isinstance(arr, list):
            malformed.append(f"{os.path.basename(path)}: not a list")
            continue
        for v in arr:
            vid = v.get("id")
            if vid in verdicts:
                dupes.append(vid)
            verdicts[vid] = v

    got = set(verdicts)
    missing = sorted(expected - got)
    extra = sorted(got - expected)

    passed, acceptable, known_gap, regression = [], [], [], []
    for vid in sorted(expected & got):
        v = verdicts[vid]
        verdict = v.get("verdict")
        if verdict == "clean":
            passed.append(vid)
            continue
        cd = concrete_dims(v)
        if not cd and verdict in ("unverifiable", "no_evidence"):
            # right entity, no contradiction -- only uncheckable detail
            if verdict == "unverifiable":
                acceptable.append(
                    {"id": vid, "verdict": verdict, "notes": v.get("notes")}
                )
                continue
        rec = {
            "id": vid,
            "verdict": verdict,
            "raised": sorted(cd),
            "isGap": vid in gaps,
            "gapDims": gaps.get(vid, {}).get("dims", []),
            "fieldIssues": v.get("fieldIssues"),
            "wrongClaims": v.get("wrongClaims"),
            "wikiLinkVerdict": v.get("wikiLinkVerdict"),
            "keyTracksVerdict": v.get("keyTracksVerdict"),
            "keyTracksUnmatched": v.get("keyTracksUnmatched"),
            "notes": v.get("notes"),
        }
        if vid in gaps:
            allowed: set[str] = set()
            for d in gaps[vid]["dims"]:
                allowed |= ACCEPTS.get(d, set())
            # for no_evidence/unverifiable-with-no-concrete-dim on a gap, treat verdict as the dim
            check = cd if cd else {verdict.replace("_error", "")}
            if check <= allowed:
                rec["gapCats"] = gaps[vid]["categories"]
                known_gap.append(rec)
                continue
        regression.append(rec)

    result = {
        "expected": len(expected),
        "judged": len(got & expected),
        "missing": missing,
        "extra": extra,
        "dupes": sorted(set(dupes)),
        "malformed": malformed,
        "pass_clean": len(passed),
        "acceptable_unverifiable": acceptable,
        "known_gap": known_gap,
        "regression": regression,
    }
    with open(f"{OUT}/reverify_reconciled.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"expected {len(expected)} | judged {len(got & expected)}")
    print(
        f"missing {len(missing)} | extra {len(extra)} | dupes {result['dupes']} | malformed {malformed}"
    )
    print(f"PASS clean              : {len(passed)}")
    print(
        f"ACCEPTABLE_UNVERIFIABLE : {len(acceptable)}  {[a['id'] for a in acceptable]}"
    )
    print(f"KNOWN_GAP               : {len(known_gap)}  {[k['id'] for k in known_gap]}")
    print(f"REGRESSION (actionable) : {len(regression)}")
    for r in regression:
        print(
            f"  {r['id']:55s} {r['verdict']:14s} raised={r['raised']} isGap={r['isGap']}"
        )
    return 0


if __name__ == "__main__":
    main()

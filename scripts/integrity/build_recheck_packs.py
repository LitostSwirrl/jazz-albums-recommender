"""Build adversarial-recheck packs for the 201 judgment-call verdicts.

Recheck set = entity_mismatch_albums (67) + prose_factual (134: 114 albums + 20 artist bios).
Each recheck item bundles the ORIGINAL verdict's claim with that item's pack evidence
(ours + fetched evidence). A skeptic subagent then tries to REFUTE the flag from this
evidence alone (see skeptic_instructions.md).

Also emits a random 30-item sample of unverifiable_prose for a false-negative spot-check.

Outputs:
  scripts/integrity/out/recheck_packs/recheck_NN.json   (~20 items each)
  scripts/integrity/out/recheck_packs/spotcheck_unverifiable.json
  scripts/integrity/out/recheck_packs/manifest.json
"""

import glob
import json
import os

OUT = "scripts/integrity/out"
PACKS = f"{OUT}/packs"
DEST = f"{OUT}/recheck_packs"
SEED = 20260613  # deterministic sample (no Math.random / wall-clock)


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(o, p):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
        f.write("\n")


# 1) index every pack item by "kind:id"
pack_index = {}
for pf in sorted(glob.glob(f"{PACKS}/*.json")):
    if os.path.basename(pf) == "index.json":
        continue
    data = load(pf)
    items = data if isinstance(data, list) else data.get("items", [])
    for it in items:
        pack_index[f"{it['kind']}:{it['id']}"] = it

verdicts = load(f"{OUT}/verdicts.json")  # keyed bare id? or kind:id? -> normalize
# verdicts.json keys look like bare id in some samples but summary uses kind:id.
# Detect: sample a key.
sample_key = next(iter(verdicts))
verdicts_by_kindid = {}
for k, v in verdicts.items():
    kk = k if ":" in k else f"{v.get('kind', 'album')}:{v['id']}"
    verdicts_by_kindid[kk] = v

worklist = load(f"{OUT}/repair_worklist.json")
recheck_ids = worklist["entity_mismatch_albums"] + worklist["prose_factual"]
assert len(recheck_ids) == 201, len(recheck_ids)


def build_item(kindid):
    v = verdicts_by_kindid.get(kindid)
    pk = pack_index.get(kindid)
    if v is None or pk is None:
        return None, f"missing verdict={v is None} pack={pk is None} for {kindid}"
    return {
        "id": pk["id"],
        "kind": pk["kind"],
        "originalVerdict": {
            "verdict": v.get("verdict"),
            "confidence": v.get("confidence"),
            "entityMatch": v.get("entityMatch"),
            "wikiLinkVerdict": v.get("wikiLinkVerdict"),
            "keyTracksVerdict": v.get("keyTracksVerdict"),
            "fieldIssues": v.get("fieldIssues"),
            "wrongClaims": v.get("wrongClaims"),
            "notes": v.get("notes"),
        },
        "ours": pk["ours"],
        "evidence": pk["evidence"],
    }, None


os.makedirs(DEST, exist_ok=True)
items, errs = [], []
for kindid in recheck_ids:
    it, err = build_item(kindid)
    (items if it else errs).append(it or err)

# chunk into packs of ~20, keeping entity_mismatch and prose together but ordered
CHUNK = 20
manifest = {"recheck_packs": [], "total_items": len(items), "errors": errs}
for i in range(0, len(items), CHUNK):
    chunk = items[i : i + CHUNK]
    name = f"recheck_{i // CHUNK:02d}.json"
    dump(chunk, f"{DEST}/{name}")
    manifest["recheck_packs"].append(
        {
            "file": name,
            "count": len(chunk),
            "ids": [f"{c['kind']}:{c['id']}" for c in chunk],
        }
    )

# 2) spot-check sample of unverifiable_prose (deterministic shuffle)
unv = worklist["unverifiable_prose"]
order = sorted(range(len(unv)), key=lambda i: hash((SEED, unv[i])) & 0xFFFFFFFF)
sample_ids = [unv[i] for i in order[:30]]
sample = []
for kindid in sample_ids:
    it, err = build_item(kindid)
    if it:
        # carry the original 'unverifiable' verdict note for context
        sample.append(it)
    else:
        errs.append(err)
dump(sample, f"{DEST}/spotcheck_unverifiable.json")
manifest["spotcheck_unverifiable"] = {
    "file": "spotcheck_unverifiable.json",
    "count": len(sample),
    "ids": sample_ids,
}

dump(manifest, f"{DEST}/manifest.json")
print(f"recheck items: {len(items)} (errors: {len(errs)})")
print(f"recheck packs: {len(manifest['recheck_packs'])} of ~{CHUNK}")
print(f"spotcheck: {len(sample)} unverifiable_prose items")
if errs:
    print("ERRORS:")
    for e in errs[:20]:
        print("  ", e)

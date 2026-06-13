"""Build prose-rewrite packs for the 180 confirmed-bad items (post adversarial recheck).

For each confirmed item bundle: the repair class, the specific bad claim the skeptic upheld,
which evidence is entity-matched (so the rewriter trusts MB but NOT a wrong-entity wiki),
the CURRENT content (post-mechanical-fix, from src/data), and the cached evidence.

Outputs:
  scripts/integrity/out/rewrite_packs/rewrite_NN.json   (~15 items each)
  scripts/integrity/out/rewrite_packs/manifest.json
"""

import glob
import json
import os

OUT = "scripts/integrity/out"
DATA = "src/data"
RP = f"{OUT}/recheck_packs"
DEST = f"{OUT}/rewrite_packs"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(o, p):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
        f.write("\n")


# evidence + original verdict, indexed by bare id (from the recheck packs)
pack_index = {}
for pf in glob.glob(f"{RP}/recheck_*.json"):
    for it in load(pf):
        pack_index[it["id"]] = it

result = load(f"{OUT}/recheck_result.json")
confirmed = result[
    "detail"
]  # 180 items: id, kind, repairClass, specificBadClaim, contradictingQuote, decision

albums = {a["id"]: a for a in load(f"{DATA}/albums.json")}
albumsDetail = load(f"{DATA}/albumsDetail.json")
artistsDetail = load(f"{DATA}/artistsDetail.json")

os.makedirs(DEST, exist_ok=True)
items, errs = [], []
for c in confirmed:
    aid, kind = c["id"], c["kind"]
    pk = pack_index.get(aid)
    if not pk:
        errs.append(f"no evidence pack for {kind}:{aid}")
        continue
    ov = pk.get("originalVerdict", {})
    if kind == "album":
        a = albums.get(aid)
        if not a:
            errs.append(f"album row missing {aid}")
            continue
        ours = {
            "title": a.get("title"),
            "artist": a.get("artist"),
            "year": a.get("year"),
            "label": a.get("label"),
            "albumDNA": a.get("albumDNA"),
            "keyTracks": albumsDetail.get(aid, {}).get("keyTracks"),
        }
        field, target_file = "albumDNA", "albums"
    else:
        bio = artistsDetail.get(aid, {})
        ours = {"name": pk["ours"].get("name") or aid, "bio": bio.get("bio")}
        field, target_file = "bio", "artistsDetail"
    items.append(
        {
            "id": aid,
            "kind": kind,
            "repairClass": c["repairClass"],
            "field": field,
            "targetFile": target_file,
            "specificBadClaim": c.get("specificBadClaim"),
            "contradictingQuote": c.get("contradictingQuote"),
            "skepticDecision": c.get("decision"),
            "entityMatch": ov.get("entityMatch"),
            "originalWrongClaims": ov.get("wrongClaims"),
            "originalNotes": ov.get("notes"),
            "ours": ours,
            "evidence": pk.get("evidence"),
        }
    )

# entity_mismatch first (full rewrites), then factual_error (targeted) -- keep classes grouped
items.sort(
    key=lambda x: (
        0 if x["repairClass"] == "entity_mismatch" else 1,
        x["kind"],
        x["id"],
    )
)
CHUNK = 15
manifest = {"total": len(items), "errors": errs, "packs": []}
for i in range(0, len(items), CHUNK):
    chunk = items[i : i + CHUNK]
    name = f"rewrite_{i // CHUNK:02d}.json"
    dump(chunk, f"{DEST}/{name}")
    manifest["packs"].append(
        {
            "file": name,
            "count": len(chunk),
            "ids": [f"{c['repairClass'][:2]}:{c['id']}" for c in chunk],
        }
    )
dump(manifest, f"{DEST}/manifest.json")

em = sum(1 for x in items if x["repairClass"] == "entity_mismatch")
fe_alb = sum(
    1 for x in items if x["repairClass"] == "factual_error" and x["kind"] == "album"
)
fe_art = sum(
    1 for x in items if x["repairClass"] == "factual_error" and x["kind"] == "artist"
)
print(f"rewrite items: {len(items)} (errors {len(errs)})")
print(
    f"  entity_mismatch (full): {em} | factual_error album (targeted): {fe_alb} | factual_error bio (targeted): {fe_art}"
)
print(f"  packs: {len(manifest['packs'])} of ~{CHUNK}")
for e in errs:
    print("  ERR", e)

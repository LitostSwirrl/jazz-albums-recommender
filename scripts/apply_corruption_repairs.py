"""Replace the corrupted albumDNA prose for 5 albums with researched, sourced rewrites.

The originals described the wrong artist entirely (e.g. King Oliver's entry held pop-singer
"King Princess" text; the Nancy Wilson/Cannonball entry was duplicated from "Somethin' Else").
Replacement prose + sources live in scripts/out/corruption_repairs.json.
"""

import json

DATA = "src/data"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(o, p):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
        f.write("\n")


repairs = load("scripts/out/corruption_repairs.json")["repairs"]
albums_raw = load(f"{DATA}/albums.json")
albums = albums_raw if isinstance(albums_raw, list) else albums_raw["albums"]
by_id = {a["id"]: a for a in albums}

done, missing = [], []
for r in repairs:
    a = by_id.get(r["albumId"])
    if not a:
        missing.append(r["albumId"])
        continue
    a["albumDNA"] = r["albumDNA"]
    done.append(r["albumId"])

dump(albums_raw, f"{DATA}/albums.json")

print(f"repaired: {len(done)}/{len(repairs)}")
for x in done:
    print("  ok  ", x)
if missing:
    print("MISSING:", missing)

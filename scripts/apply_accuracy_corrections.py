"""Apply the verified accuracy corrections from scripts/out/accuracy_corrections.json.

Each correction is a precise, source-backed string fix produced by the multi-source audit.
This script only does the mechanical apply + verification: it asserts the `current` value is
present before replacing, and reports loudly if any correction fails to match (which would
mean the data drifted and the correction needs a human look).

Routing: field 'bio' -> src/data/artistsDetail.json (bios were split out of artists.json);
fields 'label'/'albumDNA' -> src/data/albums.json.
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


corrections = load("scripts/out/accuracy_corrections.json")["corrections"]
albums_raw = load(f"{DATA}/albums.json")
albums = albums_raw if isinstance(albums_raw, list) else albums_raw["albums"]
by_id = {a["id"]: a for a in albums}
artist_detail = load(f"{DATA}/artistsDetail.json")

applied, failed = [], []

for c in corrections:
    aid, field, cur, new = c["albumId"], c["field"], c["current"], c["corrected"]

    if field == "bio":
        d = artist_detail.get(aid)
        if d and cur in d.get("bio", ""):
            d["bio"] = d["bio"].replace(cur, new, 1)
            applied.append((aid, field))
        else:
            failed.append((aid, field, "bio substring not found"))
        continue

    a = by_id.get(aid)
    if not a:
        failed.append((aid, field, "album id not found"))
        continue

    if field == "label":
        if a.get("label") == cur:
            a["label"] = new
            applied.append((aid, field))
        else:
            failed.append(
                (aid, field, f"label is {a.get('label')!r}, expected {cur!r}")
            )
    elif field == "albumDNA":
        if cur in a.get("albumDNA", ""):
            a["albumDNA"] = a["albumDNA"].replace(cur, new, 1)
            applied.append((aid, field))
        else:
            failed.append((aid, field, "albumDNA substring not found"))
    else:
        failed.append((aid, field, "unknown field"))

dump(albums_raw, f"{DATA}/albums.json")
dump(artist_detail, f"{DATA}/artistsDetail.json")

print(f"APPLIED: {len(applied)}/{len(corrections)}")
for x in applied:
    print("  ok  ", *x)
if failed:
    print(f"FAILED: {len(failed)}")
    for x in failed:
        print("  FAIL", *x)
else:
    print("All corrections applied cleanly.")

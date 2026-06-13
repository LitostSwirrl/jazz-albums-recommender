"""Merge + validate Phase-2.5 research repairs into repairs_research.json.

Validates schema, field->file consistency, sourceUrl presence, and pins `before` to the
current src/data value (logging drift). Collects resolved/unresolved from the websearch
cache for the gaps report.
"""

import glob
import json

OUT = "scripts/integrity/out"
DATA = "src/data"

FIELD_FILE = {
    "year": "albums",
    "label": "albums",
    "albumDNA": "albums",
    "keyTracks": "albumsDetail",
    "wikipedia": {"albumsDetail", "artistsDetail"},
    "bio": "artistsDetail",
    "birthYear": "artists",
    "deathYear": "artists",
    "instruments": "artists",
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(o, p):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
        f.write("\n")


albums = {a["id"]: a for a in load(f"{DATA}/albums.json")}
albumsDetail = load(f"{DATA}/albumsDetail.json")
artists = {a["id"]: a for a in load(f"{DATA}/artists.json")}
artistsDetail = load(f"{DATA}/artistsDetail.json")


def current(file, rid, field):
    if file == "albums":
        return albums.get(rid, {}).get(field)
    if file == "artists":
        return artists.get(rid, {}).get(field)
    if file == "albumsDetail":
        return albumsDetail.get(rid, {}).get(field)
    if file == "artistsDetail":
        return artistsDetail.get(rid, {}).get(field)
    return None


rows = []
for f in sorted(glob.glob(f"{OUT}/repairs_research/research_*.json")):
    rows.extend(load(f))

problems, noops, drift, kept = [], [], [], []
for r in rows:
    rid, fld, fil = r.get("id"), r.get("field"), r.get("file")
    exp = FIELD_FILE.get(fld)
    ok_file = (fil in exp) if isinstance(exp, set) else (fil == exp)
    if not ok_file:
        problems.append(f"{rid}.{fld}: file={fil} (expected {exp})")
        continue
    if not r.get("sourceUrl"):
        problems.append(f"{rid}.{fld}: missing sourceUrl")
        continue
    cur = current(fil, rid, fld)
    if cur != r.get("before"):
        drift.append(f"{rid}.{fld}")
        r["before"] = cur
    if r.get("before") == r.get("after"):
        noops.append(f"{rid}.{fld}")
        continue
    kept.append(r)

dump({"count": len(kept), "repairs": kept}, f"{OUT}/repairs_research.json")

# resolved/unresolved from websearch cache
results = []
for f in sorted(glob.glob("scripts/integrity/cache/websearch/*.json")):
    try:
        e = load(f)
        results.append(
            {
                "id": e.get("id"),
                "kind": e.get("kind"),
                "resolved": e.get("resolved"),
                "note": e.get("note"),
                "sources": e.get("sources", []),
            }
        )
    except Exception as ex:
        problems.append(f"bad websearch cache {f}: {ex}")
unresolved = [r for r in results if r.get("resolved") is False]
dump({"results": results, "unresolved": unresolved}, f"{OUT}/research_results.json")

by_field = {}
for r in kept:
    by_field[r["field"]] = by_field.get(r["field"], 0) + 1
print(
    f"research repairs kept: {len(kept)} (raw {len(rows)}, no-ops {len(noops)}, drift-pinned {len(drift)})"
)
print(f"  by field: {by_field}")
print(f"  websearch cache files: {len(results)} | unresolved: {len(unresolved)}")
print(f"  PROBLEMS: {len(problems)}")
for p in problems:
    print("   ", p)
print("\nUNRESOLVED (for gaps.md):")
for u in unresolved:
    print(f"  - {u['kind']}:{u['id']} — {u['note']}")

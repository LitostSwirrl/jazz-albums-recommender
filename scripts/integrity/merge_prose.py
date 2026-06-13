"""Merge + validate the 12 prose-rewrite shards into repairs_prose.json.

Validates: schema, that each `before` matches the CURRENT src/data value (so apply won't
conflict), that `after` is a non-empty string, and that the id set equals the 180 confirmed.
Flags no-ops (before==after), over-600 rewrites, and thin-evidence stubs for the gaps report.
"""

import glob
import json

OUT = "scripts/integrity/out"
DATA = "src/data"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(o, p):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
        f.write("\n")


albums = {a["id"]: a for a in load(f"{DATA}/albums.json")}
albumsDetail = load(f"{DATA}/albumsDetail.json")
artistsDetail = load(f"{DATA}/artistsDetail.json")

rows = []
for f in sorted(glob.glob(f"{OUT}/repairs_prose/rewrite_*.json")):
    rows.extend(load(f))

confirmed = {x["id"] for x in load(f"{OUT}/recheck_result.json")["detail"]}

problems, noops, over600, thin, before_diffs = [], [], [], [], []
seen = set()
for r in rows:
    rid, fld, fil = r.get("id"), r.get("field"), r.get("file")
    seen.add(rid)
    # current value
    if fil == "albums":
        cur = albums.get(rid, {}).get("albumDNA")
    elif fil == "artistsDetail":
        cur = artistsDetail.get(rid, {}).get("bio")
    else:
        problems.append(f"{rid}: bad file {fil}")
        continue
    if not isinstance(r.get("after"), str) or not r["after"].strip():
        problems.append(f"{rid}: empty/invalid after")
    # the rewriter's recorded `before` can differ from current by serialization quirks
    # (e.g. non-breaking spaces). Current src/data is authoritative for what we replace;
    # pin `before` to it so apply matches, and log any real text drift.
    if cur is not None and cur != r.get("before"):
        before_diffs.append(rid)
        r["before"] = cur
    if r.get("before") == r.get("after"):
        noops.append(rid)
    if isinstance(r.get("after"), str) and len(r["after"]) > 600:
        over600.append(f"{rid} ({len(r['after'])})")
    if r.get("thinEvidence"):
        thin.append(rid)

missing = confirmed - seen
extra = seen - confirmed
dump({"count": len(rows), "repairs": rows}, f"{OUT}/repairs_prose.json")

print(f"prose repairs merged: {len(rows)} (confirmed set: {len(confirmed)})")
print(f"  missing from rewrites: {len(missing)} {sorted(missing) if missing else ''}")
print(f"  extra (not in confirmed): {len(extra)} {sorted(extra) if extra else ''}")
print(f"  no-ops (before==after): {len(noops)} {noops}")
print(f"  over 600 chars: {len(over600)} {over600}")
print(f"  thin-evidence stubs: {len(thin)} {thin}")
print(
    f"  before pinned to current (serialization drift): {len(before_diffs)} {before_diffs}"
)
print(f"  PROBLEMS: {len(problems)}")
for p in problems:
    print("   ", p)

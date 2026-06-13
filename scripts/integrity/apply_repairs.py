"""Apply integrity repairs to src/data in place, preserving key order + JSON hygiene.

Reads every repairs_*.json source that exists (mechanical, prose, research), applies each
fix to its target file/id/field, and writes a combined scripts/integrity/out/repairs.json.

Idempotent + safe: for each fix, if the field already holds `after` it is skipped (already
applied); if it holds `before` it is applied; otherwise a CONFLICT is logged and skipped
(data drifted since the repair was computed -- never blindly overwrite).

Usage:
  python3 scripts/integrity/apply_repairs.py          # apply
  python3 scripts/integrity/apply_repairs.py --dry    # report only, write nothing
"""

import json
import sys

OUT = "scripts/integrity/out"
DATA = "src/data"
SOURCES = [
    "repairs_mechanical.json",
    "repairs_prose.json",
    "repairs_research.json",
    "repairs_reverify.json",
]
DRY = "--dry" in sys.argv


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(o, p):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
        f.write("\n")


albums = load(f"{DATA}/albums.json")
albumsDetail = load(f"{DATA}/albumsDetail.json")
artists = load(f"{DATA}/artists.json")
artistsDetail = load(f"{DATA}/artistsDetail.json")
targets = {
    "albums": {a["id"]: a for a in albums},
    "artists": {a["id"]: a for a in artists},
    "albumsDetail": albumsDetail,
    "artistsDetail": artistsDetail,
}

all_repairs = []
for src in SOURCES:
    try:
        all_repairs.extend(load(f"{OUT}/{src}")["repairs"])
    except FileNotFoundError:
        pass

# Collapse collisions on the same (file,id,field) into ONE net repair (first.before ->
# last.after), so a research-found correct wikipedia URL supersedes an earlier mechanical
# "drop to null" for the 2 albums in both wrong_wiki_link and no_evidence. Chaining the
# before/after keeps apply idempotent and drops any net no-op.
_chain = {}
for r in all_repairs:
    k = (r["file"], r["id"], r["field"])
    if k in _chain:
        merged = dict(
            r
        )  # keep the latest source's metadata (action/sourceUrl/evidence)
        merged["before"] = _chain[k]["before"]  # chain from the earliest before
        _chain[k] = merged
    else:
        _chain[k] = dict(r)
all_repairs = [r for r in _chain.values() if r["before"] != r["after"]]

valid_album_ids = set(targets["albums"])
valid_artist_ids = set(targets["artists"])
applied = skipped = conflicts = missing = created = 0
log = []
for r in all_repairs:
    table = targets.get(r["file"])
    obj = table.get(r["id"]) if table else None
    if obj is None:
        # detail files are sparse -- create an entry for a catalog item that lacks one
        # (e.g. a no_evidence album whose keyTracks were null so it had no albumsDetail row)
        if r["file"] == "albumsDetail" and r["id"] in valid_album_ids:
            obj = albumsDetail[r["id"]] = {}
            created += 1
        elif r["file"] == "artistsDetail" and r["id"] in valid_artist_ids:
            obj = artistsDetail[r["id"]] = {}
            created += 1
        else:
            missing += 1
            log.append(f"MISSING {r['file']}:{r['id']}.{r['field']}")
            continue
    cur = obj.get(r["field"])
    if cur == r["after"]:
        skipped += 1
        continue
    if cur != r["before"]:
        conflicts += 1
        log.append(
            f"CONFLICT {r['file']}:{r['id']}.{r['field']} cur={cur!r} expected_before={r['before']!r}"
        )
        continue
    if not DRY:
        obj[r["field"]] = r["after"]
    applied += 1

if not DRY:
    dump(albums, f"{DATA}/albums.json")
    dump(albumsDetail, f"{DATA}/albumsDetail.json")
    dump(artists, f"{DATA}/artists.json")
    dump(artistsDetail, f"{DATA}/artistsDetail.json")
    dump({"count": len(all_repairs), "repairs": all_repairs}, f"{OUT}/repairs.json")

print(
    f"{'DRY-RUN ' if DRY else ''}repairs: {len(all_repairs)} | applied {applied} | "
    f"already-applied {skipped} | created-detail {created} | conflicts {conflicts} | missing {missing}"
)
for line in log[:40]:
    print("  ", line)

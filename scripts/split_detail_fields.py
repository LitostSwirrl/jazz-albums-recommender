"""Split detail-only fields out of the eagerly-bundled catalog into lazy detail files.

Moves album keyTracks/wikipedia/reviews and artist bio/wikipedia (consumed only by the
already-lazy Album.tsx / Artist.tsx routes) into albumsDetail.json / artistsDetail.json.
Because those pages import the detail files statically, Rollup places the heavy fields in
the lazy route chunks instead of the initial bundle -- no async loading required.

Idempotent-ish: re-running after a split simply finds the fields already gone. Backs up
the originals to scripts/out/ before writing.
"""

import json
import os
import shutil

DATA = "src/data"
OUT = "scripts/out"
os.makedirs(OUT, exist_ok=True)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


# --- Backups -------------------------------------------------------------
shutil.copy(f"{DATA}/albums.json", f"{OUT}/albums_pre_split_backup.json")
shutil.copy(f"{DATA}/artists.json", f"{OUT}/artists_pre_split_backup.json")

# --- Albums: keyTracks, wikipedia, reviews -> albumsDetail.json -----------
albums_raw = load(f"{DATA}/albums.json")
albums = albums_raw if isinstance(albums_raw, list) else albums_raw["albums"]
album_detail = {}
for a in albums:
    d = {}
    kt = a.pop("keyTracks", None)
    if kt:
        d["keyTracks"] = kt
    wk = a.pop("wikipedia", None)
    if wk:
        d["wikipedia"] = wk
    rv = a.pop("reviews", None)
    if rv:
        d["reviews"] = rv
    if d:
        album_detail[a["id"]] = d

# --- Artists: bio, wikipedia -> artistsDetail.json ------------------------
artists_raw = load(f"{DATA}/artists.json")
artists = artists_raw if isinstance(artists_raw, list) else artists_raw["artists"]
artist_detail = {}
for a in artists:
    d = {}
    bio = a.pop("bio", None)
    if bio is not None:
        d["bio"] = bio
    wk = a.pop("wikipedia", None)
    if wk:
        d["wikipedia"] = wk
    if d:
        artist_detail[a["id"]] = d

dump(albums_raw, f"{DATA}/albums.json")
dump(artists_raw, f"{DATA}/artists.json")
dump(album_detail, f"{DATA}/albumsDetail.json")
dump(artist_detail, f"{DATA}/artistsDetail.json")


def kb(path):
    return f"{os.path.getsize(path) / 1024:.0f}K"


print("slim albums.json     ", kb(f"{DATA}/albums.json"))
print("slim artists.json    ", kb(f"{DATA}/artists.json"))
print(
    "albumsDetail.json    ",
    kb(f"{DATA}/albumsDetail.json"),
    f"({len(album_detail)} entries)",
)
print(
    "artistsDetail.json   ",
    kb(f"{DATA}/artistsDetail.json"),
    f"({len(artist_detail)} entries)",
)

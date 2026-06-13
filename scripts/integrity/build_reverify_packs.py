"""Phase 4: assemble RE-VERIFY packs for fresh judges.

Each item pairs the CURRENT post-repair content from src/data (the proof subject)
with the same cached external evidence Phase 2 used, PLUS Phase-2.5 websearch
evidence where it exists. Packs are deliberately BLIND -- no gap tags, identical in
shape to Phase 2 packs -- so judges verify ours-vs-evidence honestly. Gap
reconciliation happens downstream against out/_gap_ids.json.

Scope: only the 335 repaired entities (out/_repaired_ids.json). Output:
out/reverify_packs/{albums,artists}_NN.json + index.json.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_evidence_packs as bep  # noqa: E402

OUT = HERE / "out"
PACKS = OUT / "reverify_packs"
WEBSEARCH = bep.CACHE / "websearch"


def attach_websearch(item: dict) -> dict:
    p = WEBSEARCH / f"{item['id']}.json"
    if not p.exists():
        return item
    rec = json.loads(p.read_text(encoding="utf-8"))
    item["evidence"]["websearch"] = {
        "resolved": rec.get("resolved"),
        "sources": rec.get("sources"),
        "findings": rec.get("findings"),
        "note": rec.get("note"),
    }
    return item


def write_packs(items: list[dict], prefix: str, index: dict) -> None:
    for n in range(0, len(items), bep.PACK_SIZE):
        chunk = items[n : n + bep.PACK_SIZE]
        name = f"{prefix}_{n // bep.PACK_SIZE:02d}.json"
        (PACKS / name).write_text(
            json.dumps(chunk, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        index[name] = [c["id"] for c in chunk]


def main() -> int:
    repaired = json.loads((OUT / "_repaired_ids.json").read_text(encoding="utf-8"))
    album_ids = set(repaired["album_ids"])
    artist_ids = set(repaired["artist_ids"])

    albums = bep.load(bep.DATA / "albums.json")
    artists = bep.load(bep.DATA / "artists.json")
    albums_detail = bep.load(bep.DATA / "albumsDetail.json")
    artists_detail = bep.load(bep.DATA / "artistsDetail.json")
    PACKS.mkdir(parents=True, exist_ok=True)

    album_items = [
        attach_websearch(
            bep.album_item(
                a,
                albums_detail,
                bep.cached("albums_mb", a["id"]),
                bep.cached("albums_wiki", a["id"]),
            )
        )
        for a in albums
        if a["id"] in album_ids
    ]
    artist_items = [
        attach_websearch(
            bep.artist_item(a, artists_detail, bep.cached("artists", a["id"]))
        )
        for a in artists
        if a["id"] in artist_ids
    ]

    # completeness: every repaired id must appear in exactly one pack
    got_albums = {i["id"] for i in album_items}
    got_artists = {i["id"] for i in artist_items}
    missing_alb = album_ids - got_albums
    missing_art = artist_ids - got_artists
    if missing_alb or missing_art:
        print(
            f"WARNING missing albums {sorted(missing_alb)}; artists {sorted(missing_art)}"
        )

    index: dict[str, list[str]] = {}
    write_packs(album_items, "albums", index)
    write_packs(artist_items, "artists", index)
    (PACKS / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    ws = sum(1 for i in album_items + artist_items if "websearch" in i["evidence"])
    print(
        f"reverify packs: {len(index)} files, {len(album_items)} albums + "
        f"{len(artist_items)} artists ({len(album_items) + len(artist_items)} total)"
    )
    print(f"items with websearch evidence attached: {ws}")
    return 0


if __name__ == "__main__":
    main()

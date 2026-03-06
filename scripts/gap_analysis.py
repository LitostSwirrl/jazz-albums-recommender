#!/usr/bin/env python3
"""
Gap analysis script for jazz albums recommender.
Identifies underrepresented eras, artists with few albums,
missing keyAlbums, and genre coverage gaps.
Output: scripts/gap_analysis_report.md
"""
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).parent.parent
ALBUMS_FILE = ROOT / "src" / "data" / "albums.json"
ARTISTS_FILE = ROOT / "src" / "data" / "artists.json"
OUTPUT_FILE = Path(__file__).parent / "gap_analysis_report.md"

ERA_ORDER = [
    "early-jazz", "swing", "bebop", "cool-jazz",
    "hard-bop", "free-jazz", "fusion", "contemporary",
]
ERA_TARGET = 125  # target albums per era
ARTIST_FEW_ALBUMS = 2  # flag artists with <= this many albums
GENRE_MIN_ALBUMS = 20  # flag genres with < this many albums


def main() -> None:
    with open(ALBUMS_FILE) as f:
        albums: list[dict] = json.load(f)
    with open(ARTISTS_FILE) as f:
        artists: list[dict] = json.load(f)

    album_ids = {a["id"] for a in albums}
    album_by_era: Counter = Counter(a["era"] for a in albums)
    album_by_genre: Counter = Counter(
        g for a in albums for g in a.get("genres", [])
    )
    album_by_artist: Counter = Counter(a.get("artistId") for a in albums)

    lines: list[str] = [
        "# Gap Analysis Report",
        "",
        f"Analyzing {len(albums)} albums across {len(artists)} artists.",
        "",
    ]

    # 1. Under-represented eras
    lines.append("## Under-Represented Eras")
    lines.append("")
    lines.append(f"Target: {ERA_TARGET} albums per era")
    lines.append("")
    any_gap = False
    for era in ERA_ORDER:
        count = album_by_era.get(era, 0)
        gap = ERA_TARGET - count
        status = "OK" if gap <= 0 else f"NEEDS +{gap}"
        lines.append(f"- `{era}`: {count} albums — {status}")
        if gap > 0:
            any_gap = True
    if not any_gap:
        lines.append("")
        lines.append("All eras meet the target.")
    lines.append("")

    # 2. Artists with few albums (1-2 in collection)
    lines.append(f"## Artists with {ARTIST_FEW_ALBUMS} or Fewer Albums in Collection")
    lines.append("")
    few = [
        a for a in artists
        if album_by_artist.get(a["id"], 0) <= ARTIST_FEW_ALBUMS
        and a["id"] != "various-artists"
    ]
    few.sort(key=lambda a: album_by_artist.get(a["id"], 0))
    for artist in few[:50]:  # cap at 50 to keep report readable
        count = album_by_artist.get(artist["id"], 0)
        lines.append(f"- **{artist['name']}** (`{artist['id']}`): {count} album(s) in collection")
    if len(few) > 50:
        lines.append(f"- … and {len(few) - 50} more")
    lines.append("")

    # 3. Missing keyAlbums (artist.keyAlbums not yet in collection)
    lines.append("## Missing keyAlbums (artist references not in collection)")
    lines.append("")
    missing_map: dict[str, list[str]] = {}
    for artist in artists:
        missing = [kid for kid in artist.get("keyAlbums", []) if kid not in album_ids]
        if missing:
            missing_map[artist["name"]] = missing
    if missing_map:
        for name, ids in sorted(missing_map.items()):
            lines.append(f"- **{name}**: {', '.join(f'`{i}`' for i in ids)}")
    else:
        lines.append("All keyAlbums are present in the collection.")
    lines.append("")

    # 4. Genre coverage gaps
    lines.append(f"## Genres with Fewer than {GENRE_MIN_ALBUMS} Albums")
    lines.append("")
    sparse = [(g, c) for g, c in album_by_genre.most_common() if c < GENRE_MIN_ALBUMS]
    sparse.sort(key=lambda x: x[1])
    if sparse:
        for genre, count in sparse:
            lines.append(f"- `{genre}`: {count} album(s)")
    else:
        lines.append("All genres meet the minimum threshold.")
    lines.append("")

    # 5. Summary
    lines.insert(3, f"**Gaps found:** {len(few)} artists with few albums, "
                    f"{len(missing_map)} artists with missing keyAlbums, "
                    f"{len(sparse)} sparse genres")
    lines.insert(4, "")

    OUTPUT_FILE.write_text("\n".join(lines))
    print(f"Report written to {OUTPUT_FILE}")
    print(f"  Artists with few albums: {len(few)}")
    print(f"  Artists with missing keyAlbums: {len(missing_map)}")
    print(f"  Sparse genres: {len(sparse)}")


if __name__ == "__main__":
    main()

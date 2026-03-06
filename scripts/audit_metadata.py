#!/usr/bin/env python3
"""
Metadata audit script for jazz albums recommender.
Detects and reports data quality issues grouped by type.
Output: scripts/metadata_audit_report.md
"""
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
ALBUMS_FILE = ROOT / "src" / "data" / "albums.json"
ARTISTS_FILE = ROOT / "src" / "data" / "artists.json"
ERAS_FILE = ROOT / "src" / "data" / "eras.json"
OUTPUT_FILE = Path(__file__).parent / "metadata_audit_report.md"

# Regexes matching boilerplate auto-generated text
TEMPLATE_DESC = re.compile(
    r"^.{10,60} is a .{5,40} (album|record) by .{5,40} from \d{4}",
    re.IGNORECASE,
)
TEMPLATE_SIG = re.compile(
    r"^A .{5,40} (entry|album|recording) from \d{4}",
    re.IGNORECASE,
)

# Map genres to eras (mirrors discovery.ts logic)
EXEMPT_ERAS = {"early-jazz", "swing"}
LINK_FIELDS = ["spotifyUrl", "appleMusicUrl", "youtubeMusicUrl", "youtubeUrl"]

# Map genres to eras (mirrors discovery.ts logic)
GENRE_ERA_MAP: dict[str, str] = {
    "dixieland": "early-jazz",
    "new orleans jazz": "early-jazz",
    "ragtime": "early-jazz",
    "blues": "early-jazz",
    "swing": "swing",
    "big band": "swing",
    "stride piano": "swing",
    "bebop": "bebop",
    "hard bop": "hard-bop",
    "post-bop": "hard-bop",
    "soul jazz": "hard-bop",
    "cool jazz": "cool-jazz",
    "west coast jazz": "cool-jazz",
    "third stream": "cool-jazz",
    "free jazz": "free-jazz",
    "avant-garde": "free-jazz",
    "experimental": "free-jazz",
    "jazz fusion": "fusion",
    "electric jazz": "fusion",
    "jazz funk": "fusion",
    # "contemporary jazz" excluded — used too broadly across all eras
    "nu jazz": "contemporary",
    "jazz rap": "contemporary",
}

ERA_ORDER = [
    "early-jazz", "swing", "bebop", "cool-jazz",
    "hard-bop", "free-jazz", "fusion", "contemporary",
]


def era_distance(a: str, b: str) -> int:
    try:
        return abs(ERA_ORDER.index(a) - ERA_ORDER.index(b))
    except ValueError:
        return 0


def main() -> None:
    with open(ALBUMS_FILE) as f:
        albums: list[dict] = json.load(f)
    with open(ARTISTS_FILE) as f:
        artists: list[dict] = json.load(f)

    album_ids = {a["id"] for a in albums}
    artist_ids = {a["id"] for a in artists}

    issues: dict[str, list[dict]] = defaultdict(list)

    for album in albums:
        # 0. Broken artistId (no matching artist entry)
        artist_id = album.get("artistId", "")
        if artist_id and artist_id not in artist_ids:
            issues["broken_artist_id"].append({
                "id": album.get("id", "?"),
                "title": album.get("title", "?"),
                "artist": album.get("artist", "?"),
                "artistId": artist_id,
            })
        aid = album.get("id", "?")
        title = album.get("title", "?")
        artist = album.get("artist", "?")

        # 1. Missing year
        year = album.get("year")
        if not year:
            issues["missing_year"].append({"id": aid, "title": title, "artist": artist})

        # 2. Missing cover URL
        cover = album.get("coverUrl", "")
        if not cover or not cover.startswith("http"):
            issues["missing_cover"].append({"id": aid, "title": title, "artist": artist})

        # 3. Empty key tracks
        if not album.get("keyTracks"):
            issues["empty_key_tracks"].append({"id": aid, "title": title, "artist": artist})

        # 4. Template description
        desc = album.get("description", "")
        if TEMPLATE_DESC.match(desc):
            issues["template_description"].append({
                "id": aid, "title": title, "artist": artist,
                "snippet": desc[:100] + "…",
            })

        # 5. Template significance
        sig = album.get("significance", "")
        if TEMPLATE_SIG.match(sig):
            issues["template_significance"].append({
                "id": aid, "title": title, "artist": artist,
                "snippet": sig[:100] + "…",
            })

        # 6. Missing streaming links (non-exempt eras only)
        era = album.get("era", "")
        if era not in EXEMPT_ERAS and not any(album.get(f) for f in LINK_FIELDS):
            issues["missing_streaming_links"].append({"id": aid, "title": title, "artist": artist, "era": era})

        # 7. Genre/era mismatch (genre suggests era 3+ positions away, to reduce false positives)
        # "contemporary jazz" is excluded — it's used loosely across all eras
        genres = album.get("genres", [])
        for genre in genres:
            mapped = GENRE_ERA_MAP.get(genre.lower())
            if mapped and era_distance(era, mapped) >= 4:
                issues["era_mismatch"].append({
                    "id": aid, "title": title, "artist": artist,
                    "era": era, "genre": genre, "genre_era": mapped,
                })
                break  # one flag per album is enough

    # 7. Missing keyAlbums on artists (artist references album IDs not in collection)
    for artist in artists:
        missing = [
            kid for kid in artist.get("keyAlbums", [])
            if kid not in album_ids
        ]
        if missing:
            issues["artist_missing_key_albums"].append({
                "id": artist["id"], "name": artist["name"],
                "missing": missing,
            })

    # Write report
    lines: list[str] = [
        "# Metadata Audit Report",
        "",
        f"Generated from {len(albums)} albums and {len(artists)} artists.",
        "",
    ]

    def section(key: str, title: str, row_fn) -> None:
        rows = issues[key]
        lines.append(f"## {title} ({len(rows)})")
        lines.append("")
        if not rows:
            lines.append("No issues found.")
        else:
            for row in rows:
                lines.append(row_fn(row))
        lines.append("")

    section(
        "broken_artist_id", "Broken artistId (no matching artist entry)",
        lambda r: f"- `{r['id']}` — **{r['title']}** by {r['artist']} (artistId: `{r['artistId']}`)",
    )
    section(
        "missing_streaming_links", "Missing Streaming Links (non-exempt eras)",
        lambda r: f"- `{r['id']}` — **{r['title']}** by {r['artist']} [{r['era']}]",
    )
    section(
        "missing_year", "Missing Year",
        lambda r: f"- `{r['id']}` — **{r['title']}** by {r['artist']}",
    )
    section(
        "missing_cover", "Missing Cover URL",
        lambda r: f"- `{r['id']}` — **{r['title']}** by {r['artist']}",
    )
    section(
        "empty_key_tracks", "Empty Key Tracks",
        lambda r: f"- `{r['id']}` — **{r['title']}** by {r['artist']}",
    )
    section(
        "template_description", "Template / Boilerplate Description",
        lambda r: f"- `{r['id']}` — **{r['title']}**\n  > {r['snippet']}",
    )
    section(
        "template_significance", "Template / Boilerplate Significance",
        lambda r: f"- `{r['id']}` — **{r['title']}**\n  > {r['snippet']}",
    )
    section(
        "era_mismatch", "Genre/Era Mismatch (genre suggests different era)",
        lambda r: f"- `{r['id']}` — **{r['title']}** tagged `{r['era']}` but genre `{r['genre']}` → `{r['genre_era']}`",
    )
    section(
        "artist_missing_key_albums", "Artist keyAlbums Not in Collection",
        lambda r: f"- `{r['id']}` — **{r['name']}**: {', '.join(r['missing'])}",
    )

    total = sum(len(v) for v in issues.values())
    lines.insert(3, f"**Total issues: {total}**")
    lines.insert(4, "")

    OUTPUT_FILE.write_text("\n".join(lines))
    print(f"Report written to {OUTPUT_FILE}")

    # Summary to stdout
    for key, rows in issues.items():
        print(f"  {key}: {len(rows)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Duplicate album detector.
Groups albums by normalized title + artist and reports near-duplicates
with a data completeness score to help decide which entry to keep.
Output: scripts/duplicates_report.md
"""
import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
ALBUMS_FILE = ROOT / "src" / "data" / "albums.json"
OUTPUT_FILE = Path(__file__).parent / "duplicates_report.md"

SCORED_FIELDS = ["coverUrl", "spotifyUrl", "appleMusicUrl", "youtubeMusicUrl", "youtubeUrl", "wikipedia"]


def normalize(text: str) -> str:
    """Normalize title for comparison — strips quotes, dashes, diacritics."""
    # Curly/smart quotes → straight
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    # En/em dash → hyphen
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    # Remove all non-alphanumeric
    text = re.sub(r"[^a-z0-9\s]", "", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def completeness_score(album: dict) -> int:
    score = sum(1 for f in SCORED_FIELDS if album.get(f))
    score += 1 if album.get("keyTracks") else 0
    score += 1 if album.get("reviews") else 0
    return score


def main() -> None:
    with open(ALBUMS_FILE) as f:
        albums: list[dict] = json.load(f)

    # Group by (normalized_artist, normalized_title)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for album in albums:
        key = (normalize(album.get("artist", "")), normalize(album.get("title", "")))
        groups[key].append(album)

    duplicates = {k: v for k, v in groups.items() if len(v) > 1}

    lines = [
        "# Duplicate Albums Report",
        "",
        f"Found **{len(duplicates)}** duplicate groups across {len(albums)} albums.",
        "",
    ]

    for (artist_norm, title_norm), entries in sorted(duplicates.items()):
        lines.append(f"## {entries[0]['artist']} — {entries[0]['title']}")
        lines.append("")
        lines.append(f"Normalized key: `{artist_norm}` / `{title_norm}`")
        lines.append("")
        for e in sorted(entries, key=completeness_score, reverse=True):
            score = completeness_score(e)
            marker = " **← KEEP**" if e == sorted(entries, key=completeness_score, reverse=True)[0] else " ← remove"
            lines.append(f"- `{e['id']}` (score {score}){marker}")
            lines.append(f"  - Title: {e['title']!r}")
            lines.append(f"  - Year: {e.get('year')}")
            for f in SCORED_FIELDS:
                if e.get(f):
                    lines.append(f"  - {f}: ✓")
            kt = e.get("keyTracks", [])
            lines.append(f"  - keyTracks: {len(kt)}")
        lines.append("")

    OUTPUT_FILE.write_text("\n".join(lines))
    print(f"Report written to {OUTPUT_FILE}")
    print(f"Found {len(duplicates)} duplicate groups:")
    for (_, title_norm), entries in sorted(duplicates.items()):
        ids = [e["id"] for e in entries]
        print(f"  {entries[0]['artist']}: {ids}")


if __name__ == "__main__":
    main()

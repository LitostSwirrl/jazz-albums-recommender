"""RYM chart validator: validates hand-captured RateYourMusic chart JSON
files (one per chart slug, saved by a one-time assisted browser-capture
session -- Task 8 in the recs pipeline plan) and writes a normalized
cache/rym.json.

Every chart file at cache/rym_charts/<slug>.json must be a JSON array of
entries: {"rank": int, "artist": str, "album": str, "year": int-or-null,
"rating": float, "rating_count": int}. Any entry failing the contract (rank
int, artist/album non-empty str, rating float in 0-5, rating_count int > 0)
fails the whole run loud -- naming the chart slug and rank -- before any
output is written. Zero chart files is a loud failure too: nothing to
validate is an error, not a silent success.

Run: python3 -m scripts.recs.validate_rym
"""

import sys
from pathlib import Path

from scripts.recs import common

CHARTS_DIR = common.CACHE / "rym_charts"
OUTPUT_PATH = common.CACHE / "rym.json"


def _fail_loud(message: str) -> None:
    """Never write output on a bad run: print the reason, exit 1."""
    print(f"VALIDATION FAILURE: {message}")
    sys.exit(1)


def _is_int(value) -> bool:
    """bool is a subclass of int in Python -- exclude it explicitly so a
    stray true/false in captured data doesn't pass as a valid rank/count."""
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_and_normalize(entry: dict, slug: str) -> dict:
    rank = entry.get("rank")
    if not _is_int(rank):
        _fail_loud(f"rym chart '{slug}' rank {rank!r}: rank must be an int")

    artist = entry.get("artist")
    if not isinstance(artist, str) or not artist.strip():
        _fail_loud(
            f"rym chart '{slug}' rank {rank!r}: artist must be a non-empty string"
        )

    album = entry.get("album")
    if not isinstance(album, str) or not album.strip():
        _fail_loud(
            f"rym chart '{slug}' rank {rank!r}: album must be a non-empty string"
        )

    rating = entry.get("rating")
    if not isinstance(rating, float):
        _fail_loud(f"rym chart '{slug}' rank {rank!r}: rating must be a float")
    if not (0 <= rating <= 5):
        _fail_loud(
            f"rym chart '{slug}' rank {rank!r}: rating {rating!r} out of 0-5 range"
        )

    rating_count = entry.get("rating_count")
    if not _is_int(rating_count):
        _fail_loud(f"rym chart '{slug}' rank {rank!r}: rating_count must be an int")
    if rating_count <= 0:
        _fail_loud(
            f"rym chart '{slug}' rank {rank!r}: "
            f"rating_count {rating_count!r} must be > 0"
        )

    return {
        "rank": rank,
        "norm_key": common.norm_key(artist, album),
        "artist": artist,
        "title": album,
        "year": entry.get("year"),
        "rating": rating,
        "rating_count": rating_count,
    }


def validate_charts(charts_dir: Path) -> dict[str, list[dict]]:
    """Load + validate every <slug>.json in charts_dir, return
    {slug: [normalized entries]}. Fails loud (exit 1) on the first invalid
    entry, or if charts_dir has no chart files at all."""
    chart_files = sorted(charts_dir.glob("*.json"))
    if not chart_files:
        _fail_loud(f"no chart files found in {charts_dir}")

    charts: dict[str, list[dict]] = {}
    for path in chart_files:
        slug = path.stem
        entries = common.load_json(path)
        charts[slug] = [_validate_and_normalize(entry, slug) for entry in entries]

    return charts


def _print_summary(charts: dict[str, list[dict]]) -> None:
    for slug, entries in charts.items():
        print(f"{slug}: {len(entries)} entries")


def main() -> None:
    charts = validate_charts(CHARTS_DIR)

    common.CACHE.mkdir(parents=True, exist_ok=True)
    common.save_json(OUTPUT_PATH, {"charts": charts})
    _print_summary(charts)


if __name__ == "__main__":
    main()

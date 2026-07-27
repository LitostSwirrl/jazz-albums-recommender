"""RYM chart validator: validates hand-captured RateYourMusic chart JSON
files (one per chart slug, saved by a one-time assisted browser-capture
session -- Task 8 in the recs pipeline plan) and writes a normalized
cache/rym.json.

Every chart file at cache/rym_charts/<slug>.json must be a JSON array of
entries: {"rank": int, "artist": str, "album": str, "year": int-or-null,
"rating": number (int or float), "rating_count": int}. Any entry failing the
contract (rank int; artist/album non-empty str; rating a number in 0-5;
rating_count int > 0; year int or null) fails the whole run loud -- naming
the chart slug and rank -- before any output is written. Zero chart files is
a loud failure too: nothing to validate is an error, not a silent success.

Run: python3 -m scripts.recs.validate_rym
"""

import sys

from scripts.recs import common


def _is_int(value) -> bool:
    """bool is a subclass of int in Python -- exclude it explicitly so a
    stray true/false in captured data doesn't pass as a valid rank/count/year."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value) -> bool:
    """int or float, excluding bool (a subclass of int)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_and_normalize(slug: str, entries: list[dict]) -> list[dict]:
    """Validate one chart's entries against the RYM chart contract and
    return the normalized list (field order: rank, norm_key, artist, title,
    year, rating, rating_count), preserving input order. Raises ValueError,
    naming the chart slug and the entry's rank, on the first entry that
    fails: rank must be int; artist/album non-empty str; rating a number in
    0.0-5.0; rating_count an int > 0; year int or null (nullable)."""
    normalized = []
    for entry in entries:
        rank = entry.get("rank")
        if not _is_int(rank):
            raise ValueError(f"rym chart '{slug}' rank {rank!r}: rank must be an int")

        artist = entry.get("artist")
        if not isinstance(artist, str) or not artist.strip():
            raise ValueError(
                f"rym chart '{slug}' rank {rank!r}: artist must be a non-empty string"
            )

        album = entry.get("album")
        if not isinstance(album, str) or not album.strip():
            raise ValueError(
                f"rym chart '{slug}' rank {rank!r}: album must be a non-empty string"
            )

        rating = entry.get("rating")
        if not _is_number(rating):
            raise ValueError(
                f"rym chart '{slug}' rank {rank!r}: rating must be a number"
            )
        if not (0.0 <= rating <= 5.0):
            raise ValueError(
                f"rym chart '{slug}' rank {rank!r}: rating {rating!r} out of 0-5 range"
            )

        rating_count = entry.get("rating_count")
        if not _is_int(rating_count):
            raise ValueError(
                f"rym chart '{slug}' rank {rank!r}: rating_count must be an int"
            )
        if rating_count <= 0:
            raise ValueError(
                f"rym chart '{slug}' rank {rank!r}: "
                f"rating_count {rating_count!r} must be > 0"
            )

        year = entry.get("year")
        if year is not None and not _is_int(year):
            raise ValueError(
                f"rym chart '{slug}' rank {rank!r}: year must be an int or null"
            )

        normalized.append(
            {
                "rank": rank,
                "norm_key": common.norm_key(artist, album),
                "artist": artist,
                "title": album,
                "year": year,
                "rating": rating,
                "rating_count": rating_count,
            }
        )
    return normalized


def _print_summary(charts: dict[str, list[dict]]) -> None:
    total = 0
    for slug, entries in charts.items():
        print(f"{slug}: {len(entries)} entries")
        total += len(entries)
    print(f"total: {total} entries across {len(charts)} charts")


def main() -> None:
    charts_dir = common.CACHE / "rym_charts"
    chart_files = sorted(charts_dir.glob("*.json"))
    if not chart_files:
        print(
            "cache/rym_charts/ has no chart files -- "
            "run the Task 8 assisted capture first",
            file=sys.stderr,
        )
        sys.exit(1)

    charts: dict[str, list[dict]] = {}
    for path in chart_files:
        slug = path.stem
        entries = common.load_json(path)
        charts[slug] = validate_and_normalize(slug, entries)

    common.CACHE.mkdir(parents=True, exist_ok=True)
    common.save_json(common.CACHE / "rym.json", {"charts": charts})
    _print_summary(charts)


if __name__ == "__main__":
    main()

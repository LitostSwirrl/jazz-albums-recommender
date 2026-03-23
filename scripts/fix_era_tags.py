#!/usr/bin/env python3
"""Fix album era mistagging by cross-referencing with artist era data.

Albums were originally tagged with eras based on release year ranges,
not musical style. This script reassigns eras using the artist's known
eras from artists.json as the source of truth.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "src" / "data"


def load_json(filename: str):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename: str, data):
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def best_era_for_year(artist_eras: list[str], album_year: int | None, era_ranges: dict[str, tuple[int, int]]) -> str:
    """Pick the best era from artist's eras list for a given album year."""
    if len(artist_eras) == 1:
        return artist_eras[0]

    if album_year is None:
        return artist_eras[0]

    # Find eras whose year range contains the album year
    matching = [e for e in artist_eras if e in era_ranges and era_ranges[e][0] <= album_year <= era_ranges[e][1]]
    if matching:
        return matching[-1]  # Prefer later era if multiple match (more specific)

    # No range contains the year — use the latest era in the artist's list
    # (for reissues/posthumous releases that are beyond all ranges)
    return artist_eras[-1]


def main():
    albums = load_json("albums.json")
    artists = load_json("artists.json")
    eras = load_json("eras.json")

    # Build lookups
    artist_eras = {a["id"]: a.get("eras", []) for a in artists}
    era_ranges = {e["id"]: (e["years"][0], e["years"][1]) for e in eras}

    changes = []
    skipped_no_artist = 0
    skipped_empty_eras = 0
    already_correct = 0

    for album in albums:
        artist_id = album.get("artistId", "")
        album_era = album.get("era", "")

        if artist_id not in artist_eras:
            skipped_no_artist += 1
            continue

        a_eras = artist_eras[artist_id]
        if not a_eras:
            skipped_empty_eras += 1
            continue

        if album_era in a_eras:
            already_correct += 1
            continue

        # Mismatch found — compute correct era
        new_era = best_era_for_year(a_eras, album.get("year"), era_ranges)
        changes.append({
            "title": album["title"],
            "artist": album.get("artist", ""),
            "year": album.get("year"),
            "old_era": album_era,
            "new_era": new_era,
        })
        album["era"] = new_era

    # Print summary
    print(f"Total albums: {len(albums)}")
    print(f"Already correct: {already_correct}")
    print(f"Skipped (no artist match): {skipped_no_artist}")
    print(f"Skipped (empty artist eras): {skipped_empty_eras}")
    print(f"Fixed: {len(changes)}")
    print()

    if changes:
        # Group by old_era → new_era
        from collections import Counter
        transitions = Counter((c["old_era"], c["new_era"]) for c in changes)
        print("Era transitions:")
        for (old, new), count in transitions.most_common():
            print(f"  {old} → {new}: {count}")
        print()

        print("All changes:")
        for c in sorted(changes, key=lambda x: (x["artist"], x["year"] or 0)):
            print(f"  {c['artist']} - \"{c['title']}\" ({c['year']}) : {c['old_era']} → {c['new_era']}")

        save_json("albums.json", albums)
        print(f"\nSaved {len(changes)} fixes to albums.json")
    else:
        print("No changes needed.")


if __name__ == "__main__":
    main()

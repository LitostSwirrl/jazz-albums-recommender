#!/usr/bin/env python3
"""
Fix 40 malformed artist entries in artists.json.

These artists were added by add_critical_100.py and add_final_41.py with
field names that don't match the TypeScript Artist interface:
  - influenced → influencedBy
  - era (string) → eras (string[])
  - photoUrl → imageUrl
  - add instruments: [] if missing
  - remove genres (not in interface)
"""
import json
from pathlib import Path

ARTISTS_FILE = Path(__file__).parent.parent / "src" / "data" / "artists.json"

def main():
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)

    fixed = 0
    for artist in artists:
        changed = False

        # influenced → influencedBy
        if "influenced" in artist and "influencedBy" not in artist:
            artist["influencedBy"] = artist.pop("influenced")
            changed = True

        # era (string) → eras (string[])
        if "era" in artist and "eras" not in artist:
            artist["eras"] = [artist.pop("era")]
            changed = True

        # photoUrl → imageUrl
        if "photoUrl" in artist and "imageUrl" not in artist:
            artist["imageUrl"] = artist.pop("photoUrl")
            changed = True

        # Add instruments if missing
        if "instruments" not in artist:
            artist["instruments"] = []
            changed = True

        # Remove genres (not in interface)
        if "genres" in artist:
            del artist["genres"]
            changed = True

        # Add birthYear if missing (required by interface)
        if "birthYear" not in artist:
            artist["birthYear"] = 0
            changed = True

        if changed:
            fixed += 1
            print(f"  Fixed: {artist['name']}")

    print(f"\nFixed {fixed} artists out of {len(artists)} total")

    with open(ARTISTS_FILE, "w") as f:
        json.dump(artists, f, indent=2, ensure_ascii=False)

    print("Saved artists.json")

if __name__ == "__main__":
    main()

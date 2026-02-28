#!/usr/bin/env python3
"""
Stage 0: Album Expansion Planner

Analyzes the current jazz albums data and generates a target list of albums
to add, broken down by artist tier. Outputs /tmp/expansion_plan.json.

Usage:
    python3 scripts/plan_expansion.py
"""

import json
import os
import sys
from collections import Counter

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
ALBUMS_PATH = os.path.join(BASE_DIR, "src", "data", "albums.json")
ARTISTS_PATH = os.path.join(BASE_DIR, "src", "data", "artists.json")
OUTPUT_PATH = "/tmp/expansion_plan.json"

# Tier definitions: artist-id -> target album count
TIER_1 = {
    "miles-davis": 12,
    "duke-ellington": 12,
    "charles-mingus": 10,
    "john-coltrane": 10,
    "thelonious-monk": 10,
    "herbie-hancock": 10,
}

TIER_2 = {
    "sonny-rollins": 7,
    "art-blakey": 7,
    "bill-evans": 7,
    "ornette-coleman": 6,
    "dizzy-gillespie": 6,
    "charlie-parker": 6,
    "cecil-taylor": 6,
    "sun-ra": 7,
    "mccoy-tyner": 6,
    "chick-corea": 6,
    "pat-metheny": 6,
    "wayne-shorter": 6,
    "pharoah-sanders": 6,
}

TIER_3 = {aid: 5 for aid in [
    "louis-armstrong", "dexter-gordon", "sarah-vaughan", "ella-fitzgerald",
    "nina-simone", "eric-dolphy", "lee-morgan", "freddie-hubbard",
    "kenny-dorham", "horace-silver", "cannonball-adderley", "keith-jarrett",
    "weather-report", "max-roach", "bud-powell", "dave-brubeck",
    "stan-getz", "wes-montgomery", "oscar-peterson", "ahmad-jamal",
    "donald-byrd", "bobby-hutcherson", "jackie-mclean", "woody-shaw",
    "kenny-burrell", "yusef-lateef", "andrew-hill", "joe-henderson",
]}

# Merge all tiers into one lookup
ALL_TIERS = {}
ALL_TIERS.update(TIER_1)
ALL_TIERS.update(TIER_2)
ALL_TIERS.update(TIER_3)

# ---------------------------------------------------------------------------
# Curated must-have albums (canonical records that MUST be in the expansion)
# ---------------------------------------------------------------------------

CURATED_MUST_HAVE = {
    "miles-davis": [
        "'Round About Midnight",
        "Milestones",
        "Sketches of Spain",
        "E.S.P.",
        "Miles Smiles",
        "Agharta",
    ],
    "john-coltrane": [
        "My Favorite Things",
        "Crescent",
        "Ballads",
    ],
    "duke-ellington": [
        "Such Sweet Thunder",
        "Far East Suite",
        "Masterpieces by Ellington",
        "Ellington Indigos",
        "The Popular Duke Ellington",
    ],
    "thelonious-monk": [
        "Solo Monk",
        "Genius of Modern Music Vol. 1",
        "Monk's Music",
    ],
    "charles-mingus": [
        "Pithecanthropus Erectus",
        "The Clown",
        "Mingus Mingus Mingus Mingus Mingus",
        "Let My Children Hear Music",
    ],
    "herbie-hancock": [
        "Mwandishi",
        "Speak Like a Child",
        "Future Shock",
    ],
}

# ---------------------------------------------------------------------------
# New artists to add (not yet in artists.json)
# ---------------------------------------------------------------------------

NEW_ARTISTS = [
    {
        "id": "art-pepper",
        "name": "Art Pepper",
        "instrument": "alto saxophone",
        "style": "cool-jazz/hard-bop",
        "birth_year": 1925,
        "death_year": 1982,
        "suggested_albums": 4,
        "notes": "West Coast alto legend; Art Pepper Meets the Rhythm Section, "
                 "Smack Up, Living Legend, Winter Moon",
    },
    {
        "id": "gerry-mulligan",
        "name": "Gerry Mulligan",
        "instrument": "baritone saxophone",
        "style": "cool-jazz",
        "birth_year": 1927,
        "death_year": 1996,
        "suggested_albums": 3,
        "notes": "Pioneered pianoless quartet; Mulligan Meets Monk, "
                 "Night Lights, What Is There to Say?",
    },
    {
        "id": "lee-konitz",
        "name": "Lee Konitz",
        "instrument": "alto saxophone",
        "style": "cool-jazz",
        "birth_year": 1927,
        "death_year": 2020,
        "suggested_albums": 3,
        "notes": "Tristano school, Birth of the Cool; Subconscious-Lee, "
                 "Motion, The Real Lee Konitz",
    },
    {
        "id": "hampton-hawes",
        "name": "Hampton Hawes",
        "instrument": "piano",
        "style": "hard-bop",
        "birth_year": 1928,
        "death_year": 1977,
        "suggested_albums": 2,
        "notes": "West Coast bop piano; The Trio Vol. 1, All Night Session!",
    },
    {
        "id": "tina-brooks",
        "name": "Tina Brooks",
        "instrument": "tenor saxophone",
        "style": "hard-bop",
        "birth_year": 1932,
        "death_year": 1974,
        "suggested_albums": 2,
        "notes": "Tragically under-recorded Blue Note tenor; True Blue, "
                 "Back to the Tracks",
    },
    {
        "id": "blue-mitchell",
        "name": "Blue Mitchell",
        "instrument": "trumpet",
        "style": "hard-bop",
        "birth_year": 1930,
        "death_year": 1979,
        "suggested_albums": 2,
        "notes": "Riverside hard-bop trumpeter; Blue's Moods, The Thing to Do",
    },
    {
        "id": "booker-little",
        "name": "Booker Little",
        "instrument": "trumpet",
        "style": "hard-bop/free-jazz",
        "birth_year": 1938,
        "death_year": 1961,
        "suggested_albums": 2,
        "notes": "Died at 23, bridged hard-bop and free; Out Front, "
                 "Booker Little and Friend",
    },
    {
        "id": "paul-chambers",
        "name": "Paul Chambers",
        "instrument": "bass",
        "style": "hard-bop",
        "birth_year": 1935,
        "death_year": 1969,
        "suggested_albums": 2,
        "notes": "First-call bassist for Miles quintet; Bass on Top, "
                 "Whims of Chambers",
    },
]

# Artists that were listed as candidates but already exist in artists.json
ALREADY_EXISTING_ARTISTS = [
    "abbey-lincoln",
    "betty-carter",
    "elvin-jones",
    "grant-green",
    "jimmy-smith",
    "mal-waldron",
    "mccoy-tyner",
]


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def load_json(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def count_albums_per_artist(albums: list) -> Counter:
    """Count how many albums each artist currently has."""
    counts: Counter = Counter()
    for album in albums:
        aid = album.get("artistId", "")
        if aid:
            counts[aid] += 1
    return counts


def get_existing_titles_by_artist(albums: list) -> dict:
    """Map artist-id -> set of existing album titles (lowercased for matching)."""
    titles: dict = {}
    for album in albums:
        aid = album.get("artistId", "")
        title = album.get("title", "")
        if aid and title:
            titles.setdefault(aid, set()).add(title.lower().strip())
    return titles


def check_must_haves(existing_titles: dict) -> dict:
    """Check which curated must-have albums are already present vs missing."""
    result = {}
    for artist_id, must_titles in CURATED_MUST_HAVE.items():
        existing = existing_titles.get(artist_id, set())
        present = []
        missing = []
        for title in must_titles:
            if title.lower().strip() in existing:
                present.append(title)
            else:
                missing.append(title)
        result[artist_id] = {
            "must_have_total": len(must_titles),
            "already_present": present,
            "missing": missing,
        }
    return result


def build_expansion_plan(
    album_counts: Counter,
    existing_titles: dict,
    artists_by_id: dict,
) -> dict:
    """Build per-artist expansion targets."""
    plan = {}

    for artist_id, target in ALL_TIERS.items():
        current = album_counts.get(artist_id, 0)
        needed = max(0, target - current)

        # Determine tier label
        if artist_id in TIER_1:
            tier = "tier-1"
        elif artist_id in TIER_2:
            tier = "tier-2"
        else:
            tier = "tier-3"

        artist_name = artists_by_id.get(artist_id, {}).get("name", artist_id)

        entry = {
            "artist_name": artist_name,
            "tier": tier,
            "target": target,
            "current": current,
            "needed": needed,
        }

        # Add must-have info if applicable
        if artist_id in CURATED_MUST_HAVE:
            existing = existing_titles.get(artist_id, set())
            missing_must_haves = [
                t for t in CURATED_MUST_HAVE[artist_id]
                if t.lower().strip() not in existing
            ]
            entry["must_have_missing"] = missing_must_haves
            entry["must_have_missing_count"] = len(missing_must_haves)

        plan[artist_id] = entry

    return plan


def print_summary(plan: dict, must_have_check: dict, album_counts: Counter) -> None:
    """Print a human-readable summary to stdout."""
    print("=" * 70)
    print("  JAZZ ALBUM EXPANSION PLAN — Stage 0")
    print("=" * 70)
    print()

    total_current = sum(album_counts.values())
    total_needed = sum(e["needed"] for e in plan.values())
    new_artist_albums = sum(a["suggested_albums"] for a in NEW_ARTISTS)
    total_expansion = total_needed + new_artist_albums

    print(f"  Current total albums:        {total_current}")
    print(f"  Albums needed (existing):    {total_needed}")
    print(f"  Albums from new artists:     {new_artist_albums}")
    print(f"  Total expansion target:      ~{total_expansion}")
    print(f"  Projected total:             ~{total_current + total_expansion}")
    print()

    # --- Tier 1 ---
    print("-" * 70)
    print("  TIER 1 — Pillars (target 10-12 albums each)")
    print("-" * 70)
    for aid in sorted(TIER_1.keys()):
        e = plan[aid]
        status = "OK" if e["needed"] == 0 else f"+{e['needed']}"
        must_have_info = ""
        if e.get("must_have_missing"):
            must_have_info = f"  [must-haves missing: {e['must_have_missing_count']}]"
        print(f"  {e['artist_name']:<30} {e['current']:>2}/{e['target']:<2}  {status:>4}{must_have_info}")
    print()

    # --- Tier 2 ---
    print("-" * 70)
    print("  TIER 2 — Major figures (target 6-7 albums each)")
    print("-" * 70)
    for aid in sorted(TIER_2.keys()):
        e = plan[aid]
        status = "OK" if e["needed"] == 0 else f"+{e['needed']}"
        print(f"  {e['artist_name']:<30} {e['current']:>2}/{e['target']:<2}  {status:>4}")
    print()

    # --- Tier 3 ---
    print("-" * 70)
    print("  TIER 3 — Essential artists (target 5 albums each)")
    print("-" * 70)
    for aid in sorted(TIER_3.keys()):
        e = plan[aid]
        status = "OK" if e["needed"] == 0 else f"+{e['needed']}"
        print(f"  {e['artist_name']:<30} {e['current']:>2}/{e['target']:<2}  {status:>4}")
    print()

    # --- Must-have albums ---
    print("-" * 70)
    print("  CURATED MUST-HAVE ALBUMS")
    print("-" * 70)
    total_must = 0
    total_present = 0
    total_missing = 0
    for aid, info in sorted(must_have_check.items()):
        total_must += info["must_have_total"]
        total_present += len(info["already_present"])
        total_missing += len(info["missing"])
        if info["missing"]:
            artist_name = plan.get(aid, {}).get("artist_name", aid)
            print(f"\n  {artist_name} — {len(info['missing'])} missing:")
            for title in info["missing"]:
                print(f"    - {title}")
        else:
            artist_name = plan.get(aid, {}).get("artist_name", aid)
            print(f"  {artist_name} — all {info['must_have_total']} present")
    print(f"\n  Must-have totals: {total_present}/{total_must} present, "
          f"{total_missing} to add")
    print()

    # --- New artists ---
    print("-" * 70)
    print("  NEW ARTISTS TO ADD")
    print("-" * 70)
    for a in NEW_ARTISTS:
        print(f"  {a['name']:<25} {a['instrument']:<22} "
              f"{a['style']:<20} ~{a['suggested_albums']} albums")
    print()
    print(f"  Already in data (skip creation): "
          f"{', '.join(ALREADY_EXISTING_ARTISTS)}")
    print()

    # --- Artists with excess albums ---
    print("-" * 70)
    print("  ARTISTS ALREADY AT OR ABOVE TARGET")
    print("-" * 70)
    at_target = [(aid, plan[aid]) for aid in plan if plan[aid]["needed"] == 0]
    at_target.sort(key=lambda x: x[1]["current"], reverse=True)
    for aid, e in at_target:
        print(f"  {e['artist_name']:<30} {e['current']:>2}/{e['target']:<2}")
    if not at_target:
        print("  (none)")
    print()

    print("=" * 70)
    print(f"  Output written to: {OUTPUT_PATH}")
    print("=" * 70)


def main() -> None:
    # Load data
    if not os.path.exists(ALBUMS_PATH):
        print(f"ERROR: Albums file not found: {ALBUMS_PATH}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(ARTISTS_PATH):
        print(f"ERROR: Artists file not found: {ARTISTS_PATH}", file=sys.stderr)
        sys.exit(1)

    albums = load_json(ALBUMS_PATH)
    artists = load_json(ARTISTS_PATH)

    print(f"Loaded {len(albums)} albums, {len(artists)} artists")
    print()

    # Index artists by id
    artists_by_id = {a["id"]: a for a in artists}

    # Count albums per artist
    album_counts = count_albums_per_artist(albums)
    existing_titles = get_existing_titles_by_artist(albums)

    # Check must-haves
    must_have_check = check_must_haves(existing_titles)

    # Build plan
    plan = build_expansion_plan(album_counts, existing_titles, artists_by_id)

    # Build output JSON
    output = {
        "_meta": {
            "description": "Jazz album expansion plan — Stage 0",
            "current_album_count": len(albums),
            "current_artist_count": len(artists),
            "tiered_artists_count": len(ALL_TIERS),
            "total_albums_needed_existing_artists": sum(
                e["needed"] for e in plan.values()
            ),
            "total_albums_from_new_artists": sum(
                a["suggested_albums"] for a in NEW_ARTISTS
            ),
            "total_must_have_albums": sum(
                len(v) for v in CURATED_MUST_HAVE.values()
            ),
            "must_have_already_present": sum(
                len(info["already_present"])
                for info in must_have_check.values()
            ),
            "must_have_missing": sum(
                len(info["missing"])
                for info in must_have_check.values()
            ),
        },
        "expansion_plan": plan,
        "curated_must_have": {
            artist_id: {
                "titles": titles,
                "status": must_have_check[artist_id],
            }
            for artist_id, titles in CURATED_MUST_HAVE.items()
        },
        "new_artists": NEW_ARTISTS,
        "already_existing_artists": ALREADY_EXISTING_ARTISTS,
    }

    # Write output
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Print summary
    print_summary(plan, must_have_check, album_counts)


if __name__ == "__main__":
    main()

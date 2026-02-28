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
# Round 2 targets — era-balanced expansion (912 → 1000)
TIER_1 = {
    "miles-davis": 16,
    "duke-ellington": 17,
    "charles-mingus": 12,
    "john-coltrane": 14,
    "thelonious-monk": 13,
    "herbie-hancock": 12,
}

TIER_2 = {
    "sonny-rollins": 9,
    "art-blakey": 9,
    "bill-evans": 7,
    "ornette-coleman": 6,
    "dizzy-gillespie": 6,
    "charlie-parker": 6,
    "cecil-taylor": 6,
    "sun-ra": 9,
    "mccoy-tyner": 6,
    "chick-corea": 6,
    "pat-metheny": 6,
    "wayne-shorter": 6,
    "pharoah-sanders": 6,
    # Early-jazz / Swing — promoted to Tier 2
    "louis-armstrong": 8,
    "count-basie": 7,
    "billie-holiday": 6,
    "ella-fitzgerald": 7,
    "lester-young": 6,
    "art-tatum": 6,
}

TIER_3 = {
    # Original Tier 3 artists
    "dexter-gordon": 5, "sarah-vaughan": 5, "nina-simone": 5,
    "lee-morgan": 5, "freddie-hubbard": 5,
    "horace-silver": 5, "cannonball-adderley": 5, "keith-jarrett": 6,
    "max-roach": 5, "bud-powell": 5,
    "wes-montgomery": 5, "oscar-peterson": 5, "ahmad-jamal": 5,
    "donald-byrd": 5, "jackie-mclean": 5, "woody-shaw": 5,
    "kenny-burrell": 5, "yusef-lateef": 5, "andrew-hill": 5, "joe-henderson": 5,
    # Early-jazz / Swing deepening
    "benny-goodman": 6, "coleman-hawkins": 5, "sidney-bechet": 5,
    "fletcher-henderson": 5, "fats-waller": 5, "django-reinhardt": 4,
    # Cool-jazz deepening
    "chet-baker": 5, "stan-getz": 7, "dave-brubeck": 7, "gerry-mulligan": 5,
    # Hard-bop gaps
    "j-j-johnson": 3, "kenny-dorham": 4, "elvin-jones": 5, "tony-williams": 5,
    "jimmy-smith": 5, "grant-green": 6,
    # Free-jazz deepening
    "eric-dolphy": 7, "alice-coltrane": 6, "bobby-hutcherson": 7,
    # Fusion deepening
    "weather-report": 7, "jaco-pastorius": 5,
}

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
    # Round 2 — early-jazz / swing canonical albums
    "louis-armstrong": [
        "Satchmo at Symphony Hall",
    ],
    "count-basie": [
        "The Atomic Mr. Basie",
        "April in Paris",
    ],
    "billie-holiday": [
        "Lady in Satin",
        "Songs for Distingué Lovers",
    ],
    "art-tatum": [
        "Piano Starts Here",
    ],
    "lester-young": [
        "The President Plays with the Oscar Peterson Trio",
    ],
    "alice-coltrane": [
        "Journey in Satchidananda",
    ],
}

# ---------------------------------------------------------------------------
# New artists to add (not yet in artists.json)
# ---------------------------------------------------------------------------

NEW_ARTISTS = [
    # Round 2 — fill critical early-jazz/swing gaps
    {
        "id": "bix-beiderbecke",
        "name": "Bix Beiderbecke",
        "instrument": "cornet, piano",
        "style": "early-jazz",
        "birth_year": 1903,
        "death_year": 1931,
        "suggested_albums": 3,
        "notes": "Lyrical cornetist, first great white jazz soloist; "
                 "Singin' the Blues, In a Mist, At the Jazz Band Ball",
    },
    {
        "id": "jimmie-lunceford",
        "name": "Jimmie Lunceford",
        "instrument": "bandleader, alto saxophone",
        "style": "swing",
        "birth_year": 1902,
        "death_year": 1947,
        "suggested_albums": 3,
        "notes": "Precision swing orchestra; Rhythm Is Our Business, "
                 "Lunceford Special, For Dancers Only",
    },
    {
        "id": "jack-teagarden",
        "name": "Jack Teagarden",
        "instrument": "trombone, vocals",
        "style": "swing/early-jazz",
        "birth_year": 1905,
        "death_year": 1964,
        "suggested_albums": 2,
        "notes": "Greatest jazz trombonist of swing era; "
                 "Jack Teagarden's Big Eight, Think Well of Me",
    },
]

# Artists that were listed as candidates but already exist in artists.json
ALREADY_EXISTING_ARTISTS = [
    "abbey-lincoln", "betty-carter", "elvin-jones", "grant-green",
    "jimmy-smith", "mal-waldron", "mccoy-tyner",
    # Round 1 artists that now exist
    "art-pepper", "gerry-mulligan", "lee-konitz", "hampton-hawes",
    "tina-brooks", "blue-mitchell", "booker-little", "paul-chambers",
    # Already existed before both rounds
    "sidney-bechet", "fletcher-henderson", "art-tatum", "fats-waller",
    "django-reinhardt",
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

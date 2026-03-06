#!/usr/bin/env python3
"""
Enforce outbound link quality standard on albums.json.

Rule: Every album in a non-exempt era MUST have at least one streaming link.
Exempt eras: early-jazz, swing (pre-1950 recordings rarely have modern streaming links).

Safe-to-remove: failing albums where the artist has OTHER albums with links.
At-risk: failing albums where this is the only coverage for that artist.

Usage: python3 scripts/enforce_link_standard.py [--dry-run]
Output: scripts/link_standard_report.md + updated albums.json (unless --dry-run)
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
ALBUMS_FILE = ROOT / "src" / "data" / "albums.json"
OUTPUT_FILE = Path(__file__).parent / "link_standard_report.md"

EXEMPT_ERAS = {"early-jazz", "swing"}
LINK_FIELDS = ["spotifyUrl", "appleMusicUrl", "youtubeMusicUrl", "youtubeUrl"]


def has_link(album: dict) -> bool:
    return any(album.get(f) for f in LINK_FIELDS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Report only, don't modify albums.json")
    args = parser.parse_args()

    with open(ALBUMS_FILE) as f:
        albums: list[dict] = json.load(f)

    # Build a map: artistId → list of albums WITH links (in non-exempt eras)
    linked_by_artist: dict[str, list[str]] = defaultdict(list)
    for a in albums:
        if a.get("era") not in EXEMPT_ERAS and has_link(a):
            linked_by_artist[a["artistId"]].append(a["id"])

    # Identify failing albums
    failing: list[dict] = []
    for a in albums:
        if a.get("era") in EXEMPT_ERAS:
            continue
        if not has_link(a):
            failing.append(a)

    safe_to_remove: list[dict] = []
    at_risk: list[dict] = []

    for a in failing:
        artist_has_other_linked = bool(linked_by_artist.get(a["artistId"]))
        if artist_has_other_linked:
            safe_to_remove.append(a)
        else:
            at_risk.append(a)

    # Build report
    lines = [
        "# Link Standard Enforcement Report",
        "",
        f"Checked {len(albums)} albums. Exempt eras: {sorted(EXEMPT_ERAS)}",
        "",
        f"**Failing albums (non-exempt, no streaming links): {len(failing)}**",
        f"- Safe to remove (artist has other linked albums): {len(safe_to_remove)}",
        f"- Artist at risk (only coverage for this artist): {len(at_risk)}",
        "",
    ]

    lines.append("## Safe to Remove")
    lines.append("")
    for a in sorted(safe_to_remove, key=lambda x: (x["artist"], x["title"])):
        lines.append(f"- `{a['id']}` — **{a['title']}** by {a['artist']} [{a['era']}]")
    lines.append("")

    lines.append("## Artist at Risk (requires manual follow-up)")
    lines.append("")
    if at_risk:
        for a in at_risk:
            lines.append(f"- `{a['id']}` — **{a['title']}** by {a['artist']} [{a['era']}]")
        lines.append("")
        lines.append("### Suggested follow-up commands:")
        lines.append("")
        at_risk_artists = {a["artist"] for a in at_risk}
        for artist in sorted(at_risk_artists):
            lines.append(f'```')
            lines.append(f'python3 scripts/batch_add_albums.py --artist "{artist}" --limit 5')
            lines.append(f'```')
    else:
        lines.append("None — all artists remain represented.")
    lines.append("")

    OUTPUT_FILE.write_text("\n".join(lines))
    print(f"Report written to {OUTPUT_FILE}")

    if args.dry_run:
        print(f"DRY RUN — no changes made to albums.json")
        print(f"Would remove {len(failing)} albums ({len(safe_to_remove)} safe + {len(at_risk)} at-risk)")
        return

    # Remove all failing albums (both safe and at-risk)
    remove_ids = {a["id"] for a in failing}
    before = len(albums)
    albums = [a for a in albums if a["id"] not in remove_ids]
    after = len(albums)

    with open(ALBUMS_FILE, "w") as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)

    print(f"albums.json: {before} → {after} albums (removed {before - after})")
    print(f"  Safe removals: {len(safe_to_remove)}")
    if at_risk:
        print(f"  At-risk removals: {len(at_risk)}")
        for a in at_risk:
            print(f"    - {a['artist']}: {a['title']}")
        print()
        print("Run batch_add_albums.py for at-risk artists to restore coverage:")
        at_risk_artists = {a["artist"] for a in at_risk}
        for artist in sorted(at_risk_artists):
            print(f'  python3 scripts/batch_add_albums.py --artist "{artist}" --limit 5')


if __name__ == "__main__":
    main()

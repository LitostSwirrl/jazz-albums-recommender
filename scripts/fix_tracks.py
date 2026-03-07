#!/usr/bin/env python3
"""
Fix keyTracks in albums.json using MusicBrainz track listings.

1. Empty keyTracks → populate from MusicBrainz (up to 6 tracks)
2. Populated keyTracks → compare against MusicBrainz listing, flag mismatches

Output: scripts/track_fix_report.md
Usage: python3 scripts/fix_tracks.py [--dry-run]
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
ALBUMS_FILE = ROOT / "src" / "data" / "albums.json"
REPORT_FILE = Path(__file__).parent / "track_fix_report.md"

MUSICBRAINZ_BASE = "https://musicbrainz.org/ws/2"
HEADERS = {
    "User-Agent": "JazzAlbumsRecommender/1.0 (https://github.com/LitostSwirrl/jazz-albums-recommender)",
    "Accept": "application/json",
}


def mb_get(path: str, params: dict) -> dict:
    params["fmt"] = "json"
    qs = urllib.parse.urlencode(params)
    url = f"{MUSICBRAINZ_BASE}/{path}?{qs}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.load(resp)


def search_release(title: str, artist: str) -> str | None:
    """Search MusicBrainz for the best matching release MBID."""
    try:
        query = f'release:"{title}" AND artist:"{artist}"'
        data = mb_get("release", {"query": query, "limit": 3})
        releases = data.get("releases", [])
        if releases:
            return releases[0]["id"]
    except Exception:
        pass
    return None


def get_tracks(mbid: str) -> list[str]:
    """Get track listing for a release (first disc, up to 10 tracks)."""
    try:
        data = mb_get(f"release/{mbid}", {"inc": "recordings"})
        tracks: list[str] = []
        for medium in data.get("media", [])[:1]:  # first disc only
            for t in medium.get("tracks", [])[:10]:
                name = t.get("title", "") or (t.get("recording", {}) or {}).get("title", "")
                if name:
                    tracks.append(name)
        return tracks
    except Exception:
        return []


def normalize(s: str) -> str:
    """Normalize for comparison: lowercase, strip punctuation."""
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def track_match_ratio(our_tracks: list[str], mb_tracks: list[str]) -> float:
    """Return fraction of our tracks that appear in MB listing."""
    if not our_tracks or not mb_tracks:
        return 0.0
    mb_normalized = {normalize(t) for t in mb_tracks}
    matches = sum(1 for t in our_tracks if normalize(t) in mb_normalized)
    return matches / len(our_tracks)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(ALBUMS_FILE) as f:
        albums: list[dict] = json.load(f)

    stats = {"populated": 0, "mismatched": 0, "matched": 0, "mb_not_found": 0, "skipped": 0}
    report_lines = ["# Track Fix Report", "", f"Checked {len(albums)} albums.", ""]
    mismatches: list[dict] = []

    for i, album in enumerate(albums):
        aid = album["id"]
        title = album["title"]
        artist = album["artist"]
        our_tracks = album.get("keyTracks", [])

        # Search MusicBrainz
        mbid = search_release(title, artist)
        time.sleep(1.1)  # rate limit

        if not mbid:
            stats["mb_not_found"] += 1
            if not our_tracks:
                print(f"  [{i+1}/{len(albums)}] {aid} — MB not found, tracks empty")
            continue

        mb_tracks = get_tracks(mbid)
        time.sleep(1.1)

        if not mb_tracks:
            stats["mb_not_found"] += 1
            continue

        # Case 1: Empty keyTracks → populate
        if not our_tracks:
            album["keyTracks"] = mb_tracks[:6]
            stats["populated"] += 1
            print(f"  [{i+1}/{len(albums)}] {aid} — POPULATED {len(album['keyTracks'])} tracks")
            continue

        # Case 2: Populated → check for mismatch
        ratio = track_match_ratio(our_tracks, mb_tracks)
        if ratio < 0.5:
            stats["mismatched"] += 1
            mismatches.append({
                "id": aid,
                "title": title,
                "artist": artist,
                "our_tracks": our_tracks,
                "mb_tracks": mb_tracks[:8],
                "match_ratio": ratio,
            })
            # Auto-fix: replace with MB tracks
            album["keyTracks"] = mb_tracks[:6]
            print(f"  [{i+1}/{len(albums)}] {aid} — MISMATCH ({ratio:.0%}) → replaced with MB tracks")
        else:
            stats["matched"] += 1
            if (i + 1) % 50 == 0:
                print(f"  [{i+1}/{len(albums)}] ... {stats['matched']} matched so far")

    # Report
    report_lines.append(f"**Populated (was empty):** {stats['populated']}")
    report_lines.append(f"**Mismatched (replaced):** {stats['mismatched']}")
    report_lines.append(f"**Matched (no change):** {stats['matched']}")
    report_lines.append(f"**MB not found:** {stats['mb_not_found']}")
    report_lines.append("")

    if mismatches:
        report_lines.append("## Mismatched Albums (auto-replaced)")
        report_lines.append("")
        for m in mismatches:
            report_lines.append(f"### `{m['id']}` — {m['title']} by {m['artist']}")
            report_lines.append(f"Match ratio: {m['match_ratio']:.0%}")
            report_lines.append(f"**Our tracks:** {', '.join(m['our_tracks'])}")
            report_lines.append(f"**MB tracks:** {', '.join(m['mb_tracks'])}")
            report_lines.append("")

    REPORT_FILE.write_text("\n".join(report_lines))
    print(f"\nReport: {REPORT_FILE}")
    print(f"Populated: {stats['populated']} | Mismatched: {stats['mismatched']} | Matched: {stats['matched']} | Not found: {stats['mb_not_found']}")

    if args.dry_run:
        print("DRY RUN — no changes saved")
        return

    with open(ALBUMS_FILE, "w") as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(albums)} albums")


if __name__ == "__main__":
    main()

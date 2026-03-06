#!/usr/bin/env python3
"""
Batch album addition pipeline.
Orchestrates: MusicBrainz fetch → cover art → streaming links → quality check → JSON patch.

Usage:
  python3 scripts/batch_add_albums.py --artist "Miles Davis" --limit 10
  python3 scripts/batch_add_albums.py --mbids "mbid1,mbid2,mbid3"

Output: scripts/batch_add_output.json  (ready to review and merge into albums.json)
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
ARTISTS_FILE = ROOT / "src" / "data" / "artists.json"
OUTPUT_FILE = Path(__file__).parent / "batch_add_output.json"

MUSICBRAINZ_BASE = "https://musicbrainz.org/ws/2"
COVERART_BASE = "https://coverartarchive.org"
ODESLI_BASE = "https://api.song.link/v1-alpha.1/links"
ITUNES_SEARCH = "https://itunes.apple.com/search"

HEADERS = {
    "User-Agent": "JazzAlbumsRecommender/1.0 (https://github.com/your-repo)",
    "Accept": "application/json",
}

# Boilerplate detection (mirrors audit_metadata.py)
TEMPLATE_DESC = re.compile(
    r"^.{10,60} is a .{5,40} (album|record) by .{5,40} from \d{4}", re.IGNORECASE
)
TEMPLATE_SIG = re.compile(
    r"^A .{5,40} (entry|album|recording) from \d{4}", re.IGNORECASE
)

ERA_BY_DECADE = {
    1900: "early-jazz", 1910: "early-jazz", 1920: "early-jazz",
    1930: "swing", 1940: "bebop",
    1950: "cool-jazz", 1960: "hard-bop",
    1970: "fusion", 1980: "contemporary",
    1990: "contemporary", 2000: "contemporary",
    2010: "contemporary", 2020: "contemporary",
}


def mb_get(path: str, params: dict) -> dict:
    params["fmt"] = "json"
    qs = urllib.parse.urlencode(params)
    url = f"{MUSICBRAINZ_BASE}/{path}?{qs}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)


def fetch_cover(mbid: str) -> str:
    try:
        url = f"{COVERART_BASE}/release/{mbid}/front-500"
        req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
        with urllib.request.urlopen(req, timeout=5):
            return f"{COVERART_BASE}/release/{mbid}/front"
    except Exception:
        pass

    # Fallback: iTunes
    return ""


def fetch_streaming(title: str, artist: str) -> dict[str, str]:
    links: dict[str, str] = {}
    try:
        query = urllib.parse.quote(f"{title} {artist}")
        url = f"{ITUNES_SEARCH}?term={query}&entity=album&limit=1"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.load(resp)
        if data.get("results"):
            result = data["results"][0]
            links["appleMusicUrl"] = result.get("collectionViewUrl", "")
    except Exception:
        pass
    return links


def guess_era(year: int | None) -> str:
    if not year:
        return "contemporary"
    decade = (year // 10) * 10
    return ERA_BY_DECADE.get(decade, "contemporary")


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text


def mb_id_to_album(mbid: str, existing_ids: set[str]) -> dict | None:
    print(f"  Fetching MusicBrainz release: {mbid}")
    try:
        data = mb_get(f"release/{mbid}", {"inc": "artist-credits recordings"})
    except Exception as e:
        print(f"    Error: {e}")
        return None

    title = data.get("title", "")
    year_raw = data.get("date", "")[:4]
    year = int(year_raw) if year_raw.isdigit() else None

    artist_credits = data.get("artist-credit", [])
    artist = artist_credits[0]["artist"]["name"] if artist_credits else "Unknown"
    artist_id = slugify(artist)

    album_id = slugify(f"{title}-{artist}")
    if album_id in existing_ids:
        print(f"    Skipping {album_id} (already in collection)")
        return None

    # Key tracks from recordings
    key_tracks = []
    for medium in data.get("media", [])[:1]:
        for track in medium.get("tracks", [])[:6]:
            key_tracks.append(track.get("title", ""))

    era = guess_era(year)
    cover_url = fetch_cover(mbid)
    time.sleep(0.5)  # MusicBrainz rate limit

    streaming = fetch_streaming(title, artist)

    description = f"{title} is an album by {artist}" + (f" from {year}." if year else ".")
    significance = f"A jazz recording by {artist}."

    album = {
        "id": album_id,
        "title": title,
        "artist": artist,
        "artistId": artist_id,
        "year": year,
        "label": "Unknown",
        "era": era,
        "genres": ["jazz"],
        "description": description,
        "significance": significance,
        "keyTracks": key_tracks,
        "coverUrl": cover_url,
        "_mbid": mbid,
        "_quality_flags": [],
    }

    # Quality flags
    if TEMPLATE_DESC.match(description):
        album["_quality_flags"].append("template_description")
    if not cover_url:
        album["_quality_flags"].append("missing_cover")
    if not key_tracks:
        album["_quality_flags"].append("empty_key_tracks")

    album.update(streaming)
    return album


def fetch_by_artist(artist_name: str, limit: int, existing_ids: set[str]) -> list[dict]:
    print(f"Searching MusicBrainz for artist: {artist_name}")
    try:
        data = mb_get("artist", {"query": f'artist:"{artist_name}"', "limit": 1})
        artists = data.get("artists", [])
        if not artists:
            print("  Artist not found.")
            return []
        artist = artists[0]
        artist_id = artist["id"]
        print(f"  Found: {artist['name']} ({artist_id})")
    except Exception as e:
        print(f"  Error finding artist: {e}")
        return []

    print(f"  Fetching releases (limit {limit})...")
    try:
        data = mb_get(
            "release",
            {"artist": artist_id, "type": "album", "status": "official", "limit": limit},
        )
    except Exception as e:
        print(f"  Error fetching releases: {e}")
        return []

    results = []
    for release in data.get("releases", []):
        mbid = release["id"]
        album = mb_id_to_album(mbid, existing_ids)
        if album:
            results.append(album)
        time.sleep(1)  # MusicBrainz rate limit between releases
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch add albums from MusicBrainz")
    parser.add_argument("--artist", help="Artist name to search")
    parser.add_argument("--limit", type=int, default=10, help="Max albums to fetch per artist")
    parser.add_argument("--mbids", help="Comma-separated MusicBrainz release IDs")
    args = parser.parse_args()

    if not args.artist and not args.mbids:
        parser.error("Provide --artist or --mbids")

    with open(ALBUMS_FILE) as f:
        existing = json.load(f)
    existing_ids = {a["id"] for a in existing}

    results = []

    if args.mbids:
        for mbid in [m.strip() for m in args.mbids.split(",")]:
            album = mb_id_to_album(mbid, existing_ids)
            if album:
                results.append(album)
            time.sleep(1)

    if args.artist:
        results.extend(fetch_by_artist(args.artist, args.limit, existing_ids))

    if not results:
        print("No new albums found.")
        return

    OUTPUT_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nOutput: {len(results)} albums → {OUTPUT_FILE}")
    flagged = sum(1 for a in results if a.get("_quality_flags"))
    if flagged:
        print(f"  {flagged} albums have quality flags (review before merging)")
    print("\nReview the output, fill in description/significance, then merge into albums.json")


if __name__ == "__main__":
    main()

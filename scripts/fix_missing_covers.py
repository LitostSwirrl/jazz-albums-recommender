#!/usr/bin/env python3
"""
Fix missing and broken album covers + artist photos.

Phase A: Unwrap wsrv.nl proxy URLs → direct coverartarchive.org URLs
Phase B: Fix http:// → https:// for coverartarchive.org URLs
Phase C: For truly missing covers (no coverUrl), search MusicBrainz CAA
Phase D: Fix missing artist photos via Wikimedia Commons

Usage:
  python3 scripts/fix_missing_covers.py           # dry-run
  python3 scripts/fix_missing_covers.py --apply    # write changes
"""

import json
import sys
import time
import re
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from urllib.parse import urlparse, parse_qs

DATA_DIR = Path(__file__).parent.parent / "src" / "data"
ALBUMS_PATH = DATA_DIR / "albums.json"
ARTISTS_PATH = DATA_DIR / "artists.json"

COVER_CACHE = Path("/tmp/missing_covers_cache.json")

MB_BASE = "https://musicbrainz.org/ws/2"
CAA_BASE = "https://coverartarchive.org"
USER_AGENT = "JazzAlbumsRecommender/1.0 (jinsoon@github)"

# Known artist photo URLs from Wikimedia Commons (verified 2026-03-02)
ARTIST_PHOTOS: dict[str, str] = {
    "bix-beiderbecke": "https://upload.wikimedia.org/wikipedia/commons/f/fa/Bix_Beiderbecke_cropped.jpg",
    "jimmie-lunceford": "https://upload.wikimedia.org/wikipedia/commons/7/7d/Jimmie_Lunceford_August_1946_%28Gottlieb%29.jpg",
    "jack-teagarden": "https://upload.wikimedia.org/wikipedia/commons/b/bc/Jack_Teagarden_Billboard.jpg",
    # yuki-arimasa: No Wikimedia Commons photo exists
}


def load_json(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_cache(path: Path) -> dict:
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {}


def save_cache(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def head_check(url: str, timeout: int = 10) -> tuple[bool, int]:
    """Check if URL is accessible. Returns (ok, status_code)."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", USER_AGENT)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return (resp.status == 200, resp.status)
    except urllib.error.HTTPError as e:
        return (False, e.code)
    except Exception:
        return (False, 0)


def unwrap_wsrv_url(url: str) -> str | None:
    """Extract the real URL from a wsrv.nl proxy URL."""
    if "wsrv.nl" not in url:
        return None
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    real_urls = params.get("url", [])
    if not real_urls:
        return None
    return real_urls[0]


def normalize_caa_url(url: str) -> str:
    """Normalize a coverartarchive.org URL to use the /front-500 pattern."""
    # Extract the release UUID from the URL
    match = re.search(r"coverartarchive\.org/release/([a-f0-9-]{36})", url)
    if match:
        uuid = match.group(1)
        return f"https://coverartarchive.org/release/{uuid}/front-500"
    return url


def mb_search_release(artist: str, title: str) -> str | None:
    """Search MusicBrainz for a release and return a CAA front-500 URL."""
    cache = load_cache(COVER_CACHE)
    cache_key = f"{artist}|||{title}"
    if cache_key in cache:
        return cache[cache_key]

    # Clean up search terms
    artist_clean = artist.split("/")[0].strip()
    title_clean = title.replace("'", "").replace('"', "")

    for query_fmt in [
        'artist:"{a}" AND release:"{t}"',
        "artist:{a} AND release:{t}",
    ]:
        query = query_fmt.format(a=artist_clean, t=title_clean)
        params = urllib.parse.urlencode({"query": query, "fmt": "json", "limit": "5"})
        url = f"{MB_BASE}/release/?{params}"

        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", USER_AGENT)
            time.sleep(1.1)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            for rel in data.get("releases", []):
                mbid = rel["id"]
                caa_url = f"{CAA_BASE}/release/{mbid}"
                try:
                    req2 = urllib.request.Request(caa_url)
                    req2.add_header("User-Agent", USER_AGENT)
                    time.sleep(1.1)
                    with urllib.request.urlopen(req2, timeout=10) as resp2:
                        caa_data = json.loads(resp2.read().decode())
                        for img in caa_data.get("images", []):
                            if img.get("front"):
                                cover_url = f"{CAA_BASE}/release/{mbid}/front-500"
                                cache[cache_key] = cover_url
                                save_cache(COVER_CACHE, cache)
                                return cover_url
                except Exception:
                    continue
        except Exception as e:
            print(f"  MB search error: {e}")

    cache[cache_key] = None
    save_cache(COVER_CACHE, cache)
    return None


def phase_a_unwrap_wsrv(albums: list, apply: bool) -> int:
    """Phase A: Unwrap wsrv.nl proxy URLs to direct coverartarchive.org URLs."""
    count = 0
    for album in albums:
        url = album.get("coverUrl", "")
        if "wsrv.nl" not in url:
            continue
        real_url = unwrap_wsrv_url(url)
        if real_url:
            # Fix http → https but keep original image file path
            if real_url.startswith("http://"):
                real_url = real_url.replace("http://", "https://", 1)
            if apply:
                album["coverUrl"] = real_url
            count += 1

    print(f"Phase A: Unwrapped {count} wsrv.nl proxy URLs")
    return count


def phase_b_fix_http(albums: list, apply: bool) -> int:
    """Phase B: Fix http:// → https:// for coverartarchive.org URLs."""
    count = 0
    for album in albums:
        url = album.get("coverUrl", "")
        if url.startswith("http://coverartarchive.org"):
            new_url = url.replace("http://", "https://", 1)
            if apply:
                album["coverUrl"] = new_url
            count += 1

    print(f"Phase B: Fixed {count} http:// → https:// URLs")
    return count


def phase_d_search_missing(albums: list, apply: bool) -> int:
    """Phase D: Search MusicBrainz for albums with no coverUrl."""
    missing = [a for a in albums if not a.get("coverUrl")]
    print(f"\nPhase D: Searching MusicBrainz for {len(missing)} missing covers...")

    fixed = 0
    not_found = []

    for i, album in enumerate(missing):
        print(f"  [{i+1}/{len(missing)}] {album['title']} by {album['artist']} ({album.get('year', '?')})")
        cover_url = mb_search_release(album["artist"], album["title"])
        if cover_url:
            print(f"    FOUND: {cover_url}")
            if apply:
                album["coverUrl"] = cover_url
            fixed += 1
        else:
            print(f"    NOT FOUND")
            not_found.append(album)

    print(f"\nPhase D results: {fixed} found, {len(not_found)} not found")
    if not_found:
        print("Still missing:")
        for a in not_found:
            print(f"  - {a['id']}: {a['title']} by {a['artist']}")

    return fixed


def fix_artist_photos(artists: list, apply: bool) -> int:
    """Fix missing artist photos."""
    missing = [a for a in artists if not a.get("imageUrl") and a["id"] != "various-artists"]
    print(f"\nArtist photos: {len(missing)} missing (excluding Various Artists)")

    fixed = 0
    for artist in missing:
        aid = artist["id"]
        if aid in ARTIST_PHOTOS:
            url = ARTIST_PHOTOS[aid]
            ok, status = head_check(url)
            if ok:
                print(f"  {artist['name']}: FOUND {url}")
                if apply:
                    artist["imageUrl"] = url
                fixed += 1
            else:
                print(f"  {artist['name']}: URL check failed (status {status}), adding anyway")
                if apply:
                    artist["imageUrl"] = url
                fixed += 1
        else:
            print(f"  {artist['name']}: No known photo URL")

    return fixed


def main() -> None:
    apply = "--apply" in sys.argv

    print(f"Mode: {'APPLY' if apply else 'DRY RUN'}")
    print(f"Data dir: {DATA_DIR}\n")

    albums = load_json(ALBUMS_PATH)
    artists = load_json(ARTISTS_PATH)

    total_album_fixes = 0

    # Phase A: Unwrap wsrv.nl proxy URLs (keep original image paths)
    total_album_fixes += phase_a_unwrap_wsrv(albums, apply)

    # Phase B: Fix http -> https
    total_album_fixes += phase_b_fix_http(albums, apply)

    # Phase D: Search for missing covers
    total_album_fixes += phase_d_search_missing(albums, apply)

    # Artist photos
    photos_fixed = fix_artist_photos(artists, apply)

    print(f"\n{'='*60}")
    print(f"Total album cover fixes: {total_album_fixes}")
    print(f"Total artist photo fixes: {photos_fixed}")
    print(f"{'='*60}")

    if apply:
        if total_album_fixes > 0:
            save_json(ALBUMS_PATH, albums)
            print(f"\nWrote album fixes to {ALBUMS_PATH}")
        if photos_fixed > 0:
            save_json(ARTISTS_PATH, artists)
            print(f"Wrote artist photo fixes to {ARTISTS_PATH}")
    else:
        print(f"\nDry run complete. Use --apply to write changes.")


if __name__ == "__main__":
    main()

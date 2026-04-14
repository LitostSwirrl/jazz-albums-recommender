#!/usr/bin/env python3
"""
Fill missing Spotify URLs for albums in albums.json.

Uses Spotify Web API search to find album URLs.
Searches by album title + artist name, picks the best match.

Usage:
  export SPOTIFY_CLIENT_ID=...
  export SPOTIFY_CLIENT_SECRET=...
  python3 scripts/fill_spotify_urls.py
"""

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher

ALBUMS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "data", "albums.json"
)
CACHE_FILE = "/tmp/spotify_url_cache.json"

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")


def get_token():
    creds = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=b"grant_type=client_credentials",
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp["access_token"]


def _spotify_get(url, token, max_429_retries=5):
    """GET with iterative 429-retry. Returns (status, payload_or_None).
    status in: 'ok', 'token_expired', 'not_found', 'error', 'rate_limited_exhausted'."""
    for attempt in range(max_429_retries + 1):
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req) as resp:
                return "ok", json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = int(e.headers.get("Retry-After", "5") or "5")
                # Cap per-attempt wait; back off exponentially overall.
                wait = min(max(retry_after, 1), 30) * (2**attempt)
                print(
                    f"  429 rate-limited (attempt {attempt + 1}/{max_429_retries + 1}); "
                    f"sleeping {wait}s"
                )
                time.sleep(wait)
                continue
            if e.code == 401:
                return "token_expired", None
            if e.code == 404:
                return "not_found", None
            print(f"  HTTP {e.code} for {url}")
            return "error", None
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"  network error: {e}")
            if attempt < max_429_retries:
                time.sleep(2**attempt)
                continue
            return "error", None
    print("  rate-limit retries exhausted")
    return "rate_limited_exhausted", None


def search_album(token, title, artist):
    """Search Spotify for an album, return best matching URL or None,
    or the sentinel 'TOKEN_EXPIRED' when the access token needs refreshing.

    Uses market=US to avoid geographic bias (without it, broad searches
    return regional pop albums unrelated to the query). Tries a qualified
    search first, then a broad fallback. Per S3 spec, requires artist
    similarity >= 0.85 on the chosen result."""
    strategies = [
        # qualified field search
        {
            "q": f"album:{title} artist:{artist}",
            "type": "album",
            "limit": 5,
            "market": "US",
        },
        # broad fallback (some albums don't surface in field-qualified search)
        {"q": f"{title} {artist}", "type": "album", "limit": 10, "market": "US"},
    ]

    items: list[dict] = []
    for params in strategies:
        url = "https://api.spotify.com/v1/search?" + urllib.parse.urlencode(params)
        status, resp = _spotify_get(url, token)
        if status == "token_expired":
            return "TOKEN_EXPIRED"
        if status != "ok":
            return None
        items = resp.get("albums", {}).get("items", [])
        if items:
            break

    if not items:
        return None

    # Score: primary gate is artist similarity (>= 0.85). Title similarity
    # is a tie-breaker only — Spotify appends "Remaster" / "Legacy Edition"
    # / year suffixes to album names and we don't want to reject those.
    best_score = -1.0
    best_url = None
    best_artist_sim = 0.0
    title_lower = title.lower()
    artist_lower = artist.lower()

    for item in items:
        item_title = item.get("name", "").lower()
        item_artists = " ".join(a["name"].lower() for a in item.get("artists", []))
        artist_sim = SequenceMatcher(None, artist_lower, item_artists).ratio()
        if artist_sim < 0.85:
            continue
        title_sim = SequenceMatcher(None, title_lower, item_title).ratio()
        # Also accept when the album's title appears as a substring of the
        # Spotify name (Spotify often adds suffixes).
        if title_sim < 0.5 and title_lower not in item_title:
            continue
        score = artist_sim * 0.7 + title_sim * 0.3
        if score > best_score:
            best_score = score
            best_artist_sim = artist_sim
            best_url = item["external_urls"].get("spotify")

    return best_url if best_url else None


def main():
    # Load albums
    with open(ALBUMS_PATH) as f:
        albums = json.load(f)

    missing = [(i, a) for i, a in enumerate(albums) if not a.get("spotifyUrl")]
    print(f"Total albums: {len(albums)}")
    print(f"Missing Spotify URLs: {len(missing)}")

    if not missing:
        print("Nothing to do!")
        return

    # Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached results")

    token = get_token()
    found = 0
    not_found = 0
    errors = 0

    for count, (idx, album) in enumerate(missing, 1):
        title = album["title"]
        artist = album["artist"]
        cache_key = f"{artist}|{title}"

        if cache_key in cache:
            url = cache[cache_key]
        else:
            url = search_album(token, title, artist)
            if url == "TOKEN_EXPIRED":
                print("  Refreshing token...")
                token = get_token()
                url = search_album(token, title, artist)

            cache[cache_key] = url
            # Rate limiting: ~3 requests per second
            time.sleep(0.35)

        if url and url != "TOKEN_EXPIRED":
            albums[idx]["spotifyUrl"] = url
            found += 1
            status = "FOUND"
        else:
            not_found += 1
            status = "NOT FOUND"

        print(f"[{count}/{len(missing)}] {status}: {artist} - {title}")

        # Save cache every 25 albums
        if count % 25 == 0:
            with open(CACHE_FILE, "w") as f:
                json.dump(cache, f)

    # Final cache save
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

    # Write updated albums
    with open(ALBUMS_PATH, "w") as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Found: {found}, Not found: {not_found}")
    print(
        f"Total albums with Spotify URLs: {len([a for a in albums if a.get('spotifyUrl')])} / {len(albums)}"
    )


if __name__ == "__main__":
    main()

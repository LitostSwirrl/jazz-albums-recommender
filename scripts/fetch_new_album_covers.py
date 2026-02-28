#!/usr/bin/env python3
"""
Stage 3b: Fetch cover art from Cover Art Archive for newly discovered albums.
Tries multiple releases per release-group if first has no art.
Requires: /tmp/discovered_albums.json from Stage 2
Output: /tmp/new_album_covers.json
"""

import json
import time
import urllib.request
import urllib.parse
import urllib.error
import os
import sys

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

DISCOVERED_FILE = '/tmp/discovered_albums.json'
CACHE_FILE = '/tmp/new_album_covers.json'


def api_get(url, timeout=20):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (503, 429):
                time.sleep(5 * (attempt + 1))
                continue
            return None
        except Exception:
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            return None
    return None


def get_releases_for_group(rg_mbid):
    """Get all releases for a release-group."""
    url = f'https://musicbrainz.org/ws/2/release-group/{rg_mbid}?inc=releases&fmt=json'
    data = api_get(url)
    if not data:
        return []
    releases = data.get('releases', [])
    return [r['id'] for r in releases[:5]]  # Try up to 5 releases


def get_cover_art(release_mbid):
    """Get cover art URL from Cover Art Archive."""
    url = f'https://coverartarchive.org/release/{release_mbid}/'
    data = api_get(url)
    if not data or not data.get('images'):
        return None

    # Prefer front cover
    for img in data['images']:
        if img.get('front'):
            t = img.get('thumbnails', {})
            cover_url = t.get('large') or t.get('500') or img.get('image')
            if cover_url:
                return cover_url.replace('http://', 'https://')

    # Fallback to first image
    img = data['images'][0]
    t = img.get('thumbnails', {})
    cover_url = t.get('large') or t.get('500') or img.get('image')
    if cover_url:
        return cover_url.replace('http://', 'https://')

    return None


def find_cover_for_album(album):
    """Try to find cover art for an album, trying multiple releases."""
    rg_mbid = album.get('releaseGroupMbid')
    if not rg_mbid:
        return None

    # Get releases for this release-group
    time.sleep(1.1)
    release_ids = get_releases_for_group(rg_mbid)

    if not release_ids:
        return None

    # Try each release for cover art
    for rel_id in release_ids:
        time.sleep(1.2)
        cover = get_cover_art(rel_id)
        if cover:
            return cover

    return None


def main():
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    # Load discovered albums
    if not os.path.exists(DISCOVERED_FILE):
        print(f'ERROR: {DISCOVERED_FILE} not found. Run discover_albums.py first.')
        sys.exit(1)

    with open(DISCOVERED_FILE) as f:
        discovered = json.load(f)

    # Flatten all discovered albums
    all_albums = []
    for artist_data in discovered.values():
        all_albums.extend(artist_data.get('albums', []))

    print(f'Total albums to find covers for: {len(all_albums)}')

    # Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f'Cache loaded: {len(cache)} entries')

    total = len(all_albums)
    found = sum(1 for v in cache.values() if v)
    not_found_count = 0

    for i, album in enumerate(all_albums):
        if i < start_from:
            continue

        aid = album['id']
        if aid in cache:
            continue

        print(f'[{i+1}/{total}] {album["title"]} - {album["artist"]}...', end=' ', flush=True)

        cover = find_cover_for_album(album)

        if cover:
            cache[aid] = cover
            found += 1
            print(f'FOUND')
        else:
            cache[aid] = None
            not_found_count += 1
            print('NOT FOUND')

        # Save every 10
        if (i + 1) % 10 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2)

    # Final save
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

    found_total = sum(1 for v in cache.values() if v)
    print(f'\n=== Results ===')
    print(f'Total: {len(cache)}')
    print(f'Found: {found_total}')
    print(f'Not found: {len(cache) - found_total}')
    print(f'Cache: {CACHE_FILE}')


if __name__ == '__main__':
    main()

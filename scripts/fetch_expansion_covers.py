#!/usr/bin/env python3
"""
Stage 4a: Fetch cover art from Cover Art Archive for expansion albums.
Tries multiple releases per release-group if first has no art.
Requires: /tmp/expansion_discovered.json from Stage 2
Output: /tmp/expansion_covers.json
"""

import json
import time
import urllib.request
import urllib.error
import os
import sys

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

DISCOVERED_FILE = '/tmp/expansion_discovered.json'
CACHE_FILE = '/tmp/expansion_covers.json'


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
    return [r['id'] for r in releases[:5]]


def get_cover_art(release_mbid):
    """Get cover art URL from Cover Art Archive."""
    url = f'https://coverartarchive.org/release/{release_mbid}/'
    data = api_get(url)
    if not data or not data.get('images'):
        return None

    for img in data['images']:
        if img.get('front'):
            t = img.get('thumbnails', {})
            cover_url = t.get('large') or t.get('500') or img.get('image')
            if cover_url:
                return cover_url.replace('http://', 'https://')

    img = data['images'][0]
    t = img.get('thumbnails', {})
    cover_url = t.get('large') or t.get('500') or img.get('image')
    if cover_url:
        return cover_url.replace('http://', 'https://')

    return None


def make_proxy_url(raw_url):
    """Wrap in wsrv.nl proxy for consistent sizing and WebP."""
    if not raw_url:
        return None
    encoded = urllib.request.quote(raw_url, safe='')
    return f'https://wsrv.nl/?url={encoded}&w=500&output=webp'


def find_cover_for_album(album):
    """Try to find cover art for an album, trying multiple releases."""
    rg_mbid = album.get('releaseGroupMbid')
    if not rg_mbid:
        return None

    time.sleep(1.1)
    release_ids = get_releases_for_group(rg_mbid)

    if not release_ids:
        return None

    for rel_id in release_ids:
        time.sleep(1.2)
        cover = get_cover_art(rel_id)
        if cover:
            return make_proxy_url(cover)

    return None


def main():
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    if not os.path.exists(DISCOVERED_FILE):
        print(f'ERROR: {DISCOVERED_FILE} not found. Run discover_expansion_albums.py first.')
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
            print('FOUND')
        else:
            cache[aid] = None
            print('NOT FOUND')

        if (i + 1) % 10 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2)

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

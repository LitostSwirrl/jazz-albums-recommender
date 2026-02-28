#!/usr/bin/env python3
"""
Fix broken cover art URLs using MusicBrainz API.
Optimized: one search per album, check top 3 results for CAA art.
Writes fixes incrementally to output file.
"""

import json
import time
import urllib.request
import urllib.parse
import urllib.error
import sys
import os

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

FIXES_FILE = '/tmp/cover_fixes_all.json'

def api_get(url: str) -> dict | None:
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
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

def find_cover(title: str, artist: str) -> str | None:
    query = urllib.parse.quote(f'"{title}" AND artist:"{artist}"')
    url = f'https://musicbrainz.org/ws/2/release/?query={query}&fmt=json&limit=10'
    data = api_get(url)
    time.sleep(1.2)

    if not data or not data.get('releases'):
        return None

    for rel in data['releases'][:6]:
        mbid = rel['id']
        caa = api_get(f'https://coverartarchive.org/release/{mbid}/')
        time.sleep(1.2)
        if not caa or not caa.get('images'):
            continue
        for img in caa['images']:
            if img.get('front'):
                t = img.get('thumbnails', {})
                return t.get('large') or t.get('500') or img.get('image')
        img = caa['images'][0]
        t = img.get('thumbnails', {})
        return t.get('large') or t.get('500') or img.get('image')

    return None

def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    albums_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'albums.json')
    albums = json.load(open(albums_path))
    broken_ids = open('/tmp/broken_albums.txt').read().strip().split('\n')
    broken = [a for a in albums if a['id'] in set(broken_ids)]

    # Load existing fixes
    fixes = {}
    if os.path.exists(FIXES_FILE):
        try:
            fixes = json.load(open(FIXES_FILE))
        except:
            pass

    total = len(broken)
    for i, album in enumerate(broken):
        if i < start:
            continue
        if album['id'] in fixes:
            continue

        print(f'[{i+1}/{total}] {album["title"]} - {album["artist"]}')
        url = find_cover(album['title'], album['artist'])
        if url:
            url = url.replace('http://', 'https://')
            fixes[album['id']] = url
            print(f'  FOUND: {url[:80]}')
            # Save incrementally
            json.dump(fixes, open(FIXES_FILE, 'w'), indent=2)
        else:
            print(f'  NOT FOUND')

    print(f'\nTotal fixed: {len(fixes)}/{total}')
    not_fixed = [a['id'] for a in broken if a['id'] not in fixes]
    if not_fixed:
        print(f'Still missing ({len(not_fixed)}): {not_fixed}')

if __name__ == '__main__':
    main()

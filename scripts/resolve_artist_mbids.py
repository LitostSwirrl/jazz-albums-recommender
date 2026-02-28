#!/usr/bin/env python3
"""
Stage 1: Map all 262 artists to MusicBrainz artist MBIDs.
Searches MB API, prefers results with "jazz" disambiguation.
Cache: /tmp/artist_mbids.json
Rate limit: 1 req/sec
"""

import json
import time
import urllib.request
import urllib.parse
import urllib.error
import os
import sys
import re

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
CACHE_FILE = '/tmp/artist_mbids.json'


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


def search_artist_mbid(name):
    """Search MusicBrainz for an artist, prefer jazz-related results."""
    encoded = urllib.parse.quote(name)
    url = f'https://musicbrainz.org/ws/2/artist/?query=artist:{encoded}&fmt=json&limit=10'
    data = api_get(url)
    if not data:
        return None

    artists = data.get('artists', [])
    if not artists:
        return None

    name_lower = name.lower().strip()

    # First pass: exact name match with jazz tag or disambiguation
    for a in artists:
        a_name = a.get('name', '').lower().strip()
        if a_name == name_lower:
            disambig = (a.get('disambiguation') or '').lower()
            tags = [t.get('name', '').lower() for t in a.get('tags', [])]
            if 'jazz' in disambig or any('jazz' in t for t in tags):
                return a['id']

    # Second pass: exact name match
    for a in artists:
        if a.get('name', '').lower().strip() == name_lower:
            return a['id']

    # Third pass: name without "The" prefix
    name_no_the = name_lower
    if name_no_the.startswith('the '):
        name_no_the = name_no_the[4:]
    for a in artists:
        a_name = a.get('name', '').lower().strip()
        if a_name.startswith('the '):
            a_name = a_name[4:]
        if a_name == name_no_the:
            return a['id']

    # Fourth pass: cleaned name match (remove punctuation)
    name_clean = re.sub(r'[^a-z0-9 ]', '', name_lower)
    for a in artists:
        a_clean = re.sub(r'[^a-z0-9 ]', '', a.get('name', '').lower())
        if a_clean == name_clean and a.get('score', 0) >= 80:
            return a['id']

    # Fallback: high-score first result
    if artists[0].get('score', 0) >= 95:
        return artists[0]['id']

    return None


def main():
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    with open(ARTISTS_FILE) as f:
        artists = json.load(f)

    # Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f'Cache loaded: {len(cache)} entries')

    total = len(artists)
    found = sum(1 for v in cache.values() if v)
    not_found = sum(1 for v in cache.values() if v is None)
    skipped = 0

    for i, artist in enumerate(artists):
        if i < start_from:
            continue

        aid = artist['id']
        if aid in cache:
            skipped += 1
            continue

        name = artist['name']
        print(f'[{i+1}/{total}] {name}...', end=' ', flush=True)

        time.sleep(1.1)
        mbid = search_artist_mbid(name)

        if mbid:
            cache[aid] = mbid
            found += 1
            print(f'FOUND ({mbid[:8]}...)')
        else:
            cache[aid] = None
            not_found += 1
            print('NOT FOUND')

        # Save every 10
        if (i + 1) % 10 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2)

    # Final save
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

    print(f'\n=== Results ===')
    print(f'Total artists: {total}')
    print(f'Found MBID: {found}')
    print(f'Not found: {not_found}')
    print(f'Skipped (cached): {skipped}')
    print(f'Cache: {CACHE_FILE}')

    # List not found
    missing = [aid for aid, mbid in cache.items() if mbid is None]
    if missing:
        print(f'\nMissing MBIDs ({len(missing)}):')
        artist_map = {a['id']: a['name'] for a in artists}
        for aid in missing:
            print(f'  {artist_map.get(aid, aid)}')


if __name__ == '__main__':
    main()

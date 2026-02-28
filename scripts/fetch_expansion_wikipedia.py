#!/usr/bin/env python3
"""
Stage 4c: Fetch Wikipedia URLs for expansion albums.
Queries Wikipedia REST API to find article URLs for each album.
Requires: /tmp/expansion_discovered.json from Stage 2
Output: /tmp/expansion_wikipedia.json
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

DISCOVERED_FILE = '/tmp/expansion_discovered.json'
CACHE_FILE = '/tmp/expansion_wikipedia.json'


def wiki_get(title_query):
    """Fetch Wikipedia page summary. Returns (url, extract) or (None, None)."""
    encoded = urllib.parse.quote(title_query.replace(' ', '_'))
    url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}'
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            if data.get('type') == 'standard':
                page_url = data.get('content_urls', {}).get('desktop', {}).get('page')
                return page_url, data.get('extract', '')
    except Exception:
        pass
    return None, None


def find_wikipedia_url(title, artist):
    """Try multiple query patterns to find a Wikipedia article for an album."""
    queries = [
        f'{title} ({artist} album)',
        f'{title} (album)',
        f'{title} ({artist.split()[-1]} album)' if ' ' in artist else None,
        title,
    ]

    title_lower = title.lower()
    artist_lower = artist.lower()

    for query in queries:
        if not query:
            continue
        time.sleep(0.5)
        page_url, extract = wiki_get(query)
        if page_url and extract:
            extract_lower = extract.lower()
            # Validate: must mention artist or be about music
            if (artist_lower.split()[-1].lower() in extract_lower or
                    'album' in extract_lower or
                    'jazz' in extract_lower or
                    'record' in extract_lower or
                    title_lower in extract_lower):
                return page_url

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

    print(f'Total albums to find Wikipedia URLs for: {len(all_albums)}')

    # Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f'Cache loaded: {len(cache)} entries')

    total = len(all_albums)

    for i, album in enumerate(all_albums):
        if i < start_from:
            continue

        aid = album['id']
        if aid in cache:
            continue

        title = album['title']
        artist = album['artist']
        print(f'[{i+1}/{total}] {title} - {artist}...', end=' ', flush=True)

        wiki_url = find_wikipedia_url(title, artist)

        cache[aid] = wiki_url
        if wiki_url:
            print('FOUND')
        else:
            print('not found')

        if (i + 1) % 10 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2)

    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

    found = sum(1 for v in cache.values() if v)
    print(f'\n=== Results ===')
    print(f'Total: {len(cache)}')
    print(f'Found: {found} ({found * 100 // max(len(cache), 1)}%)')
    print(f'Not found: {len(cache) - found}')
    print(f'Cache: {CACHE_FILE}')


if __name__ == '__main__':
    main()

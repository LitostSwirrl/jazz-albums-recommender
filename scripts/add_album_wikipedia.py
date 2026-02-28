#!/usr/bin/env python3
"""
Fetch Wikipedia URLs for albums that have Wikipedia articles.
Uses Wikipedia REST API to search for album articles.
Cache: /tmp/album_wikipedia.json
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
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')
CACHE_FILE = '/tmp/album_wikipedia.json'

BAD_INDICATORS = [
    'may refer to:', 'may also refer to', 'is a disambiguation',
    'disambiguation page', 'is a list of', 'is the discography',
]


def api_get(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 503):
                time.sleep(3 * (attempt + 1))
                continue
            return None
        except Exception:
            if attempt < 2:
                time.sleep(2)
                continue
            return None
    return None


def find_wikipedia_url(title, artist):
    """Try to find the Wikipedia URL for an album."""
    clean_title = re.sub(r'\s*\(.*?\)', '', title).strip()

    queries = [
        f"{clean_title} ({artist} album)",
        f"{clean_title} (album)",
    ]

    for query in queries:
        encoded = urllib.parse.quote(query.replace(' ', '_'))
        url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}'

        data = api_get(url)
        if not data:
            time.sleep(0.3)
            continue

        extract = data.get('extract', '')
        wiki_url = data.get('content_urls', {}).get('desktop', {}).get('page', '')

        # Validate
        if not extract or len(extract) < 30:
            time.sleep(0.3)
            continue

        lower = extract.lower()

        # Reject disambiguation
        if any(bad.lower() in lower for bad in BAD_INDICATORS):
            time.sleep(0.3)
            continue

        # Must be about music
        music_words = ['album', 'jazz', 'record', 'music', 'recording', 'released', 'label', 'studio']
        if not any(w in lower for w in music_words):
            time.sleep(0.3)
            continue

        # Must mention artist
        artist_lower = artist.lower()
        artist_parts = artist_lower.split()
        artist_last = artist_parts[-1] if artist_parts else ''
        if not (artist_lower in lower or artist_last in lower):
            significant = [w for w in artist_parts if len(w) > 3 and w not in ('the', 'and', 'with')]
            if not any(w in lower for w in significant):
                time.sleep(0.3)
                continue

        return wiki_url

    return None


def main():
    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f'Loaded cache with {len(cache)} entries')

    # Only process albums not already cached
    to_process = [a for a in albums if a['id'] not in cache]
    print(f'Albums to process: {len(to_process)} (skipping {len(cache)} cached)')

    start_from = 0
    if len(sys.argv) > 1:
        try:
            start_from = int(sys.argv[1])
        except ValueError:
            pass

    found = 0
    total = len(to_process)

    for i, album in enumerate(to_process[start_from:], start=start_from):
        aid = album['id']
        title = album['title']
        artist = album['artist']

        print(f'[{i+1}/{total}] {aid}...', end=' ', flush=True)

        wiki_url = find_wikipedia_url(title, artist)
        if wiki_url:
            cache[aid] = wiki_url
            found += 1
            print(f'FOUND')
        else:
            cache[aid] = None
            print('NOT FOUND')

        if (i + 1) % 20 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)

        time.sleep(0.5)

    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    total_found = sum(1 for v in cache.values() if v)
    print(f'\n=== Wikipedia URLs ===')
    print(f'Found this run: {found}')
    print(f'Total found: {total_found}/{len(cache)}')
    print(f'Cache: {CACHE_FILE}')


if __name__ == '__main__':
    main()

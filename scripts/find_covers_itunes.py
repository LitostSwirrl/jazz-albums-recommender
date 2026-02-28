#!/usr/bin/env python3
"""
Find cover art from iTunes for albums missing covers.
iTunes artwork (mzstatic.com) works directly in <img> tags, no proxy needed.
Cache: /tmp/itunes_covers.json
"""

import json
import time
import urllib.request
import urllib.parse
import os
import sys
import re

CACHE_FILE = '/tmp/itunes_covers.json'
ALBUMS_FILE = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'albums.json')


def normalize(s: str) -> str:
    """Normalize for fuzzy matching."""
    s = s.lower()
    s = re.sub(r'\s*\(.*?\)\s*', ' ', s)
    s = re.sub(r'\s*\[.*?\]\s*', ' ', s)
    s = re.sub(r'[^\w\s]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def title_match(query_title: str, result_title: str) -> bool:
    """Fuzzy title matching."""
    q = normalize(query_title)
    r = normalize(result_title)
    if q == r or q in r or r in q:
        return True
    q_words = set(q.split())
    r_words = set(r.split())
    if not q_words:
        return False
    return len(q_words & r_words) >= max(1, len(q_words) * 0.6)


def search_itunes_cover(title: str, artist: str) -> str | None:
    """Search iTunes for album artwork, return 600x600 URL or None."""
    # Try title + artist first
    query = urllib.parse.quote(f'{title} {artist}')
    url = f'https://itunes.apple.com/search?term={query}&media=music&entity=album&limit=10&country=US'

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'JazzAlbumsRecommender/1.0',
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f'  ERROR: {e}')
        return None

    if data.get('results'):
        artist_lower = artist.lower()
        for r in data['results']:
            r_artist = r.get('artistName', '').lower()
            r_title = r.get('collectionName', '')

            if (artist_lower in r_artist or r_artist in artist_lower) and \
               title_match(title, r_title):
                artwork = r.get('artworkUrl100', '')
                if artwork:
                    return artwork.replace('100x100bb', '600x600bb')

    return None


def search_artist_only_cover(title: str, artist: str) -> str | None:
    """Search by artist only, fuzzy match title for artwork."""
    query = urllib.parse.quote(artist)
    url = f'https://itunes.apple.com/search?term={query}&media=music&entity=album&limit=25&country=US'

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'JazzAlbumsRecommender/1.0',
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None

    if data.get('results'):
        for r in data['results']:
            r_title = r.get('collectionName', '')
            if title_match(title, r_title):
                artwork = r.get('artworkUrl100', '')
                if artwork:
                    return artwork.replace('100x100bb', '600x600bb')

    return None


def main():
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    # Target: albums missing cover art
    targets = [a for a in albums if not a.get('coverUrl')]
    print(f'Albums missing cover art: {len(targets)}')

    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                cache = json.load(f)
            print(f'Cache loaded: {len(cache)} entries')
        except Exception:
            pass

    found = 0

    for i, album in enumerate(targets):
        if i < start_from:
            continue

        aid = album['id']
        if aid in cache:
            continue

        title = album['title']
        artist = album['artist']
        print(f'[{i+1}/{len(targets)}] {title} - {artist}...', end=' ', flush=True)

        # Strategy 1: title + artist
        time.sleep(3.1)
        cover = search_itunes_cover(title, artist)

        # Strategy 2: artist-only with fuzzy title match
        if not cover:
            time.sleep(3.1)
            cover = search_artist_only_cover(title, artist)

        if cover:
            cache[aid] = cover
            found += 1
            print('FOUND')
        else:
            cache[aid] = None
            print('NOT FOUND')

        if (i + 1) % 5 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)

    # Final save
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    found_total = sum(1 for v in cache.values() if v)
    print(f'\n=== Results ===')
    print(f'Total searched: {len(cache)}')
    print(f'Found covers: {found_total}')
    print(f'Not found: {len(cache) - found_total}')


if __name__ == '__main__':
    main()

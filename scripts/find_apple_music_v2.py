#!/usr/bin/env python3
"""
Find Apple Music URLs for albums still missing them, with relaxed matching.
Tries multiple search strategies and country variants (US, JP, GB).
Also saves artwork URLs for cover art fallback.
Cache: /tmp/apple_music_links_v2.json
"""

import json
import time
import urllib.request
import urllib.parse
import os
import sys
import re

CACHE_FILE = '/tmp/apple_music_links_v2.json'
ALBUMS_FILE = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'albums.json')

COUNTRIES = ['US', 'JP', 'GB']


def normalize(s: str) -> str:
    """Normalize string for fuzzy matching."""
    s = s.lower()
    s = re.sub(r'\s*\(.*?\)\s*', ' ', s)  # Remove parentheticals
    s = re.sub(r'\s*\[.*?\]\s*', ' ', s)  # Remove brackets
    s = re.sub(r'[^\w\s]', '', s)           # Remove punctuation
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def title_match(query_title: str, result_title: str) -> bool:
    """Fuzzy title matching."""
    q = normalize(query_title)
    r = normalize(result_title)

    if q == r:
        return True
    if q in r or r in q:
        return True

    # Word overlap: at least 60% of query words found in result
    q_words = set(q.split())
    r_words = set(r.split())
    if not q_words:
        return False
    overlap = len(q_words & r_words)
    return overlap >= max(1, len(q_words) * 0.6)


def search_itunes(title: str, artist: str, country: str = 'US') -> dict | None:
    """Search iTunes, return {url, artworkUrl} or None."""
    query = urllib.parse.quote(f'{title} {artist}')
    url = f'https://itunes.apple.com/search?term={query}&media=music&entity=album&limit=10&country={country}'

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'JazzAlbumsRecommender/1.0',
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f'  ERROR ({country}): {e}')
        return None

    if not data.get('results'):
        return None

    artist_lower = artist.lower()

    for r in data['results']:
        r_artist = r.get('artistName', '').lower()
        r_title = r.get('collectionName', '')

        # Artist must match
        if artist_lower not in r_artist and r_artist not in artist_lower:
            continue

        # Title must fuzzy-match
        if not title_match(title, r_title):
            continue

        am_url = r.get('collectionViewUrl', '')
        if '?uo=' in am_url:
            am_url = am_url.split('?uo=')[0]

        artwork = r.get('artworkUrl100', '')
        if artwork:
            artwork = artwork.replace('100x100bb', '600x600bb')

        return {'url': am_url, 'artworkUrl': artwork}

    return None


def search_artist_only(title: str, artist: str, country: str = 'US') -> dict | None:
    """Search by artist name only, then fuzzy match title from results."""
    query = urllib.parse.quote(artist)
    url = f'https://itunes.apple.com/search?term={query}&media=music&entity=album&limit=25&country={country}'

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'JazzAlbumsRecommender/1.0',
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None

    if not data.get('results'):
        return None

    for r in data['results']:
        r_title = r.get('collectionName', '')
        if title_match(title, r_title):
            am_url = r.get('collectionViewUrl', '')
            if '?uo=' in am_url:
                am_url = am_url.split('?uo=')[0]
            artwork = r.get('artworkUrl100', '')
            if artwork:
                artwork = artwork.replace('100x100bb', '600x600bb')
            return {'url': am_url, 'artworkUrl': artwork}

    return None


def main():
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    # Target: albums missing Apple Music URL
    targets = [a for a in albums if not a.get('appleMusicUrl')]
    print(f'Albums missing Apple Music: {len(targets)}')

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

        result = None

        # Strategy 1: title + artist search, try each country
        for country in COUNTRIES:
            time.sleep(3.1)
            result = search_itunes(title, artist, country)
            if result:
                print(f'FOUND ({country})')
                break

        # Strategy 2: artist-only search with fuzzy title match
        if not result:
            for country in COUNTRIES:
                time.sleep(3.1)
                result = search_artist_only(title, artist, country)
                if result:
                    print(f'FOUND (artist-only, {country})')
                    break

        if result:
            cache[aid] = result
            found += 1
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
    print(f'Found: {found_total}')
    print(f'Not found: {len(cache) - found_total}')
    artwork_count = sum(1 for v in cache.values() if isinstance(v, dict) and v.get('artworkUrl'))
    print(f'With artwork: {artwork_count}')


if __name__ == '__main__':
    main()

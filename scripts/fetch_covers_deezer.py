#!/usr/bin/env python3
"""
Fetch missing album cover art from Deezer API.
Deezer requires NO authentication and returns 1000x1000 cover images.

Endpoint: https://api.deezer.com/search/album?q={artist}+{title}
Returns: cover_xl (1000x1000 JPEG URL)

Usage:
    python3 scripts/fetch_covers_deezer.py
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
CACHE_FILE = '/tmp/deezer_covers.json'

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history)',
    'Accept': 'application/json',
}


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def normalize_title(title):
    """Normalize album title for comparison."""
    title = title.lower().strip()
    title = re.sub(r'\([^)]*\)', '', title)  # Remove parentheticals
    title = re.sub(r'[^\w\s]', '', title)  # Remove punctuation
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def search_deezer(artist_name, album_title):
    """Search Deezer for an album and return cover_xl URL if found."""
    # Try different query strategies
    queries = [
        f'{artist_name} {album_title}',
        album_title,
    ]

    for query in queries:
        encoded = urllib.parse.quote(query)
        url = f'https://api.deezer.com/search/album?q={encoded}&limit=5'

        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            results = data.get('data', [])
            if not results:
                continue

            # Match by title similarity
            norm_target = normalize_title(album_title)
            norm_artist = artist_name.lower()

            for result in results:
                r_title = normalize_title(result.get('title', ''))
                r_artist = result.get('artist', {}).get('name', '').lower()

                # Check if title matches (fuzzy)
                title_match = (
                    norm_target in r_title or
                    r_title in norm_target or
                    norm_target == r_title
                )

                # Check if artist matches
                artist_parts = norm_artist.split()
                artist_match = any(part in r_artist for part in artist_parts if len(part) > 2)

                if title_match and artist_match:
                    cover = result.get('cover_xl') or result.get('cover_big') or result.get('cover_medium')
                    if cover:
                        return cover

            # If first query didn't work, try next
        except Exception as e:
            print(f'  Deezer error: {e}')

        time.sleep(1)

    return None


def main():
    with open(ALBUMS_FILE) as f:
        albums = json.load(f)
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)

    artist_map = {a['id']: a['name'] for a in artists}

    # Find albums missing covers
    missing = [a for a in albums if not a.get('coverUrl')]
    print(f'Albums missing cover art: {len(missing)}')

    cache = load_cache()
    found = 0
    not_found = 0

    for i, album in enumerate(missing):
        aid = album['id']
        if aid in cache:
            if cache[aid]:
                found += 1
            else:
                not_found += 1
            continue

        artist_name = artist_map.get(album.get('artistId', ''), '')
        title = album.get('title', '')
        print(f'[{i+1}/{len(missing)}] {artist_name} - {title}')

        cover = search_deezer(artist_name, title)
        if cover:
            print(f'  FOUND: {cover[:80]}')
            cache[aid] = cover
            found += 1
        else:
            print(f'  Not found')
            cache[aid] = None
            not_found += 1

        if (i + 1) % 5 == 0:
            save_cache(cache)

        time.sleep(2)  # Be respectful

    save_cache(cache)
    print(f'\nResults: {found} found, {not_found} not found')


if __name__ == '__main__':
    main()

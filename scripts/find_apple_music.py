#!/usr/bin/env python3
"""
Find Apple Music URLs for all albums using the iTunes Search API (free, no auth).
Rate limit: ~20 req/min to be safe.
"""

import json
import time
import urllib.request
import urllib.parse
import os
import sys

LINKS_FILE = '/tmp/apple_music_links.json'

def search_itunes(title: str, artist: str) -> str | None:
    """Search iTunes for an album and return the Apple Music URL."""
    query = urllib.parse.quote(f'{title} {artist}')
    url = f'https://itunes.apple.com/search?term={query}&media=music&entity=album&limit=5'

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f'  ERROR: {e}')
        return None

    if not data.get('results'):
        return None

    # Try to match by artist name (case-insensitive)
    artist_lower = artist.lower()
    title_lower = title.lower()

    for r in data['results']:
        r_artist = r.get('artistName', '').lower()
        r_title = r.get('collectionName', '').lower()

        # Good match: artist name appears in result and title is similar
        if (artist_lower in r_artist or r_artist in artist_lower) and \
           (title_lower in r_title or r_title in title_lower or
            any(word in r_title for word in title_lower.split() if len(word) > 3)):
            am_url = r['collectionViewUrl']
            # Remove tracking parameter
            if '?uo=' in am_url:
                am_url = am_url.split('?uo=')[0]
            return am_url

    # Fallback: just check if first result has matching artist
    r = data['results'][0]
    if artist_lower in r.get('artistName', '').lower():
        am_url = r['collectionViewUrl']
        if '?uo=' in am_url:
            am_url = am_url.split('?uo=')[0]
        return am_url

    return None


def main():
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    albums_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'albums.json')
    with open(albums_path) as f:
        albums = json.load(f)

    # Load existing results
    results = {}
    if os.path.exists(LINKS_FILE):
        try:
            with open(LINKS_FILE) as f:
                results = json.load(f)
        except Exception:
            pass

    total = len(albums)
    found = 0
    not_found = 0

    for i, album in enumerate(albums):
        if i < start_from:
            continue

        aid = album['id']
        if aid in results:
            continue

        title = album['title']
        artist = album['artist']

        url = search_itunes(title, artist)
        time.sleep(3.1)  # Rate limit: ~20/min

        if url:
            results[aid] = url
            found += 1
            print(f'[{i+1}/{total}] {title} - {artist} → FOUND')
        else:
            results[aid] = None
            not_found += 1
            print(f'[{i+1}/{total}] {title} - {artist} → NOT FOUND')

        # Save every 10
        if (i + 1) % 10 == 0:
            with open(LINKS_FILE, 'w') as f:
                json.dump(results, f, indent=2)

    # Final save
    with open(LINKS_FILE, 'w') as f:
        json.dump(results, f, indent=2)

    found_total = sum(1 for v in results.values() if v)
    print(f'\n=== Results ===')
    print(f'Found: {found_total}/{total}')
    print(f'Not found: {total - found_total}')

    # List not found
    not_found_list = [k for k, v in results.items() if not v]
    if not_found_list:
        print(f'\nNot found albums: {not_found_list}')


if __name__ == '__main__':
    main()

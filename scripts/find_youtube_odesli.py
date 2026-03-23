#!/usr/bin/env python3
"""
Find YouTube and YouTube Music URLs via Odesli (song.link) API.
Queries albums that have Spotify URLs but are missing YouTube/YouTube Music.
Also picks up any missing Apple Music links as a bonus.

Rate limit: 10 req/min (6s between requests).
Cache: /tmp/youtube_odesli_cache.json
Usage: python3 find_youtube_odesli.py [start_index]
"""

import json
import time
import urllib.request
import urllib.parse
import urllib.error
import os
import sys

CACHE_FILE = '/tmp/youtube_odesli_cache.json'
ALBUMS_FILE = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'albums.json')


def query_odesli(url: str) -> dict | None:
    """Query Odesli API with a music URL, return platform links."""
    encoded = urllib.parse.quote(url, safe='')
    api_url = f'https://api.song.link/v1-alpha.1/links?url={encoded}&userCountry=US'

    req = urllib.request.Request(api_url, headers={
        'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history)',
    })

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())
            links = data.get('linksByPlatform', {})
            result = {}
            if links.get('youtube', {}).get('url'):
                result['youtubeUrl'] = links['youtube']['url']
            if links.get('youtubeMusic', {}).get('url'):
                result['youtubeMusicUrl'] = links['youtubeMusic']['url']
            if links.get('appleMusic', {}).get('url'):
                result['appleMusicUrl'] = links['appleMusic']['url']
            if links.get('spotify', {}).get('url'):
                result['spotifyUrl'] = links['spotify']['url']
            return result
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}
            if e.code == 429:
                wait = 15 * (attempt + 1)
                print(f'  Rate limited, waiting {wait}s...', flush=True)
                time.sleep(wait)
                continue
            if attempt < 2:
                time.sleep(5)
                continue
            return None
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
                continue
            print(f'  ERROR: {e}')
            return None
    return None


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_cache(cache: dict):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def main():
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    cache = load_cache()
    print(f'Loaded {len(cache)} cached entries')

    # Target: albums with Spotify URL but missing YouTube or YouTube Music
    targets = []
    for album in albums:
        spotify = album.get('spotifyUrl')
        if not spotify:
            continue
        missing_yt = not album.get('youtubeUrl')
        missing_ytm = not album.get('youtubeMusicUrl')
        missing_am = not album.get('appleMusicUrl')
        if missing_yt or missing_ytm or missing_am:
            targets.append(album)

    print(f'\nTarget albums (have Spotify, missing YT/YTM/AM): {len(targets)}')

    found_yt = 0
    found_ytm = 0
    found_am = 0
    errors = 0

    for i, album in enumerate(targets):
        if i < start_from:
            continue

        aid = album['id']
        if aid in cache:
            continue

        spotify_url = album['spotifyUrl']
        print(f'[{i+1}/{len(targets)}] {album["title"]} - {album["artist"]}...', end=' ', flush=True)

        time.sleep(6.1)
        result = query_odesli(spotify_url)

        if result is None:
            cache[aid] = {'error': True}
            errors += 1
            print('ERROR')
        elif result:
            cache[aid] = result
            parts = []
            if result.get('youtubeUrl') and not album.get('youtubeUrl'):
                found_yt += 1
                parts.append('YouTube')
            if result.get('youtubeMusicUrl') and not album.get('youtubeMusicUrl'):
                found_ytm += 1
                parts.append('YT Music')
            if result.get('appleMusicUrl') and not album.get('appleMusicUrl'):
                found_am += 1
                parts.append('Apple')
            print(f'FOUND: {", ".join(parts)}' if parts else 'no new links')
        else:
            cache[aid] = {}
            print('NOT FOUND')

        if (i + 1) % 5 == 0:
            save_cache(cache)
            if (i + 1) % 50 == 0:
                print(f'\n  --- Checkpoint: {i+1}/{len(targets)}, +{found_yt} YT, +{found_ytm} YTM, +{found_am} AM ---\n')

    save_cache(cache)

    print(f'\n{"="*50}')
    print(f'Results:')
    print(f'  YouTube:       +{found_yt}')
    print(f'  YouTube Music: +{found_ytm}')
    print(f'  Apple Music:   +{found_am}')
    print(f'  Errors:         {errors}')
    print(f'  Total cached:   {len(cache)}')


if __name__ == '__main__':
    main()

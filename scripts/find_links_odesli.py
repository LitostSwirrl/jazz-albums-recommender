#!/usr/bin/env python3
"""
Find Spotify and YouTube URLs via Odesli (song.link) API.
Pass 1: Query with Apple Music URLs for albums missing Spotify/YouTube.
Pass 2: Query with Spotify URLs for albums still missing YouTube.
Rate limit: 10 req/min (6s between requests).
Cache: /tmp/odesli_links.json
"""

import json
import time
import urllib.request
import urllib.parse
import urllib.error
import os
import sys

CACHE_FILE = '/tmp/odesli_links.json'
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
            if links.get('spotify', {}).get('url'):
                result['spotifyUrl'] = links['spotify']['url']
            if links.get('youtube', {}).get('url'):
                result['youtubeUrl'] = links['youtube']['url']
            if links.get('youtubeMusic', {}).get('url'):
                result['youtubeMusicUrl'] = links['youtubeMusic']['url']
            if links.get('appleMusic', {}).get('url'):
                result['appleMusicUrl'] = links['appleMusic']['url']
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
    pass_num = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    cache = load_cache()
    print(f'Loaded {len(cache)} cached entries')

    if pass_num == 1:
        # Pass 1: Albums with Apple Music but missing Spotify or YouTube
        targets = []
        for album in albums:
            am_url = album.get('appleMusicUrl')
            if not am_url:
                continue
            missing_spotify = not album.get('spotifyUrl')
            missing_youtube = not album.get('youtubeUrl')
            if missing_spotify or missing_youtube:
                targets.append(album)

        print(f'\n=== Pass 1: Apple Music → Spotify/YouTube ===')
        print(f'Target albums: {len(targets)}')

        found_spotify = 0
        found_youtube = 0

        for i, album in enumerate(targets):
            if i < start_from:
                continue

            aid = album['id']
            cache_key = f'pass1:{aid}'
            if cache_key in cache:
                continue

            am_url = album['appleMusicUrl']
            print(f'[{i+1}/{len(targets)}] {album["title"]} - {album["artist"]}...', end=' ', flush=True)

            time.sleep(6.1)
            result = query_odesli(am_url)

            if result is None:
                cache[cache_key] = {'error': True}
                print('ERROR')
            elif result:
                cache[cache_key] = result
                parts = []
                if result.get('spotifyUrl') and not album.get('spotifyUrl'):
                    found_spotify += 1
                    parts.append('Spotify')
                if (result.get('youtubeUrl') or result.get('youtubeMusicUrl')) and not album.get('youtubeUrl'):
                    found_youtube += 1
                    parts.append('YouTube')
                print(f'FOUND: {", ".join(parts)}' if parts else 'no new links')
            else:
                cache[cache_key] = {}
                print('NOT FOUND')

            if (i + 1) % 5 == 0:
                save_cache(cache)

        save_cache(cache)
        print(f'\nPass 1 results: +{found_spotify} Spotify, +{found_youtube} YouTube')

    elif pass_num == 2:
        # Pass 2: Use newly found Spotify URLs to find YouTube
        # First, build effective Spotify map from cache
        spotify_from_cache = {}
        for key, val in cache.items():
            if key.startswith('pass1:') and isinstance(val, dict) and val.get('spotifyUrl'):
                aid = key.replace('pass1:', '')
                spotify_from_cache[aid] = val['spotifyUrl']

        targets = []
        for album in albums:
            aid = album['id']
            if album.get('youtubeUrl'):
                continue
            # Check if we have a YouTube from pass1 already
            p1 = cache.get(f'pass1:{aid}', {})
            if isinstance(p1, dict) and (p1.get('youtubeUrl') or p1.get('youtubeMusicUrl')):
                continue
            # Need a Spotify URL to query with
            spotify = album.get('spotifyUrl') or spotify_from_cache.get(aid)
            if spotify:
                targets.append((album, spotify))

        print(f'\n=== Pass 2: Spotify → YouTube ===')
        print(f'Target albums: {len(targets)}')

        found_youtube = 0

        for i, (album, spotify_url) in enumerate(targets):
            if i < start_from:
                continue

            aid = album['id']
            cache_key = f'pass2:{aid}'
            if cache_key in cache:
                continue

            print(f'[{i+1}/{len(targets)}] {album["title"]} - {album["artist"]}...', end=' ', flush=True)

            time.sleep(6.1)
            result = query_odesli(spotify_url)

            if result is None:
                cache[cache_key] = {'error': True}
                print('ERROR')
            elif result:
                cache[cache_key] = result
                if result.get('youtubeUrl') or result.get('youtubeMusicUrl'):
                    found_youtube += 1
                    print('FOUND YouTube')
                else:
                    print('no YouTube')
            else:
                cache[cache_key] = {}
                print('NOT FOUND')

            if (i + 1) % 5 == 0:
                save_cache(cache)

        save_cache(cache)
        print(f'\nPass 2 results: +{found_youtube} YouTube')

    # Summary
    p1_spotify = sum(1 for k, v in cache.items()
                     if k.startswith('pass1:') and isinstance(v, dict) and v.get('spotifyUrl'))
    p1_youtube = sum(1 for k, v in cache.items()
                     if k.startswith('pass1:') and isinstance(v, dict)
                     and (v.get('youtubeUrl') or v.get('youtubeMusicUrl')))
    p2_youtube = sum(1 for k, v in cache.items()
                     if k.startswith('pass2:') and isinstance(v, dict)
                     and (v.get('youtubeUrl') or v.get('youtubeMusicUrl')))

    print(f'\n=== Cache Summary ===')
    print(f'Pass 1: {p1_spotify} Spotify, {p1_youtube} YouTube')
    print(f'Pass 2: {p2_youtube} YouTube')
    print(f'Total entries: {len(cache)}')


if __name__ == '__main__':
    main()

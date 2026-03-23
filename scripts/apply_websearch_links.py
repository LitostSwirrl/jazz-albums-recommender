#!/usr/bin/env python3
"""
Merge WebSearch-discovered and Odesli-discovered streaming links into albums.json.
Reads from:
  /tmp/streaming_websearch_cache.json  - Apple Music from WebSearch
  /tmp/youtube_odesli_cache.json       - YouTube/YT Music from Odesli
Never overwrites existing non-empty URLs.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')

WEBSEARCH_CACHE = '/tmp/streaming_websearch_cache.json'
ODESLI_CACHE = '/tmp/youtube_odesli_cache.json'


def clean_apple_url(url: str) -> str:
    """Remove tracking params from Apple Music URLs."""
    if not url:
        return url
    for param in ['?uo=', '?ls=', '?at=', '?ct=']:
        if param in url:
            url = url.split(param)[0]
    return url


def load_json(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            print(f'WARNING: Failed to load {path}: {e}')
    else:
        print(f'INFO: {path} not found, skipping')
    return {}


def main():
    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    total = len(albums)

    # Before stats
    before = {
        'apple': sum(1 for a in albums if a.get('appleMusicUrl')),
        'youtube': sum(1 for a in albums if a.get('youtubeUrl')),
        'ytmusic': sum(1 for a in albums if a.get('youtubeMusicUrl')),
        'zero': sum(1 for a in albums if not any(a.get(k) for k in ('spotifyUrl', 'appleMusicUrl', 'youtubeUrl', 'youtubeMusicUrl'))),
    }

    # Load caches
    websearch = load_json(WEBSEARCH_CACHE)
    odesli = load_json(ODESLI_CACHE)

    print(f'Caches loaded:')
    print(f'  WebSearch: {len(websearch)} entries')
    print(f'  Odesli:    {len(odesli)} entries')

    apple_added = 0
    youtube_added = 0
    ytmusic_added = 0

    for album in albums:
        aid = album['id']

        # --- Apple Music ---
        if not album.get('appleMusicUrl'):
            # Try WebSearch cache first
            ws = websearch.get(aid)
            if isinstance(ws, dict) and ws.get('appleMusicUrl'):
                album['appleMusicUrl'] = clean_apple_url(ws['appleMusicUrl'])
                apple_added += 1
            else:
                # Try Odesli cache
                od = odesli.get(aid)
                if isinstance(od, dict) and od.get('appleMusicUrl'):
                    album['appleMusicUrl'] = clean_apple_url(od['appleMusicUrl'])
                    apple_added += 1

        # --- YouTube ---
        if not album.get('youtubeUrl'):
            od = odesli.get(aid)
            if isinstance(od, dict) and od.get('youtubeUrl'):
                album['youtubeUrl'] = od['youtubeUrl']
                youtube_added += 1

        # --- YouTube Music ---
        if not album.get('youtubeMusicUrl'):
            od = odesli.get(aid)
            if isinstance(od, dict) and od.get('youtubeMusicUrl'):
                album['youtubeMusicUrl'] = od['youtubeMusicUrl']
                ytmusic_added += 1

    # Save
    with open(ALBUMS_FILE, 'w') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)

    # After stats
    after = {
        'apple': sum(1 for a in albums if a.get('appleMusicUrl')),
        'youtube': sum(1 for a in albums if a.get('youtubeUrl')),
        'ytmusic': sum(1 for a in albums if a.get('youtubeMusicUrl')),
        'zero': sum(1 for a in albums if not any(a.get(k) for k in ('spotifyUrl', 'appleMusicUrl', 'youtubeUrl', 'youtubeMusicUrl'))),
    }

    print(f'\n{"="*50}')
    print(f'{"Platform":<15} {"Before":>8} {"After":>8} {"Delta":>8}')
    print(f'{"-"*50}')
    print(f'{"Apple Music":<15} {before["apple"]:>8} {after["apple"]:>8} {"+" + str(apple_added):>8}')
    print(f'{"YouTube":<15} {before["youtube"]:>8} {after["youtube"]:>8} {"+" + str(youtube_added):>8}')
    print(f'{"YT Music":<15} {before["ytmusic"]:>8} {after["ytmusic"]:>8} {"+" + str(ytmusic_added):>8}')
    print(f'{"Zero links":<15} {before["zero"]:>8} {after["zero"]:>8} {after["zero"] - before["zero"]:>+8}')
    print(f'{"-"*50}')
    print(f'\nSaved to {ALBUMS_FILE}')


if __name__ == '__main__':
    main()

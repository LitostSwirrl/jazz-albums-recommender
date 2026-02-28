#!/usr/bin/env python3
"""
Merge all cached streaming links and cover art into albums.json.
Reads from:
  /tmp/odesli_links.json       - Spotify/YouTube from Odesli
  /tmp/apple_music_links_v2.json - Apple Music v2 (relaxed search)
  /tmp/itunes_covers.json      - Cover art from iTunes
Never overwrites existing non-empty URLs.
"""

import json
import os
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')

ODESLI_FILE = '/tmp/odesli_links.json'
APPLE_V2_FILE = '/tmp/apple_music_links_v2.json'
ITUNES_COVERS_FILE = '/tmp/itunes_covers.json'


def youtube_normalize(url: str) -> str:
    """Convert music.youtube.com URLs to www.youtube.com."""
    if not url:
        return url
    return url.replace('music.youtube.com', 'www.youtube.com')


def load_json(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            print(f'WARNING: Failed to load {path}: {e}')
    else:
        print(f'WARNING: {path} not found')
    return {}


def main():
    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    total = len(albums)

    # Before stats
    before = {
        'spotify': sum(1 for a in albums if a.get('spotifyUrl')),
        'apple': sum(1 for a in albums if a.get('appleMusicUrl')),
        'youtube': sum(1 for a in albums if a.get('youtubeUrl')),
        'covers': sum(1 for a in albums if a.get('coverUrl')),
    }

    # Load caches
    odesli = load_json(ODESLI_FILE)
    apple_v2 = load_json(APPLE_V2_FILE)
    itunes_covers = load_json(ITUNES_COVERS_FILE)

    print(f'Caches loaded:')
    print(f'  Odesli: {len(odesli)} entries')
    print(f'  Apple Music v2: {len(apple_v2)} entries')
    print(f'  iTunes covers: {len(itunes_covers)} entries')

    spotify_added = 0
    apple_added = 0
    youtube_added = 0
    covers_added = 0

    for album in albums:
        aid = album['id']

        # --- Spotify ---
        if not album.get('spotifyUrl'):
            # Try odesli pass1
            p1 = odesli.get(f'pass1:{aid}', {})
            if isinstance(p1, dict) and p1.get('spotifyUrl'):
                album['spotifyUrl'] = p1['spotifyUrl']
                spotify_added += 1

        # --- Apple Music ---
        if not album.get('appleMusicUrl'):
            # Try odesli (may have Apple Music link)
            p1 = odesli.get(f'pass1:{aid}', {})
            if isinstance(p1, dict) and p1.get('appleMusicUrl'):
                album['appleMusicUrl'] = p1['appleMusicUrl']
                apple_added += 1
            else:
                # Try apple_v2 cache
                v2 = apple_v2.get(aid)
                if isinstance(v2, dict) and v2.get('url'):
                    album['appleMusicUrl'] = v2['url']
                    apple_added += 1

        # --- YouTube ---
        if not album.get('youtubeUrl'):
            # Try odesli pass1
            p1 = odesli.get(f'pass1:{aid}', {})
            yt = None
            if isinstance(p1, dict):
                yt = p1.get('youtubeUrl') or p1.get('youtubeMusicUrl')
            # Try odesli pass2
            if not yt:
                p2 = odesli.get(f'pass2:{aid}', {})
                if isinstance(p2, dict):
                    yt = p2.get('youtubeUrl') or p2.get('youtubeMusicUrl')
            if yt:
                album['youtubeUrl'] = youtube_normalize(yt)
                youtube_added += 1

        # --- Cover Art ---
        if not album.get('coverUrl'):
            # Try iTunes covers
            cover = itunes_covers.get(aid)
            if cover:
                album['coverUrl'] = cover
                covers_added += 1
            else:
                # Try artwork from apple_v2
                v2 = apple_v2.get(aid)
                if isinstance(v2, dict) and v2.get('artworkUrl'):
                    album['coverUrl'] = v2['artworkUrl']
                    covers_added += 1

    # Save
    with open(ALBUMS_FILE, 'w') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)

    # After stats
    after = {
        'spotify': sum(1 for a in albums if a.get('spotifyUrl')),
        'apple': sum(1 for a in albums if a.get('appleMusicUrl')),
        'youtube': sum(1 for a in albums if a.get('youtubeUrl')),
        'covers': sum(1 for a in albums if a.get('coverUrl')),
    }

    # Link distribution
    def count_links(albums_list):
        dist = {0: 0, 1: 0, 2: 0, 3: 0}
        for a in albums_list:
            n = sum(1 for k in ('spotifyUrl', 'appleMusicUrl', 'youtubeUrl') if a.get(k))
            dist[n] = dist.get(n, 0) + 1
        return dist

    dist = count_links(albums)

    print(f'\n{"="*50}')
    print(f'{"Platform":<15} {"Before":>8} {"After":>8} {"Delta":>8}')
    print(f'{"-"*50}')
    print(f'{"Spotify":<15} {before["spotify"]:>8} {after["spotify"]:>8} {"+"+str(spotify_added):>8}')
    print(f'{"Apple Music":<15} {before["apple"]:>8} {after["apple"]:>8} {"+"+str(apple_added):>8}')
    print(f'{"YouTube":<15} {before["youtube"]:>8} {after["youtube"]:>8} {"+"+str(youtube_added):>8}')
    print(f'{"Cover Art":<15} {before["covers"]:>8} {after["covers"]:>8} {"+"+str(covers_added):>8}')
    print(f'{"-"*50}')
    print(f'\nLink distribution ({total} albums):')
    for n in range(4):
        pct = dist.get(n, 0) / total * 100
        print(f'  {n} links: {dist.get(n, 0):>4} ({pct:.1f}%)')
    print(f'\nSaved to {ALBUMS_FILE}')


if __name__ == '__main__':
    main()

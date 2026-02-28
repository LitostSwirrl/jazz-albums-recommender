#!/usr/bin/env python3
"""
Apply streaming links from cache files to albums.json.
Reads from /tmp/streaming_links.json and /tmp/apple_music_links.json,
applies to albums that are missing streaming URLs.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')

STREAMING_FILE = '/tmp/streaming_links.json'
APPLE_FILE = '/tmp/apple_music_links.json'


def main():
    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    # Load streaming links (MusicBrainz URL rels)
    streaming = {}
    if os.path.exists(STREAMING_FILE):
        with open(STREAMING_FILE) as f:
            streaming = json.load(f)
        print(f'Streaming cache: {len(streaming)} entries')
    else:
        print(f'WARNING: {STREAMING_FILE} not found')

    # Load Apple Music links (iTunes Search API)
    apple = {}
    if os.path.exists(APPLE_FILE):
        with open(APPLE_FILE) as f:
            apple = json.load(f)
        print(f'Apple Music cache: {len(apple)} entries')
    else:
        print(f'WARNING: {APPLE_FILE} not found')

    spotify_added = 0
    apple_added = 0
    youtube_added = 0

    for album in albums:
        aid = album['id']

        # From MusicBrainz URL relationships
        stream = streaming.get(aid, {})
        if isinstance(stream, dict):
            if stream.get('spotifyUrl') and not album.get('spotifyUrl'):
                album['spotifyUrl'] = stream['spotifyUrl']
                spotify_added += 1
            if stream.get('appleMusicUrl') and not album.get('appleMusicUrl'):
                album['appleMusicUrl'] = stream['appleMusicUrl']
                apple_added += 1
            if stream.get('youtubeUrl') and not album.get('youtubeUrl'):
                album['youtubeUrl'] = stream['youtubeUrl']
                youtube_added += 1
            if stream.get('youtubeMusicUrl') and not album.get('youtubeUrl'):
                album['youtubeUrl'] = stream['youtubeMusicUrl']
                youtube_added += 1

        # From iTunes Search API
        am_url = apple.get(aid)
        if am_url and not album.get('appleMusicUrl'):
            album['appleMusicUrl'] = am_url
            apple_added += 1

    with open(ALBUMS_FILE, 'w') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)

    # Coverage stats
    has_spotify = sum(1 for a in albums if a.get('spotifyUrl'))
    has_apple = sum(1 for a in albums if a.get('appleMusicUrl'))
    has_youtube = sum(1 for a in albums if a.get('youtubeUrl'))
    total = len(albums)

    print(f'\n=== Applied ===')
    print(f'Spotify added: {spotify_added} (total: {has_spotify}/{total})')
    print(f'Apple Music added: {apple_added} (total: {has_apple}/{total})')
    print(f'YouTube added: {youtube_added} (total: {has_youtube}/{total})')


if __name__ == '__main__':
    main()

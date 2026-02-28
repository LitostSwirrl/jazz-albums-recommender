#!/usr/bin/env python3
"""
Stage 4b: Find streaming links for expansion albums.
Combines MusicBrainz URL rels + iTunes Search API.
Requires: /tmp/expansion_discovered.json from Stage 2
Output: /tmp/expansion_streaming.json
"""

import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import os
import sys

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

DISCOVERED_FILE = '/tmp/expansion_discovered.json'
CACHE_FILE = '/tmp/expansion_streaming.json'


def api_get(url, timeout=20):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (503, 429):
                time.sleep(5 * (attempt + 1))
                continue
            return None
        except Exception:
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            return None
    return None


def search_mb_release(title, artist):
    """Search MusicBrainz for a release and return MBID."""
    query = urllib.parse.quote(f'"{title}" AND artist:"{artist}"')
    url = f'https://musicbrainz.org/ws/2/release/?query={query}&fmt=json&limit=5'
    data = api_get(url)
    if data and data.get('releases'):
        return data['releases'][0]['id']
    return None


def get_streaming_urls_from_mb(mbid):
    """Query MusicBrainz for URL relationships of a release."""
    url = f'https://musicbrainz.org/ws/2/release/{mbid}?inc=url-rels&fmt=json'
    data = api_get(url)
    if not data:
        return {}

    result = {}
    relations = data.get('relations', [])
    for rel in relations:
        rel_type = rel.get('type', '')
        if rel_type in ('streaming music', 'free streaming', 'streaming', 'streaming page'):
            link = rel.get('url', {}).get('resource', '')
            if 'open.spotify.com' in link and 'spotifyUrl' not in result:
                result['spotifyUrl'] = link
            elif 'music.apple.com' in link and 'appleMusicUrl' not in result:
                result['appleMusicUrl'] = link
            elif 'music.youtube.com' in link and 'youtubeMusicUrl' not in result:
                result['youtubeMusicUrl'] = link
            elif ('youtube.com/watch' in link or 'youtu.be' in link) and 'music.youtube.com' not in link:
                if 'youtubeUrl' not in result:
                    result['youtubeUrl'] = link

    return result


def search_itunes(title, artist):
    """Search iTunes API for Apple Music link."""
    query = urllib.parse.quote(f'{artist} {title}')
    url = f'https://itunes.apple.com/search?term={query}&media=music&entity=album&limit=5'
    data = api_get(url)
    if not data or not data.get('results'):
        return None

    title_clean = re.sub(r'[^a-z0-9 ]', '', title.lower())
    artist_clean = re.sub(r'[^a-z0-9 ]', '', artist.lower())

    for result in data['results']:
        col_name = re.sub(r'[^a-z0-9 ]', '', result.get('collectionName', '').lower())
        art_name = re.sub(r'[^a-z0-9 ]', '', result.get('artistName', '').lower())

        if title_clean in col_name or col_name in title_clean:
            if artist_clean in art_name or art_name in artist_clean:
                collection_url = result.get('collectionViewUrl', '')
                if collection_url:
                    return collection_url

    return None


def main():
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    if not os.path.exists(DISCOVERED_FILE):
        print(f'ERROR: {DISCOVERED_FILE} not found. Run discover_expansion_albums.py first.')
        sys.exit(1)

    with open(DISCOVERED_FILE) as f:
        discovered = json.load(f)

    # Flatten all discovered albums
    all_albums = []
    for artist_data in discovered.values():
        all_albums.extend(artist_data.get('albums', []))

    print(f'Total albums to find streaming links for: {len(all_albums)}')

    # Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f'Cache loaded: {len(cache)} entries')

    total = len(all_albums)

    for i, album in enumerate(all_albums):
        if i < start_from:
            continue

        aid = album['id']
        if aid in cache:
            continue

        title = album['title']
        artist = album['artist']
        print(f'[{i+1}/{total}] {title} - {artist}...', end=' ', flush=True)

        urls = {}

        # Step 1: Try MusicBrainz URL relationships
        time.sleep(1.1)
        mbid = search_mb_release(title, artist)
        if mbid:
            time.sleep(1.1)
            urls = get_streaming_urls_from_mb(mbid)

        # Step 2: If no Apple Music, try iTunes Search
        if 'appleMusicUrl' not in urls:
            time.sleep(1.1)
            apple_url = search_itunes(title, artist)
            if apple_url:
                urls['appleMusicUrl'] = apple_url

        cache[aid] = urls
        if urls:
            platforms = ', '.join(urls.keys())
            print(platforms)
        else:
            print('no links')

        if (i + 1) % 10 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2)

    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

    all_spotify = sum(1 for v in cache.values() if v.get('spotifyUrl'))
    all_apple = sum(1 for v in cache.values() if v.get('appleMusicUrl'))
    all_ytmusic = sum(1 for v in cache.values() if v.get('youtubeMusicUrl'))
    all_yt = sum(1 for v in cache.values() if v.get('youtubeUrl'))
    has_any = sum(1 for v in cache.values() if v)

    print(f'\n=== Results ===')
    print(f'Total processed: {len(cache)}/{total}')
    print(f'Spotify: {all_spotify}')
    print(f'Apple Music: {all_apple}')
    print(f'YouTube Music: {all_ytmusic}')
    print(f'YouTube: {all_yt}')
    print(f'Albums with at least one link: {has_any}')
    print(f'Cache: {CACHE_FILE}')


if __name__ == '__main__':
    main()

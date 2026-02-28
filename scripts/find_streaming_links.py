#!/usr/bin/env python3
"""
Extract streaming service URLs from MusicBrainz URL relationships.
Uses MBIDs extracted from album cover URLs to query MusicBrainz directly.
"""

import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

LINKS_FILE = '/tmp/streaming_links.json'

def api_get(url: str) -> dict | None:
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
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


def extract_mbid(cover_url: str) -> str | None:
    """Extract MusicBrainz release ID from cover URL."""
    if not cover_url:
        return None
    # From archive.org: mbid-{uuid}
    m = re.search(r'mbid-([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', cover_url)
    if m:
        return m.group(1)
    # From coverartarchive.org: release/{uuid}
    m = re.search(r'coverartarchive\.org/release/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', cover_url)
    if m:
        return m.group(1)
    return None


def search_mbid(title: str, artist: str) -> str | None:
    """Search MusicBrainz for a release and return MBID."""
    query = urllib.parse.quote(f'"{title}" AND artist:"{artist}"')
    url = f'https://musicbrainz.org/ws/2/release/?query={query}&fmt=json&limit=5'
    data = api_get(url)
    if data and data.get('releases'):
        return data['releases'][0]['id']
    return None


def get_streaming_urls(mbid: str) -> dict:
    """Query MusicBrainz for URL relationships of a release."""
    url = f'https://musicbrainz.org/ws/2/release/{mbid}?inc=url-rels&fmt=json'
    data = api_get(url)
    if not data:
        return {}

    result = {}
    relations = data.get('relations', [])
    for rel in relations:
        if rel.get('type') == 'streaming music' or rel.get('type') == 'free streaming' or rel.get('type') == 'streaming':
            link = rel.get('url', {}).get('resource', '')
            if 'open.spotify.com' in link:
                result['spotifyUrl'] = link
            elif 'music.apple.com' in link:
                result['appleMusicUrl'] = link
            elif 'music.youtube.com' in link:
                result['youtubeMusicUrl'] = link
            elif ('youtube.com/watch' in link or 'youtu.be' in link) and 'music.youtube.com' not in link:
                result['youtubeUrl'] = link
            elif 'deezer.com' in link:
                pass  # skip deezer
            elif 'tidal.com' in link:
                pass  # skip tidal

        # Also check for 'streaming page' type
        if rel.get('type') in ('streaming page', 'purchase for download', 'download for free'):
            link = rel.get('url', {}).get('resource', '')
            if 'open.spotify.com' in link and 'spotifyUrl' not in result:
                result['spotifyUrl'] = link
            elif 'music.apple.com' in link and 'appleMusicUrl' not in result:
                result['appleMusicUrl'] = link
            elif 'music.youtube.com' in link and 'youtubeMusicUrl' not in result:
                result['youtubeMusicUrl'] = link

    return result


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
    found_count = 0
    empty_count = 0

    for i, album in enumerate(albums):
        if i < start_from:
            continue

        aid = album['id']
        if aid in results:
            continue

        # Extract or search for MBID
        mbid = extract_mbid(album.get('coverUrl', ''))
        if not mbid:
            print(f'[{i+1}/{total}] {album["title"]} - {album["artist"]} → searching MusicBrainz...')
            mbid = search_mbid(album['title'], album['artist'])
            time.sleep(1.1)

        if not mbid:
            print(f'[{i+1}/{total}] {album["title"]} - {album["artist"]} → NO MBID FOUND')
            results[aid] = {}
            continue

        # Query URL relationships
        urls = get_streaming_urls(mbid)
        time.sleep(1.1)  # Rate limit

        results[aid] = urls
        if urls:
            found_count += 1
            platforms = ', '.join(urls.keys())
            print(f'[{i+1}/{total}] {album["title"]} - {album["artist"]} → {platforms}')
        else:
            empty_count += 1
            if (i + 1) % 20 == 0:
                print(f'[{i+1}/{total}] {album["title"]} - no streaming links in MusicBrainz')

        # Save incrementally every 10
        if (i + 1) % 10 == 0:
            with open(LINKS_FILE, 'w') as f:
                json.dump(results, f, indent=2)

    # Final save
    with open(LINKS_FILE, 'w') as f:
        json.dump(results, f, indent=2)

    # Report
    all_spotify = sum(1 for v in results.values() if v.get('spotifyUrl'))
    all_apple = sum(1 for v in results.values() if v.get('appleMusicUrl'))
    all_ytmusic = sum(1 for v in results.values() if v.get('youtubeMusicUrl'))
    all_yt = sum(1 for v in results.values() if v.get('youtubeUrl'))

    print(f'\n=== Results ===')
    print(f'Total processed: {len(results)}/{total}')
    print(f'Spotify: {all_spotify}')
    print(f'Apple Music: {all_apple}')
    print(f'YouTube Music: {all_ytmusic}')
    print(f'YouTube: {all_yt}')
    print(f'Albums with at least one link: {found_count}')
    print(f'Albums with no links: {empty_count}')


if __name__ == '__main__':
    main()

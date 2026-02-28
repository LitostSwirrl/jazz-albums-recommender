#!/usr/bin/env python3
"""
Fix broken cover art URLs by querying MusicBrainz API.
Uses 2-second delays to respect rate limits.
Outputs a JSON mapping of album_id -> new_cover_url.
"""

import json
import time
import urllib.request
import urllib.parse
import urllib.error
import sys
import os

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history project; contact: github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

def api_get(url: str, retries: int = 2) -> dict | None:
    """Make an API request with retries."""
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 503 or e.code == 429:
                time.sleep(5)
                continue
            print(f'  HTTP {e.code} for {url}', file=sys.stderr)
            return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3)
                continue
            print(f'  Error: {e}', file=sys.stderr)
            return None
    return None

def find_caa_url(title: str, artist: str) -> str | None:
    """Search MusicBrainz for a release with cover art."""
    # Strategy 1: Direct release search
    query = urllib.parse.quote(f'release:"{title}" AND artist:"{artist}"')
    url = f'https://musicbrainz.org/ws/2/release/?query={query}&fmt=json&limit=15'
    data = api_get(url)
    time.sleep(2)

    if data and data.get('releases'):
        for rel in data['releases'][:8]:
            mbid = rel['id']
            caa_url = f'https://coverartarchive.org/release/{mbid}/'
            caa_data = api_get(caa_url)
            time.sleep(1.5)
            if caa_data and caa_data.get('images'):
                for img in caa_data['images']:
                    if img.get('front', False):
                        thumbs = img.get('thumbnails', {})
                        return thumbs.get('large') or thumbs.get('500') or img.get('image')
                # No front cover, use first image
                img = caa_data['images'][0]
                thumbs = img.get('thumbnails', {})
                return thumbs.get('large') or thumbs.get('500') or img.get('image')

    # Strategy 2: Simpler search with just title
    query2 = urllib.parse.quote(f'"{title}" AND artist:"{artist}"')
    url2 = f'https://musicbrainz.org/ws/2/release/?query={query2}&fmt=json&limit=10'
    data2 = api_get(url2)
    time.sleep(2)

    if data2 and data2.get('releases'):
        for rel in data2['releases'][:5]:
            mbid = rel['id']
            caa_url = f'https://coverartarchive.org/release/{mbid}/'
            caa_data = api_get(caa_url)
            time.sleep(1.5)
            if caa_data and caa_data.get('images'):
                for img in caa_data['images']:
                    if img.get('front', False):
                        thumbs = img.get('thumbnails', {})
                        return thumbs.get('large') or thumbs.get('500') or img.get('image')
                img = caa_data['images'][0]
                thumbs = img.get('thumbnails', {})
                return thumbs.get('large') or thumbs.get('500') or img.get('image')

    return None

def main():
    # Read args: start_idx and end_idx for batching
    start_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 999

    albums_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'albums.json')
    with open(albums_path) as f:
        albums = json.load(f)

    broken_ids = open('/tmp/broken_albums.txt').read().strip().split('\n')
    broken_set = set(broken_ids)
    broken_albums = [a for a in albums if a['id'] in broken_set]

    # Get our batch
    batch = broken_albums[start_idx:end_idx]
    print(f'Processing batch [{start_idx}:{end_idx}], {len(batch)} albums', file=sys.stderr)

    fixes = {}
    for i, album in enumerate(batch):
        title = album['title']
        artist = album['artist']
        print(f'[{start_idx+i+1}/{start_idx+len(batch)}] {title} - {artist}', file=sys.stderr)

        url = find_caa_url(title, artist)
        if url:
            url = url.replace('http://', 'https://')
            fixes[album['id']] = url
            print(f'  -> FOUND', file=sys.stderr)
        else:
            print(f'  -> NOT FOUND', file=sys.stderr)

    # Output fixes as JSON to stdout
    json.dump(fixes, sys.stdout, indent=2)
    print(f'\nBatch done: {len(fixes)}/{len(batch)} fixed', file=sys.stderr)

if __name__ == '__main__':
    main()

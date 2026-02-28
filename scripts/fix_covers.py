#!/usr/bin/env python3
"""
Fix broken cover art URLs by querying MusicBrainz API and Cover Art Archive.
Uses MusicBrainz search to find releases, then checks CAA for available art.
"""

import json
import time
import urllib.request
import urllib.parse
import urllib.error
import sys
import os

# MusicBrainz requires a User-Agent header
HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (personal project)',
    'Accept': 'application/json',
}

def mb_search_release(title: str, artist: str) -> list:
    """Search MusicBrainz for a release by title and artist."""
    query = f'release:"{title}" AND artist:"{artist}"'
    url = f'https://musicbrainz.org/ws/2/release/?query={urllib.parse.quote(query)}&fmt=json&limit=10'
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get('releases', [])
    except Exception as e:
        print(f'  MB search error: {e}', file=sys.stderr)
        return []

def mb_search_release_group(title: str, artist: str) -> list:
    """Search MusicBrainz for a release-group, then get its releases."""
    query = f'releasegroup:"{title}" AND artist:"{artist}"'
    url = f'https://musicbrainz.org/ws/2/release-group/?query={urllib.parse.quote(query)}&fmt=json&limit=5'
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            groups = data.get('release-groups', [])
            if not groups:
                return []
            # Get releases from the first matching group
            rgid = groups[0]['id']
            time.sleep(1.1)
            url2 = f'https://musicbrainz.org/ws/2/release-group/{rgid}?inc=releases&fmt=json'
            req2 = urllib.request.Request(url2, headers=HEADERS)
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                data2 = json.loads(resp2.read())
                return data2.get('releases', [])
    except Exception as e:
        print(f'  MB release-group search error: {e}', file=sys.stderr)
        return []

def check_caa_has_art(mbid: str) -> str | None:
    """Check if Cover Art Archive has art for a given release MBID."""
    url = f'https://coverartarchive.org/release/{mbid}/'
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            images = data.get('images', [])
            # Look for front cover first
            for img in images:
                if img.get('front', False):
                    # Return the 500px thumbnail or the main image
                    thumbs = img.get('thumbnails', {})
                    if 'large' in thumbs:
                        return thumbs['large']
                    if '500' in thumbs:
                        return thumbs['500']
                    return img.get('image', '')
            # If no front cover, take the first image
            if images:
                thumbs = images[0].get('thumbnails', {})
                if 'large' in thumbs:
                    return thumbs['large']
                return images[0].get('image', '')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        print(f'  CAA error for {mbid}: {e}', file=sys.stderr)
    except Exception as e:
        print(f'  CAA error for {mbid}: {e}', file=sys.stderr)
    return None

def find_cover_url(title: str, artist: str) -> str | None:
    """Try to find a working cover art URL for an album."""
    # Step 1: Search MusicBrainz for releases
    releases = mb_search_release(title, artist)
    time.sleep(1.1)  # MusicBrainz rate limit: 1 request/second

    # Try each release
    for rel in releases[:5]:
        mbid = rel['id']
        url = check_caa_has_art(mbid)
        if url:
            return url
        time.sleep(1.1)

    # Step 2: Try release-group search
    releases = mb_search_release_group(title, artist)
    time.sleep(1.1)

    for rel in releases[:5]:
        mbid = rel['id']
        url = check_caa_has_art(mbid)
        if url:
            return url
        time.sleep(1.1)

    return None

def main():
    albums_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'albums.json')
    with open(albums_path) as f:
        albums = json.load(f)

    # Read broken album IDs from stdin or file
    broken_ids_file = '/tmp/broken_albums.txt'
    with open(broken_ids_file) as f:
        broken_ids = set(line.strip() for line in f if line.strip())

    print(f'Found {len(broken_ids)} broken albums to fix')

    fixes = {}
    still_broken = []

    for album in albums:
        if album['id'] not in broken_ids:
            continue

        title = album['title']
        artist = album['artist']
        print(f'\nSearching: {title} by {artist} [{album["id"]}]')

        url = find_cover_url(title, artist)
        if url:
            # Ensure HTTPS
            url = url.replace('http://', 'https://')
            fixes[album['id']] = url
            print(f'  FOUND: {url[:80]}...')
        else:
            still_broken.append(album['id'])
            print(f'  NOT FOUND')

    # Save fixes
    fixes_path = '/tmp/cover_fixes.json'
    with open(fixes_path, 'w') as f:
        json.dump(fixes, f, indent=2)

    print(f'\n\nResults:')
    print(f'  Fixed: {len(fixes)}')
    print(f'  Still broken: {len(still_broken)}')
    if still_broken:
        print(f'  Broken IDs: {still_broken}')

if __name__ == '__main__':
    main()

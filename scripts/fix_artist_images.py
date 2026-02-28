#!/usr/bin/env python3
"""
Stage 5b: Fix missing artist images using Wikimedia Commons API.
Queries Wikipedia for artist page images, falls back to Commons search.
Updates src/data/artists.json directly.
"""

import json
import time
import urllib.request
import urllib.parse
import urllib.error
import os
import sys
import re

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
CACHE_FILE = '/tmp/artist_images_fix.json'


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


def get_image_from_wikipedia(wiki_url):
    """Extract image URL from Wikipedia page using pageimages API."""
    if not wiki_url:
        return None

    # Extract title from Wikipedia URL
    title = wiki_url.rstrip('/').split('/')[-1]
    encoded = urllib.parse.quote(title)

    url = (
        f'https://en.wikipedia.org/w/api.php'
        f'?action=query&titles={encoded}'
        f'&prop=pageimages&pithumbsize=500&format=json'
    )

    data = api_get(url)
    if not data:
        return None

    pages = data.get('query', {}).get('pages', {})
    for page_id, page in pages.items():
        if page_id == '-1':
            continue
        thumb = page.get('thumbnail', {}).get('source')
        if thumb:
            return thumb
        # Try original image
        original = page.get('original', {}).get('source')
        if original:
            return original

    return None


def get_image_from_commons(artist_name):
    """Search Wikimedia Commons for artist image."""
    query = urllib.parse.quote(f'{artist_name} jazz musician')
    url = (
        f'https://commons.wikimedia.org/w/api.php'
        f'?action=query&generator=search&gsrsearch={query}'
        f'&gsrnamespace=6&gsrlimit=5'
        f'&prop=imageinfo&iiprop=url|extmetadata'
        f'&iiurlwidth=500&format=json'
    )

    data = api_get(url)
    if not data:
        return None

    pages = data.get('query', {}).get('pages', {})
    if not pages:
        return None

    artist_lower = artist_name.lower()

    for page_id, page in sorted(pages.items()):
        title = page.get('title', '').lower()
        # Skip non-image files
        if not any(ext in title for ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg']):
            continue

        # Prefer files with artist name in title
        if artist_lower.split()[-1].lower() in title:
            imageinfo = page.get('imageinfo', [{}])
            if imageinfo:
                thumb = imageinfo[0].get('thumburl')
                if thumb:
                    return thumb
                return imageinfo[0].get('url')

    # Fallback: first image result
    for page_id, page in sorted(pages.items()):
        imageinfo = page.get('imageinfo', [{}])
        if imageinfo:
            thumb = imageinfo[0].get('thumburl')
            if thumb:
                return thumb

    return None


def get_image_from_rest_api(artist_name):
    """Try Wikipedia REST API for artist image."""
    # Try different title formats
    queries = [
        artist_name,
        f'{artist_name} (musician)',
        f'{artist_name} (jazz musician)',
    ]

    for query in queries:
        encoded = urllib.parse.quote(query.replace(' ', '_'))
        url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}'

        req = urllib.request.Request(url, headers={
            'User-Agent': 'JazzAlbumsRecommender/1.0',
            'Accept': 'application/json',
        })

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                # Check thumbnail
                thumb = data.get('thumbnail', {}).get('source')
                if thumb:
                    # Get higher-res version
                    # Thumbnail URLs often have /XXXpx-/ in them
                    # Replace with 500px
                    high_res = re.sub(r'/\d+px-', '/500px-', thumb)
                    return high_res
                # Try originalimage
                original = data.get('originalimage', {}).get('source')
                if original:
                    return original
        except Exception:
            pass

        time.sleep(0.5)

    return None


def main():
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)

    # Find artists without images
    missing = [a for a in artists if not a.get('imageUrl')]
    print(f'Artists without images: {len(missing)}')

    if not missing:
        print('All artists have images!')
        return

    # Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f'Cache loaded: {len(cache)} entries')

    fixed = 0
    for i, artist in enumerate(missing):
        aid = artist['id']
        if aid in cache:
            continue

        print(f'[{i+1}/{len(missing)}] {artist["name"]}...', end=' ', flush=True)

        image_url = None

        # Method 1: Wikipedia page images API
        if artist.get('wikipedia'):
            time.sleep(1.0)
            image_url = get_image_from_wikipedia(artist['wikipedia'])
            if image_url:
                print(f'FOUND (wikipedia pageimages)')
                cache[aid] = image_url
                fixed += 1
                continue

        # Method 2: Wikipedia REST API
        time.sleep(1.0)
        image_url = get_image_from_rest_api(artist['name'])
        if image_url:
            print(f'FOUND (rest api)')
            cache[aid] = image_url
            fixed += 1
            continue

        # Method 3: Wikimedia Commons search
        time.sleep(1.0)
        image_url = get_image_from_commons(artist['name'])
        if image_url:
            print(f'FOUND (commons)')
            cache[aid] = image_url
            fixed += 1
            continue

        cache[aid] = None
        print('NOT FOUND')

        # Save every 5
        if (i + 1) % 5 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2)

    # Final save cache
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

    # Apply fixes to artists.json
    artist_map = {a['id']: a for a in artists}
    applied = 0
    for aid, url in cache.items():
        if url and aid in artist_map:
            artist_map[aid]['imageUrl'] = url
            applied += 1

    with open(ARTISTS_FILE, 'w') as f:
        json.dump(artists, f, indent=2, ensure_ascii=False)

    print(f'\n=== Results ===')
    print(f'Total missing: {len(missing)}')
    print(f'Found: {sum(1 for v in cache.values() if v)}')
    print(f'Not found: {sum(1 for v in cache.values() if v is None)}')
    print(f'Applied to artists.json: {applied}')


if __name__ == '__main__':
    main()

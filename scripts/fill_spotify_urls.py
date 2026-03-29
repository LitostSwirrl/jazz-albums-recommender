#!/usr/bin/env python3
"""
Fill missing Spotify URLs for albums in albums.json.

Uses Spotify Web API search to find album URLs.
Searches by album title + artist name, picks the best match.

Usage:
  export SPOTIFY_CLIENT_ID=...
  export SPOTIFY_CLIENT_SECRET=...
  python3 scripts/fill_spotify_urls.py
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher

ALBUMS_PATH = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'albums.json')
CACHE_FILE = '/tmp/spotify_url_cache.json'

SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')


def get_token():
    creds = base64.b64encode(f'{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}'.encode()).decode()
    req = urllib.request.Request(
        'https://accounts.spotify.com/api/token',
        data=b'grant_type=client_credentials',
        headers={
            'Authorization': f'Basic {creds}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp['access_token']


def search_album(token, title, artist):
    """Search Spotify for an album, return best matching URL or None."""
    # Try exact search first
    query = f'album:{title} artist:{artist}'
    url = f'https://api.spotify.com/v1/search?{urllib.parse.urlencode({"q": query, "type": "album", "limit": 5})}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})

    try:
        resp = json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            retry_after = int(e.headers.get('Retry-After', 5))
            print(f'  Rate limited, waiting {retry_after}s...')
            time.sleep(retry_after)
            return search_album(token, title, artist)
        elif e.code == 401:
            return 'TOKEN_EXPIRED'
        print(f'  HTTP {e.code} for {title}')
        return None

    items = resp.get('albums', {}).get('items', [])

    if not items:
        # Fallback: broader search without field qualifiers
        query = f'{title} {artist}'
        url = f'https://api.spotify.com/v1/search?{urllib.parse.urlencode({"q": query, "type": "album", "limit": 10})}'
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
        try:
            resp = json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError:
            return None
        items = resp.get('albums', {}).get('items', [])

    if not items:
        return None

    # Score matches by title + artist similarity
    best_score = 0
    best_url = None
    title_lower = title.lower()
    artist_lower = artist.lower()

    for item in items:
        item_title = item.get('name', '').lower()
        item_artists = ' '.join(a['name'].lower() for a in item.get('artists', []))

        title_sim = SequenceMatcher(None, title_lower, item_title).ratio()
        artist_sim = SequenceMatcher(None, artist_lower, item_artists).ratio()
        score = title_sim * 0.6 + artist_sim * 0.4

        if score > best_score:
            best_score = score
            best_url = item['external_urls'].get('spotify')

    # Require reasonable match quality
    if best_score >= 0.5:
        return best_url
    return None


def main():
    # Load albums
    with open(ALBUMS_PATH) as f:
        albums = json.load(f)

    missing = [(i, a) for i, a in enumerate(albums) if not a.get('spotifyUrl')]
    print(f'Total albums: {len(albums)}')
    print(f'Missing Spotify URLs: {len(missing)}')

    if not missing:
        print('Nothing to do!')
        return

    # Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f'Loaded {len(cache)} cached results')

    token = get_token()
    found = 0
    not_found = 0
    errors = 0

    for count, (idx, album) in enumerate(missing, 1):
        title = album['title']
        artist = album['artist']
        cache_key = f'{artist}|{title}'

        if cache_key in cache:
            url = cache[cache_key]
        else:
            url = search_album(token, title, artist)
            if url == 'TOKEN_EXPIRED':
                print('  Refreshing token...')
                token = get_token()
                url = search_album(token, title, artist)

            cache[cache_key] = url
            # Rate limiting: ~3 requests per second
            time.sleep(0.35)

        if url and url != 'TOKEN_EXPIRED':
            albums[idx]['spotifyUrl'] = url
            found += 1
            status = 'FOUND'
        else:
            not_found += 1
            status = 'NOT FOUND'

        print(f'[{count}/{len(missing)}] {status}: {artist} - {title}')

        # Save cache every 25 albums
        if count % 25 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f)

    # Final cache save
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

    # Write updated albums
    with open(ALBUMS_PATH, 'w') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)

    print(f'\nDone! Found: {found}, Not found: {not_found}')
    print(f'Total albums with Spotify URLs: {len([a for a in albums if a.get("spotifyUrl")])} / {len(albums)}')


if __name__ == '__main__':
    main()

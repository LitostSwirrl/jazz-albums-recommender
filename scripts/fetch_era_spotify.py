#!/usr/bin/env python3
"""
Fetch artist genre data from Spotify to validate era assignments.

Uses Spotify Web API to get artist genres (artist-level, not album-specific).
Skips albums already resolved by Wikidata or Last.fm.

Cache: /tmp/era_spotify_cache.json
Usage: python3 fetch_era_spotify.py [start_index]
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import base64

SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '***REMOVED***')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '***REMOVED***')

CACHE_FILE = '/tmp/era_spotify_cache.json'
WIKIDATA_CACHE_FILE = '/tmp/era_wikidata_cache.json'
LASTFM_CACHE_FILE = '/tmp/era_lastfm_cache.json'
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history)',
}

GENRE_TO_ERA = {
    # Early Jazz
    'dixieland': 'early-jazz', 'new orleans jazz': 'early-jazz',
    'early jazz': 'early-jazz', 'ragtime': 'early-jazz',
    'trad jazz': 'early-jazz', 'traditional jazz': 'early-jazz',
    'classic jazz': 'early-jazz', 'new orleans': 'early-jazz',
    # Swing
    'swing': 'swing', 'big band': 'swing', 'gypsy jazz': 'swing',
    'jump blues': 'swing', 'vocal jazz': 'swing',
    # Bebop
    'bebop': 'bebop', 'bop': 'bebop',
    # Cool Jazz
    'cool jazz': 'cool-jazz', 'west coast jazz': 'cool-jazz',
    'bossa nova': 'cool-jazz', 'chamber jazz': 'cool-jazz',
    'third stream': 'cool-jazz',
    # Hard Bop
    'hard bop': 'hard-bop', 'soul jazz': 'hard-bop',
    'post-bop': 'hard-bop', 'modal jazz': 'hard-bop',
    'jazz organ': 'hard-bop', 'jazz trumpet': 'hard-bop',
    'jazz saxophone': 'hard-bop', 'jazz piano': 'hard-bop',
    # Free Jazz
    'free jazz': 'free-jazz', 'avant-garde jazz': 'free-jazz',
    'free improvisation': 'free-jazz', 'spiritual jazz': 'free-jazz',
    'loft jazz': 'free-jazz', 'ecm-style jazz': 'free-jazz',
    # Fusion
    'jazz fusion': 'fusion', 'jazz-funk': 'fusion',
    'jazz funk': 'fusion', 'jazz rock': 'fusion',
    'electric jazz': 'fusion', 'crossover jazz': 'fusion',
    'jazz bass': 'fusion', 'progressive jazz': 'fusion',
    # Contemporary
    'contemporary jazz': 'contemporary', 'nu jazz': 'contemporary',
    'acid jazz': 'contemporary', 'smooth jazz': 'contemporary',
    'jazz rap': 'contemporary', 'neo-bop': 'contemporary',
    'modern jazz': 'contemporary',
}

ERA_PRIORITY = {
    'early-jazz': 0, 'swing': 1, 'bebop': 2, 'cool-jazz': 3,
    'hard-bop': 4, 'free-jazz': 5, 'fusion': 6, 'contemporary': 7,
}

# Cache for Spotify access token
_token_cache = {'token': None, 'expires_at': 0}
# Cache for artist genres (avoid redundant API calls for same artist)
_artist_genre_cache = {}


def get_spotify_token():
    """Get OAuth token via client credentials flow."""
    if _token_cache['token'] and time.time() < _token_cache['expires_at'] - 60:
        return _token_cache['token']

    auth_str = base64.b64encode(
        f'{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}'.encode()
    ).decode()

    data = urllib.parse.urlencode({'grant_type': 'client_credentials'}).encode()
    req = urllib.request.Request(
        'https://accounts.spotify.com/api/token',
        data=data,
        headers={
            'Authorization': f'Basic {auth_str}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        _token_cache['token'] = result['access_token']
        _token_cache['expires_at'] = time.time() + result.get('expires_in', 3600)
        return _token_cache['token']
    except Exception as e:
        print(f'Error getting Spotify token: {e}')
        return None


def spotify_get(url):
    """Make authenticated Spotify API request."""
    token = get_spotify_token()
    if not token:
        return None

    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {token}',
        'User-Agent': 'JazzAlbumsRecommender/1.0',
    })

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429:
                retry_after = int(e.headers.get('Retry-After', 5))
                print(f'  Rate limited, waiting {retry_after}s...')
                time.sleep(retry_after)
                continue
            if e.code == 401:
                # Token expired, refresh
                _token_cache['token'] = None
                token = get_spotify_token()
                if not token:
                    return None
                req.remove_header('Authorization')
                req.add_header('Authorization', f'Bearer {token}')
                continue
            return None
        except Exception:
            if attempt < 2:
                time.sleep(2)
                continue
            return None
    return None


def extract_spotify_album_id(spotify_url):
    """Extract album ID from Spotify URL."""
    if not spotify_url:
        return None
    # https://open.spotify.com/album/XXXXX or /album/XXXXX?si=...
    parts = spotify_url.split('/album/')
    if len(parts) < 2:
        return None
    album_id = parts[1].split('?')[0].split('#')[0]
    return album_id if album_id else None


def get_artist_genres(spotify_url):
    """Get artist genres from a Spotify album URL."""
    album_id = extract_spotify_album_id(spotify_url)
    if not album_id:
        return [], 'no_album_id'

    # Get album to find artist ID
    album_data = spotify_get(f'https://api.spotify.com/v1/albums/{album_id}')
    if not album_data:
        return [], 'album_not_found'

    time.sleep(0.1)

    artists = album_data.get('artists', [])
    if not artists:
        return [], 'no_artists'

    # Check artist genre cache first
    artist_id = artists[0].get('id', '')
    if artist_id in _artist_genre_cache:
        return _artist_genre_cache[artist_id], 'cached'

    # Get artist details for genres
    artist_data = spotify_get(f'https://api.spotify.com/v1/artists/{artist_id}')
    if not artist_data:
        return [], 'artist_not_found'

    genres = [g.lower() for g in artist_data.get('genres', [])]
    _artist_genre_cache[artist_id] = genres
    return genres, 'artist'


def classify_genres(genres):
    """Map Spotify genres to a suggested era."""
    mapped_eras = []
    for genre in genres:
        era = GENRE_TO_ERA.get(genre)
        if era and era not in mapped_eras:
            mapped_eras.append(era)

    if not mapped_eras:
        return None

    if len(mapped_eras) == 1:
        return mapped_eras[0]

    mapped_eras.sort(key=lambda e: ERA_PRIORITY.get(e, 99))
    return mapped_eras[0]


def load_cache(path):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def main():
    # Verify token works
    token = get_spotify_token()
    if not token:
        print('ERROR: Could not get Spotify access token.')
        print('Check SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.')
        sys.exit(1)
    print('Spotify auth OK')

    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    cache = load_cache(CACHE_FILE)
    wikidata_cache = load_cache(WIKIDATA_CACHE_FILE)
    lastfm_cache = load_cache(LASTFM_CACHE_FILE)
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    print(f'Total albums: {len(albums)}')
    print(f'Already in Spotify cache: {len(cache)}')
    print(f'Starting from index: {start_from}')
    print()

    resolved = 0
    unresolved = 0
    skipped_prior = 0
    skipped_no_url = 0

    for idx, album in enumerate(albums):
        aid = album['id']

        if idx < start_from:
            continue

        if aid in cache:
            continue

        # Skip if already resolved by prior sources
        if (wikidata_cache.get(aid, {}).get('status') == 'resolved' or
                lastfm_cache.get(aid, {}).get('status') == 'resolved'):
            cache[aid] = {'status': 'skipped', 'reason': 'already_resolved'}
            skipped_prior += 1
            continue

        spotify_url = album.get('spotifyUrl', '')
        if not spotify_url:
            cache[aid] = {
                'status': 'skipped',
                'source': 'spotify',
                'reason': 'no_spotify_url',
            }
            skipped_no_url += 1
            continue

        artist = album.get('artist', '')
        title = album['title']

        genres, source_level = get_artist_genres(spotify_url)
        time.sleep(0.3)

        if not genres:
            cache[aid] = {
                'status': 'unresolved',
                'source': 'spotify',
                'genres': [],
                'reason': source_level,
            }
            unresolved += 1
            print(f'[{idx + 1}/{len(albums)}] {artist} - {title[:40]}: no genres ({source_level})')
            if (idx + 1) % 20 == 0:
                save_cache(cache)
            continue

        suggested_era = classify_genres(genres)

        if suggested_era:
            cache[aid] = {
                'status': 'resolved',
                'source': 'spotify',
                'genres': genres,
                'suggested_era': suggested_era,
                'confidence': 'medium',
                'source_level': source_level,
            }
            resolved += 1
            print(f'[{idx + 1}/{len(albums)}] {artist} - {title[:40]}: {genres[:3]} -> {suggested_era}')
        else:
            cache[aid] = {
                'status': 'unresolved',
                'source': 'spotify',
                'genres': genres,
                'reason': 'no_era_match',
            }
            unresolved += 1
            print(f'[{idx + 1}/{len(albums)}] {artist} - {title[:40]}: no match {genres[:3]}')

        if (idx + 1) % 20 == 0:
            save_cache(cache)
            print(f'  [cache saved at {idx + 1}]')

    save_cache(cache)

    all_statuses = [v.get('status') for v in cache.values()]
    print(f'\n=== Spotify Fetch Summary ===')
    print(f'Resolved (genres → era):       {all_statuses.count("resolved")}')
    print(f'Unresolved (no genre match):   {all_statuses.count("unresolved")}')
    print(f'Skipped (prior resolved):      {skipped_prior}')
    print(f'Skipped (no Spotify URL):      {skipped_no_url}')
    print(f'Total cached: {len(cache)}')


if __name__ == '__main__':
    main()

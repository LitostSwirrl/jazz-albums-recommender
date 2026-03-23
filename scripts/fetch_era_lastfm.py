#!/usr/bin/env python3
"""
Fetch album genre tags from Last.fm to validate era assignments.

Uses album.getTopTags endpoint. Skips albums already resolved by Wikidata.

Cache: /tmp/era_lastfm_cache.json
Usage: python3 fetch_era_lastfm.py [start_index]
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

LASTFM_API_KEY = os.environ.get('LASTFM_API_KEY', '')

if not LASTFM_API_KEY:
    print('Error: LASTFM_API_KEY environment variable is required.')
    print('  export LASTFM_API_KEY=your_api_key')
    sys.exit(1)
CACHE_FILE = '/tmp/era_lastfm_cache.json'
WIKIDATA_CACHE_FILE = '/tmp/era_wikidata_cache.json'
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

GENRE_TO_ERA = {
    # Early Jazz
    'dixieland': 'early-jazz', 'new orleans jazz': 'early-jazz',
    'early jazz': 'early-jazz', 'ragtime': 'early-jazz',
    'trad jazz': 'early-jazz', 'traditional jazz': 'early-jazz',
    # Swing
    'swing': 'swing', 'swing music': 'swing', 'big band': 'swing',
    'big band music': 'swing', 'gypsy jazz': 'swing', 'jump blues': 'swing',
    # Bebop
    'bebop': 'bebop', 'bop': 'bebop', 'be-bop': 'bebop',
    # Cool Jazz
    'cool jazz': 'cool-jazz', 'west coast jazz': 'cool-jazz',
    'bossa nova': 'cool-jazz', 'chamber jazz': 'cool-jazz',
    'third stream': 'cool-jazz',
    # Hard Bop
    'hard bop': 'hard-bop', 'hardbop': 'hard-bop',
    'soul jazz': 'hard-bop', 'post-bop': 'hard-bop', 'post bop': 'hard-bop',
    'modal jazz': 'hard-bop', 'funky jazz': 'hard-bop',
    # Free Jazz
    'free jazz': 'free-jazz', 'avant-garde jazz': 'free-jazz',
    'avant-garde': 'free-jazz', 'free improvisation': 'free-jazz',
    'spiritual jazz': 'free-jazz', 'loft jazz': 'free-jazz',
    'experimental': 'free-jazz', 'avant garde': 'free-jazz',
    # Fusion
    'jazz fusion': 'fusion', 'fusion': 'fusion',
    'jazz-funk': 'fusion', 'jazz funk': 'fusion',
    'jazz-rock': 'fusion', 'jazz rock': 'fusion',
    'electric jazz': 'fusion', 'crossover jazz': 'fusion',
    # Contemporary
    'contemporary jazz': 'contemporary', 'nu jazz': 'contemporary',
    'acid jazz': 'contemporary', 'smooth jazz': 'contemporary',
    'jazz rap': 'contemporary', 'neo-bop': 'contemporary',
}

# Tags to ignore (not genre-relevant)
SKIP_TAGS = {
    'jazz', 'jazz music', 'seen live', 'favorites', 'favourite',
    'albums i own', 'my favorites', 'best albums', 'classic',
    'instrumental', 'american', 'male vocalists', 'female vocalists',
    '00s', '10s', '20s', '90s', '80s', '70s', '60s', '50s', '40s', '30s',
    'music', 'favourite albums', 'albums', 'vinyl', 'cd', 'own it',
    'usa', 'american jazz', 'piano', 'saxophone', 'trumpet', 'guitar',
    'bass', 'drums', 'vocals', 'vocal', 'singer',
}

ERA_PRIORITY = {
    'early-jazz': 0, 'swing': 1, 'bebop': 2, 'cool-jazz': 3,
    'hard-bop': 4, 'free-jazz': 5, 'fusion': 6, 'contemporary': 7,
}


def api_get(url, timeout=15):
    """Fetch JSON with retries."""
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (503, 429):
                time.sleep(3 * (attempt + 1))
                continue
            return None
        except Exception:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            return None
    return None


def get_album_tags(artist, album_title):
    """Get top tags for an album from Last.fm."""
    params = urllib.parse.urlencode({
        'method': 'album.getTopTags',
        'artist': artist,
        'album': album_title,
        'api_key': LASTFM_API_KEY,
        'format': 'json',
    })
    url = f'https://ws.audioscrobbler.com/2.0/?{params}'
    data = api_get(url)
    if not data:
        return []

    # Last.fm returns error in JSON body sometimes
    if 'error' in data:
        return []

    tags = data.get('toptags', {}).get('tag', [])
    if isinstance(tags, dict):
        tags = [tags]
    return [{'name': t.get('name', '').lower().strip(), 'count': int(t.get('count', 0))}
            for t in tags if t.get('name')]


def classify_tags(tags):
    """Map Last.fm tags to a suggested era."""
    mapped_eras = []
    for tag in tags:
        name = tag['name']
        count = tag['count']
        if name in SKIP_TAGS or count < 5:
            continue
        era = GENRE_TO_ERA.get(name)
        if era and era not in mapped_eras:
            mapped_eras.append(era)

    if not mapped_eras:
        return None

    # Tags are ranked by Last.fm community usage count,
    # so first matched era reflects community consensus
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
    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    cache = load_cache(CACHE_FILE)
    wikidata_cache = load_cache(WIKIDATA_CACHE_FILE)
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    # Count already resolved by Wikidata
    wd_resolved = sum(1 for v in wikidata_cache.values() if v.get('status') == 'resolved')
    print(f'Total albums: {len(albums)}')
    print(f'Wikidata resolved (skip): {wd_resolved}')
    print(f'Already in Last.fm cache: {len(cache)}')
    print(f'Starting from index: {start_from}')
    print()

    resolved = 0
    unresolved = 0
    errors = 0
    skipped_wd = 0
    skipped_cached = 0

    for idx, album in enumerate(albums):
        aid = album['id']

        if idx < start_from:
            continue

        if aid in cache:
            skipped_cached += 1
            continue

        # Skip if Wikidata already resolved
        if wikidata_cache.get(aid, {}).get('status') == 'resolved':
            cache[aid] = {'status': 'skipped', 'reason': 'resolved_by_wikidata'}
            skipped_wd += 1
            continue

        artist = album.get('artist', '')
        title = album['title']

        tags = get_album_tags(artist, title)
        time.sleep(0.25)

        if not tags:
            cache[aid] = {
                'status': 'unresolved',
                'source': 'lastfm',
                'genres': [],
                'reason': 'no_tags_returned',
            }
            unresolved += 1
            print(f'[{idx + 1}/{len(albums)}] {artist} - {title[:40]}: no tags')
            if (idx + 1) % 20 == 0:
                save_cache(cache)
            continue

        # Filter and classify
        useful_tags = [t for t in tags if t['name'] not in SKIP_TAGS and t['count'] >= 5]
        genre_names = [t['name'] for t in useful_tags[:10]]
        suggested_era = classify_tags(tags)

        if suggested_era:
            cache[aid] = {
                'status': 'resolved',
                'source': 'lastfm',
                'genres': genre_names,
                'suggested_era': suggested_era,
                'confidence': 'high',
                'top_tags': [{'name': t['name'], 'count': t['count']} for t in useful_tags[:5]],
            }
            resolved += 1
            print(f'[{idx + 1}/{len(albums)}] {artist} - {title[:40]}: {genre_names[:3]} -> {suggested_era}')
        else:
            cache[aid] = {
                'status': 'unresolved',
                'source': 'lastfm',
                'genres': genre_names,
                'reason': 'no_jazz_subgenre_tags',
                'top_tags': [{'name': t['name'], 'count': t['count']} for t in useful_tags[:5]],
            }
            unresolved += 1
            print(f'[{idx + 1}/{len(albums)}] {artist} - {title[:40]}: no match {genre_names[:3]}')

        if (idx + 1) % 20 == 0:
            save_cache(cache)
            print(f'  [cache saved at {idx + 1}]')

    save_cache(cache)

    # Summary
    all_statuses = [v.get('status') for v in cache.values()]
    print(f'\n=== Last.fm Fetch Summary ===')
    print(f'Resolved (tags → era):      {all_statuses.count("resolved")}')
    print(f'Unresolved (no subgenre):   {all_statuses.count("unresolved")}')
    print(f'Skipped (Wikidata resolved): {all_statuses.count("skipped")}')
    print(f'Total cached: {len(cache)}')


if __name__ == '__main__':
    main()

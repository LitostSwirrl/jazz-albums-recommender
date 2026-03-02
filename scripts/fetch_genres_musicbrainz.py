#!/usr/bin/env python3
"""
Fetch album genre tags from MusicBrainz release-groups.

955/1000 albums have MB release UUIDs in coverUrl.
Strategy:
  1. Extract UUID from coverUrl
  2. Fetch release -> get release-group ID
  3. Fetch release-group genres + tags
  4. For albums without coverUrl UUID, search by artist MBID + title

Cache: /tmp/mb_genre_tags_cache.json
Rate limit: 1.1s between requests
Usage: python3 fetch_genres_musicbrainz.py [start_index]
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
CACHE_FILE = '/tmp/mb_genre_tags_cache.json'
ARTIST_MBID_CACHE = '/tmp/artist_mbids.json'

UUID_PATTERN = re.compile(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})')

# Normalization map: raw MB tag -> curated genre
GENRE_NORMALIZE = {
    'bebop': 'bebop',
    'bop': 'bebop',
    'be-bop': 'bebop',
    'hard bop': 'hard bop',
    'hardbop': 'hard bop',
    'hard-bop': 'hard bop',
    'cool jazz': 'cool jazz',
    'west coast jazz': 'cool jazz',
    'free jazz': 'free jazz',
    'avant-garde jazz': 'avant-garde jazz',
    'avant-garde music': 'avant-garde jazz',
    'avant-garde': 'avant-garde jazz',
    'free improvisation': 'free improvisation',
    'jazz fusion': 'jazz fusion',
    'fusion': 'jazz fusion',
    'jazz-rock': 'jazz fusion',
    'jazz rock': 'jazz fusion',
    'post-bop': 'post-bop',
    'post bop': 'post-bop',
    'modal jazz': 'modal jazz',
    'soul jazz': 'soul jazz',
    'latin jazz': 'latin jazz',
    'afro-cuban jazz': 'latin jazz',
    'swing music': 'swing',
    'swing': 'swing',
    'big band': 'big band',
    'big band music': 'big band',
    'dixieland': 'dixieland',
    'new orleans jazz': 'early jazz',
    'early jazz': 'early jazz',
    'spiritual jazz': 'spiritual jazz',
    'vocal jazz': 'vocal jazz',
    'smooth jazz': 'smooth jazz',
    'contemporary jazz': 'contemporary jazz',
    'jazz-funk': 'jazz-funk',
    'jazz funk': 'jazz-funk',
    'orchestral jazz': 'orchestral jazz',
    'third stream': 'orchestral jazz',
    'chamber jazz': 'chamber jazz',
    'blues': 'blues',
    'loft jazz': 'loft jazz',
    'african jazz': 'African jazz',
    'world music': 'world jazz',
    'brazilian jazz': 'Brazilian jazz',
    'bossa nova': 'bossa nova',
    'experimental music': 'experimental',
    'experimental': 'experimental',
    'piano trio': 'piano trio',
    'acid jazz': 'acid jazz',
    'nu jazz': 'contemporary jazz',
    'afrobeat': 'African jazz',
    'jazz': None,  # skip — redundant on a jazz site
    'jazz music': None,
}

# Tags to skip entirely (not genre-relevant)
SKIP_TAGS = {
    'jazz', 'jazz music', 'seen live', 'favorites', 'favourite',
    'albums i own', 'my favorites', 'best albums', 'classic',
    'instrumental', 'american', 'male vocalists', 'female vocalists',
    'music', 'favourite albums', 'albums', 'vinyl', 'cd', 'own it',
    'usa', 'american jazz', 'piano', 'saxophone', 'trumpet', 'guitar',
    'bass', 'drums', 'vocals', 'vocal', 'singer',
}


def api_get(url, timeout=15):
    """Fetch JSON with retries and rate-limit handling."""
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (503, 429):
                wait = 5 * (attempt + 1)
                print(f'  Rate limited ({e.code}), waiting {wait}s...')
                time.sleep(wait)
                continue
            return None
        except Exception:
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            return None
    return None


def extract_genres(data):
    """Extract normalized genres from MB response (tags + genres fields)."""
    genres = []
    # MB 'genres' field (structured)
    for g in data.get('genres', []):
        name = g.get('name', '').lower().strip()
        if name in SKIP_TAGS:
            continue
        normalized = GENRE_NORMALIZE.get(name)
        if normalized and normalized not in genres:
            genres.append(normalized)
    # MB 'tags' field (community-voted)
    for t in data.get('tags', []):
        name = t.get('name', '').lower().strip()
        count = t.get('count', 0)
        if name in SKIP_TAGS or count < 1:
            continue
        normalized = GENRE_NORMALIZE.get(name)
        if normalized and normalized not in genres:
            genres.append(normalized)
    return genres


def fetch_by_release_id(release_id):
    """Fetch genres via release -> release-group chain."""
    url = f'https://musicbrainz.org/ws/2/release/{release_id}?inc=release-groups+genres+tags&fmt=json'
    data = api_get(url)
    if not data:
        return [], None

    genres = extract_genres(data)

    # Get release-group for better genre coverage
    rg_id = data.get('release-group', {}).get('id')
    if rg_id:
        time.sleep(1.1)
        url2 = f'https://musicbrainz.org/ws/2/release-group/{rg_id}?inc=genres+tags&fmt=json'
        data2 = api_get(url2)
        if data2:
            rg_genres = extract_genres(data2)
            for g in rg_genres:
                if g not in genres:
                    genres.append(g)

    return genres, rg_id


def fetch_by_artist_mbid_and_title(artist_mbid, title):
    """Search for release-group by artist MBID + title."""
    safe_title = title.replace('"', '\\"')
    query = f'releasegroup:"{safe_title}" AND arid:{artist_mbid}'
    params = urllib.parse.urlencode({
        'query': query,
        'fmt': 'json',
        'limit': '5',
    })
    url = f'https://musicbrainz.org/ws/2/release-group/?{params}'
    data = api_get(url)
    if not data:
        return []

    rgs = data.get('release-groups', [])
    if not rgs:
        return []

    # Use first matching release-group
    rg_id = rgs[0].get('id')
    if not rg_id:
        return []

    time.sleep(1.1)
    url2 = f'https://musicbrainz.org/ws/2/release-group/{rg_id}?inc=genres+tags&fmt=json'
    data2 = api_get(url2)
    if not data2:
        return []

    return extract_genres(data2)


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
    artist_mbids = load_cache(ARTIST_MBID_CACHE)
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    total = len(albums)
    resolved = 0
    unresolved = 0
    skipped = 0
    no_uuid = 0

    print(f'Total albums: {total}')
    print(f'Already cached: {len(cache)}')
    print(f'Artist MBIDs available: {sum(1 for v in artist_mbids.values() if v)}')
    print(f'Starting from index: {start_from}')
    print()

    for idx, album in enumerate(albums):
        if idx < start_from:
            continue

        aid = album['id']
        if aid in cache:
            skipped += 1
            continue

        title = album['title']
        artist = album.get('artist', '')
        cover_url = album.get('coverUrl', '')

        # Strategy 1: Extract UUID from coverUrl
        mb_match = UUID_PATTERN.search(cover_url) if cover_url else None
        # Skip wsrv.nl proxy URLs that aren't MB cover art
        if mb_match and 'wsrv.nl' in cover_url:
            mb_match = None

        if mb_match:
            release_id = mb_match.group(1)
            genres, rg_id = fetch_by_release_id(release_id)
            time.sleep(1.1)

            if genres:
                cache[aid] = {
                    'status': 'resolved',
                    'source': 'musicbrainz_release',
                    'release_id': release_id,
                    'release_group_id': rg_id,
                    'genres': genres,
                }
                resolved += 1
                print(f'[{idx+1}/{total}] {artist} - {title[:35]}: {genres}')
            else:
                cache[aid] = {
                    'status': 'unresolved',
                    'source': 'musicbrainz_release',
                    'release_id': release_id,
                    'release_group_id': rg_id,
                    'genres': [],
                    'reason': 'no_genre_tags',
                }
                unresolved += 1
                print(f'[{idx+1}/{total}] {artist} - {title[:35]}: no tags')
        else:
            # Strategy 2: Search by artist MBID + title
            artist_id = album.get('artistId', '')
            artist_mbid = artist_mbids.get(artist_id)

            if artist_mbid:
                genres = fetch_by_artist_mbid_and_title(artist_mbid, title)
                time.sleep(1.1)

                if genres:
                    cache[aid] = {
                        'status': 'resolved',
                        'source': 'musicbrainz_search',
                        'genres': genres,
                    }
                    resolved += 1
                    print(f'[{idx+1}/{total}] {artist} - {title[:35]}: (search) {genres}')
                else:
                    cache[aid] = {
                        'status': 'unresolved',
                        'source': 'musicbrainz_search',
                        'genres': [],
                        'reason': 'no_genre_tags_from_search',
                    }
                    unresolved += 1
                    print(f'[{idx+1}/{total}] {artist} - {title[:35]}: (search) no tags')
            else:
                cache[aid] = {
                    'status': 'unresolved',
                    'source': 'no_mb_id',
                    'genres': [],
                    'reason': 'no_cover_uuid_or_artist_mbid',
                }
                no_uuid += 1
                print(f'[{idx+1}/{total}] {artist} - {title[:35]}: no MB ID available')

        # Save cache periodically
        if (idx + 1) % 20 == 0:
            save_cache(cache)
            print(f'  [cache saved at {idx+1}]')

    save_cache(cache)

    # Summary
    all_resolved = sum(1 for v in cache.values() if v.get('status') == 'resolved')
    all_unresolved = sum(1 for v in cache.values() if v.get('status') == 'unresolved')

    print(f'\n=== MusicBrainz Genre Fetch Summary ===')
    print(f'Total albums: {total}')
    print(f'Resolved (with genres): {all_resolved}')
    print(f'Unresolved (no tags):   {all_unresolved}')
    print(f'Skipped (cached):       {skipped}')
    print(f'No MB ID available:     {no_uuid}')
    print(f'Cache: {CACHE_FILE}')

    # Genre distribution
    from collections import Counter
    genre_counts = Counter()
    for v in cache.values():
        for g in v.get('genres', []):
            genre_counts[g] += 1
    if genre_counts:
        print(f'\nGenre distribution ({len(genre_counts)} unique):')
        for g, c in genre_counts.most_common():
            print(f'  {g}: {c}')


if __name__ == '__main__':
    main()

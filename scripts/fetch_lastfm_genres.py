#!/usr/bin/env python3
"""
Improved Last.fm genre tag fetcher with artist-level fallback + name normalization.

Improvements over fetch_era_lastfm.py:
  A. Artist-level fallback: when album.getTopTags returns nothing,
     call artist.getTopTags for genre context (marked source_level: "artist")
  B. Name normalization: strip colons/subtitles, handle & in artist names,
     ellipsis, try shortened title if full title fails

Cache: /tmp/lastfm_genre_tags_cache.json
Usage: python3 fetch_lastfm_genres.py [start_index]
"""

import json
import os
import re
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
CACHE_FILE = '/tmp/lastfm_genre_tags_cache.json'
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

# Normalization map: raw Last.fm tag -> curated genre
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
    'avant garde': 'avant-garde jazz',
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
    'electric jazz': 'jazz fusion',
    'crossover jazz': 'jazz fusion',
    'neo-bop': 'post-bop',
    'gypsy jazz': 'swing',
    'trad jazz': 'early jazz',
    'traditional jazz': 'early jazz',
}

# Tags to skip (not genre-relevant)
SKIP_TAGS = {
    'jazz', 'jazz music', 'seen live', 'favorites', 'favourite',
    'albums i own', 'my favorites', 'best albums', 'classic',
    'instrumental', 'american', 'male vocalists', 'female vocalists',
    'music', 'favourite albums', 'albums', 'vinyl', 'cd', 'own it',
    'usa', 'american jazz', 'piano', 'saxophone', 'trumpet', 'guitar',
    'bass', 'drums', 'vocals', 'vocal', 'singer',
    '00s', '10s', '20s', '90s', '80s', '70s', '60s', '50s', '40s', '30s',
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


def normalize_title(title):
    """Generate title variants for fuzzy matching."""
    variants = [title]

    # Strip subtitle after colon
    if ':' in title:
        variants.append(title.split(':')[0].strip())

    # Strip subtitle after dash (but only if > 3 chars before dash)
    if ' - ' in title and len(title.split(' - ')[0]) > 3:
        variants.append(title.split(' - ')[0].strip())

    # Handle ellipsis
    if '...' in title:
        variants.append(title.replace('...', '').strip())

    # Strip parenthetical suffixes
    paren = re.sub(r'\s*\([^)]*\)\s*$', '', title).strip()
    if paren != title:
        variants.append(paren)

    return variants


def normalize_artist(artist):
    """Generate artist name variants."""
    variants = [artist]

    # Handle & -> and
    if '&' in artist:
        variants.append(artist.replace('&', 'and'))

    # Handle "and" -> &
    if ' and ' in artist.lower():
        variants.append(re.sub(r'\band\b', '&', artist, flags=re.IGNORECASE))

    return variants


def get_album_tags(artist, title):
    """Get top tags for an album from Last.fm, trying name variants."""
    artist_variants = normalize_artist(artist)
    title_variants = normalize_title(title)

    for a_variant in artist_variants:
        for t_variant in title_variants:
            params = urllib.parse.urlencode({
                'method': 'album.getTopTags',
                'artist': a_variant,
                'album': t_variant,
                'api_key': LASTFM_API_KEY,
                'format': 'json',
            })
            url = f'https://ws.audioscrobbler.com/2.0/?{params}'
            data = api_get(url)
            time.sleep(0.25)

            if not data or 'error' in data:
                continue

            tags = data.get('toptags', {}).get('tag', [])
            if isinstance(tags, dict):
                tags = [tags]

            useful = [
                {'name': t.get('name', '').lower().strip(), 'count': int(t.get('count', 0))}
                for t in tags if t.get('name')
            ]
            # Filter for tags with minimum usage
            useful = [t for t in useful if t['count'] >= 5 and t['name'] not in SKIP_TAGS]

            if useful:
                return useful, 'album'

    return [], None


def get_artist_tags(artist):
    """Get top tags for an artist (fallback when no album tags)."""
    artist_variants = normalize_artist(artist)

    for a_variant in artist_variants:
        params = urllib.parse.urlencode({
            'method': 'artist.getTopTags',
            'artist': a_variant,
            'api_key': LASTFM_API_KEY,
            'format': 'json',
        })
        url = f'https://ws.audioscrobbler.com/2.0/?{params}'
        data = api_get(url)
        time.sleep(0.25)

        if not data or 'error' in data:
            continue

        tags = data.get('toptags', {}).get('tag', [])
        if isinstance(tags, dict):
            tags = [tags]

        useful = [
            {'name': t.get('name', '').lower().strip(), 'count': int(t.get('count', 0))}
            for t in tags if t.get('name')
        ]
        useful = [t for t in useful if t['count'] >= 5 and t['name'] not in SKIP_TAGS]

        if useful:
            return useful, 'artist'

    return [], None


def extract_genres(tags):
    """Map raw tags to normalized genre names."""
    genres = []
    for tag in tags[:15]:  # top 15 tags
        name = tag['name']
        normalized = GENRE_NORMALIZE.get(name)
        if normalized and normalized not in genres:
            genres.append(normalized)
    return genres


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
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    total = len(albums)
    album_resolved = 0
    artist_resolved = 0
    unresolved = 0
    skipped = 0

    print(f'Total albums: {total}')
    print(f'Already cached: {len(cache)}')
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

        # Try album-level tags first
        tags, source_level = get_album_tags(artist, title)

        if tags:
            genres = extract_genres(tags)
            if genres:
                cache[aid] = {
                    'status': 'resolved',
                    'source': 'lastfm',
                    'source_level': 'album',
                    'genres': genres,
                    'top_tags': [{'name': t['name'], 'count': t['count']} for t in tags[:5]],
                }
                album_resolved += 1
                print(f'[{idx+1}/{total}] {artist} - {title[:35]}: (album) {genres}')
                if (idx + 1) % 20 == 0:
                    save_cache(cache)
                continue

        # Artist-level fallback
        tags, source_level = get_artist_tags(artist)

        if tags:
            genres = extract_genres(tags)
            if genres:
                cache[aid] = {
                    'status': 'resolved',
                    'source': 'lastfm',
                    'source_level': 'artist',
                    'genres': genres,
                    'confidence': 'medium',
                    'top_tags': [{'name': t['name'], 'count': t['count']} for t in tags[:5]],
                }
                artist_resolved += 1
                print(f'[{idx+1}/{total}] {artist} - {title[:35]}: (artist) {genres}')
                if (idx + 1) % 20 == 0:
                    save_cache(cache)
                continue

        # Unresolved
        cache[aid] = {
            'status': 'unresolved',
            'source': 'lastfm',
            'genres': [],
            'reason': 'no_tags_found',
        }
        unresolved += 1
        print(f'[{idx+1}/{total}] {artist} - {title[:35]}: no tags')

        if (idx + 1) % 20 == 0:
            save_cache(cache)
            print(f'  [cache saved at {idx+1}]')

    save_cache(cache)

    # Summary
    all_album = sum(1 for v in cache.values()
                    if v.get('status') == 'resolved' and v.get('source_level') == 'album')
    all_artist = sum(1 for v in cache.values()
                     if v.get('status') == 'resolved' and v.get('source_level') == 'artist')
    all_unresolved = sum(1 for v in cache.values() if v.get('status') == 'unresolved')

    print(f'\n=== Last.fm Genre Fetch Summary ===')
    print(f'Total albums: {total}')
    print(f'Resolved (album tags):  {all_album}')
    print(f'Resolved (artist tags): {all_artist}')
    print(f'Unresolved:             {all_unresolved}')
    print(f'Skipped (cached):       {skipped}')
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

#!/usr/bin/env python3
"""
Fetch cover art for albums with empty coverUrl in albums.json.

Sources tried in order:
  1. MusicBrainz search -> Cover Art Archive (front image)
  2. iTunes Search API fallback (artworkUrl100 bumped to 600x600)

Archive.org / coverartarchive.org URLs are proxied via wsrv.nl.
Cache: /tmp/missing_covers.json
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ALBUMS_FILE = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'albums.json')
CACHE_FILE = '/tmp/missing_covers.json'

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (contact@example.com)',
    'Accept': 'application/json',
}


def api_get(url, timeout=20):
    """HTTP GET with retries for transient errors."""
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


def proxy_url(original_url):
    """Proxy archive.org / coverartarchive.org URLs through wsrv.nl."""
    if not original_url:
        return original_url
    if 'archive.org' in original_url or 'coverartarchive.org' in original_url:
        encoded = urllib.parse.quote(original_url, safe='')
        return f'https://wsrv.nl/?url={encoded}&w=500&output=webp'
    return original_url


def normalize(s):
    """Normalize string for fuzzy matching."""
    s = s.lower()
    s = re.sub(r'\s*\(.*?\)\s*', ' ', s)
    s = re.sub(r'\s*\[.*?\]\s*', ' ', s)
    s = re.sub(r'[^\w\s]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def title_match(query_title, result_title):
    """Fuzzy title matching."""
    q = normalize(query_title)
    r = normalize(result_title)
    if q == r or q in r or r in q:
        return True
    q_words = set(q.split())
    r_words = set(r.split())
    if not q_words:
        return False
    return len(q_words & r_words) >= max(1, len(q_words) * 0.6)


# --- Source 1: MusicBrainz + Cover Art Archive ---

def search_musicbrainz(title, artist):
    """Search MusicBrainz for release-groups matching title + artist."""
    query = urllib.parse.quote(f'"{title}" AND artist:"{artist}"')
    url = f'https://musicbrainz.org/ws/2/release-group/?query={query}&fmt=json&limit=5'
    time.sleep(1.1)  # MusicBrainz rate limit: 1 req/sec
    data = api_get(url)
    if not data:
        return []
    return data.get('release-groups', [])


def get_cover_from_release_group(rg_mbid):
    """Try Cover Art Archive for a release-group directly."""
    url = f'https://coverartarchive.org/release-group/{rg_mbid}/'
    data = api_get(url)
    if not data or not data.get('images'):
        return None

    # Prefer front cover
    for img in data['images']:
        if img.get('front'):
            t = img.get('thumbnails', {})
            cover = t.get('large') or t.get('500') or img.get('image')
            if cover:
                return cover.replace('http://', 'https://')

    # Fallback to first image
    img = data['images'][0]
    t = img.get('thumbnails', {})
    cover = t.get('large') or t.get('500') or img.get('image')
    if cover:
        return cover.replace('http://', 'https://')

    return None


def find_cover_musicbrainz(title, artist):
    """Search MusicBrainz, then try Cover Art Archive for each match."""
    release_groups = search_musicbrainz(title, artist)

    artist_lower = artist.lower()
    for rg in release_groups:
        # Verify artist name is a reasonable match
        rg_artist = ''
        credits = rg.get('artist-credit', [])
        if credits:
            rg_artist = credits[0].get('name', '').lower() if credits else ''

        if not (artist_lower in rg_artist or rg_artist in artist_lower):
            continue

        # Check title similarity
        rg_title = rg.get('title', '')
        if not title_match(title, rg_title):
            continue

        mbid = rg.get('id')
        if not mbid:
            continue

        time.sleep(1.1)
        cover = get_cover_from_release_group(mbid)
        if cover:
            return proxy_url(cover)

    return None


# --- Source 2: iTunes Search API ---

def search_itunes_cover(title, artist):
    """Search iTunes for album artwork, return 600x600 URL or None."""
    query = urllib.parse.quote(f'{title} {artist}')
    url = f'https://itunes.apple.com/search?term={query}&media=music&entity=album&limit=5&country=US'

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'JazzAlbumsRecommender/1.0 (contact@example.com)',
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f'  iTunes error: {e}')
        return None

    if not data.get('results'):
        return None

    artist_lower = artist.lower()
    for r in data['results']:
        r_artist = r.get('artistName', '').lower()
        r_title = r.get('collectionName', '')

        if (artist_lower in r_artist or r_artist in artist_lower) and \
           title_match(title, r_title):
            artwork = r.get('artworkUrl100', '')
            if artwork:
                return artwork.replace('100x100bb', '600x600bb')

    return None


def search_itunes_artist_only(title, artist):
    """Search by artist only, fuzzy match title."""
    query = urllib.parse.quote(artist)
    url = f'https://itunes.apple.com/search?term={query}&media=music&entity=album&limit=25&country=US'

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'JazzAlbumsRecommender/1.0 (contact@example.com)',
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None

    if not data.get('results'):
        return None

    for r in data['results']:
        r_title = r.get('collectionName', '')
        if title_match(title, r_title):
            artwork = r.get('artworkUrl100', '')
            if artwork:
                return artwork.replace('100x100bb', '600x600bb')

    return None


# --- Main ---

def main():
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    # Load albums
    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    # Find albums with empty coverUrl
    targets = [a for a in albums if a.get('coverUrl', '') == '']
    print(f'Albums with empty coverUrl: {len(targets)}')

    # Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                cache = json.load(f)
            print(f'Cache loaded: {len(cache)} entries')
        except Exception:
            pass

    found_this_run = 0
    searched_this_run = 0

    for i, album in enumerate(targets):
        if i < start_from:
            continue

        aid = album['id']
        if aid in cache:
            continue

        title = album['title']
        artist = album['artist']
        print(f'[{i+1}/{len(targets)}] {artist} - {title} ({album["year"]})...', end=' ', flush=True)
        searched_this_run += 1

        # Strategy 1: MusicBrainz + Cover Art Archive
        cover = find_cover_musicbrainz(title, artist)

        # Strategy 2: iTunes (title + artist)
        if not cover:
            time.sleep(3.0)
            cover = search_itunes_cover(title, artist)

        # Strategy 3: iTunes (artist only, fuzzy title match)
        if not cover:
            time.sleep(3.0)
            cover = search_itunes_artist_only(title, artist)

        if cover:
            cache[aid] = cover
            found_this_run += 1
            print('FOUND')
        else:
            cache[aid] = None
            print('NOT FOUND')

        # Save cache every 5 albums
        if searched_this_run % 5 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)

    # Final cache save
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    # --- Apply found covers to albums.json ---
    found_covers = {k: v for k, v in cache.items() if v}
    if found_covers:
        print(f'\nApplying {len(found_covers)} covers to albums.json...')
        album_map = {a['id']: a for a in albums}
        applied = 0
        for aid, cover_url in found_covers.items():
            if aid in album_map and album_map[aid].get('coverUrl', '') == '':
                album_map[aid]['coverUrl'] = cover_url
                applied += 1

        if applied > 0:
            with open(ALBUMS_FILE, 'w') as f:
                json.dump(albums, f, indent=2, ensure_ascii=False)
            print(f'Applied {applied} covers to albums.json')
        else:
            print('No new covers to apply (all already had coverUrl)')

    # --- Summary ---
    found_total = sum(1 for v in cache.values() if v)
    not_found_total = sum(1 for v in cache.values() if not v)
    remaining_empty = sum(1 for a in albums if a.get('coverUrl', '') == '')

    print(f'\n{"=" * 40}')
    print(f'         SUMMARY')
    print(f'{"=" * 40}')
    print(f'Searched this run:   {searched_this_run}')
    print(f'Found this run:      {found_this_run}')
    print(f'Total in cache:      {len(cache)}')
    print(f'  - Found:           {found_total}')
    print(f'  - Not found:       {not_found_total}')
    print(f'Still missing covers: {remaining_empty}')
    print(f'Cache file: {CACHE_FILE}')


if __name__ == '__main__':
    main()

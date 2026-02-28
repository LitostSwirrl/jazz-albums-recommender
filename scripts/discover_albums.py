#!/usr/bin/env python3
"""
Stage 2: Discover albums for artists with fewer than 3 albums.
Queries MusicBrainz for release-groups (type=album), scores and ranks them.
Requires: /tmp/artist_mbids.json from Stage 1.
Output: /tmp/discovered_albums.json
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
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')
MBID_FILE = '/tmp/artist_mbids.json'
CACHE_FILE = '/tmp/discovered_albums.json'

# Artists to skip (no jazz recordings)
SKIP_ARTISTS = {
    'arnold-schoenberg', 'darius-milhaud', 'buddy-bolden',
    'lovie-austin', 'james-jamerson', 'jerry-jemmott',
}

TARGET_ALBUMS = 3


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


def fetch_release_groups(artist_mbid, artist_name, offset=0):
    """Fetch album release-groups for an artist from MusicBrainz."""
    encoded = urllib.parse.quote(artist_mbid)
    url = (
        f'https://musicbrainz.org/ws/2/release-group'
        f'?artist={encoded}&type=album&fmt=json&limit=100&offset={offset}'
    )
    data = api_get(url)
    if not data:
        return []

    return data.get('release-groups', [])


def score_release_group(rg, existing_titles):
    """Score a release group for selection priority."""
    title = rg.get('title', '')
    title_lower = title.lower()

    # Skip if title matches existing album
    for et in existing_titles:
        if et.lower() == title_lower:
            return -1
        # Also skip close matches (subset)
        et_clean = re.sub(r'[^a-z0-9 ]', '', et.lower())
        title_clean = re.sub(r'[^a-z0-9 ]', '', title_lower)
        if et_clean and title_clean and (et_clean in title_clean or title_clean in et_clean):
            return -1

    score = 0

    # MB rating (0-100)
    rating = rg.get('rating', {})
    if rating and rating.get('value'):
        score += float(rating['value']) * 20  # 0-100

    # Rating count (popularity indicator)
    rating_count = rating.get('votes-count', 0) if rating else 0
    score += min(rating_count * 5, 50)  # Cap at 50 points

    # Primary type preference: Album > EP > Single
    primary_type = rg.get('primary-type', '')
    if primary_type == 'Album':
        score += 30
    elif primary_type == 'EP':
        score += 10

    # Secondary types: penalize compilations, live, remix
    secondary_types = [t.lower() for t in rg.get('secondary-types', [])]
    if 'compilation' in secondary_types:
        score -= 50
    if 'live' in secondary_types:
        score -= 20
    if 'remix' in secondary_types:
        score -= 40
    if 'soundtrack' in secondary_types:
        score -= 30

    # Skip "Greatest Hits", "Best of", "Complete", etc.
    skip_patterns = [
        'greatest hits', 'best of', 'complete', 'anthology',
        'collection', 'essential', 'definitive', 'box set',
    ]
    for pat in skip_patterns:
        if pat in title_lower:
            score -= 100

    # Prefer titled albums over generic names
    if title_lower in ('live', 'greatest hits', 'untitled'):
        score -= 30

    return score


def generate_album_id(title, artist_name, existing_ids):
    """Generate a unique kebab-case album ID."""
    # Convert to kebab-case
    clean = re.sub(r'[^a-zA-Z0-9\s-]', '', title.lower())
    clean = re.sub(r'\s+', '-', clean.strip())
    clean = re.sub(r'-+', '-', clean)
    clean = clean.strip('-')

    if not clean:
        clean = 'untitled'

    album_id = clean

    # If collision, add artist surname
    if album_id in existing_ids:
        # Get last name
        parts = artist_name.split()
        surname = parts[-1].lower() if parts else 'unknown'
        surname = re.sub(r'[^a-z]', '', surname)
        album_id = f'{clean}-{surname}'

    # If still collision, add number
    if album_id in existing_ids:
        n = 2
        while f'{album_id}-{n}' in existing_ids:
            n += 1
        album_id = f'{album_id}-{n}'

    return album_id


def main():
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    with open(ARTISTS_FILE) as f:
        artists = json.load(f)
    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    # Load artist MBIDs
    if not os.path.exists(MBID_FILE):
        print(f'ERROR: {MBID_FILE} not found. Run resolve_artist_mbids.py first.')
        sys.exit(1)

    with open(MBID_FILE) as f:
        mbid_map = json.load(f)

    # Build existing album lookup
    existing_album_ids = {a['id'] for a in albums}
    artist_albums = {}
    for a in albums:
        aid = a.get('artistId', '')
        if aid not in artist_albums:
            artist_albums[aid] = []
        artist_albums[aid].append(a['title'])

    # Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f'Cache loaded: {len(cache)} artists processed')

    # Build set of all IDs (existing + already discovered)
    all_ids = set(existing_album_ids)
    for artist_data in cache.values():
        for album in artist_data.get('albums', []):
            all_ids.add(album['id'])

    # Find artists needing more albums
    artists_needing = []
    for artist in artists:
        aid = artist['id']
        if aid in SKIP_ARTISTS:
            continue
        current_count = len(artist_albums.get(aid, []))
        # Also count already-discovered albums in cache
        cached_count = len(cache.get(aid, {}).get('albums', []))
        total = current_count + cached_count
        if total < TARGET_ALBUMS:
            artists_needing.append((artist, TARGET_ALBUMS - total))

    print(f'Artists needing albums: {len(artists_needing)}')
    print(f'Artists with MBID: {sum(1 for a, _ in artists_needing if mbid_map.get(a["id"]))}')

    total = len(artists_needing)
    new_albums_total = 0

    for i, (artist, needed) in enumerate(artists_needing):
        if i < start_from:
            continue

        aid = artist['id']
        if aid in cache:
            continue

        mbid = mbid_map.get(aid)
        if not mbid:
            print(f'[{i+1}/{total}] {artist["name"]} - NO MBID, skipping')
            cache[aid] = {'albums': [], 'error': 'no_mbid'}
            continue

        print(f'[{i+1}/{total}] {artist["name"]} (need {needed})...', end=' ', flush=True)

        time.sleep(1.1)
        release_groups = fetch_release_groups(mbid, artist['name'])

        if not release_groups:
            print('no release-groups found')
            cache[aid] = {'albums': [], 'error': 'no_releases'}
            continue

        # Score and rank
        existing_titles = artist_albums.get(aid, [])
        scored = []
        for rg in release_groups:
            s = score_release_group(rg, existing_titles)
            if s >= 0:
                scored.append((s, rg))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected = scored[:needed]

        discovered = []
        for score, rg in selected:
            title = rg.get('title', 'Untitled')
            rg_id = rg.get('id', '')  # release-group MBID
            first_release = rg.get('first-release-date', '')
            year = int(first_release[:4]) if first_release and len(first_release) >= 4 else None

            album_id = generate_album_id(title, artist['name'], all_ids)
            all_ids.add(album_id)

            discovered.append({
                'id': album_id,
                'title': title,
                'artist': artist['name'],
                'artistId': aid,
                'releaseGroupMbid': rg_id,
                'year': year,
                'primaryType': rg.get('primary-type', ''),
                'secondaryTypes': rg.get('secondary-types', []),
                'score': score,
            })

        cache[aid] = {'albums': discovered}
        new_albums_total += len(discovered)
        titles = [d['title'] for d in discovered]
        print(f'{len(discovered)} albums: {", ".join(titles[:3])}')

        # Save every 10
        if (i + 1) % 10 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)

    # Final save
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    # Stats
    all_discovered = []
    for artist_data in cache.values():
        all_discovered.extend(artist_data.get('albums', []))

    print(f'\n=== Results ===')
    print(f'Total new albums discovered: {len(all_discovered)}')
    print(f'Artists processed: {len(cache)}')
    print(f'Cache: {CACHE_FILE}')

    # Show artists that got 0 albums
    zero_albums = [(aid, d.get('error', '')) for aid, d in cache.items()
                   if len(d.get('albums', [])) == 0]
    if zero_albums:
        print(f'\nArtists with 0 new albums ({len(zero_albums)}):')
        artist_map = {a['id']: a['name'] for a in artists}
        for aid, err in zero_albums[:20]:
            print(f'  {artist_map.get(aid, aid)} ({err})')


if __name__ == '__main__':
    main()

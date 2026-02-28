#!/usr/bin/env python3
"""
Stage 2 (Expansion): Discover albums from MusicBrainz based on expansion plan.
Reads /tmp/expansion_plan.json (from Stage 0) and /tmp/artist_mbids.json (from Stage 1).
Checks src/data/albums.json to avoid duplicates.
Uses enhanced scoring with curated must-have list from the expansion plan.
Output: /tmp/expansion_discovered.json (resumable, saves every 10 artists)

Usage: python3 discover_expansion_albums.py [start_from_index]
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
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')

PLAN_FILE = '/tmp/expansion_plan.json'
MBID_FILE = '/tmp/artist_mbids.json'
CACHE_FILE = '/tmp/expansion_discovered.json'

# Must-have albums always get this score so they are always selected
MUST_HAVE_SCORE = 10000


def api_get(url, timeout=20):
    """Fetch JSON from URL with 3 retries and backoff on 503/429."""
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


def fetch_release_groups(artist_mbid, offset=0):
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


def normalize_title(title):
    """Strip punctuation and lowercase for fuzzy matching."""
    return re.sub(r'[^a-z0-9 ]', '', title.lower()).strip()


def is_curated_match(rg_title, curated_titles_normalized):
    """Check if a release-group title fuzzy-matches any curated must-have title."""
    rg_normalized = normalize_title(rg_title)
    if not rg_normalized:
        return False
    for curated_norm in curated_titles_normalized:
        if not curated_norm:
            continue
        # Exact normalized match
        if rg_normalized == curated_norm:
            return True
        # Substring match (curated is contained in rg or vice versa)
        if curated_norm in rg_normalized or rg_normalized in curated_norm:
            return True
    return False


def score_release_group(rg, existing_titles, curated_titles_normalized):
    """Score a release group for selection priority.

    Returns -1 if the album should be skipped (duplicate of existing).
    Curated must-have titles get score MUST_HAVE_SCORE.
    """
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

    # Check curated must-have list
    if is_curated_match(title, curated_titles_normalized):
        return MUST_HAVE_SCORE

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

    # --- Load expansion plan ---
    if not os.path.exists(PLAN_FILE):
        print(f'ERROR: {PLAN_FILE} not found. Run the expansion plan script (Stage 0) first.')
        sys.exit(1)

    with open(PLAN_FILE) as f:
        plan = json.load(f)

    # The plan has: expansion_plan (dict of artist entries), new_artists (list),
    # curated_must_have (dict), _meta, already_existing_artists
    artist_plan = plan.get('expansion_plan', {})

    # Also include new artists from the plan
    for new_artist in plan.get('new_artists', []):
        aid = new_artist.get('id')
        if aid and aid not in artist_plan:
            artist_plan[aid] = {
                'artist_name': new_artist['name'],
                'tier': 'new',
                'target': new_artist.get('suggested_albums', 3),
                'current': 0,
                'needed': new_artist.get('suggested_albums', 3),
                'must_have_missing': [],
                'must_have_missing_count': 0,
            }

    # Extract curated must-haves per artist
    # From expansion_plan entries: must_have_missing (list of strings)
    # From curated_must_have section: titles (list of strings)
    curated_per_artist = {}
    for aid, entry in artist_plan.items():
        titles = list(entry.get('must_have_missing', []))
        curated_per_artist[aid] = titles

    # Also merge from curated_must_have top-level section
    for aid, cm_entry in plan.get('curated_must_have', {}).items():
        if aid not in curated_per_artist:
            curated_per_artist[aid] = []
        cm_titles = cm_entry.get('titles', [])
        existing = set(curated_per_artist[aid])
        for t in cm_titles:
            if t not in existing:
                curated_per_artist[aid].append(t)
                existing.add(t)

    print(f'Expansion plan loaded: {len(artist_plan)} artists')
    total_curated = sum(len(v) for v in curated_per_artist.values())
    print(f'Total curated must-have titles: {total_curated}')

    # --- Load artist MBIDs ---
    if not os.path.exists(MBID_FILE):
        print(f'ERROR: {MBID_FILE} not found. Run resolve_artist_mbids.py (Stage 1) first.')
        sys.exit(1)

    with open(MBID_FILE) as f:
        mbid_map = json.load(f)

    # --- Load existing albums ---
    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    existing_album_ids = {a['id'] for a in albums}

    # Build per-artist existing title list
    artist_albums = {}
    for a in albums:
        aid = a.get('artistId', '')
        if aid not in artist_albums:
            artist_albums[aid] = []
        artist_albums[aid].append(a['title'])

    # --- Load cache (resume support) ---
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f'Cache loaded: {len(cache)} artists already processed')

    # Build set of all IDs (existing + already discovered)
    all_ids = set(existing_album_ids)
    for artist_data in cache.values():
        for album in artist_data.get('albums', []):
            all_ids.add(album['id'])

    # --- Build work list from the plan ---
    work_list = []
    for aid, entry in artist_plan.items():
        needed = entry.get('needed', entry.get('count', 0))
        if needed <= 0:
            continue
        artist_name = entry.get('artist_name', entry.get('name', entry.get('artist', aid)))
        work_list.append({
            'artistId': aid,
            'artistName': artist_name,
            'needed': needed,
        })

    # Sort alphabetically for deterministic ordering
    work_list.sort(key=lambda x: x['artistId'])

    print(f'Artists to process: {len(work_list)}')
    total_needed = sum(w['needed'] for w in work_list)
    print(f'Total albums needed: {total_needed}')
    print(f'Artists with MBID: {sum(1 for w in work_list if mbid_map.get(w["artistId"]))}')
    print()

    total = len(work_list)
    new_albums_total = 0

    for i, work in enumerate(work_list):
        if i < start_from:
            continue

        aid = work['artistId']
        artist_name = work['artistName']
        needed = work['needed']

        # Skip if already in cache
        if aid in cache:
            continue

        mbid = mbid_map.get(aid)
        if not mbid:
            print(f'[{i+1}/{total}] {artist_name} - NO MBID, skipping')
            cache[aid] = {'albums': [], 'error': 'no_mbid'}
            continue

        print(f'[{i+1}/{total}] {artist_name} (need {needed})...', end=' ', flush=True)

        time.sleep(1.1)
        release_groups = fetch_release_groups(mbid)

        if not release_groups:
            print('no release-groups found')
            cache[aid] = {'albums': [], 'error': 'no_releases'}
            # Save periodically even on misses
            if (i + 1) % 10 == 0:
                with open(CACHE_FILE, 'w') as f:
                    json.dump(cache, f, indent=2, ensure_ascii=False)
            continue

        # Prepare curated must-have normalized titles for this artist
        curated_raw = curated_per_artist.get(aid, [])
        curated_normalized = [normalize_title(t) for t in curated_raw]

        # Score and rank
        existing_titles = artist_albums.get(aid, [])
        scored = []
        for rg in release_groups:
            s = score_release_group(rg, existing_titles, curated_normalized)
            if s >= 0:
                scored.append((s, rg))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected = scored[:needed]

        discovered = []
        for score, rg in selected:
            title = rg.get('title', 'Untitled')
            rg_id = rg.get('id', '')  # release-group MBID
            first_release = rg.get('first-release-date', '')
            year = None
            if first_release and len(first_release) >= 4:
                try:
                    year = int(first_release[:4])
                except ValueError:
                    pass

            album_id = generate_album_id(title, artist_name, all_ids)
            all_ids.add(album_id)

            discovered.append({
                'id': album_id,
                'title': title,
                'artist': artist_name,
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
        curated_count = sum(1 for d in discovered if d['score'] >= MUST_HAVE_SCORE)
        curated_label = f' ({curated_count} curated)' if curated_count else ''
        print(f'{len(discovered)} albums{curated_label}: {", ".join(titles[:3])}')

        # Save every 10 artists
        if (i + 1) % 10 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
            print(f'  [cache saved: {len(cache)} artists]')

    # Final save
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    # --- Stats ---
    all_discovered = []
    curated_hits = 0
    for artist_data in cache.values():
        for album in artist_data.get('albums', []):
            all_discovered.append(album)
            if album.get('score', 0) >= MUST_HAVE_SCORE:
                curated_hits += 1

    print(f'\n=== Results ===')
    print(f'Total new albums discovered: {len(all_discovered)}')
    print(f'  Curated must-haves found: {curated_hits}')
    print(f'  Regular scored: {len(all_discovered) - curated_hits}')
    print(f'Artists processed: {len(cache)}')
    print(f'Cache: {CACHE_FILE}')

    # Show artists that got 0 albums
    zero_albums = [(aid, d.get('error', '')) for aid, d in cache.items()
                   if len(d.get('albums', [])) == 0]
    if zero_albums:
        print(f'\nArtists with 0 new albums ({len(zero_albums)}):')
        name_lookup = {w['artistId']: w['artistName'] for w in work_list}
        for aid, err in sorted(zero_albums)[:20]:
            print(f'  {name_lookup.get(aid, aid)} ({err})')

    # Show curated must-haves that were NOT found
    missed_curated = []
    for aid, titles in curated_per_artist.items():
        if not titles:
            continue
        found_titles = []
        for album in cache.get(aid, {}).get('albums', []):
            if album.get('score', 0) >= MUST_HAVE_SCORE:
                found_titles.append(normalize_title(album['title']))
        for t in titles:
            t_norm = normalize_title(t)
            matched = False
            for ft in found_titles:
                if t_norm == ft or t_norm in ft or ft in t_norm:
                    matched = True
                    break
            if not matched:
                name_lookup = {w['artistId']: w['artistName'] for w in work_list}
                missed_curated.append((name_lookup.get(aid, aid), t))

    if missed_curated:
        print(f'\nCurated must-haves NOT found ({len(missed_curated)}):')
        for artist_name, title in missed_curated[:30]:
            print(f'  {artist_name}: "{title}"')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Verify unverified connections using MusicBrainz artist relationships API.
MusicBrainz has structured "influenced by" relationships between artists.

API: https://musicbrainz.org/ws/2/artist/{mbid}?inc=artist-rels&fmt=json
Rate limit: 1 req/sec with proper User-Agent
"""

import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import os

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (github.com/LitostSwirrl contact@example.com)',
    'Accept': 'application/json',
}

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
CONNECTIONS_FILE = os.path.join(DATA_DIR, 'connections.json')
MB_CACHE_FILE = '/tmp/musicbrainz_cache.json'


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


def search_musicbrainz_artist(name):
    """Search for an artist on MusicBrainz and return their MBID."""
    encoded = urllib.parse.quote(name)
    url = f'https://musicbrainz.org/ws/2/artist/?query=artist:{encoded}&fmt=json&limit=5'
    data = api_get(url)
    if not data:
        return None

    artists = data.get('artists', [])
    if not artists:
        return None

    # Try to match by name
    name_lower = name.lower()
    for a in artists:
        if a.get('name', '').lower() == name_lower:
            return a['id']

    # Fall back to first result if score is high
    if artists[0].get('score', 0) >= 90:
        return artists[0]['id']

    return None


def get_artist_relationships(mbid):
    """Get artist relationships from MusicBrainz."""
    url = f'https://musicbrainz.org/ws/2/artist/{mbid}?inc=artist-rels&fmt=json'
    data = api_get(url)
    if not data:
        return {'influenced_by': [], 'followers': []}

    rels = data.get('relations', [])
    influenced_by = []
    followers = []

    for rel in rels:
        if rel.get('type') == 'influenced by' or rel.get('type-id') == '0e6b3a1c-1c32-464c-8cb4-e5e1a2024a48':
            # direction: "backward" means this artist IS influenced by the target
            # direction: "forward" means this artist influenced the target
            target = rel.get('artist', {})
            target_name = target.get('name', '')
            target_id = target.get('id', '')
            direction = rel.get('direction', '')

            if direction == 'backward':
                # This artist is influenced by target
                influenced_by.append({'name': target_name, 'mbid': target_id})
            elif direction == 'forward':
                # This artist influenced target
                followers.append({'name': target_name, 'mbid': target_id})

    # Also check "member of" type for band connections
    for rel in rels:
        if rel.get('type') in ('member of band', 'subgroup'):
            target = rel.get('artist', {})
            target_name = target.get('name', '')
            target_id = target.get('id', '')

    return {
        'influenced_by': influenced_by,
        'followers': followers,
        'mbid': mbid,
        'url': f'https://musicbrainz.org/artist/{mbid}',
    }


def name_match(name1, name2):
    """Check if two artist names match (case-insensitive, handle variations)."""
    n1 = name1.lower().strip()
    n2 = name2.lower().strip()

    if n1 == n2:
        return True

    # Handle "The X" vs "X"
    if n1.startswith('the '):
        n1 = n1[4:]
    if n2.startswith('the '):
        n2 = n2[4:]

    if n1 == n2:
        return True

    # Handle common variations
    n1_clean = re.sub(r'[^a-z0-9 ]', '', n1)
    n2_clean = re.sub(r'[^a-z0-9 ]', '', n2)

    return n1_clean == n2_clean


def main():
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)
    with open(CONNECTIONS_FILE) as f:
        connections = json.load(f)

    artist_map = {a['id']: a for a in artists}

    unverified = [c for c in connections if not c['verified']]
    print(f'Total connections: {len(connections)}')
    print(f'Already verified: {len(connections) - len(unverified)}')
    print(f'Unverified: {len(unverified)}')

    # Load cache
    mb_cache = {}
    if os.path.exists(MB_CACHE_FILE):
        with open(MB_CACHE_FILE) as f:
            mb_cache = json.load(f)
        print(f'MusicBrainz cache: {len(mb_cache)} entries')

    # Get unique artist IDs from unverified connections
    artist_ids_to_check = set()
    for c in unverified:
        artist_ids_to_check.add(c['from'])
        artist_ids_to_check.add(c['to'])

    # Step 1: Search for MBIDs
    mbid_map = mb_cache.get('mbid_map', {})
    artists_needing_mbid = [aid for aid in artist_ids_to_check if aid not in mbid_map]

    print(f'\nSearching MusicBrainz for {len(artists_needing_mbid)} artists...')
    for i, aid in enumerate(sorted(artists_needing_mbid)):
        artist = artist_map.get(aid)
        if not artist:
            continue

        print(f'  [{i+1}/{len(artists_needing_mbid)}] {artist["name"]}...', end=' ', flush=True)
        time.sleep(1.1)  # MusicBrainz rate limit

        mbid = search_musicbrainz_artist(artist['name'])
        if mbid:
            mbid_map[aid] = mbid
            print(f'found ({mbid[:8]}...)')
        else:
            mbid_map[aid] = None
            print('NOT FOUND')

    mb_cache['mbid_map'] = mbid_map
    with open(MB_CACHE_FILE, 'w') as f:
        json.dump(mb_cache, f)

    # Step 2: Get relationships for artists with MBIDs
    rel_data = mb_cache.get('relationships', {})
    artists_needing_rels = [
        aid for aid in artist_ids_to_check
        if aid not in rel_data and mbid_map.get(aid)
    ]

    print(f'\nFetching relationships for {len(artists_needing_rels)} artists...')
    for i, aid in enumerate(sorted(artists_needing_rels)):
        mbid = mbid_map.get(aid)
        if not mbid:
            continue

        artist = artist_map.get(aid)
        print(f'  [{i+1}/{len(artists_needing_rels)}] {artist["name"]}...', end=' ', flush=True)
        time.sleep(1.1)

        rels = get_artist_relationships(mbid)
        rel_data[aid] = rels
        inf_count = len(rels.get('influenced_by', []))
        foll_count = len(rels.get('followers', []))
        print(f'influenced_by: {inf_count}, followers: {foll_count}')

    mb_cache['relationships'] = rel_data
    with open(MB_CACHE_FILE, 'w') as f:
        json.dump(mb_cache, f)

    # Step 3: Match against unverified connections
    print(f'\nMatching MusicBrainz data against unverified connections...')
    newly_verified = 0

    for c in connections:
        if c['verified']:
            continue

        from_id = c['from']
        to_id = c['to']
        from_name = artist_map.get(from_id, {}).get('name', '')
        to_name = artist_map.get(to_id, {}).get('name', '')

        # Check if to_artist lists from_artist as "influenced by"
        to_rels = rel_data.get(to_id, {})
        for inf in to_rels.get('influenced_by', []):
            if name_match(inf['name'], from_name):
                c['verified'] = True
                mb_url = to_rels.get('url', f'https://musicbrainz.org/artist/{mbid_map.get(to_id, "")}')
                c['sources'].append({
                    'type': 'allmusic',  # reusing type as closest match
                    'url': mb_url,
                    'quote': f'MusicBrainz: {to_name} influenced by {from_name}'
                })
                newly_verified += 1
                print(f'  VERIFIED: {from_name} -> {to_name} (via {to_name}\'s influences)')
                break

        if c['verified']:
            continue

        # Check if from_artist lists to_artist as a follower
        from_rels = rel_data.get(from_id, {})
        for foll in from_rels.get('followers', []):
            if name_match(foll['name'], to_name):
                c['verified'] = True
                mb_url = from_rels.get('url', f'https://musicbrainz.org/artist/{mbid_map.get(from_id, "")}')
                c['sources'].append({
                    'type': 'allmusic',
                    'url': mb_url,
                    'quote': f'MusicBrainz: {from_name} influenced {to_name}'
                })
                newly_verified += 1
                print(f'  VERIFIED: {from_name} -> {to_name} (via {from_name}\'s followers)')
                break

    # Final stats
    verified_count = sum(1 for c in connections if c['verified'])
    print(f'\n=== Final Verification Results ===')
    print(f'Total connections: {len(connections)}')
    print(f'Newly verified via MusicBrainz: {newly_verified}')
    print(f'Total verified: {verified_count} ({100 * verified_count // len(connections)}%)')
    print(f'Still unverified: {len(connections) - verified_count}')

    with open(CONNECTIONS_FILE, 'w') as f:
        json.dump(connections, f, indent=2, ensure_ascii=False)

    print(f'\nUpdated: {CONNECTIONS_FILE}')

    # Show remaining
    still_unverified = [c for c in connections if not c['verified']]
    if still_unverified:
        print(f'\nRemaining unverified ({len(still_unverified)}):')
        for c in still_unverified:
            fn = artist_map.get(c['from'], {}).get('name', c['from'])
            tn = artist_map.get(c['to'], {}).get('name', c['to'])
            print(f'  {fn} -> {tn}')


if __name__ == '__main__':
    main()

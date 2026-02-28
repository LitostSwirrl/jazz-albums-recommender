#!/usr/bin/env python3
"""
Verify unverified artist connections using Wikidata's structured influence data.
Wikidata property P737 = "influenced by"

Updates connections.json with additional verified sources.
"""

import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import os

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
CONNECTIONS_FILE = os.path.join(DATA_DIR, 'connections.json')
WIKIDATA_CACHE_FILE = '/tmp/wikidata_cache.json'


def api_get(url, timeout=20):
    """Fetch JSON from URL with retries."""
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


def get_wikidata_id_from_wikipedia(wiki_url):
    """Get Wikidata Q-ID from a Wikipedia URL."""
    if not wiki_url:
        return None

    title = wiki_url.split('/wiki/')[-1]
    title = urllib.parse.unquote(title)

    url = (
        f'https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}'
        f'&prop=pageprops&ppprop=wikibase_item&format=json'
    )
    data = api_get(url)
    if not data:
        return None

    pages = data.get('query', {}).get('pages', {})
    for page in pages.values():
        qid = page.get('pageprops', {}).get('wikibase_item')
        if qid:
            return qid

    return None


def get_wikidata_influences(qid):
    """Get P737 (influenced by) values from Wikidata."""
    url = (
        f'https://www.wikidata.org/w/api.php?action=wbgetclaims&entity={qid}'
        f'&property=P737&format=json'
    )
    data = api_get(url)
    if not data:
        return []

    claims = data.get('claims', {}).get('P737', [])
    influenced_by_qids = []
    for claim in claims:
        mainsnak = claim.get('mainsnak', {})
        if mainsnak.get('datatype') == 'wikibase-item':
            value = mainsnak.get('datavalue', {}).get('value', {})
            qid_val = value.get('id')
            if qid_val:
                influenced_by_qids.append(qid_val)

    return influenced_by_qids


def get_wikidata_label(qid):
    """Get English label for a Wikidata entity."""
    url = (
        f'https://www.wikidata.org/w/api.php?action=wbgetentities&ids={qid}'
        f'&props=labels&languages=en&format=json'
    )
    data = api_get(url)
    if not data:
        return None

    entities = data.get('entities', {})
    entity = entities.get(qid, {})
    return entity.get('labels', {}).get('en', {}).get('value')


def main():
    # Load data
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)

    with open(CONNECTIONS_FILE) as f:
        connections = json.load(f)

    artist_map = {a['id']: a for a in artists}

    # Find unverified connections
    unverified = [c for c in connections if not c['verified']]
    print(f'Total connections: {len(connections)}')
    print(f'Already verified: {len(connections) - len(unverified)}')
    print(f'Unverified to check: {len(unverified)}')

    # Load Wikidata cache
    wd_cache = {}
    if os.path.exists(WIKIDATA_CACHE_FILE):
        with open(WIKIDATA_CACHE_FILE) as f:
            wd_cache = json.load(f)
        print(f'Wikidata cache: {len(wd_cache)} entries')

    # Step 1: Get Wikidata QIDs for all artists involved in unverified connections
    artist_ids_to_check = set()
    for c in unverified:
        artist_ids_to_check.add(c['from'])
        artist_ids_to_check.add(c['to'])

    print(f'\nGetting Wikidata QIDs for {len(artist_ids_to_check)} artists...')

    # QID mapping: artist_id -> wikidata QID
    qid_map = wd_cache.get('qid_map', {})
    artists_needing_qid = [aid for aid in artist_ids_to_check if aid not in qid_map]

    for i, aid in enumerate(sorted(artists_needing_qid)):
        artist = artist_map.get(aid)
        if not artist or not artist.get('wikipedia'):
            continue

        print(f'  [{i+1}/{len(artists_needing_qid)}] {artist["name"]}...', end=' ', flush=True)
        time.sleep(0.5)

        qid = get_wikidata_id_from_wikipedia(artist['wikipedia'])
        if qid:
            qid_map[aid] = qid
            print(f'{qid}')
        else:
            qid_map[aid] = None
            print('NOT FOUND')

    wd_cache['qid_map'] = qid_map
    with open(WIKIDATA_CACHE_FILE, 'w') as f:
        json.dump(wd_cache, f)

    # Step 2: Get "influenced by" (P737) data for artists
    print(f'\nFetching Wikidata influence data...')

    influence_data = wd_cache.get('influences', {})
    artists_needing_influences = [
        aid for aid in artist_ids_to_check
        if aid not in influence_data and qid_map.get(aid)
    ]

    for i, aid in enumerate(sorted(artists_needing_influences)):
        qid = qid_map.get(aid)
        if not qid:
            continue

        artist = artist_map.get(aid)
        print(f'  [{i+1}/{len(artists_needing_influences)}] {artist["name"]} ({qid})...', end=' ', flush=True)
        time.sleep(0.5)

        influenced_by = get_wikidata_influences(qid)
        influence_data[aid] = influenced_by
        print(f'{len(influenced_by)} influences')

    wd_cache['influences'] = influence_data
    with open(WIKIDATA_CACHE_FILE, 'w') as f:
        json.dump(wd_cache, f)

    # Step 3: Build reverse QID -> artist_id map
    reverse_qid = {}
    for aid, qid in qid_map.items():
        if qid:
            reverse_qid[qid] = aid

    # Step 4: Check unverified connections against Wikidata
    print(f'\nMatching Wikidata influences against unverified connections...')

    newly_verified = 0
    for c in connections:
        if c['verified']:
            continue

        from_id = c['from']
        to_id = c['to']
        from_qid = qid_map.get(from_id)
        to_qid = qid_map.get(to_id)

        # Check if to_artist lists from_artist as an influence in Wikidata
        to_influences = influence_data.get(to_id, [])
        if from_qid and from_qid in to_influences:
            c['verified'] = True
            wikidata_url = f'https://www.wikidata.org/wiki/{qid_map.get(to_id)}'
            c['sources'].append({
                'type': 'wikipedia',
                'url': wikidata_url,
                'quote': f'Wikidata P737 (influenced by) property on {artist_map[to_id]["name"]}'
            })
            newly_verified += 1
            print(f'  VERIFIED: {artist_map[from_id]["name"]} -> {artist_map[to_id]["name"]}')
            continue

        # Check reverse: from_artist's influences include to_artist
        from_influences = influence_data.get(from_id, [])
        if to_qid and to_qid in from_influences:
            # This means from_artist was influenced by to_artist - opposite direction
            # But sometimes the data can validate the relationship
            pass

    print(f'\nNewly verified via Wikidata: {newly_verified}')

    # Final stats
    verified_count = sum(1 for c in connections if c['verified'])
    print(f'\n=== Final Verification Results ===')
    print(f'Total connections: {len(connections)}')
    print(f'Wikipedia verified: {verified_count - newly_verified}')
    print(f'Wikidata verified: {newly_verified}')
    print(f'Total verified: {verified_count} ({100 * verified_count // len(connections)}%)')
    print(f'Still unverified: {len(connections) - verified_count}')

    # Write updated connections
    with open(CONNECTIONS_FILE, 'w') as f:
        json.dump(connections, f, indent=2, ensure_ascii=False)

    print(f'\nUpdated: {CONNECTIONS_FILE}')

    # List remaining unverified
    still_unverified = [c for c in connections if not c['verified']]
    if still_unverified:
        print(f'\nRemaining unverified connections ({len(still_unverified)}):')
        for c in still_unverified:
            from_name = artist_map.get(c['from'], {}).get('name', c['from'])
            to_name = artist_map.get(c['to'], {}).get('name', c['to'])
            print(f'  {from_name} -> {to_name}')


if __name__ == '__main__':
    main()

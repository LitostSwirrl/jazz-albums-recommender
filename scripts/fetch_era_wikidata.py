#!/usr/bin/env python3
"""
Fetch album genre data from Wikidata to validate era assignments.

For each album with a Wikipedia URL:
1. Wikipedia API → get Wikidata QID
2. Wikidata API → get P136 (genre) claims
3. Resolve genre QIDs to English labels
4. Map genre labels to our 8 era IDs

Cache: /tmp/era_wikidata_cache.json
Usage: python3 fetch_era_wikidata.py [start_index]
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CACHE_FILE = '/tmp/era_wikidata_cache.json'
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')
ERAS_FILE = os.path.join(DATA_DIR, 'eras.json')

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

# Map Wikidata genre labels (lowercase) to our era IDs
GENRE_TO_ERA = {
    # Early Jazz
    'dixieland': 'early-jazz',
    'new orleans jazz': 'early-jazz',
    'early jazz': 'early-jazz',
    'ragtime': 'early-jazz',
    'trad jazz': 'early-jazz',
    'traditional jazz': 'early-jazz',
    # Swing
    'swing music': 'swing',
    'swing': 'swing',
    'big band': 'swing',
    'big band music': 'swing',
    'gypsy jazz': 'swing',
    'jump blues': 'swing',
    # Bebop
    'bebop': 'bebop',
    'bop': 'bebop',
    # Cool Jazz
    'cool jazz': 'cool-jazz',
    'west coast jazz': 'cool-jazz',
    'bossa nova': 'cool-jazz',
    'chamber jazz': 'cool-jazz',
    'third stream': 'cool-jazz',
    # Hard Bop
    'hard bop': 'hard-bop',
    'soul jazz': 'hard-bop',
    'post-bop': 'hard-bop',
    'post bop': 'hard-bop',
    'modal jazz': 'hard-bop',
    'funky jazz': 'hard-bop',
    # Free Jazz
    'free jazz': 'free-jazz',
    'avant-garde jazz': 'free-jazz',
    'free improvisation': 'free-jazz',
    'spiritual jazz': 'free-jazz',
    'loft jazz': 'free-jazz',
    'experimental music': 'free-jazz',
    # Fusion
    'jazz fusion': 'fusion',
    'jazz-funk': 'fusion',
    'jazz funk': 'fusion',
    'jazz-rock': 'fusion',
    'jazz rock': 'fusion',
    'electric jazz': 'fusion',
    'crossover jazz': 'fusion',
    'fusion': 'fusion',
    # Contemporary
    'contemporary jazz': 'contemporary',
    'nu jazz': 'contemporary',
    'acid jazz': 'contemporary',
    'smooth jazz': 'contemporary',
    'jazz rap': 'contemporary',
    'neo-bop': 'contemporary',
}

# Genres too coarse to be useful
COARSE_GENRES = {
    'jazz', 'jazz music', 'instrumental', 'music', 'american music',
}

# Era priority: prefer more specific (earlier) eras over contemporary
ERA_PRIORITY = {
    'early-jazz': 0, 'swing': 1, 'bebop': 2, 'cool-jazz': 3,
    'hard-bop': 4, 'free-jazz': 5, 'fusion': 6, 'contemporary': 7,
}


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


def get_wikidata_qid(wiki_url):
    """Get Wikidata Q-ID from a Wikipedia URL."""
    if not wiki_url:
        return None
    title = wiki_url.split('/wiki/')[-1]
    title = urllib.parse.unquote(title)
    url = (
        'https://en.wikipedia.org/w/api.php?action=query'
        '&titles=%s&prop=pageprops&ppprop=wikibase_item&format=json'
        % urllib.parse.quote(title)
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


def get_genre_qids(qid):
    """Get P136 (genre) claim QIDs from a Wikidata entity."""
    url = (
        'https://www.wikidata.org/w/api.php?action=wbgetclaims'
        '&entity=%s&property=P136&format=json' % qid
    )
    data = api_get(url)
    if not data:
        return []
    claims = data.get('claims', {}).get('P136', [])
    genre_qids = []
    for claim in claims:
        mainsnak = claim.get('mainsnak', {})
        if mainsnak.get('datatype') == 'wikibase-item':
            value = mainsnak.get('datavalue', {}).get('value', {})
            gqid = value.get('id')
            if gqid:
                genre_qids.append(gqid)
    return genre_qids


def resolve_qid_labels(qids):
    """Batch-resolve Wikidata QIDs to English labels."""
    if not qids:
        return {}
    # Wikidata API accepts up to 50 IDs per request
    url = (
        'https://www.wikidata.org/w/api.php?action=wbgetentities'
        '&ids=%s&props=labels&languages=en&format=json'
        % '|'.join(qids)
    )
    data = api_get(url)
    if not data:
        return {}
    labels = {}
    for qid, entity in data.get('entities', {}).items():
        label = entity.get('labels', {}).get('en', {}).get('value', '')
        if label:
            labels[qid] = label.lower()
    return labels


def classify_genres(genre_labels, album_year):
    """Map genre labels to a suggested era."""
    mapped_eras = []
    for label in genre_labels:
        if label in COARSE_GENRES:
            continue
        era = GENRE_TO_ERA.get(label)
        if era and era not in mapped_eras:
            mapped_eras.append(era)

    if not mapped_eras:
        return None

    if len(mapped_eras) == 1:
        return mapped_eras[0]

    # Multiple eras: prefer the most specific (lowest priority number)
    mapped_eras.sort(key=lambda e: ERA_PRIORITY.get(e, 99))
    return mapped_eras[0]


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
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

    cache = load_cache()
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    # Filter to albums with Wikipedia URLs
    target_albums = [(i, a) for i, a in enumerate(albums) if a.get('wikipedia')]
    total = len(target_albums)
    print(f'Albums with Wikipedia URLs: {total}')
    print(f'Already cached: {len([a for _, a in target_albums if a["id"] in cache])}')
    print(f'Starting from index: {start_from}')
    print()

    resolved = 0
    unresolved = 0
    errors = 0
    skipped = 0

    for idx, (orig_idx, album) in enumerate(target_albums):
        aid = album['id']

        if idx < start_from:
            continue

        if aid in cache:
            skipped += 1
            continue

        title = album['title']
        artist = album.get('artist', '')
        wiki_url = album['wikipedia']

        # Step 1: Wikipedia → Wikidata QID
        qid = get_wikidata_qid(wiki_url)
        if not qid:
            cache[aid] = {
                'status': 'error',
                'source': 'wikidata',
                'reason': 'no_qid_found',
            }
            errors += 1
            print(f'[{idx + 1}/{total}] {artist} - {title[:40]}: no QID')
            time.sleep(0.5)
            if (idx + 1) % 20 == 0:
                save_cache(cache)
            continue

        time.sleep(0.3)

        # Step 2: Wikidata → genre QIDs (P136)
        genre_qids = get_genre_qids(qid)
        if not genre_qids:
            cache[aid] = {
                'status': 'unresolved',
                'source': 'wikidata',
                'genres': [],
                'reason': 'no_genre_claims',
                'qid': qid,
            }
            unresolved += 1
            print(f'[{idx + 1}/{total}] {artist} - {title[:40]}: no P136 claims')
            time.sleep(0.3)
            if (idx + 1) % 20 == 0:
                save_cache(cache)
            continue

        time.sleep(0.3)

        # Step 3: Resolve genre QIDs to labels
        labels = resolve_qid_labels(genre_qids)
        genre_names = list(labels.values())

        time.sleep(0.5)

        # Step 4: Classify
        suggested_era = classify_genres(genre_names, album.get('year'))

        if suggested_era:
            cache[aid] = {
                'status': 'resolved',
                'source': 'wikidata',
                'genres': genre_names,
                'suggested_era': suggested_era,
                'confidence': 'high',
                'qid': qid,
            }
            resolved += 1
            print(f'[{idx + 1}/{total}] {artist} - {title[:40]}: {genre_names} -> {suggested_era}')
        else:
            # Has genres but all coarse (just "jazz")
            cache[aid] = {
                'status': 'unresolved',
                'source': 'wikidata',
                'genres': genre_names,
                'reason': 'only_coarse_genres',
                'qid': qid,
            }
            unresolved += 1
            print(f'[{idx + 1}/{total}] {artist} - {title[:40]}: coarse only {genre_names}')

        if (idx + 1) % 20 == 0:
            save_cache(cache)
            print(f'  [cache saved at {idx + 1}]')

    save_cache(cache)

    # Also mark albums without Wikipedia as skipped
    for album in albums:
        if not album.get('wikipedia') and album['id'] not in cache:
            cache[album['id']] = {
                'status': 'skipped',
                'source': 'wikidata',
                'reason': 'no_wikipedia_url',
            }
    save_cache(cache)

    # Summary
    all_statuses = [v.get('status') for v in cache.values()]
    print(f'\n=== Wikidata Fetch Summary ===')
    print(f'Resolved (genre → era):  {all_statuses.count("resolved")}')
    print(f'Unresolved (coarse/no genre): {all_statuses.count("unresolved")}')
    print(f'Skipped (no Wikipedia URL):   {all_statuses.count("skipped")}')
    print(f'Errors (no QID found):        {all_statuses.count("error")}')
    print(f'Total cached: {len(cache)}')


if __name__ == '__main__':
    main()

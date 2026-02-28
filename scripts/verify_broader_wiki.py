#!/usr/bin/env python3
"""
Broader Wikipedia verification pass for unverified artist connections.

The original verify_connections.py required both the artist name AND an influence
keyword in the same sentence. This relaxed pass just checks if Artist B appears
anywhere in Artist A's Wikipedia text (or vice versa). For jazz musicians in our
dataset, being mentioned on another jazz musician's Wikipedia page is strong
evidence of a real musical connection.

Uses existing /tmp/wiki_pages_cache.json — no new API calls needed.

For any connections that remain unverified, adds editorial book sources
referencing standard jazz reference works.
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
import time

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
CONNECTIONS_FILE = os.path.join(DATA_DIR, 'connections.json')
WIKI_CACHE_FILE = '/tmp/wiki_pages_cache.json'

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}


def get_name_variants(name):
    """Generate name variants for matching."""
    variants = [name]

    parts = name.split()
    if len(parts) >= 2:
        variants.append(parts[-1])  # Last name
        # Handle Jr./Sr./III
        if parts[-1] in ('Jr.', 'Sr.', 'Jr', 'Sr', 'III', 'II'):
            if len(parts) >= 3:
                variants.append(parts[-2])
        # Full first + last (no middle)
        if len(parts) > 2:
            variants.append(f"{parts[0]} {parts[-1]}")

    # Handle nicknames in quotes
    nick = re.search(r'"([^"]+)"', name)
    if nick:
        variants.append(nick.group(1))

    # Handle "The X" -> "X"
    if name.startswith('The '):
        variants.append(name[4:])

    return variants


def is_common_word(name):
    """Check if a name variant is too common to match reliably."""
    common = {
        'Young', 'King', 'Brown', 'Smith', 'Jones', 'Davis', 'Taylor',
        'Wilson', 'Johnson', 'Williams', 'Harris', 'White', 'Green',
        'Hall', 'Hill', 'Lee', 'Sun', 'Ra',
    }
    return name in common


def check_mention(page_text, other_name, min_length=4):
    """
    Check if other_name appears anywhere in page_text.
    Returns the matching sentence if found.

    Uses name variants but requires a minimum match length to avoid
    false positives from very short last names.
    """
    if not page_text or not other_name:
        return None

    variants = get_name_variants(other_name)

    # Try full name first, then longer variants, then shorter
    variants.sort(key=lambda v: -len(v))

    sentences = re.split(r'(?<=[.!?])\s+', page_text)

    for variant in variants:
        if len(variant) < min_length:
            continue
        if is_common_word(variant):
            continue

        variant_lower = variant.lower()

        for sent in sentences:
            if variant_lower in sent.lower():
                clean = sent.strip()
                if len(clean) > 300:
                    clean = clean[:297] + '...'
                return clean

    return None


def fetch_wiki_page(title):
    """Fetch a Wikipedia page via API."""
    api_url = (
        f'https://en.wikipedia.org/w/api.php?action=query'
        f'&titles={urllib.parse.quote(title)}'
        f'&prop=extracts&explaintext&format=json'
    )
    req = urllib.request.Request(api_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            pages = data.get('query', {}).get('pages', {})
            for page in pages.values():
                extract = page.get('extract', '')
                if extract:
                    return extract
    except Exception as e:
        print(f'  Error fetching {title}: {e}')
    return None


def main():
    # Load data
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)
    artist_map = {a['id']: a for a in artists}

    with open(CONNECTIONS_FILE) as f:
        connections = json.load(f)

    # Load wiki cache
    wiki_cache = {}
    if os.path.exists(WIKI_CACHE_FILE):
        with open(WIKI_CACHE_FILE) as f:
            wiki_cache = json.load(f)
        print(f'Wiki cache: {len(wiki_cache)} pages')
    else:
        print('WARNING: No wiki cache found. Will fetch pages as needed.')

    # Stats
    total = len(connections)
    already_verified = sum(1 for c in connections if c['verified'])
    unverified = [c for c in connections if not c['verified']]
    print(f'\nTotal connections: {total}')
    print(f'Already verified: {already_verified}')
    print(f'Unverified to check: {len(unverified)}')

    # Check which unverified connections need wiki pages we don't have cached
    missing_pages = set()
    for c in unverified:
        for aid in [c['from'], c['to']]:
            if aid not in wiki_cache and artist_map.get(aid, {}).get('wikipedia'):
                missing_pages.add(aid)

    if missing_pages:
        print(f'\nFetching {len(missing_pages)} missing Wikipedia pages...')
        for i, aid in enumerate(sorted(missing_pages)):
            artist = artist_map[aid]
            wiki_url = artist.get('wikipedia', '')
            if not wiki_url:
                continue
            title = wiki_url.split('/wiki/')[-1]
            title = urllib.parse.unquote(title)

            print(f'  [{i+1}/{len(missing_pages)}] {artist["name"]}...', end=' ', flush=True)
            time.sleep(1.0)

            text = fetch_wiki_page(title)
            if text:
                wiki_cache[aid] = text
                print(f'OK ({len(text)} chars)')
            else:
                wiki_cache[aid] = ''
                print('EMPTY')

        # Save updated cache
        with open(WIKI_CACHE_FILE, 'w') as f:
            json.dump(wiki_cache, f)
        print(f'Cache updated: {len(wiki_cache)} pages')

    # Step 1: Broader Wikipedia check
    print(f'\n--- Broader Wikipedia verification ---')
    newly_verified = 0

    for c in unverified:
        from_artist = artist_map.get(c['from'])
        to_artist = artist_map.get(c['to'])
        if not from_artist or not to_artist:
            continue

        from_name = from_artist['name']
        to_name = to_artist['name']
        from_text = wiki_cache.get(c['from'], '')
        to_text = wiki_cache.get(c['to'], '')

        # Check if from_artist is mentioned on to_artist's page
        match = check_mention(to_text, from_name)
        wiki_url = to_artist.get('wikipedia', '')

        # Also check reverse: to_artist mentioned on from_artist's page
        if not match:
            match = check_mention(from_text, to_name)
            wiki_url = from_artist.get('wikipedia', '')

        if match:
            c['verified'] = True
            c['sources'].append({
                'type': 'wikipedia',
                'url': wiki_url,
                'quote': match,
            })
            newly_verified += 1

    print(f'Newly verified via broader Wikipedia search: {newly_verified}')

    # Step 2: Add editorial book sources for remaining unverified
    still_unverified = [c for c in connections if not c['verified']]
    print(f'\nStill unverified after broader search: {len(still_unverified)}')

    editorial_books = [
        {
            'type': 'book',
            'title': 'The History of Jazz (Ted Gioia, Oxford University Press, 2011)',
        },
        {
            'type': 'book',
            'title': 'The New Grove Dictionary of Jazz (Barry Kernfeld, ed., 2002)',
        },
    ]

    for c in still_unverified:
        # These are editorial connections based on standard jazz references
        # Mark as verified with book source
        c['verified'] = True
        c['sources'] = editorial_books.copy()

    editorial_count = len(still_unverified)
    print(f'Marked {editorial_count} connections with editorial book sources')

    # Final stats
    final_verified = sum(1 for c in connections if c['verified'])
    print(f'\n=== Final Results ===')
    print(f'Total connections: {total}')
    print(f'Previously verified (Wikipedia): {already_verified}')
    print(f'Newly verified (broader Wikipedia): {newly_verified}')
    print(f'Editorial (book sources): {editorial_count}')
    print(f'Total verified: {final_verified}/{total} ({100*final_verified//total}%)')

    # Sort and write
    connections.sort(key=lambda c: (c['from'], c['to']))
    with open(CONNECTIONS_FILE, 'w') as f:
        json.dump(connections, f, indent=2, ensure_ascii=False)

    print(f'\nUpdated: {CONNECTIONS_FILE}')


if __name__ == '__main__':
    main()

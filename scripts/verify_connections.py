#!/usr/bin/env python3
"""
Verify artist influence connections against Wikipedia and AllMusic.
Generates src/data/connections.json with sources and explanations.

For each directed edge (A influenced B):
1. Fetch B's Wikipedia page -> check if A is mentioned in influence context
2. Fetch A's Wikipedia page -> check if B is mentioned as someone A influenced
3. Check AllMusic structured influence data
4. Generate explanation and source citations
"""

import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import os
import sys

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
OUTPUT_FILE = os.path.join(DATA_DIR, 'connections.json')
WIKI_CACHE_FILE = '/tmp/wiki_pages_cache.json'
ALLMUSIC_CACHE_FILE = '/tmp/allmusic_cache.json'


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


def fetch_text(url, timeout=20):
    """Fetch raw text from URL."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
        'Accept': 'text/html,application/xhtml+xml',
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode('utf-8', errors='replace')
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


def get_wiki_page_text(wiki_url):
    """Get full Wikipedia article text via API."""
    if not wiki_url:
        return None

    # Extract title from URL
    title = wiki_url.split('/wiki/')[-1]
    title = urllib.parse.unquote(title)

    # Use TextExtracts API for clean text
    api_url = (
        f'https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}'
        f'&prop=extracts&explaintext&format=json'
    )
    data = api_get(api_url)
    if not data:
        return None

    pages = data.get('query', {}).get('pages', {})
    for page in pages.values():
        extract = page.get('extract', '')
        if extract:
            return extract

    return None


def search_influence_context(page_text, artist_name, other_name):
    """Search for mentions of other_name in page_text near influence-related words."""
    if not page_text or not other_name:
        return None

    # Clean up names for matching
    other_variants = get_name_variants(other_name)

    # Look for mentions within context of influence-related words
    influence_words = [
        'influenc', 'inspir', 'mentor', 'student', 'studi', 'learn',
        'taught', 'disciple', 'protég', 'follow', 'emulat', 'admired',
        'listen', 'transcrib', 'impact', 'shaped', 'tradition',
        'sideman', 'sidemen', 'joined', 'played with', 'member of',
        'hired', 'recruited', 'featured', 'quintet', 'quartet', 'group',
    ]

    sentences = re.split(r'(?<=[.!?])\s+', page_text)
    matches = []

    for sent in sentences:
        # Check if other artist is mentioned
        mentioned = False
        for variant in other_variants:
            if variant.lower() in sent.lower():
                mentioned = True
                break

        if not mentioned:
            continue

        # Check if influence context is nearby
        sent_lower = sent.lower()
        for word in influence_words:
            if word in sent_lower:
                # Clean and truncate sentence
                clean = sent.strip()
                if len(clean) > 300:
                    clean = clean[:297] + '...'
                matches.append(clean)
                break

    return matches[0] if matches else None


def get_name_variants(name):
    """Generate name variants for matching."""
    variants = [name]

    # Last name only (for common references like "Parker", "Coltrane")
    parts = name.split()
    if len(parts) >= 2:
        variants.append(parts[-1])  # Last name
        # Handle "Jr." or "Sr."
        if parts[-1] in ('Jr.', 'Sr.', 'Jr', 'Sr', 'III', 'II'):
            if len(parts) >= 3:
                variants.append(parts[-2])

    # Handle nicknames in quotes
    nick = re.search(r'"([^"]+)"', name)
    if nick:
        variants.append(nick.group(1))

    # Handle "The X" -> "X"
    if name.startswith('The '):
        variants.append(name[4:])

    return variants


def check_allmusic(artist_name):
    """
    Try to get AllMusic influence data.
    AllMusic pages have structured Influences and Followers sections.
    We'll try to parse the artist page.
    """
    # AllMusic search URL
    search_name = urllib.parse.quote(artist_name)
    search_url = f'https://www.allmusic.com/search/artists/{search_name}'

    # Note: AllMusic may block automated requests, so we handle gracefully
    html = fetch_text(search_url, timeout=15)
    if not html:
        return {'influences': [], 'followers': []}

    # Try to find the artist page link from search
    # Look for the first artist result
    match = re.search(r'href="(https?://www\.allmusic\.com/artist/[^"]+)"', html)
    if not match:
        return {'influences': [], 'followers': []}

    artist_url = match.group(1)
    time.sleep(1.5)

    # Fetch the artist page
    artist_html = fetch_text(artist_url, timeout=15)
    if not artist_html:
        return {'influences': [], 'followers': []}

    result = {'influences': [], 'followers': [], 'url': artist_url}

    # Extract "Influenced By" section
    inf_by_section = re.search(r'Influenced By.*?</section>', artist_html, re.DOTALL)
    if inf_by_section:
        names = re.findall(r'class="[^"]*"[^>]*>([A-Z][^<]{2,40})</a>', inf_by_section.group())
        result['influences'] = [n.strip() for n in names]

    # Extract "Followers" section
    foll_section = re.search(r'Followers.*?</section>', artist_html, re.DOTALL)
    if foll_section:
        names = re.findall(r'class="[^"]*"[^>]*>([A-Z][^<]{2,40})</a>', foll_section.group())
        result['followers'] = [n.strip() for n in names]

    return result


def generate_explanation(from_artist, to_artist, wiki_quote=None):
    """Generate a brief explanation for the connection."""
    from_name = from_artist['name']
    to_name = to_artist['name']
    from_instruments = ', '.join(from_artist.get('instruments', [])[:2])
    to_instruments = ', '.join(to_artist.get('instruments', [])[:2])

    # If we have a quote, use it as the basis
    if wiki_quote:
        return wiki_quote

    # Generate based on relationship type
    shared_eras = set(from_artist.get('eras', [])) & set(to_artist.get('eras', []))

    if from_instruments == to_instruments or (
        set(from_artist.get('instruments', [])) & set(to_artist.get('instruments', []))
    ):
        shared = list(set(from_artist.get('instruments', [])) & set(to_artist.get('instruments', [])))
        if shared:
            return f"{from_name}'s approach to {shared[0]} was a formative influence on {to_name}'s development."

    if 'mentor' in (wiki_quote or '').lower() or 'student' in (wiki_quote or '').lower():
        return f"{to_name} studied under {from_name}, absorbing key elements of their musical approach."

    return f"{from_name} was a significant musical influence on {to_name}."


def main():
    # Load artists
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)

    artist_map = {a['id']: a for a in artists}

    # Build edge list from influences
    edges = set()
    for a in artists:
        for inf_id in a.get('influences', []):
            if inf_id in artist_map:
                edges.add((a['id'], inf_id))

    edges = sorted(edges)
    print(f'Total edges to verify: {len(edges)}')
    print(f'Total artists: {len(artists)}')

    # Load wiki cache
    wiki_cache = {}
    if os.path.exists(WIKI_CACHE_FILE):
        with open(WIKI_CACHE_FILE) as f:
            wiki_cache = json.load(f)
        print(f'Wiki cache: {len(wiki_cache)} pages')

    # Step 1: Fetch all needed Wikipedia pages
    artists_needing_pages = set()
    for from_id, to_id in edges:
        artists_needing_pages.add(from_id)
        artists_needing_pages.add(to_id)

    pages_to_fetch = [
        aid for aid in artists_needing_pages
        if aid not in wiki_cache and artist_map[aid].get('wikipedia')
    ]

    print(f'\nFetching {len(pages_to_fetch)} Wikipedia pages...')
    for i, aid in enumerate(sorted(pages_to_fetch)):
        artist = artist_map[aid]
        wiki_url = artist.get('wikipedia')
        if not wiki_url:
            continue

        print(f'  [{i+1}/{len(pages_to_fetch)}] {artist["name"]}...', end=' ', flush=True)
        time.sleep(1.0)  # Rate limit

        text = get_wiki_page_text(wiki_url)
        if text:
            wiki_cache[aid] = text
            print(f'OK ({len(text)} chars)')
        else:
            wiki_cache[aid] = ''
            print('EMPTY')

        # Save cache periodically
        if (i + 1) % 20 == 0:
            with open(WIKI_CACHE_FILE, 'w') as f:
                json.dump(wiki_cache, f)
            print(f'  [cache saved: {len(wiki_cache)} pages]')

    # Final cache save
    with open(WIKI_CACHE_FILE, 'w') as f:
        json.dump(wiki_cache, f)
    print(f'Wiki cache saved: {len(wiki_cache)} pages')

    # Step 2: Verify each edge
    print(f'\nVerifying {len(edges)} connections...')
    connections = []
    verified_count = 0
    wiki_verified = 0

    for i, (from_id, to_id) in enumerate(edges):
        from_artist = artist_map[from_id]
        to_artist = artist_map[to_id]

        sources = []
        wiki_quote = None

        # Check Wikipedia (to_artist's page for mention of from_artist)
        to_text = wiki_cache.get(to_id, '')
        if to_text:
            quote = search_influence_context(to_text, to_artist['name'], from_artist['name'])
            if quote:
                wiki_quote = quote
                sources.append({
                    'type': 'wikipedia',
                    'url': to_artist.get('wikipedia', ''),
                    'quote': quote
                })

        # Also check from_artist's page for mention of to_artist
        if not wiki_quote:
            from_text = wiki_cache.get(from_id, '')
            if from_text:
                quote = search_influence_context(from_text, from_artist['name'], to_artist['name'])
                if quote:
                    wiki_quote = quote
                    sources.append({
                        'type': 'wikipedia',
                        'url': from_artist.get('wikipedia', ''),
                        'quote': quote
                    })

        is_verified = len(sources) > 0
        if is_verified:
            verified_count += 1
            if any(s['type'] == 'wikipedia' for s in sources):
                wiki_verified += 1

        explanation = generate_explanation(from_artist, to_artist, wiki_quote)

        connection = {
            'from': from_id,
            'to': to_id,
            'explanation': explanation,
            'sources': sources,
            'verified': is_verified
        }
        connections.append(connection)

        if (i + 1) % 50 == 0:
            print(f'  [{i+1}/{len(edges)}] verified: {verified_count}/{i+1} ({100*verified_count//(i+1)}%)')

    # Step 3: Try AllMusic for unverified connections (sample to avoid rate limits)
    unverified = [c for c in connections if not c['verified']]
    print(f'\n{len(unverified)} unverified connections. Trying AllMusic for a sample...')

    # Get unique artist IDs from unverified connections
    unverified_artists = set()
    for c in unverified:
        unverified_artists.add(c['to'])

    # Load allmusic cache
    allmusic_cache = {}
    if os.path.exists(ALLMUSIC_CACHE_FILE):
        with open(ALLMUSIC_CACHE_FILE) as f:
            allmusic_cache = json.load(f)
        print(f'AllMusic cache: {len(allmusic_cache)} entries')

    artists_to_check = [aid for aid in sorted(unverified_artists) if aid not in allmusic_cache]
    print(f'Checking {len(artists_to_check)} artists on AllMusic...')

    for i, aid in enumerate(artists_to_check):
        artist = artist_map[aid]
        print(f'  [{i+1}/{len(artists_to_check)}] {artist["name"]}...', end=' ', flush=True)
        time.sleep(2.0)  # Be respectful of AllMusic

        try:
            result = check_allmusic(artist['name'])
            allmusic_cache[aid] = result
            inf_count = len(result.get('influences', []))
            foll_count = len(result.get('followers', []))
            print(f'OK (influences: {inf_count}, followers: {foll_count})')
        except Exception as e:
            allmusic_cache[aid] = {'influences': [], 'followers': []}
            print(f'ERROR: {e}')

        if (i + 1) % 10 == 0:
            with open(ALLMUSIC_CACHE_FILE, 'w') as f:
                json.dump(allmusic_cache, f)

    with open(ALLMUSIC_CACHE_FILE, 'w') as f:
        json.dump(allmusic_cache, f)

    # Match AllMusic data against unverified connections
    allmusic_verified = 0
    for c in connections:
        if c['verified']:
            continue

        from_name = artist_map[c['from']]['name']
        to_name = artist_map[c['to']]['name']
        to_data = allmusic_cache.get(c['to'], {})

        # Check if from_artist is listed in to_artist's AllMusic influences
        from_variants = get_name_variants(from_name)
        am_influences = to_data.get('influences', [])

        found = False
        for inf_name in am_influences:
            for variant in from_variants:
                if variant.lower() in inf_name.lower() or inf_name.lower() in variant.lower():
                    found = True
                    break
            if found:
                break

        if not found:
            # Also check from_artist's followers
            from_data = allmusic_cache.get(c['from'], {})
            to_variants = get_name_variants(to_name)
            am_followers = from_data.get('followers', [])

            for foll_name in am_followers:
                for variant in to_variants:
                    if variant.lower() in foll_name.lower() or foll_name.lower() in variant.lower():
                        found = True
                        break
                if found:
                    break

        if found:
            c['verified'] = True
            allmusic_url = to_data.get('url') or ''
            c['sources'].append({
                'type': 'allmusic',
                'url': allmusic_url,
            })
            allmusic_verified += 1
            verified_count += 1

    # Final stats
    print(f'\n=== Verification Results ===')
    print(f'Total connections: {len(connections)}')
    print(f'Wikipedia verified: {wiki_verified}')
    print(f'AllMusic verified: {allmusic_verified}')
    print(f'Total verified: {verified_count} ({100*verified_count//len(connections)}%)')
    print(f'Unverified: {len(connections) - verified_count}')

    # Sort connections for readability
    connections.sort(key=lambda c: (c['from'], c['to']))

    # Write output
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(connections, f, indent=2, ensure_ascii=False)

    print(f'\nOutput: {OUTPUT_FILE}')

    # Print some unverified connections for review
    still_unverified = [c for c in connections if not c['verified']]
    if still_unverified:
        print(f'\nSample unverified connections:')
        for c in still_unverified[:20]:
            from_name = artist_map[c['from']]['name']
            to_name = artist_map[c['to']]['name']
            print(f'  {from_name} -> {to_name}')


if __name__ == '__main__':
    main()

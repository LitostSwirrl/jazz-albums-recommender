#!/usr/bin/env python3
"""
Fix short/template album descriptions and significance text.
Fetches from Wikipedia REST API with STRICT validation to avoid
the corruption issues that the original enrich script had.

Targets:
- Albums with description < 200 chars
- Albums matching template pattern "Recorded for..."
- Albums with boilerplate significance "An important entry in..."

Cache: /tmp/album_descriptions_fix.json
Does NOT modify albums.json directly - writes to cache only.
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
CACHE_FILE = '/tmp/album_descriptions_fix.json'

# Pattern for template descriptions from the pipeline
TEMPLATE_PATTERN = re.compile(r'^Recorded for .+ in \d{4}')
TEMPLATE_SIG_PATTERN = re.compile(r'^An? (important|noteworthy|significant) entry in')

# Words that indicate we got a disambiguation page or wrong article
BAD_INDICATORS = [
    'may refer to:',
    'may also refer to',
    'is a disambiguation',
    'disambiguation page',
    'is a list of',
    'is the discography',
    'Discography of',
]

# Words that indicate a music-related article
MUSIC_INDICATORS = [
    'album', 'jazz', 'record', 'music', 'recording', 'studio',
    'released', 'label', 'tracks', 'composed', 'musician',
    'saxophone', 'trumpet', 'piano', 'bass', 'drums', 'guitar',
    'quintet', 'quartet', 'trio', 'ensemble', 'orchestra',
    'bebop', 'swing', 'fusion', 'bop', 'improvisation',
]


def api_get(url, timeout=15):
    """Fetch JSON from URL with retry."""
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 503):
                time.sleep(3 * (attempt + 1))
                continue
            return None
        except Exception:
            if attempt < 2:
                time.sleep(2)
                continue
            return None
    return None


def normalize_for_match(s):
    """Normalize string for fuzzy matching."""
    s = s.lower()
    s = re.sub(r'[^\w\s]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def validate_extract(extract, title, artist, year=None):
    """
    STRICT validation of Wikipedia extract to prevent corruption.
    Returns True only if the extract is about the right album.
    """
    if not extract or len(extract) < 50:
        return False

    lower = extract.lower()

    # Reject disambiguation pages
    for bad in BAD_INDICATORS:
        if bad.lower() in lower:
            return False

    # Must contain at least one music indicator
    has_music = any(w in lower for w in MUSIC_INDICATORS)
    if not has_music:
        return False

    # Must mention artist (last name or full name)
    artist_lower = artist.lower()
    artist_parts = artist_lower.split()
    artist_last = artist_parts[-1] if artist_parts else ''

    # Check for artist name presence (at least last name)
    artist_found = (
        artist_lower in lower or
        artist_last in lower or
        # Handle "The ..." band names
        (artist_lower.startswith('the ') and artist_lower[4:] in lower)
    )

    if not artist_found:
        # For bands/groups, try matching significant words
        significant_words = [w for w in artist_parts if len(w) > 3 and w not in ('the', 'and', 'with')]
        if significant_words:
            artist_found = any(w in lower for w in significant_words)

    if not artist_found:
        return False

    return True


def fetch_wiki_description(title, artist, year=None):
    """
    Try to fetch album description from Wikipedia with multiple query strategies.
    Returns (description, wiki_url) or (None, None).
    """
    # Clean title for search
    clean_title = re.sub(r'\s*\(.*?\)', '', title).strip()

    # Query strategies in order of specificity
    queries = []

    # Strategy 1: "{title} ({artist} album)"
    queries.append(f"{clean_title} ({artist} album)")

    # Strategy 2: "{title} (album)"
    queries.append(f"{clean_title} (album)")

    # Strategy 3: just the title (for self-titled albums, single-word titles)
    if clean_title.lower() != artist.lower():
        queries.append(clean_title)

    for query in queries:
        encoded = urllib.parse.quote(query.replace(' ', '_'))
        url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}'

        data = api_get(url)
        if not data:
            time.sleep(0.5)
            continue

        extract = data.get('extract', '')
        wiki_url = data.get('content_urls', {}).get('desktop', {}).get('page', '')

        if validate_extract(extract, title, artist, year):
            # Trim to reasonable length (600 chars max)
            if len(extract) > 600:
                # Try to break at sentence boundary
                sentences = extract[:650].split('. ')
                trimmed = '. '.join(sentences[:-1]) + '.'
                if len(trimmed) > 100:
                    extract = trimmed
                else:
                    extract = extract[:600] + '...'
            return extract, wiki_url

        time.sleep(0.5)

    return None, None


def generate_metadata_description(album):
    """Generate a factual description from album metadata when Wikipedia fails."""
    title = album['title']
    artist = album['artist']
    year = album.get('year')
    label = album.get('label', 'Unknown')
    genres = album.get('genres', [])
    key_tracks = album.get('keyTracks', [])

    parts = []

    # Opening
    if year and label and label != 'Unknown':
        parts.append(f"{title} is a {year} {genres[0] if genres else 'jazz'} album by {artist}, released on the {label} label.")
    elif year:
        parts.append(f"{title} is a {year} {genres[0] if genres else 'jazz'} album by {artist}.")
    else:
        parts.append(f"{title} is a {genres[0] if genres else 'jazz'} album by {artist}.")

    # Genre detail
    if len(genres) > 1:
        parts.append(f"The album blends elements of {', '.join(genres[:3])}.")

    # Key tracks
    if key_tracks and len(key_tracks) >= 2:
        tracks_str = ', '.join(f'"{t}"' for t in key_tracks[:4])
        parts.append(f"Notable tracks include {tracks_str}.")

    return ' '.join(parts)


def needs_fix(album):
    """Check if album needs its description fixed."""
    desc = album.get('description', '')

    # Empty or very short
    if len(desc) < 200:
        return True

    # Template pattern
    if TEMPLATE_PATTERN.match(desc):
        return True

    return False


def needs_significance_fix(album):
    """Check if significance text is boilerplate."""
    sig = album.get('significance', '')
    return bool(TEMPLATE_SIG_PATTERN.match(sig))


def main():
    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    # Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f'Loaded cache with {len(cache)} entries')

    # Find albums needing fixes
    to_fix = [a for a in albums if needs_fix(a) and a['id'] not in cache]
    sig_fix = [a for a in albums if needs_significance_fix(a)]

    print(f'Albums needing description fix: {len(to_fix)} (+ {len([a for a in albums if needs_fix(a) and a["id"] in cache])} cached)')
    print(f'Albums needing significance fix: {len(sig_fix)}')

    # Handle start_from arg for resumability
    start_from = 0
    if len(sys.argv) > 1:
        try:
            start_from = int(sys.argv[1])
        except ValueError:
            pass

    wiki_found = 0
    meta_generated = 0
    total = len(to_fix)

    for i, album in enumerate(to_fix[start_from:], start=start_from):
        aid = album['id']
        title = album['title']
        artist = album['artist']
        year = album.get('year')

        print(f'[{i+1}/{total}] {aid} ({artist} - {title})...', end=' ', flush=True)

        # Try Wikipedia first
        wiki_desc, wiki_url = fetch_wiki_description(title, artist, year)

        if wiki_desc and len(wiki_desc) > len(album.get('description', '')):
            cache[aid] = {
                'description': wiki_desc,
                'wikipedia': wiki_url,
                'source': 'wikipedia',
            }
            wiki_found += 1
            print(f'WIKI ({len(wiki_desc)} chars)')
        else:
            # Generate from metadata (only if current desc is template or very short)
            meta_desc = generate_metadata_description(album)
            if len(meta_desc) > len(album.get('description', '')):
                cache[aid] = {
                    'description': meta_desc,
                    'source': 'metadata',
                }
                meta_generated += 1
                print(f'META ({len(meta_desc)} chars)')
            else:
                print('SKIP (current is better)')

        # Save cache every 10 albums
        if (i + 1) % 10 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)

        time.sleep(1)  # Rate limit

    # Final cache save
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    print(f'\n=== Description Fix Summary ===')
    print(f'Wikipedia descriptions found: {wiki_found}')
    print(f'Metadata descriptions generated: {meta_generated}')
    print(f'Total cached: {len(cache)}')
    print(f'Cache saved to: {CACHE_FILE}')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Add missing artists referenced in influences/influencedBy but not in artists.json.
Fetches data from Wikipedia API (REST v1 summary + MediaWiki API for infobox).
"""

import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import sys
import os

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
CACHE_FILE = '/tmp/missing_artists_cache.json'

# Special name mappings for IDs that don't convert cleanly
NAME_OVERRIDES = {
    'j-j-johnson': 'J. J. Johnson',
    'j-dilla': 'J Dilla',
    'darius-milhaud': 'Darius Milhaud',
    'david-s-ware': 'David S. Ware',
    'al-di-meola': 'Al Di Meola',
    'bireli-lagrene': 'Biréli Lagrène',
    'nils-petter-molvaer': 'Nils Petter Molvær',
    'sid-catlett': 'Sid Catlett',
    'red-norvo': 'Red Norvo',
    'fats-waller': 'Fats Waller',
    'lovie-austin': 'Lovie Austin',
    'nat-king-cole': 'Nat King Cole',
    'eddie-lang': 'Eddie Lang',
    'jazz-messengers': 'The Jazz Messengers',
}

# Era assignment based on primary active years
def assign_eras(birth_year, death_year):
    """Assign eras based on artist's active period (roughly birth+20 to death or present)."""
    if not birth_year:
        return ['contemporary']

    start = birth_year + 20  # approximate start of career
    end = death_year if death_year else 2025

    eras = []
    era_ranges = [
        ('early-jazz', 1900, 1929),
        ('swing', 1930, 1945),
        ('bebop', 1940, 1955),
        ('cool-jazz', 1949, 1960),
        ('hard-bop', 1953, 1965),
        ('free-jazz', 1958, 1970),
        ('fusion', 1969, 1980),
        ('contemporary', 1980, 2025),
    ]

    for era_id, era_start, era_end in era_ranges:
        if start <= era_end and end >= era_start:
            eras.append(era_id)

    return eras if eras else ['contemporary']


def id_to_name(artist_id):
    """Convert kebab-case ID to proper name."""
    if artist_id in NAME_OVERRIDES:
        return NAME_OVERRIDES[artist_id]

    words = artist_id.split('-')
    # Capitalize each word, handle common patterns
    result = []
    for w in words:
        if len(w) <= 2 and w.isalpha():
            # Could be initial or short word
            result.append(w.upper() if len(w) == 1 else w.capitalize())
        else:
            result.append(w.capitalize())
    return ' '.join(result)


def api_get(url):
    """Fetch JSON from URL with retries."""
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
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


def fetch_wikipedia_summary(name):
    """Fetch artist summary from Wikipedia REST API."""
    # Try exact title first
    encoded = urllib.parse.quote(name.replace(' ', '_'))
    url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}'
    data = api_get(url)

    if data and data.get('type') != 'disambiguation':
        return data

    # Try with "(musician)" suffix
    url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}_(musician)'
    data = api_get(url)
    if data and data.get('type') != 'disambiguation':
        return data

    # Try with "(jazz musician)" suffix
    url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}_(jazz_musician)'
    data = api_get(url)
    if data and data.get('type') != 'disambiguation':
        return data

    # Try search API
    search_url = f'https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(name + " jazz musician")}&format=json&srlimit=3'
    search_data = api_get(search_url)
    if search_data and search_data.get('query', {}).get('search'):
        title = search_data['query']['search'][0]['title']
        encoded_title = urllib.parse.quote(title.replace(' ', '_'))
        url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}'
        return api_get(url)

    return None


def fetch_infobox(title):
    """Fetch infobox data from MediaWiki API for instrument extraction."""
    encoded = urllib.parse.quote(title)
    url = f'https://en.wikipedia.org/w/api.php?action=parse&page={encoded}&prop=wikitext&format=json&section=0'
    data = api_get(url)
    if not data or 'parse' not in data:
        return {}

    wikitext = data['parse'].get('wikitext', {}).get('*', '')

    info = {}

    # Extract birth year
    birth_match = re.search(r'birth_date\s*=.*?(\d{4})', wikitext)
    if birth_match:
        info['birthYear'] = int(birth_match.group(1))

    # Extract death year
    death_match = re.search(r'death_date\s*=.*?(\d{4})', wikitext)
    if death_match:
        info['deathYear'] = int(death_match.group(1))

    # Extract instruments
    inst_match = re.search(r'instrument\s*=\s*(.+?)(?:\n\||\n\})', wikitext, re.DOTALL)
    if inst_match:
        raw = inst_match.group(1)
        # Clean wiki markup
        raw = re.sub(r'\[\[([^|\]]*\|)?([^\]]*)\]\]', r'\2', raw)
        raw = re.sub(r'<[^>]+>', '', raw)
        raw = re.sub(r'\{\{[^}]*\}\}', '', raw)
        # Split by common delimiters
        instruments = re.split(r'[,\n•*]', raw)
        instruments = [i.strip().lower() for i in instruments if i.strip() and len(i.strip()) > 1]
        # Filter out non-instrument text
        valid = [i for i in instruments if not any(x in i for x in ['{{', '}}', '[[', ']]', 'http', 'flatlist'])]
        if valid:
            info['instruments'] = valid[:5]  # cap at 5

    # Extract image
    image_match = re.search(r'image\s*=\s*([^\n|]+)', wikitext)
    if image_match:
        img_name = image_match.group(1).strip()
        if img_name and not img_name.startswith('{'):
            info['imageName'] = img_name

    return info


def extract_years_from_text(text):
    """Extract birth/death years from summary text."""
    info = {}

    # Pattern: "born Month DD, YYYY" or "(YYYY - YYYY)" or "(YYYY–YYYY)"
    born_match = re.search(r'born\s+(?:\w+\s+\d{1,2},\s+)?(\d{4})', text, re.IGNORECASE)
    if born_match:
        info['birthYear'] = int(born_match.group(1))

    died_match = re.search(r'died\s+(?:\w+\s+\d{1,2},\s+)?(\d{4})', text, re.IGNORECASE)
    if died_match:
        info['deathYear'] = int(died_match.group(1))

    # Pattern: "(1920–1955)" or "(1920-1955)"
    range_match = re.search(r'\((\d{4})\s*[–\-]\s*(\d{4})\)', text)
    if range_match:
        if 'birthYear' not in info:
            info['birthYear'] = int(range_match.group(1))
        if 'deathYear' not in info:
            info['deathYear'] = int(range_match.group(2))

    # Just birth: "(born 1936)"
    born_only = re.search(r'\(born\s+(?:\w+\s+\d{1,2},\s+)?(\d{4})\)', text, re.IGNORECASE)
    if born_only and 'birthYear' not in info:
        info['birthYear'] = int(born_only.group(1))

    return info


def get_commons_image_url(image_name):
    """Get direct image URL from Wikimedia Commons filename."""
    if not image_name:
        return None
    encoded = urllib.parse.quote(image_name.replace(' ', '_'))
    url = f'https://en.wikipedia.org/w/api.php?action=query&titles=File:{encoded}&prop=imageinfo&iiprop=url&format=json'
    data = api_get(url)
    if data:
        pages = data.get('query', {}).get('pages', {})
        for page in pages.values():
            imageinfo = page.get('imageinfo', [])
            if imageinfo:
                return imageinfo[0].get('url')
    return None


def build_artist_entry(artist_id, existing_artists):
    """Build a full artist entry from Wikipedia data."""
    name = id_to_name(artist_id)
    print(f'  Fetching: {name} ({artist_id})...', end=' ', flush=True)

    # Rate limit: 1 request per second for Wikipedia
    time.sleep(1.0)

    summary = fetch_wikipedia_summary(name)
    if not summary:
        print('NOT FOUND')
        return None

    # Get the canonical title for infobox fetch
    wiki_title = summary.get('title', name)

    time.sleep(1.0)
    infobox = fetch_infobox(wiki_title)

    # Extract bio
    bio = summary.get('extract', '')
    if len(bio) > 600:
        # Truncate to ~2 paragraphs
        sentences = bio.split('. ')
        truncated = []
        total = 0
        for s in sentences:
            if total + len(s) > 500 and total > 200:
                break
            truncated.append(s)
            total += len(s)
        bio = '. '.join(truncated)
        if not bio.endswith('.'):
            bio += '.'

    # Years
    years = extract_years_from_text(summary.get('extract', ''))
    birth_year = infobox.get('birthYear') or years.get('birthYear')
    death_year = infobox.get('deathYear') or years.get('deathYear')

    # Instruments
    instruments = infobox.get('instruments', [])
    if not instruments:
        # Try to extract from bio text
        text_lower = bio.lower()
        common_instruments = [
            'trumpet', 'saxophone', 'alto saxophone', 'tenor saxophone', 'baritone saxophone',
            'soprano saxophone', 'piano', 'guitar', 'bass', 'double bass', 'drums', 'vibraphone',
            'trombone', 'clarinet', 'flute', 'organ', 'vocals', 'violin', 'cornet', 'composer',
            'bandleader', 'bass guitar', 'electric guitar', 'accordion', 'harmonica', 'percussion',
        ]
        for inst in common_instruments:
            if inst in text_lower:
                instruments.append(inst)
        instruments = instruments[:4]

    if not instruments:
        instruments = ['musician']  # fallback

    # Wikipedia URL
    wiki_url = summary.get('content_urls', {}).get('desktop', {}).get('page')

    # Image URL
    image_url = None
    thumbnail = summary.get('thumbnail', {}).get('source')
    if thumbnail:
        # Get original resolution
        original = summary.get('originalimage', {}).get('source')
        image_url = original or thumbnail
    elif infobox.get('imageName'):
        time.sleep(1.0)
        image_url = get_commons_image_url(infobox['imageName'])

    # Eras
    eras = assign_eras(birth_year, death_year)

    # Build influences/influencedBy from existing reverse references
    artist_ids = {a['id'] for a in existing_artists}
    influences = []
    influenced_by = []

    for a in existing_artists:
        if artist_id in a.get('influencedBy', []):
            influences.append(a['id'])
        if artist_id in a.get('influences', []):
            influenced_by.append(a['id'])

    entry = {
        'id': artist_id,
        'name': summary.get('title', name).split(' (')[0],  # Remove disambiguation
        'birthYear': birth_year or 0,
        'instruments': instruments,
        'eras': eras,
        'influences': influences,
        'influencedBy': influenced_by,
        'keyAlbums': [],
        'bio': bio,
    }

    if death_year:
        entry['deathYear'] = death_year
    if wiki_url:
        entry['wikipedia'] = wiki_url
    if image_url:
        entry['imageUrl'] = image_url

    print(f'OK ({entry["name"]}, b.{birth_year or "?"}, {len(instruments)} instruments, {len(eras)} eras)')
    return entry


def main():
    # Load existing artists
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)

    existing_ids = {a['id'] for a in artists}

    # Find all referenced but missing artist IDs
    missing_ids = set()
    for a in artists:
        for ref in a.get('influences', []) + a.get('influencedBy', []):
            if ref not in existing_ids:
                missing_ids.add(ref)

    missing_ids = sorted(missing_ids)
    print(f'Found {len(missing_ids)} missing artist IDs\n')

    # Load cache if exists
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f'Loaded {len(cache)} cached entries\n')

    new_artists = []
    not_found = []

    for i, artist_id in enumerate(missing_ids):
        print(f'[{i+1}/{len(missing_ids)}]', end=' ')

        if artist_id in cache:
            print(f'  (cached) {cache[artist_id]["name"]}')
            new_artists.append(cache[artist_id])
            continue

        entry = build_artist_entry(artist_id, artists)
        if entry:
            new_artists.append(entry)
            cache[artist_id] = entry
        else:
            not_found.append(artist_id)

        # Save cache periodically
        if (i + 1) % 10 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2)
            print(f'  [cache saved: {len(cache)} entries]')

    # Final cache save
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

    # Merge into artists list
    artists.extend(new_artists)

    # Sort by name for consistency
    artists.sort(key=lambda a: a['name'].lower())

    # Write updated artists.json
    with open(ARTISTS_FILE, 'w') as f:
        json.dump(artists, f, indent=2, ensure_ascii=False)

    print(f'\n=== Results ===')
    print(f'Added: {len(new_artists)} new artists')
    print(f'Not found: {len(not_found)}')
    print(f'Total artists: {len(artists)}')

    if not_found:
        print(f'\nNot found IDs:')
        for nf in not_found:
            print(f'  - {nf} (tried: {id_to_name(nf)})')

    print(f'\nArtists file updated: {ARTISTS_FILE}')


if __name__ == '__main__':
    main()

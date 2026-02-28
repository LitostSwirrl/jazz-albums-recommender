#!/usr/bin/env python3
"""
Fix missing/broken artist images and stub bios in artists.json.

Part 1: Fix 5 missing/broken artist images
Part 2: Replace 4 fragile Flickr URLs with Wikimedia alternatives
Part 3: Fix 20 stub bios (< 100 chars) using Wikipedia summaries

Uses stdlib only (urllib, json, re, time, os). Rate limit: 1 req/sec.
"""

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
CACHE_FILE = '/tmp/fix_artist_data_cache.json'

# --- Part 1: Artists with missing/broken images ---
MISSING_IMAGE_IDS = [
    'baby-face-willette',
    'jiro-inagaki',
    'joey-calderazzo',
    'yuki-arimasa',
]
BROKEN_IMAGE_IDS = [
    'bobbi-humphrey',  # Points to a file type icon, not a photo
]

# --- Part 2: Flickr URLs to replace ---
FLICKR_IDS = [
    'chris-mcgregor',
    'grachan-moncur',
    'ronnie-foster',
    'terumasa-hino',
]

# --- Part 3: Stub bios (< 100 chars) ---
STUB_BIO_IDS = [
    'arve-henriksen', 'mark-turner', 'mark-whitfield',
    'abraham-burton', 'chick-webb', 'chris-potter', 'danilo-perez',
    'david-s-ware', 'enrico-pieranunzi', 'gonzalo-rubalcaba', 'greg-osby',
    'john-patitucci', 'julian-lage', 'ken-vandermark', 'lage-lund',
    'lars-jansson', 'matthew-shipp', 'phil-woods', 'stefon-harris',
    'wallace-roney',
]

# Japanese Wikipedia fallbacks for Japanese artists
JAPANESE_WIKI_NAMES = {
    'jiro-inagaki': '稲垣次郎',
    'yuki-arimasa': '有馬祐輝',
}


def api_get(url, timeout=20):
    """Make a GET request with retries and error handling."""
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


def get_wiki_rest_summary(title, lang='en'):
    """Get Wikipedia page summary via REST API."""
    encoded = urllib.parse.quote(title.replace(' ', '_'))
    url = f'https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}'
    return api_get(url)


def get_image_from_wiki_rest(wiki_url):
    """Extract image from Wikipedia REST API using a wiki URL."""
    if not wiki_url:
        return None

    # Parse wiki URL to get lang and title
    match = re.match(r'https?://(\w+)\.wikipedia\.org/wiki/(.+)', wiki_url)
    if not match:
        return None

    lang = match.group(1)
    title = urllib.parse.unquote(match.group(2))

    data = get_wiki_rest_summary(title, lang=lang)
    if not data:
        return None

    # Prefer originalimage for better quality
    original = data.get('originalimage', {}).get('source')
    if original and is_valid_image_url(original):
        return original

    thumb = data.get('thumbnail', {}).get('source')
    if thumb and is_valid_image_url(thumb):
        # Upscale thumbnail to 500px
        high_res = re.sub(r'/\d+px-', '/500px-', thumb)
        return high_res

    return None


def get_image_from_wiki_rest_by_name(name, lang='en'):
    """Try Wikipedia REST API with name variations."""
    queries = [
        name,
        f'{name} (musician)',
        f'{name} (jazz musician)',
    ]

    for query in queries:
        data = get_wiki_rest_summary(query, lang=lang)
        if not data:
            time.sleep(1.0)
            continue

        original = data.get('originalimage', {}).get('source')
        if original and is_valid_image_url(original):
            return original

        thumb = data.get('thumbnail', {}).get('source')
        if thumb and is_valid_image_url(thumb):
            high_res = re.sub(r'/\d+px-', '/500px-', thumb)
            return high_res

        time.sleep(1.0)

    return None


def get_image_from_commons(artist_name):
    """Search Wikimedia Commons for artist image.

    Only returns images where the file title contains both the artist's
    first and last name, to avoid returning photos of wrong people.
    """
    query = urllib.parse.quote(f'{artist_name} jazz')
    url = (
        f'https://commons.wikimedia.org/w/api.php'
        f'?action=query&generator=search&gsrsearch={query}'
        f'&gsrnamespace=6&gsrlimit=5'
        f'&prop=imageinfo&iiprop=url|extmetadata'
        f'&iiurlwidth=500&format=json'
    )

    data = api_get(url)
    if not data:
        return None

    pages = data.get('query', {}).get('pages', {})
    if not pages:
        return None

    artist_lower = artist_name.lower()
    name_parts = artist_lower.split()
    surname = name_parts[-1]
    firstname = name_parts[0] if len(name_parts) > 1 else ''

    # Only accept images that clearly match the artist
    for page_id, page in sorted(pages.items()):
        title = page.get('title', '').lower()
        # Skip non-image files
        if not any(ext in title for ext in ['.jpg', '.jpeg', '.png']):
            continue
        # Skip obvious non-photo files
        if any(bad in title for bad in ['logo', 'icon', 'ogg', 'svg', 'flag',
                                         'flute', 'organ', 'bass', 'trumpet',
                                         'crows', 'brown', 'watts']):
            continue

        # Require BOTH first and last name in file title to avoid wrong people
        if surname in title and firstname in title:
            imageinfo = page.get('imageinfo', [{}])
            if imageinfo:
                thumb = imageinfo[0].get('thumburl')
                if thumb and is_valid_image_url(thumb):
                    return thumb
                url_val = imageinfo[0].get('url')
                if url_val and is_valid_image_url(url_val):
                    return url_val

    return None


def is_valid_image_url(url):
    """Check if URL looks like a real image (not an icon/placeholder)."""
    if not url:
        return False
    # Reject known bad patterns
    bad_patterns = [
        'file-type-icons',
        'fileicon',
        'placeholder',
        '.ogg',
        '.svg',
    ]
    url_lower = url.lower()
    return not any(p in url_lower for p in bad_patterns)


def get_bio_from_wikipedia(wiki_url):
    """Fetch a rich bio from Wikipedia using MediaWiki API.

    Uses exchars=1500 to get intro + early biography sections,
    then extracts 2-3 meaningful sentences (up to ~500 chars).
    """
    if not wiki_url:
        return None

    match = re.match(r'https?://(\w+)\.wikipedia\.org/wiki/(.+)', wiki_url)
    if not match:
        return None

    lang = match.group(1)
    title = match.group(2)  # Keep URL-encoded form for API
    encoded = urllib.parse.quote(urllib.parse.unquote(title))

    # Use MediaWiki API with exchars for richer text (intro + body)
    url = (
        f'https://{lang}.wikipedia.org/w/api.php'
        f'?action=query&titles={encoded}'
        f'&prop=extracts&explaintext=1&exchars=1500&format=json'
    )

    data = api_get(url)
    if not data:
        return None

    pages = data.get('query', {}).get('pages', {})
    extract = ''
    for pid, page in pages.items():
        if pid == '-1':
            return None
        extract = page.get('extract', '')
        break

    if not extract or len(extract) < 50:
        return None

    # Clean up Wikipedia formatting
    # Remove section headers like "== Biography =="
    extract = re.sub(r'\n==+\s*[^=]+\s*==+\n', ' ', extract)
    # Remove pronunciation guides and IPA
    extract = re.sub(r'\s*\([^)]*[/ˈˌ][^)]*\)\s*', ' ', extract)
    # Collapse whitespace
    extract = re.sub(r'\s+', ' ', extract).strip()

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', extract)
    if not sentences:
        return None

    # Build bio from sentences, aiming for 2-4 sentences, up to ~500 chars
    bio = ''
    sentence_count = 0
    for sentence in sentences:
        # Skip very short fragments or section artifacts
        if len(sentence) < 15:
            continue
        # Skip sentences that are just lists of albums/discography
        if sentence.startswith(('Carl Allen,', 'Sean Ardoin,')):
            continue

        candidate = (bio + ' ' + sentence).strip() if bio else sentence
        if len(candidate) > 500 and sentence_count >= 2:
            break
        bio = candidate
        sentence_count += 1
        if sentence_count >= 4:
            break

    bio = bio.strip()

    # Fix common Wikipedia artifacts
    # Remove leftover IPA/pronunciation like "( LAHZH; born" -> "(born"
    bio = re.sub(r'\(\s*[A-Z]+;\s*born', '(born', bio)
    # Fix "Born in St. " prefix that gets cut by section header removal
    # e.g., "Louis, Missouri, Osby studied" -> needs "Born in St. " prefix
    # This is handled case-by-case in post-processing

    return bio if len(bio) >= 50 else None


def load_cache():
    """Load cached results from previous runs."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {'images': {}, 'bios': {}}


def save_cache(cache):
    """Save cache to disk."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def main():
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)

    artist_map = {a['id']: a for a in artists}
    cache = load_cache()

    stats = {
        'images_fixed': 0,
        'images_not_found': 0,
        'flickr_replaced': 0,
        'flickr_kept': 0,
        'bios_updated': 0,
        'bios_unchanged': 0,
    }

    # =========================================================================
    # Part 1: Fix missing/broken artist images
    # =========================================================================
    print('=' * 60)
    print('PART 1: Fix missing/broken artist images')
    print('=' * 60)

    image_targets = MISSING_IMAGE_IDS + BROKEN_IMAGE_IDS
    for aid in image_targets:
        if aid not in artist_map:
            print(f'  WARNING: {aid} not found in artists.json')
            continue

        artist = artist_map[aid]
        cache_key = f'img:{aid}'

        if cache_key in cache['images']:
            url = cache['images'][cache_key]
            if url:
                print(f'  {artist["name"]}: cached -> {url[:80]}...')
                artist['imageUrl'] = url
                stats['images_fixed'] += 1
            else:
                print(f'  {artist["name"]}: cached -> NOT FOUND')
                stats['images_not_found'] += 1
            continue

        print(f'  Searching for {artist["name"]}...', end=' ', flush=True)

        image_url = None

        # Method 1: Wikipedia REST API from wiki URL
        wiki_url = artist.get('wikipedia', '')
        if wiki_url:
            time.sleep(1.0)
            image_url = get_image_from_wiki_rest(wiki_url)
            if image_url:
                print(f'FOUND (wiki rest)')

        # Method 2: Try English Wikipedia REST API by name
        if not image_url:
            time.sleep(1.0)
            image_url = get_image_from_wiki_rest_by_name(artist['name'])
            if image_url:
                print(f'FOUND (en wiki by name)')

        # Method 3: Try Japanese Wikipedia for Japanese artists
        if not image_url and aid in JAPANESE_WIKI_NAMES:
            time.sleep(1.0)
            jp_name = JAPANESE_WIKI_NAMES[aid]
            data = get_wiki_rest_summary(jp_name, lang='ja')
            if data:
                original = data.get('originalimage', {}).get('source')
                if original and is_valid_image_url(original):
                    image_url = original
                else:
                    thumb = data.get('thumbnail', {}).get('source')
                    if thumb and is_valid_image_url(thumb):
                        image_url = re.sub(r'/\d+px-', '/500px-', thumb)
            if image_url:
                print(f'FOUND (ja wiki)')

        # Method 4: Wikimedia Commons search
        if not image_url:
            time.sleep(1.0)
            image_url = get_image_from_commons(artist['name'])
            if image_url:
                print(f'FOUND (commons)')

        if image_url:
            cache['images'][cache_key] = image_url
            artist['imageUrl'] = image_url
            stats['images_fixed'] += 1
        else:
            cache['images'][cache_key] = None
            print('NOT FOUND')
            stats['images_not_found'] += 1

        save_cache(cache)

    print(f'\n  Part 1 results: {stats["images_fixed"]} fixed, {stats["images_not_found"]} not found')

    # =========================================================================
    # Part 2: Replace fragile Flickr URLs
    # =========================================================================
    print('\n' + '=' * 60)
    print('PART 2: Replace fragile Flickr URLs')
    print('=' * 60)

    for aid in FLICKR_IDS:
        if aid not in artist_map:
            print(f'  WARNING: {aid} not found in artists.json')
            continue

        artist = artist_map[aid]
        old_url = artist.get('imageUrl', '')
        cache_key = f'flickr:{aid}'

        if cache_key in cache['images']:
            url = cache['images'][cache_key]
            if url:
                print(f'  {artist["name"]}: cached replacement -> {url[:80]}...')
                artist['imageUrl'] = url
                stats['flickr_replaced'] += 1
            else:
                print(f'  {artist["name"]}: no alternative found, keeping Flickr URL')
                stats['flickr_kept'] += 1
            continue

        print(f'  Searching for {artist["name"]}...', end=' ', flush=True)

        image_url = None

        # Method 1: Wikipedia REST API from wiki URL
        wiki_url = artist.get('wikipedia', '')
        if wiki_url:
            time.sleep(1.0)
            image_url = get_image_from_wiki_rest(wiki_url)
            if image_url:
                print(f'FOUND (wiki rest)')

        # Method 2: Try English Wikipedia REST API by name
        if not image_url:
            time.sleep(1.0)
            image_url = get_image_from_wiki_rest_by_name(artist['name'])
            if image_url:
                print(f'FOUND (en wiki by name)')

        # Method 3: Wikimedia Commons search
        if not image_url:
            time.sleep(1.0)
            image_url = get_image_from_commons(artist['name'])
            if image_url:
                print(f'FOUND (commons)')

        if image_url:
            cache['images'][cache_key] = image_url
            artist['imageUrl'] = image_url
            stats['flickr_replaced'] += 1
        else:
            cache['images'][cache_key] = None
            print('no alternative found, keeping Flickr URL')
            stats['flickr_kept'] += 1

        save_cache(cache)

    print(f'\n  Part 2 results: {stats["flickr_replaced"]} replaced, {stats["flickr_kept"]} kept')

    # =========================================================================
    # Part 3: Fix stub bios (< 100 chars)
    # =========================================================================
    print('\n' + '=' * 60)
    print('PART 3: Fix stub bios (< 100 chars)')
    print('=' * 60)

    for aid in STUB_BIO_IDS:
        if aid not in artist_map:
            print(f'  WARNING: {aid} not found in artists.json')
            continue

        artist = artist_map[aid]
        current_bio = artist.get('bio', '')
        wiki_url = artist.get('wikipedia', '')
        cache_key = f'bio:{aid}'

        if cache_key in cache['bios']:
            new_bio = cache['bios'][cache_key]
            if new_bio and len(new_bio) > len(current_bio):
                print(f'  {artist["name"]}: cached bio ({len(current_bio)} -> {len(new_bio)} chars)')
                artist['bio'] = new_bio
                stats['bios_updated'] += 1
            else:
                print(f'  {artist["name"]}: cached - no improvement')
                stats['bios_unchanged'] += 1
            continue

        print(f'  {artist["name"]} (current: {len(current_bio)} chars)...', end=' ', flush=True)

        time.sleep(1.0)
        new_bio = get_bio_from_wikipedia(wiki_url)

        if new_bio and len(new_bio) > len(current_bio):
            cache['bios'][cache_key] = new_bio
            artist['bio'] = new_bio
            stats['bios_updated'] += 1
            print(f'UPDATED ({len(current_bio)} -> {len(new_bio)} chars)')
        else:
            cache['bios'][cache_key] = new_bio
            stats['bios_unchanged'] += 1
            if new_bio:
                print(f'no improvement ({len(current_bio)} vs {len(new_bio)})')
            else:
                print('no extract found')

        save_cache(cache)

    print(f'\n  Part 3 results: {stats["bios_updated"]} updated, {stats["bios_unchanged"]} unchanged')

    # =========================================================================
    # Save updated artists.json
    # =========================================================================
    print('\n' + '=' * 60)
    print('SAVING RESULTS')
    print('=' * 60)

    with open(ARTISTS_FILE, 'w') as f:
        json.dump(artists, f, indent=2, ensure_ascii=False)

    print(f'  Saved to {ARTISTS_FILE}')
    print(f'\n  SUMMARY:')
    print(f'    Images fixed:     {stats["images_fixed"]}')
    print(f'    Images not found: {stats["images_not_found"]}')
    print(f'    Flickr replaced:  {stats["flickr_replaced"]}')
    print(f'    Flickr kept:      {stats["flickr_kept"]}')
    print(f'    Bios updated:     {stats["bios_updated"]}')
    print(f'    Bios unchanged:   {stats["bios_unchanged"]}')


if __name__ == '__main__':
    main()

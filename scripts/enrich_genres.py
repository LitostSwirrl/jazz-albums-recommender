#!/usr/bin/env python3
"""
Enrich album genres from credible external sources.

1. Remove "jazz" from all albums (redundant on a jazz site)
2. For albums left with no genres, enrich from:
   - Wikipedia categories (albums with wikipedia URLs)
   - MusicBrainz release-group tags (albums with MB UUIDs in cover URLs)
   - Wikidata SPARQL (by title)
   - Era-based fallback (curated era classification)
3. Save updated albums.json

Sources tried in priority order. Results cached in /tmp/genre_enrichment_cache.json.
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error

ALBUMS_PATH = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'albums.json')
CACHE_PATH = '/tmp/genre_enrichment_cache.json'

# Map Wikidata/Wikipedia genre names to our 32 consolidated genres
GENRE_NORMALIZE = {
    'bebop': 'bebop',
    'bop': 'bebop',
    'hard bop': 'hard bop',
    'hardbop': 'hard bop',
    'cool jazz': 'cool jazz',
    'west coast jazz': 'cool jazz',
    'free jazz': 'free jazz',
    'avant-garde jazz': 'avant-garde jazz',
    'avant-garde music': 'avant-garde jazz',
    'free improvisation': 'free improvisation',
    'jazz fusion': 'jazz fusion',
    'fusion': 'jazz fusion',
    'jazz-rock': 'jazz fusion',
    'post-bop': 'post-bop',
    'modal jazz': 'modal jazz',
    'soul jazz': 'soul jazz',
    'latin jazz': 'latin jazz',
    'afro-cuban jazz': 'latin jazz',
    'swing music': 'swing',
    'swing': 'swing',
    'big band': 'big band',
    'big band music': 'big band',
    'dixieland': 'dixieland',
    'new orleans jazz': 'early jazz',
    'early jazz': 'early jazz',
    'spiritual jazz': 'spiritual jazz',
    'vocal jazz': 'vocal jazz',
    'smooth jazz': 'smooth jazz',
    'contemporary jazz': 'contemporary jazz',
    'jazz-funk': 'jazz-funk',
    'jazz funk': 'jazz-funk',
    'orchestral jazz': 'orchestral jazz',
    'third stream': 'orchestral jazz',
    'chamber jazz': 'chamber jazz',
    'blues': 'blues',
    'loft jazz': 'loft jazz',
    'african jazz': 'African jazz',
    'world music': 'world jazz',
    'brazilian jazz': 'Brazilian jazz',
    'bossa nova': 'Brazilian jazz',
    'experimental music': 'experimental',
    'piano trio': 'piano trio',
}

# Wikipedia category patterns that map to genres
WIKI_CAT_PATTERNS = {
    r'bebop albums': 'bebop',
    r'hard bop albums': 'hard bop',
    r'cool jazz albums': 'cool jazz',
    r'free jazz albums': 'free jazz',
    r'avant-garde jazz albums': 'avant-garde jazz',
    r'jazz fusion albums': 'jazz fusion',
    r'post-bop albums': 'post-bop',
    r'modal jazz albums': 'modal jazz',
    r'soul jazz albums': 'soul jazz',
    r'latin jazz albums': 'latin jazz',
    r'swing albums': 'swing',
    r'big band albums': 'big band',
    r'dixieland albums': 'dixieland',
    r'spiritual jazz albums': 'spiritual jazz',
    r'vocal jazz albums': 'vocal jazz',
    r'smooth jazz albums': 'smooth jazz',
    r'jazz-funk albums': 'jazz-funk',
    r'third stream albums': 'orchestral jazz',
    r'chamber jazz albums': 'chamber jazz',
    r'loft jazz albums': 'loft jazz',
    r'experimental music albums': 'experimental',
    r'bossa nova albums': 'Brazilian jazz',
    r'afro-cuban jazz albums': 'latin jazz',
}

ERA_GENRE_MAP = {
    'early-jazz': 'early jazz',
    'swing': 'swing',
    'bebop': 'bebop',
    'cool-jazz': 'cool jazz',
    'hard-bop': 'hard bop',
    'free-jazz': 'free jazz',
    'fusion': 'jazz fusion',
    'contemporary': 'contemporary jazz',
}

UUID_PATTERN = re.compile(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})')


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_PATH, 'w') as f:
        json.dump(cache, f, indent=2)


def fetch_json(url, timeout=15):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'JazzAlbumsRecommender/1.0 (genre-enrichment)')
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())


def genres_from_wikipedia(wiki_url, cache):
    """Extract genre from Wikipedia article categories."""
    cache_key = 'wiki:' + wiki_url
    if cache_key in cache:
        return cache[cache_key]

    # Extract article title from URL
    title = wiki_url.rstrip('/').split('/')[-1]
    api_url = 'https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({
        'action': 'query',
        'titles': urllib.parse.unquote(title),
        'prop': 'categories',
        'cllimit': '50',
        'format': 'json',
    })

    genres = []
    try:
        data = fetch_json(api_url)
        pages = data.get('query', {}).get('pages', {})
        for page in pages.values():
            cats = [c['title'].lower() for c in page.get('categories', [])]
            for cat in cats:
                for pattern, genre in WIKI_CAT_PATTERNS.items():
                    if pattern in cat:
                        if genre not in genres:
                            genres.append(genre)
        time.sleep(0.3)
    except Exception as e:
        print('  Wikipedia error for %s: %s' % (title[:30], e))

    cache[cache_key] = genres
    return genres


def genres_from_musicbrainz(mbid, cache):
    """Fetch genres from MusicBrainz release → release-group."""
    cache_key = 'mb:' + mbid
    if cache_key in cache:
        return cache[cache_key]

    genres = []
    try:
        # Get release with release-group info
        url = 'https://musicbrainz.org/ws/2/release/%s?inc=release-groups+genres+tags&fmt=json' % mbid
        data = fetch_json(url, timeout=10)

        # Collect tags from release
        for tag in data.get('tags', []):
            name = tag['name'].lower()
            if name in GENRE_NORMALIZE and GENRE_NORMALIZE[name] not in genres:
                genres.append(GENRE_NORMALIZE[name])

        # Get release-group for better genre coverage
        rg_id = data.get('release-group', {}).get('id')
        if rg_id:
            time.sleep(1.1)
            url2 = 'https://musicbrainz.org/ws/2/release-group/%s?inc=genres+tags&fmt=json' % rg_id
            data2 = fetch_json(url2, timeout=10)
            for tag in data2.get('tags', []):
                name = tag['name'].lower()
                if name in GENRE_NORMALIZE and GENRE_NORMALIZE[name] not in genres:
                    genres.append(GENRE_NORMALIZE[name])
            for genre in data2.get('genres', []):
                name = genre['name'].lower()
                if name in GENRE_NORMALIZE and GENRE_NORMALIZE[name] not in genres:
                    genres.append(GENRE_NORMALIZE[name])

        time.sleep(1.1)
    except Exception as e:
        print('  MusicBrainz error for %s: %s' % (mbid[:8], str(e)[:50]))

    cache[cache_key] = genres
    return genres


def genres_from_wikidata(title, cache):
    """Query Wikidata for album genres via SPARQL."""
    cache_key = 'wd:' + title
    if cache_key in cache:
        return cache[cache_key]

    safe_title = title.replace('"', '\\"')
    query = '''
SELECT ?genreLabel WHERE {
  ?item wdt:P31 wd:Q482994 .
  ?item rdfs:label "%s"@en .
  ?item wdt:P136 ?genre .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
''' % safe_title

    genres = []
    try:
        url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({
            'query': query,
            'format': 'json',
        })
        data = fetch_json(url)
        for r in data.get('results', {}).get('bindings', []):
            name = r.get('genreLabel', {}).get('value', '').lower()
            if name in GENRE_NORMALIZE and GENRE_NORMALIZE[name] not in genres:
                genres.append(GENRE_NORMALIZE[name])
        time.sleep(0.5)
    except Exception as e:
        print('  Wikidata error for %s: %s' % (title[:30], str(e)[:50]))

    cache[cache_key] = genres
    return genres


def main():
    with open(ALBUMS_PATH) as f:
        albums = json.load(f)

    cache = load_cache()
    total = len(albums)

    # Phase 1: Remove "jazz" from all albums
    jazz_removed = 0
    needs_enrichment = []
    for album in albums:
        if 'jazz' in album['genres']:
            album['genres'] = [g for g in album['genres'] if g != 'jazz']
            jazz_removed += 1
        if not album['genres']:
            needs_enrichment.append(album)

    print('Phase 1: Removed "jazz" from %d/%d albums' % (jazz_removed, total))
    print('Albums needing enrichment: %d' % len(needs_enrichment))
    print()

    # Phase 2: Enrich from external sources
    stats = {'wikipedia': 0, 'musicbrainz': 0, 'wikidata': 0, 'era_fallback': 0}

    for i, album in enumerate(needs_enrichment):
        aid = album['id']
        title = album['title']
        genres_found = []

        # Source 1: Wikipedia categories
        if album.get('wikipedia') and not genres_found:
            genres_found = genres_from_wikipedia(album['wikipedia'], cache)
            if genres_found:
                stats['wikipedia'] += 1
                print('[%d/%d] %s: Wikipedia -> %s' % (i + 1, len(needs_enrichment), title[:40], genres_found))

        # Source 2: MusicBrainz
        if not genres_found:
            cover_url = album.get('coverUrl', '')
            mb_match = UUID_PATTERN.search(cover_url)
            if mb_match and not cover_url.startswith('https://wsrv.nl'):
                mbid = mb_match.group(1)
                genres_found = genres_from_musicbrainz(mbid, cache)
                if genres_found:
                    stats['musicbrainz'] += 1
                    print('[%d/%d] %s: MusicBrainz -> %s' % (i + 1, len(needs_enrichment), title[:40], genres_found))

        # Source 3: Wikidata
        if not genres_found:
            genres_found = genres_from_wikidata(title, cache)
            if genres_found:
                stats['wikidata'] += 1
                print('[%d/%d] %s: Wikidata -> %s' % (i + 1, len(needs_enrichment), title[:40], genres_found))

        # Fallback: Era-based genre
        if not genres_found:
            era_genre = ERA_GENRE_MAP.get(album['era'])
            if era_genre:
                genres_found = [era_genre]
                stats['era_fallback'] += 1
                print('[%d/%d] %s: era fallback -> %s' % (i + 1, len(needs_enrichment), title[:40], genres_found))

        album['genres'] = genres_found

        # Save cache periodically
        if (i + 1) % 20 == 0:
            save_cache(cache)

    save_cache(cache)

    # Phase 3: Save
    with open(ALBUMS_PATH, 'w') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)

    print()
    print('=== Results ===')
    print('Removed "jazz" from: %d albums' % jazz_removed)
    print('Enriched %d albums:' % len(needs_enrichment))
    print('  Wikipedia categories: %d' % stats['wikipedia'])
    print('  MusicBrainz tags:     %d' % stats['musicbrainz'])
    print('  Wikidata genres:      %d' % stats['wikidata'])
    print('  Era-based fallback:   %d' % stats['era_fallback'])

    # Final genre distribution
    from collections import Counter
    genre_counts = Counter()
    for a in albums:
        for g in a['genres']:
            genre_counts[g] += 1
    print()
    print('Final genre distribution (%d unique):' % len(genre_counts))
    for g, c in genre_counts.most_common():
        print('  %s: %d' % (g, c))


if __name__ == '__main__':
    main()

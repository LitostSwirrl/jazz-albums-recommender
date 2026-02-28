#!/usr/bin/env python3
"""
Stage 3a: Enrich discovered albums with metadata.
For each album: MB release-group details, Wikipedia description, era/genre assignment.
Requires: /tmp/discovered_albums.json from Stage 2
Output: /tmp/enriched_albums.json
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
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
ERAS_FILE = os.path.join(DATA_DIR, 'eras.json')
DISCOVERED_FILE = '/tmp/discovered_albums.json'
CACHE_FILE = '/tmp/enriched_albums.json'

# MusicBrainz tag → genre mapping
TAG_TO_GENRE = {
    'jazz': 'jazz',
    'hard bop': 'hard bop',
    'modal jazz': 'modal jazz',
    'cool jazz': 'cool jazz',
    'free jazz': 'free jazz',
    'bebop': 'bebop',
    'post-bop': 'post-bop',
    'avant-garde jazz': 'avant-garde jazz',
    'soul jazz': 'soul jazz',
    'latin jazz': 'latin jazz',
    'jazz fusion': 'jazz fusion',
    'fusion': 'jazz fusion',
    'smooth jazz': 'smooth jazz',
    'swing': 'swing',
    'big band': 'big band',
    'vocal jazz': 'vocal jazz',
    'bossa nova': 'bossa nova',
    'dixieland': 'dixieland',
    'third stream': 'third stream',
    'spiritual jazz': 'spiritual jazz',
    'jazz-funk': 'jazz-funk',
    'jazz-rock': 'jazz-rock',
    'contemporary jazz': 'contemporary jazz',
    'ecm style': 'contemporary jazz',
    'progressive jazz': 'progressive jazz',
    'nu jazz': 'nu jazz',
    'acid jazz': 'acid jazz',
    'afro-cuban jazz': 'afro-cuban jazz',
    'jazz blues': 'jazz blues',
    'mainstream jazz': 'mainstream jazz',
    'jazz piano': 'jazz',
    'jazz trumpet': 'jazz',
    'jazz saxophone': 'jazz',
}

# Year → era mapping
ERA_RANGES = [
    ('early-jazz', 1900, 1929),
    ('swing', 1930, 1945),
    ('bebop', 1940, 1955),
    ('cool-jazz', 1949, 1960),
    ('hard-bop', 1953, 1965),
    ('free-jazz', 1958, 1970),
    ('fusion', 1969, 1980),
    ('contemporary', 1980, 2025),
]


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


def assign_era(year, artist_eras):
    """Assign era based on year and artist's eras."""
    if not year:
        return artist_eras[0] if artist_eras else 'contemporary'

    # Find matching eras for this year
    matching = []
    for era_id, start, end in ERA_RANGES:
        if start <= year <= end:
            matching.append(era_id)

    if not matching:
        if year < 1900:
            return 'early-jazz'
        return 'contemporary'

    # Prefer era that overlaps with artist's eras
    for era in matching:
        if era in artist_eras:
            return era

    return matching[-1]  # Default to latest matching era


def extract_genres_from_tags(tags):
    """Convert MusicBrainz tags to genre labels."""
    genres = []
    seen = set()
    for tag in tags:
        name = tag.get('name', '').lower()
        mapped = TAG_TO_GENRE.get(name)
        if mapped and mapped not in seen:
            genres.append(mapped)
            seen.add(mapped)
    return genres[:4] if genres else None


def get_release_group_details(rg_mbid):
    """Get release-group details including tags and ratings."""
    url = f'https://musicbrainz.org/ws/2/release-group/{rg_mbid}?inc=tags+ratings+releases&fmt=json'
    return api_get(url)


def get_release_tracks(release_mbid):
    """Get track listing for a specific release."""
    url = f'https://musicbrainz.org/ws/2/release/{release_mbid}?inc=recordings&fmt=json'
    data = api_get(url)
    if not data:
        return []

    tracks = []
    for medium in data.get('media', []):
        for track in medium.get('tracks', []):
            title = track.get('title') or track.get('recording', {}).get('title', '')
            if title:
                tracks.append(title)
    return tracks


def get_wikipedia_description(title, artist):
    """Try to get album description from Wikipedia."""
    # Try album page
    queries = [
        f'{title} ({artist} album)',
        f'{title} (album)',
        title,
    ]

    for query in queries:
        encoded = urllib.parse.quote(query.replace(' ', '_'))
        url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}'

        req = urllib.request.Request(url, headers={
            'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history)',
            'Accept': 'application/json',
        })

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                extract = data.get('extract', '')
                page_title = data.get('title', '')

                # Verify it's about the right album/artist
                if extract and len(extract) > 100:
                    extract_lower = extract.lower()
                    artist_lower = artist.lower()
                    # Check if the extract mentions the artist
                    artist_parts = artist_lower.split()
                    last_name = artist_parts[-1] if artist_parts else ''
                    if (artist_lower in extract_lower or
                            last_name in extract_lower or
                            'album' in extract_lower or
                            'jazz' in extract_lower):
                        # Clean and truncate
                        desc = extract.strip()
                        if len(desc) > 600:
                            # Cut at last sentence before 600 chars
                            cutoff = desc[:600].rfind('. ')
                            if cutoff > 200:
                                desc = desc[:cutoff + 1]
                        return desc
        except Exception:
            pass

        time.sleep(0.5)

    return None


def generate_template_description(album, label, year, tracks, genres):
    """Generate a tier-2 template description."""
    title = album['title']
    artist = album['artist']

    parts = []

    # Opening sentence
    if label and year:
        parts.append(f"Recorded for {label} in {year}, '{title}' features {artist}")
    elif year:
        parts.append(f"Released in {year}, '{title}' features {artist}")
    else:
        parts.append(f"'{title}' features {artist}")

    # Genre context
    if genres:
        genre_str = ' and '.join(genres[:2])
        parts[0] += f" exploring {genre_str}."
    else:
        parts[0] += " in a distinctive jazz setting."

    # Track mention
    if tracks and len(tracks) >= 3:
        track_sample = tracks[:3]
        parts.append(f"Key tracks include '{track_sample[0]}' and '{track_sample[1]}'.")

    return ' '.join(parts)


def generate_significance(album, genres, era):
    """Generate a brief significance statement."""
    artist = album['artist']
    era_names = {
        'early-jazz': 'early jazz',
        'swing': 'swing era',
        'bebop': 'bebop',
        'cool-jazz': 'cool jazz',
        'hard-bop': 'hard bop',
        'free-jazz': 'free jazz',
        'fusion': 'jazz fusion',
        'contemporary': 'modern jazz',
    }
    era_name = era_names.get(era, 'jazz')

    if genres:
        return f"An important entry in {artist}'s discography, showcasing their contribution to {genres[0]}."
    return f"A noteworthy album in {artist}'s body of work within the {era_name} tradition."


def main():
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    with open(ARTISTS_FILE) as f:
        artists = json.load(f)
    artist_map = {a['id']: a for a in artists}

    # Load discovered albums
    if not os.path.exists(DISCOVERED_FILE):
        print(f'ERROR: {DISCOVERED_FILE} not found. Run discover_albums.py first.')
        sys.exit(1)

    with open(DISCOVERED_FILE) as f:
        discovered = json.load(f)

    # Flatten all discovered albums
    all_albums = []
    for artist_data in discovered.values():
        all_albums.extend(artist_data.get('albums', []))

    print(f'Total albums to enrich: {len(all_albums)}')

    # Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f'Cache loaded: {len(cache)} enriched')

    total = len(all_albums)
    enriched_count = 0
    wiki_count = 0
    template_count = 0

    for i, album in enumerate(all_albums):
        if i < start_from:
            continue

        aid = album['id']
        if aid in cache:
            continue

        artist = artist_map.get(album['artistId'], {})
        artist_eras = artist.get('eras', ['contemporary'])

        print(f'[{i+1}/{total}] {album["title"]} - {album["artist"]}...', end=' ', flush=True)

        # Step 1: Get release-group details from MB
        rg_mbid = album.get('releaseGroupMbid')
        label = None
        tags = []
        year = album.get('year')
        tracks = []
        release_mbid = None

        if rg_mbid:
            time.sleep(1.1)
            rg_data = get_release_group_details(rg_mbid)

            if rg_data:
                tags = rg_data.get('tags', [])
                # Get first release for tracks and label
                releases = rg_data.get('releases', [])
                if releases:
                    release_mbid = releases[0]['id']
                    # Try to find label from release
                    if not year and releases[0].get('date'):
                        date_str = releases[0]['date']
                        if len(date_str) >= 4:
                            year = int(date_str[:4])

            # Step 2: Get tracks from first release
            if release_mbid:
                time.sleep(1.1)
                tracks = get_release_tracks(release_mbid)

                # Also try to get label from release details
                rel_url = f'https://musicbrainz.org/ws/2/release/{release_mbid}?inc=labels&fmt=json'
                time.sleep(1.1)
                rel_data = api_get(rel_url)
                if rel_data:
                    label_info = rel_data.get('label-info', [])
                    if label_info and label_info[0].get('label'):
                        label = label_info[0]['label'].get('name')

        # Step 3: Determine genres and era
        genres = extract_genres_from_tags(tags)
        if not genres:
            # Infer from artist eras
            era_to_genre = {
                'early-jazz': ['early jazz'],
                'swing': ['swing', 'big band'],
                'bebop': ['bebop'],
                'cool-jazz': ['cool jazz'],
                'hard-bop': ['hard bop'],
                'free-jazz': ['free jazz', 'avant-garde jazz'],
                'fusion': ['jazz fusion'],
                'contemporary': ['contemporary jazz'],
            }
            for era in artist_eras:
                g = era_to_genre.get(era, [])
                if g:
                    genres = g[:2]
                    break
            if not genres:
                genres = ['jazz']

        era = assign_era(year, artist_eras)

        # Step 4: Get description
        description = None
        significance = None

        # Try Wikipedia first
        time.sleep(1.0)
        wiki_desc = get_wikipedia_description(album['title'], album['artist'])

        if wiki_desc:
            description = wiki_desc
            wiki_count += 1
            tier = 'wiki'
        else:
            # Template description
            description = generate_template_description(album, label, year, tracks, genres)
            template_count += 1
            tier = 'template'

        significance = generate_significance(album, genres, era)

        # Build enriched album
        enriched = {
            'id': album['id'],
            'title': album['title'],
            'artist': album['artist'],
            'artistId': album['artistId'],
            'year': year,
            'label': label or 'Unknown',
            'era': era,
            'genres': genres,
            'description': description,
            'significance': significance,
            'keyTracks': tracks[:5] if tracks else [],
            'releaseGroupMbid': rg_mbid,
            'releaseMbid': release_mbid,
            'descriptionTier': tier,
        }

        cache[aid] = enriched
        enriched_count += 1
        print(f'{tier} | {era} | {len(tracks)} tracks | {label or "?"} | {year or "?"}')

        # Save every 10
        if enriched_count % 10 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)

    # Final save
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    print(f'\n=== Results ===')
    print(f'Total enriched: {len(cache)}')
    print(f'Wikipedia descriptions: {wiki_count}')
    print(f'Template descriptions: {template_count}')
    print(f'Cache: {CACHE_FILE}')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Stage 3: Enrich expansion-discovered albums with metadata.

For each album in /tmp/expansion_discovered.json:
  1. Fetch MusicBrainz release-group details (label, tags/genres, tracks)
  2. Fetch Wikipedia description via REST API
  3. Assign era based on year + artist eras
  4. Map genres from MB tags using TAG_TO_GENRE (consolidated 32-genre set)
  5. Generate quality descriptions and significance text

Requires: /tmp/expansion_discovered.json (from Stage 2)
Output:   /tmp/expansion_enriched.json (resumable, saves every 10)

Usage:
  python3 scripts/enrich_expansion_albums.py [start_from]
"""

import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
ERAS_FILE = os.path.join(DATA_DIR, 'eras.json')
DISCOVERED_FILE = '/tmp/expansion_discovered.json'
CACHE_FILE = '/tmp/expansion_enriched.json'

# ---------------------------------------------------------------------------
# MusicBrainz tag -> consolidated genre mapping (32-genre set)
# ---------------------------------------------------------------------------

TAG_TO_GENRE = {
    # Core jazz genres
    'jazz': 'jazz',
    'hard bop': 'hard bop',
    'modal jazz': 'modal jazz',
    'cool jazz': 'cool jazz',
    'free jazz': 'free jazz',
    'bebop': 'bebop',
    'post-bop': 'post-bop',
    'avant-garde jazz': 'avant-garde jazz',
    'soul jazz': 'soul jazz',
    # Latin family -> consolidated to latin jazz
    'latin jazz': 'latin jazz',
    'afro-cuban jazz': 'latin jazz',
    'bossa nova': 'latin jazz',
    # Fusion family -> consolidated to jazz fusion
    'jazz fusion': 'jazz fusion',
    'fusion': 'jazz fusion',
    'jazz-rock': 'jazz fusion',
    'jazz rock': 'jazz fusion',
    # Other named genres
    'smooth jazz': 'smooth jazz',
    'swing': 'swing',
    'big band': 'big band',
    'vocal jazz': 'vocal jazz',
    'dixieland': 'dixieland',
    'spiritual jazz': 'spiritual jazz',
    'jazz-funk': 'jazz-funk',
    'contemporary jazz': 'contemporary jazz',
    'ecm style': 'contemporary jazz',
    'world music': 'world jazz',
    'african jazz': 'African jazz',
    'free improvisation': 'free improvisation',
    'experimental': 'experimental',
    # Instrument tags -> generic jazz
    'jazz piano': 'jazz',
    'jazz trumpet': 'jazz',
    'jazz saxophone': 'jazz',
}

# ---------------------------------------------------------------------------
# Year -> era mapping
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Instrument display names for template descriptions
# ---------------------------------------------------------------------------

INSTRUMENT_DISPLAY = {
    'piano': 'piano',
    'trumpet': 'trumpet',
    'saxophone': 'saxophone',
    'tenor saxophone': 'tenor saxophone',
    'alto saxophone': 'alto saxophone',
    'soprano saxophone': 'soprano saxophone',
    'baritone saxophone': 'baritone saxophone',
    'bass': 'bass',
    'double bass': 'bass',
    'guitar': 'guitar',
    'drums': 'drums',
    'trombone': 'trombone',
    'clarinet': 'clarinet',
    'vibraphone': 'vibraphone',
    'organ': 'organ',
    'flute': 'flute',
    'vocals': 'vocal',
    'cornet': 'cornet',
    'violin': 'violin',
    'cello': 'cello',
    'harmonica': 'harmonica',
    'percussion': 'percussion',
    'bandleader': 'ensemble leadership',
    'composer': 'compositional',
}

# ---------------------------------------------------------------------------
# Template description sentence banks (20+ patterns)
# ---------------------------------------------------------------------------

# Opening sentence patterns: (format_string, required_keys)
OPENING_PATTERNS = [
    ("Recorded in {year} for {label}, {title} showcases {artist}'s {instrument} work in the {genre} tradition.",
     ['year', 'label', 'instrument', 'genre']),
    ("Released on {label} in {year}, {title} is a compelling {genre} statement by {artist}.",
     ['year', 'label', 'genre']),
    ("{title}, released in {year}, captures {artist} at a creative peak, blending {genre} with personal expression.",
     ['year', 'genre']),
    ("A {year} {label} session, {title} finds {artist} pushing deeper into {genre} territory.",
     ['year', 'label', 'genre']),
    ("On {title} ({year}), {artist} delivers a focused exploration of {genre}, recorded for {label}.",
     ['year', 'label', 'genre']),
    ("{artist}'s {title}, cut for {label} in {year}, stands as a distinguished entry in the {genre} canon.",
     ['year', 'label', 'genre']),
    ("With {title} ({year}), {artist} crafts a {genre} session that balances technical mastery and emotional depth.",
     ['year', 'genre']),
    ("Issued by {label} in {year}, {title} presents {artist} in a {genre} context that highlights their improvisational gifts.",
     ['year', 'label', 'genre']),
    ("{title} documents a {year} studio date for {label}, with {artist} leading a tight {genre} ensemble.",
     ['year', 'label', 'genre']),
    ("First released in {year}, {title} is an essential chapter in {artist}'s recorded output, rooted in {genre}.",
     ['year', 'genre']),
    # Instrument-focused openers
    ("{artist}'s {instrument} artistry is on full display on {title}, a {year} {label} release steeped in {genre}.",
     ['year', 'label', 'instrument', 'genre']),
    ("A showcase for {artist}'s {instrument}, {title} ({year}) draws from the {genre} vocabulary with authority.",
     ['year', 'instrument', 'genre']),
]

# Fallback openers when fewer keys available
MINIMAL_OPENERS = [
    "'{title}' features {artist} in a distinctive jazz setting.",
    "'{title}' is a noteworthy entry in {artist}'s discography.",
    "{artist} delivers a focused performance on '{title}'.",
    "On '{title}', {artist} explores new creative ground.",
]

# Track-mention patterns
TRACK_PATTERNS = [
    "Notable tracks include '{t1}' and '{t2}'.",
    "Highlights include '{t1}' and '{t2}'.",
    "The set list features '{t1}' and '{t2}' among its standout moments.",
    "Among its key performances are '{t1}' and '{t2}'.",
    "Tracks such as '{t1}' and '{t2}' anchor the program.",
]

# Era-specific color sentences
ERA_COLOR = {
    'early-jazz': "The recording reflects the communal, improvisational spirit of early jazz.",
    'swing': "The arrangement carries the rhythmic drive and ensemble polish of the swing era.",
    'bebop': "The performances bristle with the harmonic daring and velocity that defined bebop.",
    'cool-jazz': "The session exudes the understated elegance and sophisticated lyricism of the cool jazz school.",
    'hard-bop': "The music pulses with the soulful intensity and blues-rooted fire of hard bop.",
    'free-jazz': "The music ventures into adventurous, boundary-dissolving territory characteristic of the free jazz movement.",
    'fusion': "The album channels the electric energy and cross-genre experimentation of the fusion era.",
    'contemporary': "The album reflects the stylistic breadth and global awareness of contemporary jazz.",
}

# Career-position patterns (for significance)
SIGNIFICANCE_PATTERNS = [
    "An important entry in {artist}'s discography, showcasing their contribution to {genre}.",
    "A noteworthy album in {artist}'s body of work within the {era_name} tradition.",
    "Represents a key chapter in {artist}'s evolving artistic vision.",
    "Demonstrates {artist}'s command of {genre} and their place within the broader jazz lineage.",
    "An essential document of {artist}'s artistry during the {era_name} period.",
    "Adds to {artist}'s reputation as a leading voice in {genre}.",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def api_get(url, timeout=20):
    """Fetch JSON from a URL with retries and rate-limit handling."""
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
    """Assign era based on year and artist's known eras."""
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
    """Convert MusicBrainz tags to consolidated genre labels."""
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
    """Get release-group details including tags, ratings, and releases."""
    url = (
        f'https://musicbrainz.org/ws/2/release-group/{rg_mbid}'
        f'?inc=tags+ratings+releases&fmt=json'
    )
    return api_get(url)


def get_release_tracks(release_mbid):
    """Get track listing for a specific release."""
    url = (
        f'https://musicbrainz.org/ws/2/release/{release_mbid}'
        f'?inc=recordings&fmt=json'
    )
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


def get_release_label(release_mbid):
    """Get label name from a release."""
    url = (
        f'https://musicbrainz.org/ws/2/release/{release_mbid}'
        f'?inc=labels&fmt=json'
    )
    data = api_get(url)
    if not data:
        return None
    label_info = data.get('label-info', [])
    if label_info and label_info[0].get('label'):
        return label_info[0]['label'].get('name')
    return None


# ---------------------------------------------------------------------------
# Wikipedia description fetching
# ---------------------------------------------------------------------------


def get_wikipedia_description(title, artist):
    """Try to get album description from Wikipedia REST API.

    Tries queries: "{title} ({artist} album)", "{title} (album)", "{title}"
    Validates that the extract mentions the artist, or the words album/jazz/record.
    Returns 2-3 sentence extract or None.
    """
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

                if not extract or len(extract) < 100:
                    continue

                # Validate relevance: must mention artist or album/jazz/record
                extract_lower = extract.lower()
                artist_lower = artist.lower()
                artist_parts = artist_lower.split()
                last_name = artist_parts[-1] if artist_parts else ''

                is_relevant = (
                    artist_lower in extract_lower
                    or last_name in extract_lower
                    or 'album' in extract_lower
                    or 'jazz' in extract_lower
                    or 'record' in extract_lower
                )

                if not is_relevant:
                    continue

                # Clean and truncate to 2-3 sentences (aim for ~600 chars)
                desc = extract.strip()
                if len(desc) > 600:
                    cutoff = desc[:600].rfind('. ')
                    if cutoff > 200:
                        desc = desc[:cutoff + 1]

                return desc

        except Exception:
            pass

        time.sleep(0.5)

    return None


# ---------------------------------------------------------------------------
# Template description generation (improved with 20+ patterns)
# ---------------------------------------------------------------------------


def _pick_instrument(artist_data):
    """Get a display-friendly instrument string from artist data."""
    instruments = artist_data.get('instruments', [])
    if not instruments:
        return None
    primary = instruments[0]
    return INSTRUMENT_DISPLAY.get(primary, primary)


def _format_opening(title, artist, year, label, genre, instrument):
    """Pick and format an opening sentence from the pattern bank."""
    available = {
        'title': title,
        'artist': artist,
    }
    if year:
        available['year'] = str(year)
    if label and label != 'Unknown':
        available['label'] = label
    if genre:
        available['genre'] = genre
    if instrument:
        available['instrument'] = instrument

    # Filter patterns whose required keys are all available
    eligible = []
    for pattern, required in OPENING_PATTERNS:
        if all(k in available for k in required):
            eligible.append(pattern)

    if eligible:
        chosen = random.choice(eligible)
        try:
            return chosen.format(**available)
        except KeyError:
            pass

    # Fallback to minimal opener
    chosen = random.choice(MINIMAL_OPENERS)
    return chosen.format(title=title, artist=artist)


def _format_track_mention(tracks):
    """Pick a track-mention sentence."""
    if not tracks or len(tracks) < 2:
        return None
    t1 = tracks[0]
    t2 = tracks[1]
    chosen = random.choice(TRACK_PATTERNS)
    return chosen.format(t1=t1, t2=t2)


def generate_template_description(album, label, year, tracks, genres, artist_data):
    """Generate a rich template description using sentence banks.

    Incorporates era, instrument, label, year, key tracks, and genre
    for variety across albums.
    """
    title = album['title']
    artist = album['artist']
    genre = genres[0] if genres else 'jazz'
    instrument = _pick_instrument(artist_data)

    # Seed random per album for deterministic but varied output
    random.seed(hash(album['id']))

    parts = []

    # 1. Opening sentence
    opening = _format_opening(title, artist, year, label, genre, instrument)
    parts.append(opening)

    # 2. Era-specific color sentence (sometimes)
    era = assign_era(year, artist_data.get('eras', ['contemporary']))
    era_sentence = ERA_COLOR.get(era)
    if era_sentence and random.random() > 0.4:
        parts.append(era_sentence)

    # 3. Track mention
    track_sentence = _format_track_mention(tracks)
    if track_sentence:
        parts.append(track_sentence)

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
    genre = genres[0] if genres else 'jazz'

    # Pick a significance pattern with some determinism
    random.seed(hash(album['id'] + '-sig'))
    pattern = random.choice(SIGNIFICANCE_PATTERNS)

    try:
        return pattern.format(artist=artist, genre=genre, era_name=era_name)
    except KeyError:
        return f"A noteworthy album in {artist}'s body of work within the {era_name} tradition."


# ---------------------------------------------------------------------------
# Main enrichment pipeline
# ---------------------------------------------------------------------------


def main():
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    # Load artists for context
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)
    artist_map = {a['id']: a for a in artists}

    # Load discovered albums
    if not os.path.exists(DISCOVERED_FILE):
        print(f'ERROR: {DISCOVERED_FILE} not found. Run expansion discovery (Stage 2) first.')
        sys.exit(1)

    with open(DISCOVERED_FILE) as f:
        discovered = json.load(f)

    # Flatten all discovered albums
    all_albums = []
    for artist_data in discovered.values():
        all_albums.extend(artist_data.get('albums', []))

    print(f'Total albums to enrich: {len(all_albums)}')

    # Load cache (resumable)
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f'Cache loaded: {len(cache)} already enriched')

    total = len(all_albums)
    enriched_count = 0
    wiki_count = 0
    template_count = 0
    skipped_count = 0

    for i, album in enumerate(all_albums):
        if i < start_from:
            continue

        aid = album['id']
        if aid in cache:
            skipped_count += 1
            continue

        artist = artist_map.get(album.get('artistId', ''), {})
        artist_eras = artist.get('eras', ['contemporary'])

        print(f'[{i + 1}/{total}] {album["title"]} - {album["artist"]}...', end=' ', flush=True)

        # -----------------------------------------------------------------
        # Step 1: MusicBrainz release-group details
        # -----------------------------------------------------------------
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
                releases = rg_data.get('releases', [])
                if releases:
                    release_mbid = releases[0]['id']
                    # Try to extract year from release date if missing
                    if not year and releases[0].get('date'):
                        date_str = releases[0]['date']
                        if len(date_str) >= 4:
                            try:
                                year = int(date_str[:4])
                            except ValueError:
                                pass

            # Step 2: Get tracks from first release
            if release_mbid:
                time.sleep(1.1)
                tracks = get_release_tracks(release_mbid)

                # Get label from release details
                time.sleep(1.1)
                label = get_release_label(release_mbid)

        # -----------------------------------------------------------------
        # Step 3: Determine genres and era
        # -----------------------------------------------------------------
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

        # -----------------------------------------------------------------
        # Step 4: Get description (Wikipedia -> template fallback)
        # -----------------------------------------------------------------
        description = None
        tier = 'template'

        time.sleep(1.0)
        wiki_desc = get_wikipedia_description(album['title'], album['artist'])

        if wiki_desc:
            description = wiki_desc
            wiki_count += 1
            tier = 'wiki'
        else:
            description = generate_template_description(
                album, label, year, tracks, genres, artist
            )
            template_count += 1

        significance = generate_significance(album, genres, era)

        # -----------------------------------------------------------------
        # Build enriched album record
        # -----------------------------------------------------------------
        enriched = {
            'id': album['id'],
            'title': album['title'],
            'artist': album['artist'],
            'artistId': album.get('artistId', ''),
            'year': year,
            'label': label or 'Unknown',
            'era': era,
            'genres': genres,
            'description': description,
            'significance': significance,
            'keyTracks': tracks[:5] if tracks else [],
            'releaseGroupMbid': rg_mbid,
        }

        cache[aid] = enriched
        enriched_count += 1
        print(f'{tier} | {era} | {len(tracks)} tracks | {label or "?"} | {year or "?"}')

        # Save every 10 albums (resumable checkpoint)
        if enriched_count % 10 == 0:
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
            print(f'  [checkpoint saved: {len(cache)} total]')

    # Final save
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    print(f'\n{"=" * 50}')
    print(f'=== Enrichment Results ===')
    print(f'{"=" * 50}')
    print(f'Total in cache:           {len(cache)}')
    print(f'Newly enriched this run:  {enriched_count}')
    print(f'Skipped (already cached): {skipped_count}')
    print(f'Wikipedia descriptions:   {wiki_count}')
    print(f'Template descriptions:    {template_count}')
    print(f'Cache file:               {CACHE_FILE}')


if __name__ == '__main__':
    main()

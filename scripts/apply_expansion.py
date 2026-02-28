#!/usr/bin/env python3
"""
Stage 5: Merge all expansion enrichment data into albums.json and artists.json.
Reads from /tmp/expansion_*.json caches and updates src/data/.
"""

import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')

ENRICHED_FILE = '/tmp/expansion_enriched.json'
COVERS_FILE = '/tmp/expansion_covers.json'
STREAMING_FILE = '/tmp/expansion_streaming.json'
WIKIPEDIA_FILE = '/tmp/expansion_wikipedia.json'
PLAN_FILE = '/tmp/expansion_plan.json'

VALID_ERAS = {
    'early-jazz', 'swing', 'bebop', 'cool-jazz',
    'hard-bop', 'free-jazz', 'fusion', 'contemporary',
}

SKIP_ARTISTS = {
    'arnold-schoenberg', 'darius-milhaud', 'buddy-bolden',
    'lovie-austin', 'james-jamerson', 'jerry-jemmott',
}


def load_json(path, default=None):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default if default is not None else {}


def main():
    albums = load_json(ALBUMS_FILE, [])
    artists = load_json(ARTISTS_FILE, [])
    enriched = load_json(ENRICHED_FILE)
    covers = load_json(COVERS_FILE)
    streaming = load_json(STREAMING_FILE)
    wikipedia = load_json(WIKIPEDIA_FILE)
    plan = load_json(PLAN_FILE)

    if not enriched:
        print(f'ERROR: {ENRICHED_FILE} not found or empty.')
        sys.exit(1)

    existing_ids = {a['id'] for a in albums}
    artist_map = {a['id']: a for a in artists}

    # Check if plan has new artists to add
    # new_artists can be a list of dicts (from plan_expansion.py) or a dict
    new_artists_list = plan.get('new_artists', []) if plan else []
    if isinstance(new_artists_list, dict):
        new_artists_list = [{'id': k, **v} for k, v in new_artists_list.items()]

    # Style -> era mapping for new artists
    style_to_eras = {
        'cool-jazz': ['cool-jazz'],
        'cool jazz': ['cool-jazz'],
        'hard-bop': ['hard-bop'],
        'hard bop': ['hard-bop'],
        'bebop': ['bebop'],
        'post-bop': ['hard-bop', 'contemporary'],
        'free-jazz': ['free-jazz'],
        'swing': ['swing'],
    }

    for artist_entry in new_artists_list:
        artist_id = artist_entry.get('id')
        if not artist_id or artist_id in artist_map:
            continue

        # Map fields from plan format to artist format
        name = artist_entry.get('name', '')
        instrument = artist_entry.get('instrument', '')
        instruments = [instrument] if instrument else artist_entry.get('instruments', [])
        style = artist_entry.get('style', '')

        # Derive eras from style or birth year
        eras = artist_entry.get('eras', [])
        if not eras and style:
            for style_part in style.split('/'):
                style_part = style_part.strip().lower()
                if style_part in style_to_eras:
                    eras = style_to_eras[style_part]
                    break
        if not eras:
            birth = artist_entry.get('birth_year', artist_entry.get('birthYear', 0))
            if birth and birth < 1930:
                eras = ['swing', 'bebop']
            elif birth and birth < 1940:
                eras = ['hard-bop']
            else:
                eras = ['contemporary']

        new_artist = {
            'id': artist_id,
            'name': name,
            'birthYear': artist_entry.get('birth_year', artist_entry.get('birthYear', 0)),
            'bio': artist_entry.get('bio', f'{name} was a jazz {instrument or "musician"}.'),
            'instruments': instruments,
            'eras': eras,
            'influences': [],
            'influencedBy': [],
            'keyAlbums': [],
        }

        death = artist_entry.get('death_year', artist_entry.get('deathYear'))
        if death:
            new_artist['deathYear'] = death
        if artist_entry.get('imageUrl'):
            new_artist['imageUrl'] = artist_entry['imageUrl']
        if artist_entry.get('wikipedia'):
            new_artist['wikipedia'] = artist_entry['wikipedia']

        artists.append(new_artist)
        artist_map[artist_id] = new_artist
        print(f'  New artist added: {name} ({", ".join(instruments)}, eras: {", ".join(eras)})')

    added = 0
    skipped = 0
    errors = []

    new_albums = []
    for album_id, data in enriched.items():
        if album_id in existing_ids:
            skipped += 1
            continue

        if not data.get('title') or not data.get('artistId'):
            errors.append(f'{album_id}: missing title or artistId')
            continue

        era = data.get('era', 'contemporary')
        if era not in VALID_ERAS:
            era = 'contemporary'

        # Validate description quality
        description = data.get('description', '')
        if len(description) < 80:
            errors.append(f'{album_id}: description too short ({len(description)} chars)')
            description = description or f'A jazz album by {data.get("artist", "unknown artist")}.'

        album = {
            'id': data['id'],
            'title': data['title'],
            'artist': data['artist'],
            'artistId': data['artistId'],
            'year': data.get('year'),
            'label': data.get('label', 'Unknown'),
            'era': era,
            'genres': data.get('genres', ['jazz']),
            'description': description,
            'significance': data.get('significance', ''),
            'keyTracks': data.get('keyTracks', []),
        }

        # Cover art
        cover = covers.get(album_id)
        if cover:
            album['coverUrl'] = cover
        else:
            album['coverUrl'] = ''

        # Streaming links
        stream = streaming.get(album_id, {})
        if isinstance(stream, dict):
            for key in ('spotifyUrl', 'appleMusicUrl', 'youtubeMusicUrl', 'youtubeUrl'):
                if stream.get(key):
                    album[key] = stream[key]

        # Wikipedia URL
        wiki = wikipedia.get(album_id)
        if wiki:
            album['wikipedia'] = wiki

        new_albums.append(album)
        added += 1

    # Sort and merge
    new_albums.sort(key=lambda a: (a.get('year') or 9999, a['title']))
    albums.extend(new_albums)
    albums.sort(key=lambda a: (a.get('year') or 9999, a['title']))

    # Update artists' keyAlbums
    updated_artists = 0
    for album in new_albums:
        aid = album['artistId']
        if aid in artist_map:
            artist = artist_map[aid]
            if album['id'] not in artist.get('keyAlbums', []):
                if 'keyAlbums' not in artist:
                    artist['keyAlbums'] = []
                artist['keyAlbums'].append(album['id'])
                updated_artists += 1

    # Deduplicate
    all_ids = [a['id'] for a in albums]
    duplicates = [aid for aid in set(all_ids) if all_ids.count(aid) > 1]
    if duplicates:
        print(f'WARNING: Duplicate album IDs: {duplicates}')
        seen = set()
        deduped = []
        for a in albums:
            if a['id'] not in seen:
                seen.add(a['id'])
                deduped.append(a)
        albums = deduped

    # Validate eras
    invalid_eras = [a['id'] for a in albums if a.get('era') not in VALID_ERAS]
    if invalid_eras:
        print(f'WARNING: Albums with invalid eras: {invalid_eras[:10]}')

    # Write
    with open(ALBUMS_FILE, 'w') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)
        f.write('\n')

    with open(ARTISTS_FILE, 'w') as f:
        json.dump(artists, f, indent=2, ensure_ascii=False)
        f.write('\n')

    # Stats
    print(f'\n=== Apply Expansion Results ===')
    print(f'New albums added: {added}')
    print(f'Skipped (already exist): {skipped}')
    print(f'Errors: {len(errors)}')
    print(f'Total albums now: {len(albums)}')
    print(f'Total artists now: {len(artists)}')
    print(f'Artists with updated keyAlbums: {updated_artists}')

    if errors:
        print(f'\nErrors:')
        for e in errors[:20]:
            print(f'  {e}')

    # Coverage stats
    has_cover = sum(1 for a in albums if a.get('coverUrl'))
    has_spotify = sum(1 for a in albums if a.get('spotifyUrl'))
    has_apple = sum(1 for a in albums if a.get('appleMusicUrl'))
    has_wiki = sum(1 for a in albums if a.get('wikipedia'))

    print(f'\nCoverage:')
    print(f'  Cover art: {has_cover}/{len(albums)}')
    print(f'  Spotify: {has_spotify}/{len(albums)}')
    print(f'  Apple Music: {has_apple}/{len(albums)}')
    print(f'  Wikipedia: {has_wiki}/{len(albums)}')

    # Era distribution
    era_counts = {}
    for a in albums:
        era = a.get('era', 'unknown')
        era_counts[era] = era_counts.get(era, 0) + 1
    print(f'\nEra distribution:')
    for era in ['early-jazz', 'swing', 'bebop', 'cool-jazz', 'hard-bop', 'free-jazz', 'fusion', 'contemporary']:
        print(f'  {era:20s} {era_counts.get(era, 0):4d}')


if __name__ == '__main__':
    main()

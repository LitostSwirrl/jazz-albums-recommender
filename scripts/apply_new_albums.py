#!/usr/bin/env python3
"""
Stage 5a: Merge all enriched album data into src/data/albums.json and update artists.json.
Reads from /tmp/ cache files and produces final data.
"""

import json
import os
import sys
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
ERAS_FILE = os.path.join(DATA_DIR, 'eras.json')

ENRICHED_FILE = '/tmp/enriched_albums.json'
COVERS_FILE = '/tmp/new_album_covers.json'
STREAMING_FILE = '/tmp/new_streaming_links.json'
APPLE_FILE = '/tmp/new_apple_music_links.json'

# Valid era IDs
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
    # Load existing data
    albums = load_json(ALBUMS_FILE, [])
    artists = load_json(ARTISTS_FILE, [])

    # Load enriched albums
    enriched = load_json(ENRICHED_FILE)
    if not enriched:
        print(f'ERROR: {ENRICHED_FILE} not found or empty. Run enrich_album_metadata.py first.')
        sys.exit(1)

    # Load optional supplementary data
    covers = load_json(COVERS_FILE)
    streaming = load_json(STREAMING_FILE)
    apple_links = load_json(APPLE_FILE)

    # Build existing album ID set
    existing_ids = {a['id'] for a in albums}

    # Build artist map
    artist_map = {a['id']: a for a in artists}

    # Track stats
    added = 0
    skipped = 0
    errors = []

    # Process enriched albums
    new_albums = []
    for album_id, data in enriched.items():
        if album_id in existing_ids:
            skipped += 1
            continue

        # Validate required fields
        if not data.get('title') or not data.get('artistId'):
            errors.append(f'{album_id}: missing title or artistId')
            continue

        # Validate era
        era = data.get('era', 'contemporary')
        if era not in VALID_ERAS:
            era = 'contemporary'

        # Build album entry
        album = {
            'id': data['id'],
            'title': data['title'],
            'artist': data['artist'],
            'artistId': data['artistId'],
            'year': data.get('year'),
            'label': data.get('label', 'Unknown'),
            'era': era,
            'genres': data.get('genres', ['jazz']),
            'description': data.get('description', ''),
            'significance': data.get('significance', ''),
            'keyTracks': data.get('keyTracks', []),
        }

        # Add cover art (from covers cache or proxy)
        cover = covers.get(album_id)
        if cover:
            album['coverUrl'] = cover
        else:
            album['coverUrl'] = ''

        # Add streaming links
        stream = streaming.get(album_id, {})
        if isinstance(stream, dict):
            if stream.get('spotifyUrl'):
                album['spotifyUrl'] = stream['spotifyUrl']
            if stream.get('appleMusicUrl'):
                album['appleMusicUrl'] = stream['appleMusicUrl']
            if stream.get('youtubeUrl'):
                album['youtubeUrl'] = stream['youtubeUrl']

        # Apple Music from separate file
        apple = apple_links.get(album_id)
        if apple and 'appleMusicUrl' not in album:
            album['appleMusicUrl'] = apple

        new_albums.append(album)
        added += 1

    # Sort new albums by year (nulls last), then by title
    new_albums.sort(key=lambda a: (a.get('year') or 9999, a['title']))

    # Merge into existing albums list
    albums.extend(new_albums)

    # Sort all albums by year then title
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

    # Validate: check for duplicate IDs
    all_ids = [a['id'] for a in albums]
    duplicates = [aid for aid in set(all_ids) if all_ids.count(aid) > 1]
    if duplicates:
        print(f'WARNING: Duplicate album IDs found: {duplicates}')
        # Remove duplicates (keep first occurrence)
        seen = set()
        deduped = []
        for a in albums:
            if a['id'] not in seen:
                seen.add(a['id'])
                deduped.append(a)
        albums = deduped

    # Validate: all eras are valid
    invalid_eras = [a['id'] for a in albums if a.get('era') not in VALID_ERAS]
    if invalid_eras:
        print(f'WARNING: Albums with invalid eras: {invalid_eras[:10]}')

    # Write updated files
    with open(ALBUMS_FILE, 'w') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)

    with open(ARTISTS_FILE, 'w') as f:
        json.dump(artists, f, indent=2, ensure_ascii=False)

    # Stats
    print(f'\n=== Apply Results ===')
    print(f'New albums added: {added}')
    print(f'Skipped (already exist): {skipped}')
    print(f'Errors: {len(errors)}')
    print(f'Total albums now: {len(albums)}')
    print(f'Artists with updated keyAlbums: {updated_artists}')

    if errors:
        print(f'\nErrors:')
        for e in errors[:20]:
            print(f'  {e}')

    # Album count per artist
    artist_album_count = {}
    for a in albums:
        aid = a.get('artistId', '')
        artist_album_count[aid] = artist_album_count.get(aid, 0) + 1

    # Check coverage
    under_3 = []
    for artist in artists:
        aid = artist['id']
        if aid in SKIP_ARTISTS:
            continue
        count = artist_album_count.get(aid, 0)
        if count < 3:
            under_3.append((artist['name'], count))

    if under_3:
        print(f'\nArtists still under 3 albums ({len(under_3)}):')
        for name, count in sorted(under_3):
            print(f'  {name}: {count}')
    else:
        print(f'\nAll artists have 3+ albums (except skipped)')

    # Coverage stats
    has_cover = sum(1 for a in albums if a.get('coverUrl'))
    has_spotify = sum(1 for a in albums if a.get('spotifyUrl'))
    has_apple = sum(1 for a in albums if a.get('appleMusicUrl'))

    print(f'\nCoverage:')
    print(f'  Cover art: {has_cover}/{len(albums)}')
    print(f'  Spotify: {has_spotify}/{len(albums)}')
    print(f'  Apple Music: {has_apple}/{len(albums)}')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Stage 6: Post-expansion quality verification.
Checks all data integrity after applying expansion albums.
Run after apply_expansion.py.
"""

import json
import os
import sys
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')

VALID_ERAS = {
    'early-jazz', 'swing', 'bebop', 'cool-jazz',
    'hard-bop', 'free-jazz', 'fusion', 'contemporary',
}


def main():
    with open(ALBUMS_FILE) as f:
        albums = json.load(f)
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)

    album_map = {a['id']: a for a in albums}
    artist_map = {a['id']: a for a in artists}
    errors = []
    warnings = []

    print(f'Verifying {len(albums)} albums, {len(artists)} artists...\n')

    # 1. No duplicate album IDs
    ids = [a['id'] for a in albums]
    seen = set()
    for aid in ids:
        if aid in seen:
            errors.append(f'Duplicate album ID: {aid}')
        seen.add(aid)

    # 2. Every album.artistId exists in artists.json
    for a in albums:
        if a['artistId'] not in artist_map:
            errors.append(f'Album {a["id"]}: artistId "{a["artistId"]}" not in artists.json')

    # 3. Required fields present
    required_fields = ['id', 'title', 'artist', 'artistId', 'era', 'genres', 'description', 'significance']
    for a in albums:
        for field in required_fields:
            if field not in a:
                errors.append(f'Album {a["id"]}: missing field "{field}"')
        if not a.get('genres'):
            errors.append(f'Album {a["id"]}: empty genres array')
        if a.get('era') and a['era'] not in VALID_ERAS:
            errors.append(f'Album {a["id"]}: invalid era "{a["era"]}"')

    # 4. Description quality
    short_desc = []
    very_short = []
    for a in albums:
        desc_len = len(a.get('description', ''))
        if desc_len < 80:
            very_short.append((a['id'], desc_len))
        elif desc_len < 120:
            short_desc.append((a['id'], desc_len))

    if very_short:
        for aid, length in very_short[:20]:
            errors.append(f'Album {aid}: description too short ({length} chars)')
    if short_desc:
        for aid, length in short_desc[:10]:
            warnings.append(f'Album {aid}: description could be longer ({length} chars)')

    # 5. No broken keyAlbums refs
    for artist in artists:
        for ka in artist.get('keyAlbums', []):
            if ka not in album_map:
                errors.append(f'Artist {artist["id"]}: keyAlbum "{ka}" not in albums.json')

    # 6. Year reasonable
    for a in albums:
        year = a.get('year')
        if year is not None and (year < 1900 or year > 2026):
            errors.append(f'Album {a["id"]}: unreasonable year {year}')

    # 7. Label check
    empty_label = [a['id'] for a in albums if not a.get('label') or a['label'] == '']
    if empty_label:
        for aid in empty_label[:10]:
            warnings.append(f'Album {aid}: empty label (should be "Unknown")')

    # 8. coverUrl format check
    for a in albums:
        cover = a.get('coverUrl', '')
        if cover and not (cover.startswith('https://') or cover.startswith('http://')):
            warnings.append(f'Album {a["id"]}: invalid coverUrl format')

    # 9. Streaming URL format check
    for a in albums:
        for key in ('spotifyUrl', 'appleMusicUrl', 'youtubeMusicUrl', 'youtubeUrl'):
            url = a.get(key, '')
            if url and not url.startswith('http'):
                errors.append(f'Album {a["id"]}: invalid {key} format')

    # 10. Era distribution
    era_counts = {}
    for a in albums:
        era = a.get('era', 'unknown')
        era_counts[era] = era_counts.get(era, 0) + 1

    sparse_eras = [(era, count) for era, count in era_counts.items()
                   if count < 15 and era in VALID_ERAS]
    for era, count in sparse_eras:
        warnings.append(f'Era {era} has only {count} albums (consider adding more)')

    # 11. Total album count
    total = len(albums)
    if total < 900:
        warnings.append(f'Total albums ({total}) below 900 target')
    elif total > 1100:
        warnings.append(f'Total albums ({total}) above 1100 — may be too many')

    # === Report ===
    print('=' * 60)
    print('VERIFICATION RESULTS')
    print('=' * 60)

    if errors:
        print(f'\n ERRORS ({len(errors)}):')
        for e in errors:
            print(f'  {e}')
    else:
        print(f'\n No errors found!')

    if warnings:
        print(f'\n WARNINGS ({len(warnings)}):')
        for w in warnings:
            print(f'  {w}')
    else:
        print(f'\n No warnings!')

    # Stats
    print(f'\n--- Stats ---')
    print(f'Total albums: {len(albums)}')
    print(f'Total artists: {len(artists)}')

    has_cover = sum(1 for a in albums if a.get('coverUrl'))
    has_spotify = sum(1 for a in albums if a.get('spotifyUrl'))
    has_apple = sum(1 for a in albums if a.get('appleMusicUrl'))
    has_wiki = sum(1 for a in albums if a.get('wikipedia'))
    has_desc_200 = sum(1 for a in albums if len(a.get('description', '')) >= 200)

    print(f'Cover art: {has_cover}/{len(albums)} ({has_cover*100//len(albums)}%)')
    print(f'Spotify: {has_spotify}/{len(albums)} ({has_spotify*100//len(albums)}%)')
    print(f'Apple Music: {has_apple}/{len(albums)} ({has_apple*100//len(albums)}%)')
    print(f'Wikipedia: {has_wiki}/{len(albums)} ({has_wiki*100//len(albums)}%)')
    print(f'Descriptions >= 200 chars: {has_desc_200}/{len(albums)} ({has_desc_200*100//len(albums)}%)')

    print(f'\nEra distribution:')
    for era in ['early-jazz', 'swing', 'bebop', 'cool-jazz', 'hard-bop', 'free-jazz', 'fusion', 'contemporary']:
        count = era_counts.get(era, 0)
        pct = count * 100 // len(albums)
        bar = '#' * (count // 5)
        print(f'  {era:20s} {count:4d} ({pct:2d}%) {bar}')

    # Genre distribution (top 15)
    genre_counts = {}
    for a in albums:
        for g in a.get('genres', []):
            genre_counts[g] = genre_counts.get(g, 0) + 1
    print(f'\nTop 15 genres:')
    for genre, count in sorted(genre_counts.items(), key=lambda x: -x[1])[:15]:
        print(f'  {genre:30s} {count:4d}')

    # Artist album count distribution
    artist_album_count = {}
    for a in albums:
        aid = a.get('artistId', '')
        artist_album_count[aid] = artist_album_count.get(aid, 0) + 1

    top_artists = sorted(artist_album_count.items(), key=lambda x: -x[1])[:15]
    print(f'\nTop 15 artists by album count:')
    for aid, count in top_artists:
        name = artist_map.get(aid, {}).get('name', aid)
        print(f'  {name:30s} {count:4d}')

    # Final verdict
    print(f'\n{"=" * 60}')
    if errors:
        print(f'FAILED: {len(errors)} errors found. Fix before deploying.')
        sys.exit(1)
    else:
        print(f'PASSED: All checks OK ({len(warnings)} warnings)')
        sys.exit(0)


if __name__ == '__main__':
    main()

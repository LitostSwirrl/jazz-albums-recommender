#!/usr/bin/env python3
"""
Post-fix data quality verification script.
Run after all fix scripts to check for remaining issues.
"""

import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')


def load_data():
    with open(os.path.join(DATA_DIR, 'albums.json')) as f:
        albums = json.load(f)
    with open(os.path.join(DATA_DIR, 'artists.json')) as f:
        artists = json.load(f)
    with open(os.path.join(DATA_DIR, 'connections.json')) as f:
        connections = json.load(f)
    with open(os.path.join(DATA_DIR, 'historicalEvents.json')) as f:
        events = json.load(f)
    return albums, artists, connections, events


def check_corrupted_descriptions(albums):
    """Check for known corrupted description keywords."""
    bad_keywords = [
        'Olivia Newton-John', 'weather forecasting', 'Stargate SG-1',
        'Cocteau Twins', 'Fall Out Boy', 'blood transfusion',
        'BBC television', 'may refer to:', 'disambiguation',
        'video game', 'Ramsey Lewis album',
    ]
    issues = []
    for a in albums:
        desc = a.get('description', '')
        for kw in bad_keywords:
            if kw.lower() in desc.lower():
                issues.append(f"  {a['id']}: contains '{kw}'")
    return issues


def check_broken_refs(albums, artists):
    """Check for broken keyAlbums references."""
    album_ids = {a['id'] for a in albums}
    artist_ids = {a['id'] for a in artists}
    issues = []

    for ar in artists:
        for ka in ar.get('keyAlbums', []):
            if ka not in album_ids:
                issues.append(f"  {ar['id']}.keyAlbums: '{ka}' not in albums")

    for a in albums:
        if a.get('artistId') and a['artistId'] not in artist_ids:
            issues.append(f"  {a['id']}.artistId: '{a['artistId']}' not in artists")

    return issues


def check_buster_smith(albums, artists):
    """Check Buster Smith data integrity."""
    issues = []
    bs = next((a for a in artists if a['id'] == 'buster-smith'), None)
    if bs:
        if len(bs.get('eras', [])) > 2:
            issues.append(f"  buster-smith has {len(bs['eras'])} eras (should be 2)")
        if 'musician' in bs.get('instruments', []):
            issues.append(f"  buster-smith still has 'musician' instrument")

    es_albums = [a['id'] for a in albums if a['id'] in ('roman-candle', 'figure-8', 'basement-tapes-unfinishedsuppressed')]
    if es_albums:
        issues.append(f"  Elliott Smith albums still present: {es_albums}")

    return issues


def check_genre_normalization(albums):
    """Check for genre normalization issues."""
    forbidden = {'ECM jazz', 'AACM', 'Latin jazz', 'jazz funk', 'fusion', 'avant-garde', 'Afrofuturism', 'Afro-jazz'}
    issues = []
    for a in albums:
        for g in a.get('genres', []):
            if g in forbidden:
                issues.append(f"  {a['id']}: genre '{g}'")
    return issues


def check_label_normalization(albums):
    """Check for label normalization issues."""
    forbidden = {'ECM Records', 'impulse!', 'Concord Records', 'Concord', 'Warner Bros.', 'enja'}
    issues = []
    for a in albums:
        if a.get('label') in forbidden:
            issues.append(f"  {a['id']}: label '{a['label']}'")
    return issues


def coverage_stats(albums, artists, connections):
    """Print coverage statistics."""
    total = len(albums)

    has_cover = sum(1 for a in albums if a.get('coverUrl'))
    has_spotify = sum(1 for a in albums if a.get('spotifyUrl'))
    has_apple = sum(1 for a in albums if a.get('appleMusicUrl'))
    has_youtube = sum(1 for a in albums if a.get('youtubeUrl'))
    has_wiki = sum(1 for a in albums if a.get('wikipedia'))
    has_all_streaming = sum(1 for a in albums if a.get('spotifyUrl') and a.get('appleMusicUrl') and a.get('youtubeUrl'))
    no_streaming = sum(1 for a in albums if not a.get('spotifyUrl') and not a.get('appleMusicUrl') and not a.get('youtubeUrl'))
    null_year = sum(1 for a in albums if a.get('year') is None)
    unknown_label = sum(1 for a in albums if a.get('label') in ('Unknown', '[no label]'))
    short_desc = sum(1 for a in albums if len(a.get('description', '')) < 200)
    no_keytracks = sum(1 for a in albums if not a.get('keyTracks'))

    has_image = sum(1 for a in artists if a.get('imageUrl'))
    short_bio = sum(1 for a in artists if len(a.get('bio', '')) < 100)
    verified = sum(1 for c in connections if c.get('verified'))

    print(f'\n=== Coverage Statistics ===')
    print(f'Albums: {total}')
    print(f'  Cover art:       {has_cover}/{total} ({100*has_cover//total}%)')
    print(f'  Spotify:         {has_spotify}/{total} ({100*has_spotify//total}%)')
    print(f'  Apple Music:     {has_apple}/{total} ({100*has_apple//total}%)')
    print(f'  YouTube:         {has_youtube}/{total} ({100*has_youtube//total}%)')
    print(f'  Wikipedia:       {has_wiki}/{total} ({100*has_wiki//total}%)')
    print(f'  All 3 streaming: {has_all_streaming}/{total} ({100*has_all_streaming//total}%)')
    print(f'  No streaming:    {no_streaming}/{total} ({100*no_streaming//total}%)')
    print(f'  Null year:       {null_year}')
    print(f'  Unknown label:   {unknown_label}')
    print(f'  Short desc:      {short_desc}')
    print(f'  No keyTracks:    {no_keytracks}')
    print(f'\nArtists: {len(artists)}')
    print(f'  Has image:       {has_image}/{len(artists)} ({100*has_image//len(artists)}%)')
    print(f'  Short bio:       {short_bio}')
    print(f'\nConnections: {len(connections)}')
    print(f'  Verified:        {verified}/{len(connections)} ({100*verified//len(connections)}%)')


def main():
    albums, artists, connections, events = load_data()

    all_issues = []
    checks = [
        ('Corrupted descriptions', check_corrupted_descriptions(albums)),
        ('Broken references', check_broken_refs(albums, artists)),
        ('Buster Smith', check_buster_smith(albums, artists)),
        ('Genre normalization', check_genre_normalization(albums)),
        ('Label normalization', check_label_normalization(albums)),
    ]

    passed = 0
    failed = 0
    for name, issues in checks:
        if issues:
            print(f'FAIL: {name}')
            for i in issues:
                print(i)
            failed += 1
        else:
            print(f'PASS: {name}')
            passed += 1

    coverage_stats(albums, artists, connections)

    print(f'\n=== Results: {passed} passed, {failed} failed ===')
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

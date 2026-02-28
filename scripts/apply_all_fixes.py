#!/usr/bin/env python3
"""
Apply ALL cached fixes to albums.json in one pass.
This avoids concurrent write conflicts by merging all caches into a single write.

Reads from:
- /tmp/album_descriptions_fix.json (descriptions + wikipedia URLs)
- /tmp/missing_covers.json (cover art)
- /tmp/streaming_links.json (Spotify, YouTube from MusicBrainz)
- /tmp/apple_music_links_v2.json (Apple Music from iTunes)
- /tmp/album_wikipedia.json (Wikipedia URLs)

Also re-applies normalization fixes (genres, labels, eras) to ensure
they're not overwritten by other scripts that loaded the pre-normalization data.
"""

import json
import os
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')

# Cache files
DESC_CACHE = '/tmp/album_descriptions_fix.json'
COVERS_CACHE = '/tmp/missing_covers.json'
STREAMING_CACHE = '/tmp/streaming_links.json'
APPLE_CACHE = '/tmp/apple_music_links_v2.json'
WIKI_CACHE = '/tmp/album_wikipedia.json'

# Normalization maps (same as normalize_data.py)
GENRE_FIXES = {
    'jazz funk': 'jazz-funk',
    'Latin jazz': 'latin jazz',
    'fusion': 'jazz fusion',
    'avant-garde': 'avant-garde jazz',
    'ECM jazz': 'contemporary jazz',
    'AACM': 'avant-garde jazz',
    'Afrofuturism': 'afrofuturism',
    'Afro-jazz': 'afro jazz',
    'jazz-rock': 'jazz rock',
    'hip-hop jazz': 'jazz hip-hop',
}

LABEL_FIXES = {
    'ECM Records': 'ECM',
    'impulse!': 'Impulse!',
    'Concord Records': 'Concord Jazz',
    'Concord': 'Concord Jazz',
    'Warner Bros.': 'Warner Bros. Records',
    'HighNote Records, Inc.': 'HighNote Records',
    'enja': 'Enja Records',
}

ERA_FIXES = {
    'facing-you': 'fusion',
    'solo-concerts': 'fusion',
    'belonging': 'fusion',
    'the-koln-concert': 'fusion',
    'conference-of-the-birds': 'free-jazz',
    'witchi-tai-to': 'fusion',
    'gateway': 'fusion',
    'gnu-high': 'free-jazz',
    'azimuth': 'free-jazz',
    'django': 'bebop',
    'ellington-at-newport': 'hard-bop',
}


def load_cache(path):
    """Load JSON cache if it exists."""
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        print(f'  Loaded {path}: {len(data)} entries')
        return data
    print(f'  Not found: {path}')
    return {}


def fix_esp_disk(label):
    """Fix ESP-Disk Unicode variants."""
    if 'ESP' in label and 'Disk' in label:
        return 'ESP-Disk'
    return label


def main():
    with open(ALBUMS_FILE) as f:
        albums = json.load(f)
    print(f'Loaded {len(albums)} albums')

    # Load all caches
    print('\nLoading caches:')
    desc_cache = load_cache(DESC_CACHE)
    covers_cache = load_cache(COVERS_CACHE)
    streaming_cache = load_cache(STREAMING_CACHE)
    apple_cache = load_cache(APPLE_CACHE)
    wiki_cache = load_cache(WIKI_CACHE)

    # Counters
    stats = {
        'desc_updated': 0,
        'wiki_added': 0,
        'covers_added': 0,
        'spotify_added': 0,
        'apple_added': 0,
        'youtube_added': 0,
        'genre_fixed': 0,
        'label_fixed': 0,
        'era_fixed': 0,
    }

    for album in albums:
        aid = album['id']

        # 1. Apply description fixes
        if aid in desc_cache:
            entry = desc_cache[aid]
            new_desc = entry.get('description', '')
            if new_desc and len(new_desc) > len(album.get('description', '')):
                album['description'] = new_desc
                stats['desc_updated'] += 1
            wiki_url = entry.get('wikipedia', '')
            if wiki_url and not album.get('wikipedia'):
                album['wikipedia'] = wiki_url
                stats['wiki_added'] += 1

        # 2. Apply cover art
        if aid in covers_cache and not album.get('coverUrl'):
            cover = covers_cache[aid]
            if isinstance(cover, str) and cover:
                album['coverUrl'] = cover
                stats['covers_added'] += 1
            elif isinstance(cover, dict) and cover.get('coverUrl'):
                album['coverUrl'] = cover['coverUrl']
                stats['covers_added'] += 1

        # 3. Apply streaming links from MusicBrainz
        stream = streaming_cache.get(aid, {})
        if isinstance(stream, dict):
            if stream.get('spotifyUrl') and not album.get('spotifyUrl'):
                album['spotifyUrl'] = stream['spotifyUrl']
                stats['spotify_added'] += 1
            if stream.get('appleMusicUrl') and not album.get('appleMusicUrl'):
                album['appleMusicUrl'] = stream['appleMusicUrl']
                stats['apple_added'] += 1
            if stream.get('youtubeUrl') and not album.get('youtubeUrl'):
                album['youtubeUrl'] = stream['youtubeUrl']
                stats['youtube_added'] += 1
            if stream.get('youtubeMusicUrl') and not album.get('youtubeUrl'):
                album['youtubeUrl'] = stream['youtubeMusicUrl']
                stats['youtube_added'] += 1

        # 4. Apply Apple Music links
        am = apple_cache.get(aid)
        if am and not album.get('appleMusicUrl'):
            if isinstance(am, str):
                album['appleMusicUrl'] = am
                stats['apple_added'] += 1
            elif isinstance(am, dict) and am.get('url'):
                album['appleMusicUrl'] = am['url']
                stats['apple_added'] += 1

        # 5. Apply Wikipedia URLs from dedicated cache
        if aid in wiki_cache and not album.get('wikipedia'):
            wiki_url = wiki_cache[aid]
            if wiki_url:
                album['wikipedia'] = wiki_url
                stats['wiki_added'] += 1

        # 6. Re-apply genre normalization
        if album.get('genres'):
            new_genres = []
            for g in album['genres']:
                fixed = GENRE_FIXES.get(g, g)
                if fixed not in new_genres:
                    new_genres.append(fixed)
                    if fixed != g:
                        stats['genre_fixed'] += 1
            album['genres'] = new_genres

        # 7. Re-apply label normalization
        label = album.get('label', '')
        fixed_label = LABEL_FIXES.get(label, fix_esp_disk(label))
        if fixed_label != label:
            album['label'] = fixed_label
            stats['label_fixed'] += 1

        # 8. Re-apply era fixes
        if aid in ERA_FIXES:
            if album['era'] != ERA_FIXES[aid]:
                album['era'] = ERA_FIXES[aid]
                stats['era_fixed'] += 1

    # Write back
    with open(ALBUMS_FILE, 'w') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)

    # Coverage stats
    total = len(albums)
    has_cover = sum(1 for a in albums if a.get('coverUrl'))
    has_spotify = sum(1 for a in albums if a.get('spotifyUrl'))
    has_apple = sum(1 for a in albums if a.get('appleMusicUrl'))
    has_youtube = sum(1 for a in albums if a.get('youtubeUrl'))
    has_wiki = sum(1 for a in albums if a.get('wikipedia'))
    short_desc = sum(1 for a in albums if len(a.get('description', '')) < 200)

    print(f'\n=== Applied Changes ===')
    for key, val in stats.items():
        print(f'  {key}: {val}')

    print(f'\n=== Coverage ===')
    print(f'  Cover art:    {has_cover}/{total} ({100*has_cover//total}%)')
    print(f'  Spotify:      {has_spotify}/{total} ({100*has_spotify//total}%)')
    print(f'  Apple Music:  {has_apple}/{total} ({100*has_apple//total}%)')
    print(f'  YouTube:      {has_youtube}/{total} ({100*has_youtube//total}%)')
    print(f'  Wikipedia:    {has_wiki}/{total} ({100*has_wiki//total}%)')
    print(f'  Short desc:   {short_desc}/{total} ({100*short_desc//total}%)')


if __name__ == '__main__':
    main()

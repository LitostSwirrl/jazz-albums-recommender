#!/usr/bin/env python3
"""
Normalize genre, label, and era inconsistencies in albums.json.
All deterministic string replacements — no API calls.
"""

import json
import os

ALBUMS_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'src', 'data', 'albums.json'
)

# ── Genre normalization ──────────────────────────────────────────────────────
GENRE_FIXES = {
    'jazz funk': 'jazz-funk',           # standardize to hyphenated
    'Latin jazz': 'latin jazz',         # lowercase
    'fusion': 'jazz fusion',            # prefer full term
    'avant-garde': 'avant-garde jazz',  # add 'jazz'
    'ECM jazz': 'contemporary jazz',    # not a real genre
    'AACM': 'avant-garde jazz',         # org not genre
    'Afrofuturism': 'afrofuturism',     # lowercase
    'Afro-jazz': 'afro jazz',           # no hyphen
    'jazz-rock': 'jazz rock',           # space separated
    'hip-hop jazz': 'jazz hip-hop',     # standardize order
}

# ── Label normalization ──────────────────────────────────────────────────────
LABEL_FIXES = {
    'ECM Records': 'ECM',
    'impulse!': 'Impulse!',
    'Concord Records': 'Concord Jazz',
    'Concord': 'Concord Jazz',
    'Warner Bros.': 'Warner Bros. Records',
    'HighNote Records, Inc.': 'HighNote Records',
    'enja': 'Enja Records',
}

# ── Era reclassification ────────────────────────────────────────────────────
ERA_FIXES = {
    # Keith Jarrett 1972-1975 → fusion
    'facing-you': 'fusion',
    'solo-concerts': 'fusion',
    'belonging': 'fusion',
    'the-koln-concert': 'fusion',
    # Other ECM 1972-1977 → fusion or free-jazz
    'conference-of-the-birds': 'free-jazz',
    'witchi-tai-to': 'fusion',
    'gateway': 'fusion',
    'gnu-high': 'free-jazz',
    'azimuth': 'free-jazz',
    # Misplaced swing-era albums
    'django': 'bebop',                   # 1949, after swing era
    'ellington-at-newport': 'hard-bop',  # 1956, squarely hard-bop era
}


def normalize_genres(album, stats):
    """Apply genre fixes to a single album's genres array."""
    if 'genres' not in album:
        return
    new_genres = []
    for genre in album['genres']:
        if genre in GENRE_FIXES:
            replacement = GENRE_FIXES[genre]
            stats['genre'][genre] = stats['genre'].get(genre, 0) + 1
            new_genres.append(replacement)
        else:
            new_genres.append(genre)
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for g in new_genres:
        if g not in seen:
            seen.add(g)
            deduped.append(g)
    if len(deduped) < len(new_genres):
        stats['genre_dedup'] = stats.get('genre_dedup', 0) + 1
    album['genres'] = deduped


def normalize_label(album, stats):
    """Apply label fixes to a single album."""
    label = album.get('label', '')
    if label in LABEL_FIXES:
        stats['label'][label] = stats['label'].get(label, 0) + 1
        album['label'] = LABEL_FIXES[label]
    # ESP-Disk Unicode variants: normalize any ESP + non-ASCII to "ESP-Disk"
    elif 'ESP' in label and label != 'ESP-Disk':
        stats['label'][label] = stats['label'].get(label, 0) + 1
        album['label'] = 'ESP-Disk'


def normalize_era(album, stats):
    """Apply era reclassification to specific albums by ID."""
    aid = album.get('id', '')
    if aid in ERA_FIXES:
        old_era = album.get('era', '')
        new_era = ERA_FIXES[aid]
        if old_era != new_era:
            stats['era'][f"{aid}: {old_era} → {new_era}"] = 1
            album['era'] = new_era


def main():
    with open(ALBUMS_PATH, 'r', encoding='utf-8') as f:
        albums = json.load(f)

    stats = {
        'genre': {},
        'label': {},
        'era': {},
    }

    for album in albums:
        normalize_genres(album, stats)
        normalize_label(album, stats)
        normalize_era(album, stats)

    with open(ALBUMS_PATH, 'w', encoding='utf-8') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)
        f.write('\n')

    # ── Summary ──────────────────────────────────────────────────────────────
    print('=' * 60)
    print('DATA NORMALIZATION SUMMARY')
    print('=' * 60)

    print('\n── Genre fixes ──')
    genre_total = 0
    for old_val, count in sorted(stats['genre'].items()):
        new_val = GENRE_FIXES[old_val]
        print(f'  "{old_val}" → "{new_val}": {count} albums')
        genre_total += count
    if stats.get('genre_dedup'):
        print(f'  (deduplication removed genres in {stats["genre_dedup"]} albums)')
    print(f'  Total genre fixes: {genre_total}')

    print('\n── Label fixes ──')
    label_total = 0
    for old_val, count in sorted(stats['label'].items()):
        print(f'  "{old_val}" → normalized: {count} albums')
        label_total += count
    print(f'  Total label fixes: {label_total}')

    print('\n── Era fixes ──')
    era_total = 0
    for desc, count in sorted(stats['era'].items()):
        print(f'  {desc}')
        era_total += count
    print(f'  Total era fixes: {era_total}')

    grand_total = genre_total + label_total + era_total
    print(f'\n{"=" * 60}')
    print(f'GRAND TOTAL: {grand_total} changes across {len(albums)} albums')
    print(f'{"=" * 60}')


if __name__ == '__main__':
    main()

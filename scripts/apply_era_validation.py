#!/usr/bin/env python3
"""
Apply externally-validated era assignments to albums.json.

Reads cached results from:
  /tmp/era_wikidata_cache.json  (primary)
  /tmp/era_lastfm_cache.json    (secondary, optional)
  /tmp/era_spotify_cache.json   (tertiary, optional)

Dry-run by default. Pass --apply to write changes.

Usage:
  python3 apply_era_validation.py          # dry-run
  python3 apply_era_validation.py --apply  # write changes
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')
ERAS_FILE = os.path.join(DATA_DIR, 'eras.json')

CACHE_FILES = [
    ('/tmp/era_wikidata_cache.json', 'wikidata', 'high'),
    ('/tmp/era_lastfm_cache.json', 'lastfm', 'high'),
    ('/tmp/era_spotify_cache.json', 'spotify', 'medium'),
]


def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')


def main():
    apply_mode = '--apply' in sys.argv

    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    with open(ERAS_FILE) as f:
        eras_data = {e['id']: e for e in json.load(f)}

    era_ranges = {eid: (e['years'][0], e['years'][1]) for eid, e in eras_data.items()}

    # Load all caches in priority order
    caches = []
    for path, source_name, default_confidence in CACHE_FILES:
        data = load_json(path)
        if data:
            resolved_count = sum(1 for v in data.values() if v.get('status') == 'resolved')
            print(f'Loaded {source_name}: {len(data)} entries, {resolved_count} resolved')
            caches.append((data, source_name, default_confidence))
        else:
            print(f'Skipped {source_name}: cache not found at {path}')

    if not caches:
        print('No caches found. Run fetch scripts first.')
        return

    # Merge: pick first resolved result per album (priority order)
    merged = {}
    for album in albums:
        aid = album['id']
        for cache_data, source_name, default_confidence in caches:
            entry = cache_data.get(aid, {})
            if entry.get('status') == 'resolved':
                merged[aid] = {
                    'suggested_era': entry['suggested_era'],
                    'confidence': entry.get('confidence', default_confidence),
                    'source': source_name,
                    'genres': entry.get('genres', []),
                }
                break

    print(f'\nAlbums with external era suggestion: {len(merged)}')

    # Compute changes
    changes = []
    skipped_same = 0
    skipped_low_confidence = 0
    skipped_year_range = 0

    for album in albums:
        aid = album['id']
        if aid not in merged:
            continue

        suggestion = merged[aid]
        current_era = album['era']
        suggested_era = suggestion['suggested_era']
        confidence = suggestion['confidence']
        year = album.get('year') or 0

        # No change needed
        if suggested_era == current_era:
            skipped_same += 1
            continue

        # Safety: non-contemporary eras require high confidence to change
        if current_era != 'contemporary' and confidence != 'high':
            skipped_low_confidence += 1
            continue

        # Year-range sanity check (15-year buffer)
        if year > 0 and suggested_era in era_ranges:
            era_start, era_end = era_ranges[suggested_era]
            if year < (era_start - 15) or (year > (era_end + 15) and suggested_era != 'contemporary'):
                skipped_year_range += 1
                continue

        changes.append({
            'album_id': aid,
            'title': album['title'],
            'artist': album.get('artist', ''),
            'year': year,
            'current_era': current_era,
            'suggested_era': suggested_era,
            'source': suggestion['source'],
            'confidence': confidence,
            'genres': suggestion['genres'],
        })

    # Print results
    print(f'\n=== Era Validation Results ===')
    print(f'External suggestions: {len(merged)}')
    print(f'Already correct:     {skipped_same}')
    print(f'Low confidence skip: {skipped_low_confidence}')
    print(f'Year-range skip:     {skipped_year_range}')
    print(f'Proposed changes:    {len(changes)}')

    if changes:
        # Group by source
        by_source = {}
        for c in changes:
            by_source.setdefault(c['source'], []).append(c)

        for source, source_changes in by_source.items():
            print(f'\n--- Source: {source} ({len(source_changes)} changes) ---')
            # Group by transition
            transitions = Counter((c['current_era'], c['suggested_era']) for c in source_changes)
            print('Transitions:')
            for (old, new), count in transitions.most_common():
                print(f'  {old} -> {new}: {count}')

            print('\nDetails:')
            for c in sorted(source_changes, key=lambda x: (x['artist'], x['year'])):
                print(f'  [{c["current_era"]} -> {c["suggested_era"]}] '
                      f'{c["artist"]} - "{c["title"]}" ({c["year"]})')
                print(f'    genres: {c["genres"]}')

        # Era distribution before/after
        current_dist = Counter(a['era'] for a in albums)
        after_dist = Counter(current_dist)
        for c in changes:
            after_dist[c['current_era']] -= 1
            after_dist[c['suggested_era']] += 1

        print(f'\n=== Era Distribution ===')
        print(f'{"Era":<15} {"Before":>8} {"After":>8} {"Delta":>8}')
        print('-' * 41)
        for era_id in ['early-jazz', 'swing', 'bebop', 'cool-jazz',
                       'hard-bop', 'free-jazz', 'fusion', 'contemporary']:
            before = current_dist.get(era_id, 0)
            after = after_dist.get(era_id, 0)
            delta = after - before
            sign = '+' if delta > 0 else ''
            print(f'{era_id:<15} {before:>8} {after:>8} {sign + str(delta):>8}')

        if apply_mode:
            # Apply changes
            album_map = {a['id']: a for a in albums}
            for c in changes:
                album_map[c['album_id']]['era'] = c['suggested_era']
            save_json(ALBUMS_FILE, albums)
            print(f'\nApplied {len(changes)} era changes to albums.json')
        else:
            print(f'\nDry run. Use --apply to write {len(changes)} changes.')
    else:
        print('\nNo changes to apply.')


if __name__ == '__main__':
    main()

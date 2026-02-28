#!/usr/bin/env python3
"""
Audit and fix bidirectional consistency in artist influence data.
If A lists B in 'influences', B should list A in 'influencedBy' (and vice versa).
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')


def main():
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)

    artist_map = {a['id']: a for a in artists}
    artist_ids = set(artist_map.keys())

    print(f'Total artists: {len(artists)}')

    # 1. Check for dangling references
    dangling = set()
    for a in artists:
        for ref in a.get('influences', []) + a.get('influencedBy', []):
            if ref not in artist_ids:
                dangling.add(ref)

    if dangling:
        print(f'\nWARNING: {len(dangling)} dangling references still exist:')
        for d in sorted(dangling):
            print(f'  - {d}')
    else:
        print('\nNo dangling references.')

    # 2. Fix bidirectional mismatches
    fixes_made = 0

    # If A influences B, then B should have A in influencedBy
    for a in artists:
        for inf_id in list(a.get('influences', [])):
            if inf_id in artist_ids:
                target = artist_map[inf_id]
                if a['id'] not in target.get('influencedBy', []):
                    target.setdefault('influencedBy', []).append(a['id'])
                    fixes_made += 1
                    print(f'  FIX: Added {a["id"]} to {inf_id}.influencedBy')

    # If A is influencedBy B, then B should have A in influences
    for a in artists:
        for inf_by_id in list(a.get('influencedBy', [])):
            if inf_by_id in artist_ids:
                source = artist_map[inf_by_id]
                if a['id'] not in source.get('influences', []):
                    source.setdefault('influences', []).append(a['id'])
                    fixes_made += 1
                    print(f'  FIX: Added {a["id"]} to {inf_by_id}.influences')

    print(f'\nBidirectional fixes made: {fixes_made}')

    # 3. Remove duplicate entries
    dedup_count = 0
    for a in artists:
        orig_inf = len(a.get('influences', []))
        a['influences'] = list(dict.fromkeys(a.get('influences', [])))
        orig_by = len(a.get('influencedBy', []))
        a['influencedBy'] = list(dict.fromkeys(a.get('influencedBy', [])))
        dedup_count += (orig_inf - len(a['influences'])) + (orig_by - len(a['influencedBy']))

    if dedup_count:
        print(f'Deduplicated entries removed: {dedup_count}')

    # 4. Final stats
    total_inf = sum(len(a.get('influences', [])) for a in artists)
    total_by = sum(len(a.get('influencedBy', [])) for a in artists)
    edges = set()
    for a in artists:
        for inf in a.get('influences', []):
            edges.add((a['id'], inf))
        for inf_by in a.get('influencedBy', []):
            edges.add((inf_by, a['id']))

    print(f'\n=== Final Stats ===')
    print(f'Total artists: {len(artists)}')
    print(f'Total influence entries: {total_inf}')
    print(f'Total influencedBy entries: {total_by}')
    print(f'Unique directed edges: {len(edges)}')

    # Verify bidirectional consistency
    mismatches = 0
    for a in artists:
        for inf in a.get('influences', []):
            if inf in artist_ids:
                target = artist_map[inf]
                if a['id'] not in target.get('influencedBy', []):
                    mismatches += 1
        for inf_by in a.get('influencedBy', []):
            if inf_by in artist_ids:
                source = artist_map[inf_by]
                if a['id'] not in source.get('influences', []):
                    mismatches += 1

    print(f'Remaining mismatches: {mismatches}')

    # Write updated file
    with open(ARTISTS_FILE, 'w') as f:
        json.dump(artists, f, indent=2, ensure_ascii=False)

    print(f'\nUpdated: {ARTISTS_FILE}')


if __name__ == '__main__':
    main()

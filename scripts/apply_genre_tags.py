#!/usr/bin/env python3
"""
Normalize and merge genre tags from MusicBrainz + Last.fm into albums.json.

Merge strategy:
  - Union: add new genres from external sources, don't replace existing
  - Cap at 4 genres per album
  - Priority: MusicBrainz > Last.fm album-level > Last.fm artist-level > existing
  - Deduplicate via normalization map
  - Keep ~33 unique genres total

Dry-run by default. Use --apply to write changes.

Usage:
  python3 apply_genre_tags.py          # dry-run
  python3 apply_genre_tags.py --apply  # write to albums.json
"""

import json
import os
import sys
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')
MB_CACHE = '/tmp/mb_genre_tags_cache.json'
LASTFM_CACHE = '/tmp/lastfm_genre_tags_cache.json'

MAX_GENRES_PER_ALBUM = 4

# Final normalization: ensure consistent genre names
GENRE_NORMALIZE = {
    'bebop': 'bebop',
    'bop': 'bebop',
    'be-bop': 'bebop',
    'hard bop': 'hard bop',
    'hardbop': 'hard bop',
    'hard-bop': 'hard bop',
    'cool jazz': 'cool jazz',
    'west coast jazz': 'cool jazz',
    'free jazz': 'free jazz',
    'avant-garde jazz': 'avant-garde jazz',
    'avant-garde music': 'avant-garde jazz',
    'avant-garde': 'avant-garde jazz',
    'avant garde': 'avant-garde jazz',
    'free improvisation': 'free improvisation',
    'jazz fusion': 'jazz fusion',
    'fusion': 'jazz fusion',
    'jazz-rock': 'jazz fusion',
    'jazz rock': 'jazz fusion',
    'post-bop': 'post-bop',
    'post bop': 'post-bop',
    'modal jazz': 'modal jazz',
    'soul jazz': 'soul jazz',
    'latin jazz': 'latin jazz',
    'afro-cuban jazz': 'latin jazz',
    'swing music': 'swing',
    'swing': 'swing',
    'big band': 'big band',
    'big band music': 'big band',
    'dixieland': 'dixieland',
    'new orleans jazz': 'early jazz',
    'early jazz': 'early jazz',
    'spiritual jazz': 'spiritual jazz',
    'vocal jazz': 'vocal jazz',
    'smooth jazz': 'smooth jazz',
    'contemporary jazz': 'contemporary jazz',
    'jazz-funk': 'jazz-funk',
    'jazz funk': 'jazz-funk',
    'orchestral jazz': 'orchestral jazz',
    'third stream': 'orchestral jazz',
    'chamber jazz': 'chamber jazz',
    'blues': 'blues',
    'loft jazz': 'loft jazz',
    'african jazz': 'African jazz',
    'world music': 'world jazz',
    'world jazz': 'world jazz',
    'brazilian jazz': 'Brazilian jazz',
    'bossa nova': 'bossa nova',
    'experimental music': 'experimental',
    'experimental': 'experimental',
    'piano trio': 'piano trio',
    'acid jazz': 'acid jazz',
    'nu jazz': 'contemporary jazz',
    'afrobeat': 'African jazz',
    'electric jazz': 'jazz fusion',
    'crossover jazz': 'jazz fusion',
    'neo-bop': 'post-bop',
    'gypsy jazz': 'swing',
    'trad jazz': 'early jazz',
    'traditional jazz': 'early jazz',
}

# Genres to skip entirely
SKIP_GENRES = {'jazz', 'jazz music', None}


def normalize_genre(genre):
    """Normalize a genre string to our canonical form."""
    lower = genre.lower().strip()
    normalized = GENRE_NORMALIZE.get(lower)
    if normalized:
        return normalized
    # If already a known canonical genre (case-insensitive match)
    canonical = {v for v in GENRE_NORMALIZE.values() if v}
    for c in canonical:
        if c.lower() == lower:
            return c
    return None  # unknown genre, skip


def load_cache(path):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def main():
    apply_mode = '--apply' in sys.argv

    with open(ALBUMS_FILE) as f:
        albums = json.load(f)

    mb_cache = load_cache(MB_CACHE)
    lastfm_cache = load_cache(LASTFM_CACHE)

    print(f'Albums: {len(albums)}')
    print(f'MusicBrainz cache: {len(mb_cache)} entries')
    print(f'Last.fm cache: {len(lastfm_cache)} entries')
    print(f'Mode: {"APPLY" if apply_mode else "DRY-RUN"}')
    print()

    # Collect before stats
    before_counts = Counter()
    before_genre_dist = Counter()
    single_genre = 0
    for a in albums:
        n = len(a['genres'])
        before_counts[n] += 1
        if n == 1:
            single_genre += 1
        for g in a['genres']:
            before_genre_dist[g] += 1

    print(f'=== BEFORE ===')
    print(f'Genre count distribution: {dict(sorted(before_counts.items()))}')
    print(f'Albums with 1 genre: {single_genre}')
    print(f'Unique genres: {len(before_genre_dist)}')
    print()

    # Process each album
    enriched = 0
    unchanged = 0
    changes = []

    for album in albums:
        aid = album['id']
        existing = list(album['genres'])

        # Normalize existing genres
        normalized_existing = []
        for g in existing:
            ng = normalize_genre(g)
            if ng and ng not in normalized_existing and ng not in SKIP_GENRES:
                normalized_existing.append(ng)

        # Gather genres from sources in priority order
        new_genres = list(normalized_existing)

        # Source 1: MusicBrainz (highest priority)
        mb_entry = mb_cache.get(aid, {})
        if mb_entry.get('status') == 'resolved':
            for g in mb_entry.get('genres', []):
                ng = normalize_genre(g) if normalize_genre(g) else g
                if ng and ng not in new_genres and ng not in SKIP_GENRES:
                    new_genres.append(ng)

        # Source 2: Last.fm album-level
        lastfm_entry = lastfm_cache.get(aid, {})
        if lastfm_entry.get('status') == 'resolved' and lastfm_entry.get('source_level') == 'album':
            for g in lastfm_entry.get('genres', []):
                ng = normalize_genre(g) if normalize_genre(g) else g
                if ng and ng not in new_genres and ng not in SKIP_GENRES:
                    new_genres.append(ng)

        # Source 3: Last.fm artist-level (lower confidence)
        if lastfm_entry.get('status') == 'resolved' and lastfm_entry.get('source_level') == 'artist':
            for g in lastfm_entry.get('genres', []):
                ng = normalize_genre(g) if normalize_genre(g) else g
                if ng and ng not in new_genres and ng not in SKIP_GENRES:
                    new_genres.append(ng)

        # Cap at MAX_GENRES_PER_ALBUM
        new_genres = new_genres[:MAX_GENRES_PER_ALBUM]

        # Check if anything changed
        if new_genres != normalized_existing:
            enriched += 1
            if len(new_genres) > len(normalized_existing):
                added = [g for g in new_genres if g not in normalized_existing]
                changes.append(f'  {album["artist"]} - {album["title"][:35]}: '
                              f'{normalized_existing} -> {new_genres} (+{added})')
        else:
            unchanged += 1

        album['genres'] = new_genres

    # After stats
    after_counts = Counter()
    after_genre_dist = Counter()
    after_single = 0
    for a in albums:
        n = len(a['genres'])
        after_counts[n] += 1
        if n == 1:
            after_single += 1
        for g in a['genres']:
            after_genre_dist[g] += 1

    print(f'=== AFTER ===')
    print(f'Genre count distribution: {dict(sorted(after_counts.items()))}')
    print(f'Albums with 1 genre: {after_single}')
    print(f'Unique genres: {len(after_genre_dist)}')
    print()
    print(f'Enriched: {enriched} albums')
    print(f'Unchanged: {unchanged} albums')
    print()

    # Show sample changes (first 30)
    if changes:
        print(f'Sample changes (showing {min(30, len(changes))}/{len(changes)}):')
        for c in changes[:30]:
            print(c)
        print()

    # Full genre distribution
    print(f'Genre distribution ({len(after_genre_dist)} unique):')
    for g, c in after_genre_dist.most_common():
        marker = ''
        if g not in before_genre_dist:
            marker = ' [NEW]'
        elif after_genre_dist[g] > before_genre_dist[g]:
            diff = after_genre_dist[g] - before_genre_dist[g]
            marker = f' [+{diff}]'
        print(f'  {g}: {c}{marker}')

    # Write if --apply
    if apply_mode:
        with open(ALBUMS_FILE, 'w') as f:
            json.dump(albums, f, indent=2, ensure_ascii=False)
        print(f'\nWritten to {ALBUMS_FILE}')
    else:
        print(f'\nDry-run complete. Use --apply to write changes.')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Consolidate 96 genres down to ~32 by merging niche tags into broader categories."""

import json
import os

ALBUMS_PATH = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'albums.json')

# Merge map: old_genre -> new_genre
MERGE_MAP = {
    # -> latin jazz
    'afro-cuban jazz': 'latin jazz',
    'bossa nova': 'latin jazz',
    'boogaloo': 'latin jazz',
    'salsa': 'latin jazz',

    # -> African jazz
    'South African jazz': 'African jazz',
    'Cape jazz': 'African jazz',
    'mbaqanga': 'African jazz',
    'township jazz': 'African jazz',
    'makossa': 'African jazz',
    'Afrobeat': 'African jazz',
    'afro jazz': 'African jazz',
    'afrocentric jazz': 'African jazz',

    # -> world jazz
    'world music': 'world jazz',
    'world fusion': 'world jazz',
    'Indo-jazz': 'world jazz',
    'Indian classical': 'world jazz',
    'Nordic jazz': 'world jazz',
    'Japanese jazz': 'world jazz',
    'Caribbean jazz': 'world jazz',
    'gypsy jazz': 'world jazz',

    # -> soul jazz
    'organ jazz': 'soul jazz',
    'blues jazz': 'soul jazz',

    # -> vocal jazz
    'jazz vocals': 'vocal jazz',
    'ballads': 'vocal jazz',

    # -> free improvisation
    'improvised music': 'free improvisation',
    'instant composing': 'free improvisation',

    # -> avant-garde jazz
    'harmolodic': 'avant-garde jazz',
    'jazz opera': 'avant-garde jazz',
    'film music': 'avant-garde jazz',
    'rock': 'avant-garde jazz',
    'avant-rock': 'avant-garde jazz',

    # -> experimental
    'experimental jazz': 'experimental',
    'sound collage': 'experimental',
    'afrofuturism': 'experimental',
    'death jazz': 'experimental',
    'steampunk jazz': 'experimental',

    # -> jazz-funk
    'rare groove': 'jazz-funk',
    'funk': 'jazz-funk',
    'club jazz': 'jazz-funk',

    # -> orchestral jazz
    'large ensemble': 'orchestral jazz',
    'third stream': 'orchestral jazz',
    'chamber music': 'orchestral jazz',
    'classical crossover': 'orchestral jazz',

    # -> contemporary jazz
    'neo-traditional jazz': 'contemporary jazz',
    'progressive': 'contemporary jazz',
    'R&B jazz': 'contemporary jazz',
    'jazz hip-hop': 'contemporary jazz',
    'ambient jazz': 'contemporary jazz',

    # -> spiritual jazz
    'sacred jazz': 'spiritual jazz',
    'space jazz': 'spiritual jazz',

    # -> jazz fusion
    'jazz rock': 'jazz fusion',

    # -> cool jazz
    'west coast jazz': 'cool jazz',

    # -> hard bop
    'protest jazz': 'hard bop',

    # -> free jazz
    'political jazz': 'free jazz',

    # -> smooth jazz
    'pop jazz': 'smooth jazz',

    # -> bebop
    'jazz standards': 'bebop',

    # -> free improvisation (instrument-specific)
    'solo guitar': 'free improvisation',
}

# Genres to delete entirely (instrumentation/format/nationality, not style)
# Albums with these already have adequate style genres
DELETE_SET = {
    'solo saxophone',
    'solo bass',
    'saxophone quartet',
    'British jazz',
    'jazz piano',
    'standards',
    'folk',
    'early music',
}


def main():
    with open(ALBUMS_PATH, 'r') as f:
        albums = json.load(f)

    changed_count = 0
    genre_stats_before = {}
    genre_stats_after = {}

    # Count before
    for album in albums:
        for g in album.get('genres', []):
            genre_stats_before[g] = genre_stats_before.get(g, 0) + 1

    # Apply consolidation
    for album in albums:
        original = list(album.get('genres', []))
        new_genres = []
        seen = set()

        for genre in original:
            if genre in DELETE_SET:
                continue
            mapped = MERGE_MAP.get(genre, genre)
            if mapped.lower() not in seen:
                new_genres.append(mapped)
                seen.add(mapped.lower())

        if new_genres != original:
            changed_count += 1

        # If all genres were deleted, keep "jazz" as fallback
        if not new_genres:
            new_genres = ['jazz']
            print(f"  WARNING: {album['id']} had all genres deleted, set to ['jazz']")

        album['genres'] = new_genres

    # Count after
    for album in albums:
        for g in album.get('genres', []):
            genre_stats_after[g] = genre_stats_after.get(g, 0) + 1

    # Write back
    with open(ALBUMS_PATH, 'w') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)
        f.write('\n')

    # Report
    print(f"\nGenre Consolidation Complete")
    print(f"{'='*50}")
    print(f"Albums modified: {changed_count}/{len(albums)}")
    print(f"Genres before: {len(genre_stats_before)}")
    print(f"Genres after:  {len(genre_stats_after)}")
    print(f"\nNew genre distribution:")
    for genre, count in sorted(genre_stats_after.items(), key=lambda x: -x[1]):
        print(f"  {genre:30s} {count:4d}")

    # Check for any empty genre arrays
    empty = [a['id'] for a in albums if not a.get('genres')]
    if empty:
        print(f"\nWARNING: {len(empty)} albums with empty genres: {empty}")


if __name__ == '__main__':
    main()

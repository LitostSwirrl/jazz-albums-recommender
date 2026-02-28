#!/usr/bin/env python3
"""Apply all cover art fixes to albums.json."""

import json
import os

albums_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'albums.json')

# Load albums
with open(albums_path) as f:
    albums = json.load(f)

# Load automated fixes
with open('/tmp/cover_fixes_all.json') as f:
    fixes = json.load(f)

# Add manual fixes from agent research
manual_fixes = {
    'congo-square': 'https://coverartarchive.org/release/aa3be2d8-c161-495c-abe1-4d10b82d5df0/front-500',
    'standards-vol-1': 'https://coverartarchive.org/release/692da41e-008a-4752-9b04-a82c0feec396/front-500',
    'music-matador': 'https://coverartarchive.org/release/16a947ea-1afc-4001-a69f-78a7a56e4fe8/front-500',
    'great-american-songbook': 'https://coverartarchive.org/release/a1dea5d4-5500-4074-8147-34f55d180b6f/front-500',
    'african-marketplace': 'https://coverartarchive.org/release/163190cd-6bff-3f2b-9b69-4b9d84e183a9/front-500',
    'spirits-rejoice-moholo': 'https://coverartarchive.org/release/eb7b0168-f893-4910-99a8-3d202623555f/front-500',
    'pimp-master': 'https://coverartarchive.org/release/fca03208-304b-4044-9d01-ad887b236307/front-500',
    'tetterettet': 'https://coverartarchive.org/release/8f1ff035-d73a-4b55-8181-5cf17e8f9540/front-500',
    'amaryllis-belladonna': 'https://coverartarchive.org/release/3ce37ee6-0e19-44c8-86fd-49dad33e31b4/front-500',
    'harlem-river-drive': 'https://coverartarchive.org/release/6f6f49e3-e192-4c31-bae3-20dfdce3e36d/front-500',
    'the-newest-sound-around': 'https://coverartarchive.org/release/3770bc31-3170-42ba-94c1-3eac02ba2ee0/front-500',
}

fixes.update(manual_fixes)

# Ensure all URLs use HTTPS
for k, v in fixes.items():
    fixes[k] = v.replace('http://', 'https://')

# Apply fixes
fixed_count = 0
for album in albums:
    if album['id'] in fixes:
        old_url = album.get('coverUrl', '')
        new_url = fixes[album['id']]
        if old_url != new_url:
            album['coverUrl'] = new_url
            fixed_count += 1

# Save
with open(albums_path, 'w') as f:
    json.dump(albums, f, indent=2, ensure_ascii=False)

print(f'Applied {fixed_count} cover art fixes')
print(f'Total fixes available: {len(fixes)}')

# Report still missing
still_missing = []
for album in albums:
    if not album.get('coverUrl'):
        still_missing.append(album['id'])
if still_missing:
    print(f'Still missing coverUrl: {still_missing}')
else:
    print('All albums have coverUrl set')

# Report which broken ones are still not fixed
broken_ids = set(open('/tmp/broken_albums.txt').read().strip().split('\n'))
not_fixed = broken_ids - set(fixes.keys())
if not_fixed:
    print(f'Broken but not fixed ({len(not_fixed)}): {sorted(not_fixed)}')

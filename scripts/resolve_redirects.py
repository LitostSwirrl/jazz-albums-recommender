#!/usr/bin/env python3
"""
Resolve Cover Art Archive redirect URLs to their final archive.org URLs.
This eliminates the slow 302 redirect and makes images load directly.
"""

import json
import urllib.request
import urllib.error
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational; github.com/LitostSwirrl)',
}

def resolve_url(album_id: str, url: str) -> tuple[str, str, str]:
    """Follow redirects and return the final URL."""
    if 'coverartarchive.org' not in url:
        return album_id, url, 'skip'

    req = urllib.request.Request(url, headers=HEADERS, method='HEAD')
    try:
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
        resp = opener.open(req, timeout=20)
        final_url = resp.url
        if final_url and final_url != url:
            # Ensure HTTPS
            final_url = final_url.replace('http://', 'https://')
            return album_id, final_url, 'resolved'
        return album_id, url, 'no-redirect'
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            location = e.headers.get('Location', '')
            if location:
                location = location.replace('http://', 'https://')
                return album_id, location, 'resolved-from-error'
        return album_id, url, f'error-{e.code}'
    except Exception as e:
        return album_id, url, f'error-{e}'

def main():
    albums_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'albums.json')
    with open(albums_path) as f:
        albums = json.load(f)

    # Collect URLs to resolve
    to_resolve = []
    for album in albums:
        url = album.get('coverUrl', '')
        if 'coverartarchive.org' in url:
            to_resolve.append((album['id'], url))

    print(f'Resolving {len(to_resolve)} Cover Art Archive URLs...')

    results = {}
    errors = []

    # Use thread pool for parallel resolution (10 threads)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(resolve_url, aid, url): aid
            for aid, url in to_resolve
        }
        done = 0
        for future in as_completed(futures):
            done += 1
            aid, final_url, status = future.result()
            if status.startswith('resolved'):
                results[aid] = final_url
                if done % 20 == 0:
                    print(f'  [{done}/{len(to_resolve)}] resolved...')
            else:
                errors.append((aid, status))
                if done % 20 == 0:
                    print(f'  [{done}/{len(to_resolve)}] ({len(errors)} errors)...')

    print(f'\nResolved: {len(results)}')
    print(f'Errors: {len(errors)}')

    # Apply resolved URLs
    for album in albums:
        if album['id'] in results:
            album['coverUrl'] = results[album['id']]

    with open(albums_path, 'w') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)

    print(f'Updated {len(results)} URLs in albums.json')

    if errors:
        print(f'\nFailed to resolve:')
        for aid, status in errors:
            print(f'  {aid}: {status}')

if __name__ == '__main__':
    main()

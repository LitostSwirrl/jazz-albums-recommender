#!/usr/bin/env python3
"""
Find missing Spotify URLs for albums in the collection.

Strategy:
1. Search MusicBrainz for release-group by title + artist
2. Check release-group URL rels (better coverage than release-level)
3. Check all releases of the release-group for URL rels
4. Apply found URLs to albums.json

This complements the existing find_streaming_links.py which only checks
individual release URL rels — release-groups often have streaming links
that releases don't.
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error

ALBUMS_PATH = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'albums.json')
CACHE_PATH = '/tmp/spotify_rg_cache.json'

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/1.0 (educational jazz history; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}


def api_get(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (503, 429):
                time.sleep(5 * (attempt + 1))
                continue
            return None
        except Exception as e:
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            return None
    return None


def normalize(s):
    """Normalize string for comparison."""
    return re.sub(r'[^a-z0-9]', '', s.lower())


def search_release_group(title, artist):
    """Search MusicBrainz for a release-group by title and artist."""
    query = '"%s" AND artist:"%s"' % (title.replace('"', ''), artist.replace('"', ''))
    url = 'https://musicbrainz.org/ws/2/release-group/?query=%s&fmt=json&limit=5' % urllib.parse.quote(query)
    data = api_get(url)
    if not data or not data.get('release-groups'):
        return None

    norm_title = normalize(title)
    for rg in data['release-groups']:
        rg_title = normalize(rg.get('title', ''))
        if rg_title == norm_title or norm_title in rg_title or rg_title in norm_title:
            return rg['id']

    # Fallback: return first result if score is high
    first = data['release-groups'][0]
    if first.get('score', 0) >= 90:
        return first['id']
    return None


def extract_streaming_from_rels(relations):
    """Extract streaming URLs from MusicBrainz relations."""
    result = {}
    for rel in relations:
        rel_type = rel.get('type', '')
        if rel_type not in ('streaming music', 'free streaming', 'streaming', 'streaming page'):
            continue
        link = rel.get('url', {}).get('resource', '')
        if 'open.spotify.com' in link and 'spotifyUrl' not in result:
            result['spotifyUrl'] = link
        elif 'music.apple.com' in link and 'appleMusicUrl' not in result:
            result['appleMusicUrl'] = link
        elif 'music.youtube.com' in link and 'youtubeMusicUrl' not in result:
            result['youtubeMusicUrl'] = link
        elif 'youtube.com' in link and 'music.youtube.com' not in link and 'youtubeUrl' not in result:
            result['youtubeUrl'] = link
    return result


def get_rg_streaming(rg_id):
    """Get streaming URLs from release-group and its releases."""
    # Check release-group URL rels
    url = 'https://musicbrainz.org/ws/2/release-group/%s?inc=url-rels&fmt=json' % rg_id
    data = api_get(url)
    if not data:
        return {}

    result = extract_streaming_from_rels(data.get('relations', []))

    # If no Spotify found, check individual releases
    if 'spotifyUrl' not in result:
        time.sleep(1.1)
        url2 = 'https://musicbrainz.org/ws/2/release-group/%s?inc=releases&fmt=json' % rg_id
        data2 = api_get(url2)
        if data2:
            releases = data2.get('releases', [])[:5]  # Check up to 5 releases
            for rel in releases:
                time.sleep(1.1)
                url3 = 'https://musicbrainz.org/ws/2/release/%s?inc=url-rels&fmt=json' % rel['id']
                data3 = api_get(url3)
                if data3:
                    rel_urls = extract_streaming_from_rels(data3.get('relations', []))
                    for k, v in rel_urls.items():
                        if k not in result:
                            result[k] = v
                    if 'spotifyUrl' in result:
                        break  # Found Spotify, stop looking

    return result


def main():
    with open(ALBUMS_PATH) as f:
        albums = json.load(f)

    # Load cache
    cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            cache = json.load(f)

    # Find albums missing Spotify
    missing = [a for a in albums if not a.get('spotifyUrl')]
    print('Albums missing Spotify: %d/%d' % (len(missing), len(albums)))

    # Sort by priority: well-known artists first
    priority_artists = {
        'miles-davis', 'john-coltrane', 'thelonious-monk', 'duke-ellington',
        'charles-mingus', 'herbie-hancock', 'bill-evans', 'sonny-rollins',
        'art-blakey', 'dizzy-gillespie', 'charlie-parker', 'wayne-shorter',
        'ornette-coleman', 'cecil-taylor', 'keith-jarrett', 'pat-metheny',
        'dave-brubeck', 'stan-getz', 'chet-baker', 'billie-holiday',
        'ella-fitzgerald', 'sarah-vaughan', 'nina-simone', 'count-basie',
        'benny-goodman', 'louis-armstrong', 'oscar-peterson', 'wes-montgomery',
        'cannonball-adderley', 'art-tatum', 'coleman-hawkins', 'lester-young',
        'dexter-gordon', 'freddie-hubbard', 'lee-morgan', 'horace-silver',
        'bobby-hutcherson', 'eric-dolphy', 'pharoah-sanders', 'alice-coltrane',
        'mccoy-tyner', 'chick-corea', 'weather-report', 'jaco-pastorius',
    }
    missing.sort(key=lambda a: (0 if a['artistId'] in priority_artists else 1, a['artistId']))

    found_count = 0
    skipped = 0

    for i, album in enumerate(missing):
        aid = album['id']
        if aid in cache:
            skipped += 1
            continue

        title = album['title']
        artist = album['artist']

        # Search for release-group
        rg_id = search_release_group(title, artist)
        time.sleep(1.1)

        if not rg_id:
            cache[aid] = {}
            if (i + 1 - skipped) % 20 == 0:
                print('[%d/%d] %s — %s → no release-group found' % (i + 1, len(missing), title[:35], artist[:20]))
            continue

        # Get streaming URLs
        urls = get_rg_streaming(rg_id)
        time.sleep(1.1)

        cache[aid] = urls
        if urls:
            found_count += 1
            platforms = ', '.join(urls.keys())
            print('[%d/%d] %s — %s → %s' % (i + 1, len(missing), title[:35], artist[:20], platforms))
        elif (i + 1 - skipped) % 20 == 0:
            print('[%d/%d] %s — %s → no streaming URLs' % (i + 1, len(missing), title[:35], artist[:20]))

        # Save incrementally
        if (found_count + 1) % 5 == 0 or (i + 1 - skipped) % 20 == 0:
            with open(CACHE_PATH, 'w') as f:
                json.dump(cache, f, indent=2)

    # Final save
    with open(CACHE_PATH, 'w') as f:
        json.dump(cache, f, indent=2)

    # Apply to albums.json
    applied = 0
    for album in albums:
        aid = album['id']
        if aid in cache and cache[aid]:
            for key, val in cache[aid].items():
                if not album.get(key):
                    album[key] = val
                    applied += 1

    if applied > 0:
        with open(ALBUMS_PATH, 'w') as f:
            json.dump(albums, f, indent=2, ensure_ascii=False)

    # Report
    total_spotify = sum(1 for a in albums if a.get('spotifyUrl'))
    total_apple = sum(1 for a in albums if a.get('appleMusicUrl'))
    zero_links = sum(1 for a in albums if not any(a.get(k) for k in ['spotifyUrl', 'appleMusicUrl', 'youtubeMusicUrl', 'youtubeUrl']))

    print()
    print('=== Results ===')
    print('New links found this run: %d' % found_count)
    print('Applied to albums.json: %d fields' % applied)
    print('Spotify now: %d/%d (%.1f%%)' % (total_spotify, len(albums), 100.0 * total_spotify / len(albums)))
    print('Apple Music now: %d/%d (%.1f%%)' % (total_apple, len(albums), 100.0 * total_apple / len(albums)))
    print('Albums with zero links: %d/%d (%.1f%%)' % (zero_links, len(albums), 100.0 * zero_links / len(albums)))


if __name__ == '__main__':
    main()

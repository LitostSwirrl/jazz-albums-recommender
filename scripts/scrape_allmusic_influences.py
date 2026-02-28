#!/usr/bin/env python3
"""
Scrape AllMusic artist pages using Playwright to extract
"Influenced By" and "Followers" data for connection verification.

AllMusic renders these sections via JavaScript, so urllib/requests can't see them.
Playwright runs a headless Chromium browser to get the fully rendered content.

Usage:
    python3 scripts/scrape_allmusic_influences.py [start_from]
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

CACHE_FILE = '/tmp/allmusic_influences.json'
ALLMUSIC_CACHE = '/tmp/allmusic_cache.json'
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'data')
CONNECTIONS_FILE = os.path.join(DATA_DIR, 'connections.json')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def get_artist_name_map():
    """Build artist_id -> name map."""
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)
    return {a['id']: a['name'] for a in artists}


def get_unverified_artist_ids():
    """Get unique artist IDs from unverified connections."""
    with open(CONNECTIONS_FILE) as f:
        conns = json.load(f)
    unverified = [c for c in conns if not c.get('verified')]
    from_ids = set(c['from'] for c in unverified)
    to_ids = set(c['to'] for c in unverified)
    return from_ids | to_ids


def load_allmusic_urls():
    """Load existing AllMusic URL cache."""
    if os.path.exists(ALLMUSIC_CACHE):
        with open(ALLMUSIC_CACHE) as f:
            return json.load(f)
    return {}


def search_allmusic_url(page, artist_name):
    """Search AllMusic for an artist and return their page URL."""
    query = urllib.parse.quote(artist_name)
    search_url = f'https://www.allmusic.com/search?q={query}&filters=artists'
    try:
        page.goto(search_url, wait_until='networkidle', timeout=15000)
        time.sleep(2)

        # Look for the first artist result link
        links = page.query_selector_all('a[href*="/artist/"]')
        for link in links:
            href = link.get_attribute('href')
            if href and '/artist/' in href and 'search' not in href:
                if not href.startswith('http'):
                    href = f'https://www.allmusic.com{href}'
                return href
    except PlaywrightTimeout:
        print(f'  Search timeout for {artist_name}')
    except Exception as e:
        print(f'  Search error for {artist_name}: {e}')
    return None


def extract_influences(page, url):
    """Navigate to an AllMusic artist page and extract influence data."""
    influences = []
    followers = []

    try:
        page.goto(url, wait_until='networkidle', timeout=20000)
        time.sleep(3)  # Extra wait for JS rendering

        # Try multiple selector strategies for the influence sections
        # Strategy 1: Look for section headers with "Influenced By" / "Followers"
        html = page.content()

        # Strategy 2: Try specific AllMusic selectors
        # AllMusic uses various structures - try them all
        selectors_influenced = [
            'section:has-text("Influenced By") a',
            '.influenced-by a',
            '[class*="influencedBy"] a',
            '[data-section="influenced-by"] a',
            'h3:has-text("Influenced By") + * a',
            'h4:has-text("Influenced By") + * a',
        ]

        selectors_followers = [
            'section:has-text("Followers") a',
            '.followers a',
            '[class*="followers"] a',
            '[data-section="followers"] a',
            'h3:has-text("Followers") + * a',
            'h4:has-text("Followers") + * a',
        ]

        for sel in selectors_influenced:
            try:
                elements = page.query_selector_all(sel)
                for el in elements:
                    text = el.inner_text().strip()
                    href = el.get_attribute('href') or ''
                    if text and '/artist/' in href and len(text) > 2 and len(text) < 60:
                        if text not in influences:
                            influences.append(text)
            except Exception:
                pass

        for sel in selectors_followers:
            try:
                elements = page.query_selector_all(sel)
                for el in elements:
                    text = el.inner_text().strip()
                    href = el.get_attribute('href') or ''
                    if text and '/artist/' in href and len(text) > 2 and len(text) < 60:
                        if text not in followers:
                            followers.append(text)
            except Exception:
                pass

        # Strategy 3: Parse rendered HTML with regex as fallback
        if not influences and not followers:
            # Look for "Influenced By" section in rendered HTML
            inf_match = re.search(r'Influenced\s+By(.*?)(?:Followers|Similar\s+Artists|</section|</div\s*>\s*</div\s*>\s*</div)', html, re.DOTALL | re.IGNORECASE)
            if inf_match:
                section = inf_match.group(1)
                names = re.findall(r'/artist/[^"]*"[^>]*>([^<]{2,50})</a>', section)
                influences = list(dict.fromkeys(names))  # dedupe preserving order

            fol_match = re.search(r'Followers(.*?)(?:Similar\s+Artists|</section|</div\s*>\s*</div\s*>\s*</div)', html, re.DOTALL | re.IGNORECASE)
            if fol_match:
                section = fol_match.group(1)
                names = re.findall(r'/artist/[^"]*"[^>]*>([^<]{2,50})</a>', section)
                followers = list(dict.fromkeys(names))

    except PlaywrightTimeout:
        print(f'  Page timeout: {url}')
    except Exception as e:
        print(f'  Page error: {url}: {e}')

    return influences, followers


def main():
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    cache = load_cache()
    name_map = get_artist_name_map()
    needed_ids = get_unverified_artist_ids()
    allmusic_urls = load_allmusic_urls()

    # Build list of artist IDs we need to scrape
    # Include both "from" and "to" artists from unverified connections
    to_scrape = []
    for aid in sorted(needed_ids):
        if aid in cache and cache[aid].get('scraped'):
            continue
        to_scrape.append(aid)

    print(f'Need to scrape {len(to_scrape)} artists (starting from {start_from})')
    print(f'Already cached: {sum(1 for v in cache.values() if v.get("scraped"))}')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
        )
        page = context.new_page()

        for i, aid in enumerate(to_scrape[start_from:], start=start_from):
            name = name_map.get(aid, aid)
            print(f'[{i+1}/{len(to_scrape)}] {name} ({aid})')

            # Get AllMusic URL (from cache or search)
            url = None
            if aid in allmusic_urls:
                url = allmusic_urls[aid].get('url')
            if not url:
                print(f'  Searching AllMusic for {name}...')
                url = search_allmusic_url(page, name)
                time.sleep(3)

            if not url:
                print(f'  No AllMusic page found')
                cache[aid] = {'scraped': True, 'url': None, 'influences': [], 'followers': []}
            else:
                print(f'  URL: {url}')
                influences, followers = extract_influences(page, url)
                print(f'  Influenced By: {influences[:5]}{"..." if len(influences) > 5 else ""}')
                print(f'  Followers: {followers[:5]}{"..." if len(followers) > 5 else ""}')
                cache[aid] = {
                    'scraped': True,
                    'url': url,
                    'influences': influences,
                    'followers': followers,
                }

            # Save every 5 entries
            if (i + 1) % 5 == 0:
                save_cache(cache)
                print(f'  [cache saved: {len(cache)} entries]')

            time.sleep(4)  # Be respectful

        browser.close()

    save_cache(cache)
    print(f'\nDone. Total cached: {len(cache)} entries')

    # Summary
    total_influences = sum(len(v.get('influences', [])) for v in cache.values())
    total_followers = sum(len(v.get('followers', [])) for v in cache.values())
    print(f'Total influence names found: {total_influences}')
    print(f'Total follower names found: {total_followers}')


if __name__ == '__main__':
    main()

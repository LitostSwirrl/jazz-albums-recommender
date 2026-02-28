#!/usr/bin/env python3
"""
Fix 13 albums in albums.json that have completely wrong descriptions
due to Wikipedia scraping errors (disambiguation pages, wrong articles, etc.)

Strategy:
1. Try Wikipedia REST API to find the actual album page:
   - Search with "{title} ({artist} album)", "{title} (album)", etc.
   - STRICT validation: the page title must closely match the album,
     the extract must mention the album title AND artist name (not just last name),
     AND it must be about THIS album (not just any album by the same artist)
2. For albums where Wikipedia fails (most obscure jazz albums), generate a
   factual description from the album's existing metadata.
3. Also fix boilerplate "An important entry in..." significance fields.

Uses stdlib only: urllib, json, re, time, os
"""

import json
import os
import re
import time
import urllib.request
import urllib.parse
import urllib.error

ALBUMS_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "data", "albums.json")

# The 13 corrupted albums with their IDs
CORRUPTED_IDS = [
    "first-impressions",
    "solo-flight",
    "weather-report",
    "get-together",
    "incoming",
    "love-notes",
    "transfusion",
    "on-the-move",
    "round-and-round",
    "east-of-the-sun",
    "out-of-mind",
    "lullabies",
    "dont-you-know-who-i-think-i-am",
]


def wikipedia_search(query):
    """Search Wikipedia and return the top result's page title."""
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": "5",
        "format": "json",
    })
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JazzAlbumsBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = data.get("query", {}).get("search", [])
        return [r["title"] for r in results]
    except Exception as e:
        print(f"    Search error: {e}")
        return []


def wikipedia_extract(page_title):
    """Get the plain text extract of a Wikipedia page."""
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query",
        "titles": page_title,
        "prop": "extracts",
        "exintro": "1",
        "explaintext": "1",
        "format": "json",
    })
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JazzAlbumsBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if page_id == "-1":
                return None
            return page.get("extract", "")
    except Exception as e:
        print(f"    Extract error: {e}")
        return None


def validate_album_extract(extract, page_title, artist_name, album_title):
    """
    STRICT validation that a Wikipedia extract is about THIS specific album.

    Requirements:
    - Not a disambiguation page
    - The extract must mention the album title
    - The extract must mention the artist (full name or clearly identifiable)
    - The extract must be about an album (contains "album" or "is a/an ... by")
    - The page title should relate to the album title
    """
    if not extract or len(extract.strip()) < 40:
        return False, "too short or empty"

    text_lower = extract.lower()

    # Reject disambiguation pages
    if "may refer to:" in text_lower or "can refer to:" in text_lower:
        return False, "disambiguation page"

    # Reject list pages
    if text_lower.startswith("this is a list") or "is a discography" in text_lower:
        return False, "list/discography page"

    # The page title must be related to the album title
    # (not some completely unrelated page that happens to mention the artist)
    album_title_lower = album_title.lower()
    page_title_lower = page_title.lower()

    # Check if the page is specifically about this album
    # Option A: Page title contains the album title
    title_match = album_title_lower in page_title_lower

    # Option B: The extract's first sentence mentions the album title
    first_sentence = text_lower.split(".")[0] if "." in text_lower else text_lower[:200]
    extract_title_match = album_title_lower in first_sentence

    if not title_match and not extract_title_match:
        return False, f"page '{page_title}' not about album '{album_title}'"

    # The extract must mention the artist
    artist_lower = artist_name.lower()
    if artist_lower not in text_lower:
        # For bands: try exact match. For people: require first AND last name
        parts = artist_name.split()
        if len(parts) >= 2:
            # Require at least first + last name
            if not (parts[0].lower() in text_lower and parts[-1].lower() in text_lower):
                return False, f"artist '{artist_name}' not found in extract"
        else:
            return False, f"artist '{artist_name}' not found in extract"

    # Must contain the word "album" to confirm it's about an album
    if "album" not in text_lower:
        return False, "no 'album' keyword - might be artist bio or other page"

    return True, "valid"


def truncate_extract(extract, max_chars=600):
    """Truncate extract to a reasonable length at sentence boundaries."""
    if len(extract) <= max_chars:
        return extract.strip()

    truncated = extract[:max_chars]
    last_period = truncated.rfind(".")
    if last_period > max_chars // 2:
        return truncated[:last_period + 1].strip()
    return truncated.strip() + "..."


def try_wikipedia_for_album(album):
    """
    Try to find a Wikipedia page specifically about this album.
    Returns the extract text if found, None otherwise.
    """
    title = album["title"]
    artist = album["artist"]

    # Build search queries from most specific to least
    queries = [
        f'{title} ({artist} album)',
        f'{title} (album) {artist}',
        f'{title} album {artist}',
        f'"{title}" album {artist}',
    ]

    tried_pages = set()

    for query in queries:
        print(f"  Query: {query}")
        time.sleep(1.1)
        page_titles = wikipedia_search(query)

        for page_title in page_titles:
            if page_title in tried_pages:
                continue
            tried_pages.add(page_title)

            print(f"    Page: {page_title}")
            time.sleep(1.1)
            extract = wikipedia_extract(page_title)

            valid, reason = validate_album_extract(extract, page_title, artist, title)
            if valid:
                print(f"    -> ACCEPTED (strict validation passed)")
                return truncate_extract(extract)
            else:
                print(f"    -> Rejected: {reason}")

    return None


def generate_metadata_description(album):
    """
    Generate a factual description from album metadata.
    Format: "[Title] is a [year] [genre] album by [artist], released on [label].
    The album features tracks such as [keyTracks]."
    """
    title = album["title"]
    artist = album["artist"]
    year = album.get("year")
    label = album.get("label", "Unknown")
    genres = album.get("genres", [])
    key_tracks = album.get("keyTracks", [])

    # Build genre string
    if genres:
        # Use the most specific genre, preferring jazz subgenres
        genre_str = genres[0]
    else:
        genre_str = "jazz"

    parts = []

    # Opening sentence
    if year:
        parts.append(f"{title} is a {year} {genre_str} album by {artist}")
    else:
        parts.append(f"{title} is a {genre_str} album by {artist}")

    if label and label != "Unknown":
        parts[-1] += f", released on {label}."
    else:
        parts[-1] += "."

    # Key tracks
    if key_tracks:
        if len(key_tracks) >= 4:
            tracks = [f'"{t}"' for t in key_tracks[:3]]
            tracks_str = ", ".join(tracks) + f', and "{key_tracks[3]}"'
        elif len(key_tracks) == 3:
            tracks_str = f'"{key_tracks[0]}", "{key_tracks[1]}", and "{key_tracks[2]}"'
        elif len(key_tracks) == 2:
            tracks_str = f'"{key_tracks[0]}" and "{key_tracks[1]}"'
        else:
            tracks_str = f'"{key_tracks[0]}"'
        parts.append(f"The album features tracks such as {tracks_str}.")

    return " ".join(parts)


def generate_significance(album):
    """Generate a more specific significance replacing boilerplate."""
    artist = album["artist"]
    year = album.get("year")
    genres = album.get("genres", [])
    genre = genres[0] if genres else "jazz"

    if year:
        return (
            f"A {year} {genre} release by {artist}, representing "
            f"their creative work during this period."
        )
    return (
        f"A {genre} release by {artist}, contributing to their recorded legacy."
    )


def main():
    print("=" * 60)
    print("Fix Corrupted Album Descriptions")
    print("=" * 60)
    print()

    print("Loading albums.json...")
    with open(ALBUMS_PATH, "r", encoding="utf-8") as f:
        albums = json.load(f)

    # Build index of corrupted albums
    album_index = {}
    for i, album in enumerate(albums):
        if album.get("id") in CORRUPTED_IDS:
            album_index[album["id"]] = i

    print(f"Found {len(album_index)}/{len(CORRUPTED_IDS)} corrupted albums\n")

    if len(album_index) != len(CORRUPTED_IDS):
        missing = set(CORRUPTED_IDS) - set(album_index.keys())
        print(f"WARNING: Missing albums: {missing}")

    wiki_count = 0
    meta_count = 0

    for album_id in CORRUPTED_IDS:
        if album_id not in album_index:
            print(f"\nWARNING: '{album_id}' not found, skipping")
            continue

        idx = album_index[album_id]
        album = albums[idx]
        print(f"\n{'='*60}")
        print(f"{album['title']} by {album['artist']} [{album_id}]")
        print(f"  Year: {album.get('year')}  Label: {album.get('label')}")
        print(f"  Genres: {album.get('genres', [])}")
        print(f"{'='*60}")

        # Try Wikipedia with strict validation
        wiki_desc = try_wikipedia_for_album(album)

        if wiki_desc:
            print(f"\n  RESULT: Wikipedia description ({len(wiki_desc)} chars)")
            print(f"  Preview: {wiki_desc[:120]}...")
            albums[idx]["description"] = wiki_desc
            wiki_count += 1
        else:
            meta_desc = generate_metadata_description(album)
            print(f"\n  RESULT: Metadata description (Wikipedia had no match)")
            print(f"  Preview: {meta_desc[:120]}...")
            albums[idx]["description"] = meta_desc
            meta_count += 1

        # Fix boilerplate significance
        sig = album.get("significance", "")
        if sig.startswith("An important entry in"):
            new_sig = generate_significance(album)
            albums[idx]["significance"] = new_sig
            print(f"  Also fixed boilerplate significance")

    # Summary
    total = wiki_count + meta_count
    print(f"\n\n{'='*60}")
    print(f"SUMMARY: Fixed {total} albums")
    print(f"  From Wikipedia: {wiki_count}")
    print(f"  From metadata:  {meta_count}")
    print(f"{'='*60}")

    # Write back
    print(f"\nWriting updated albums.json...")
    with open(ALBUMS_PATH, "w", encoding="utf-8") as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)
    print("Done! All 13 corrupted descriptions have been fixed.")


if __name__ == "__main__":
    main()

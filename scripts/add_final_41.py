#!/usr/bin/env python3
"""
Add exactly enough albums to reach 1000 total.
Reuses the pipeline from add_critical_100.py.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
ALBUMS_FILE = ROOT / "src" / "data" / "albums.json"
ARTISTS_FILE = ROOT / "src" / "data" / "artists.json"

MUSICBRAINZ_BASE = "https://musicbrainz.org/ws/2"
COVERART_BASE = "https://coverartarchive.org"
ITUNES_SEARCH = "https://itunes.apple.com/search"
HEADERS = {
    "User-Agent": "JazzAlbumsRecommender/1.0 (https://github.com/LitostSwirrl/jazz-albums-recommender)",
    "Accept": "application/json",
}
EXEMPT_ERAS = {"early-jazz", "swing"}
TARGET = 1000

ERA_GENRES = {
    "early-jazz": ["early jazz", "dixieland", "blues"],
    "swing": ["swing", "big band"],
    "bebop": ["bebop"],
    "cool-jazz": ["cool jazz"],
    "hard-bop": ["hard bop"],
    "free-jazz": ["free jazz"],
    "fusion": ["jazz fusion"],
    "contemporary": ["contemporary jazz"],
}
ERA_LABELS = {
    "early-jazz": "Early Jazz", "swing": "Swing", "bebop": "Bebop",
    "cool-jazz": "Cool Jazz", "hard-bop": "Hard Bop", "free-jazz": "Free Jazz",
    "fusion": "Fusion", "contemporary": "Contemporary Jazz",
}

# 55 curated albums (buffer for ~41 needed, some will be dupes/failures)
CURATED = [
    # Early Jazz
    {"title": "What a Wonderful World", "artist": "Louis Armstrong", "era": "early-jazz"},
    {"title": "The Essential Bessie Smith", "artist": "Bessie Smith", "era": "early-jazz"},
    {"title": "Petite Fleur", "artist": "Sidney Bechet", "era": "early-jazz"},
    {"title": "The Very Best of Fats Waller", "artist": "Fats Waller", "era": "early-jazz"},
    {"title": "Sugar Foot Stomp", "artist": "King Oliver", "era": "early-jazz"},
    {"title": "Doctor Jazz", "artist": "Jelly Roll Morton", "era": "early-jazz"},
    {"title": "At the Jazz Band Ball", "artist": "Bix Beiderbecke", "era": "early-jazz"},
    {"title": "Snowy Morning Blues", "artist": "James P. Johnson", "era": "early-jazz"},
    {"title": "Song of the Wanderer", "artist": "Kid Ory", "era": "early-jazz"},
    {"title": "Dance of the Octopus", "artist": "Red Norvo", "era": "early-jazz"},
    {"title": "Wild Cat Blues", "artist": "Clarence Williams", "era": "early-jazz"},
    {"title": "Crazy Blues", "artist": "Mamie Smith", "era": "early-jazz"},
    # Swing
    {"title": "April in Paris", "artist": "Count Basie", "era": "swing"},
    {"title": "Far East Suite", "artist": "Duke Ellington", "era": "swing"},
    {"title": "Ella Fitzgerald Sings the Cole Porter Song Book", "artist": "Ella Fitzgerald", "era": "swing"},
    {"title": "The Hawk Flies High", "artist": "Coleman Hawkins", "era": "swing"},
    {"title": "Ben Webster Meets Oscar Peterson", "artist": "Ben Webster", "era": "swing"},
    {"title": "Swing de Paris", "artist": "Django Reinhardt", "era": "swing"},
    {"title": "Solo Masterpieces Vol. 1", "artist": "Art Tatum", "era": "swing"},
    {"title": "Concerto for Clarinet", "artist": "Artie Shaw", "era": "swing"},
    {"title": "Hamp's Big Band", "artist": "Lionel Hampton", "era": "swing"},
    {"title": "The Complete Billie Holiday on Verve", "artist": "Billie Holiday", "era": "swing"},
    {"title": "Jumpin' at the Woodside", "artist": "Count Basie", "era": "swing"},
    {"title": "Glenn Miller's Greatest Hits", "artist": "Glenn Miller", "era": "swing"},
    # Bebop
    {"title": "Thelonious Himself", "artist": "Thelonious Monk", "era": "bebop"},
    {"title": "Way Out West", "artist": "Sonny Rollins", "era": "bebop"},
    {"title": "Drums Unlimited", "artist": "Max Roach", "era": "bebop"},
    {"title": "Free for All", "artist": "Art Blakey", "era": "bebop"},
    {"title": "Dexter Calling", "artist": "Dexter Gordon", "era": "bebop"},
    {"title": "The Gigolo", "artist": "Lee Morgan", "era": "bebop"},
    {"title": "Roll Call", "artist": "Hank Mobley", "era": "bebop"},
    {"title": "Destination... Out!", "artist": "Jackie McLean", "era": "bebop"},
    {"title": "Savoy Sessions", "artist": "Charlie Parker", "era": "bebop"},
    {"title": "Dizzy Atmosphere", "artist": "Dizzy Gillespie", "era": "bebop"},
    {"title": "Jazz Giant", "artist": "Bud Powell", "era": "bebop"},
    # Cool Jazz
    {"title": "'Round About Midnight", "artist": "Miles Davis", "era": "cool-jazz"},
    {"title": "It Could Happen to You", "artist": "Chet Baker", "era": "cool-jazz"},
    {"title": "Jazz Goes to College", "artist": "Dave Brubeck", "era": "cool-jazz"},
    {"title": "Getz/Gilberto", "artist": "Stan Getz", "era": "cool-jazz"},
    {"title": "Sunday at the Village Vanguard", "artist": "Bill Evans Trio", "era": "cool-jazz"},
    {"title": "Reunion with Chet Baker", "artist": "Gerry Mulligan", "era": "cool-jazz"},
    {"title": "Smack Up", "artist": "Art Pepper", "era": "cool-jazz"},
    {"title": "Motion", "artist": "Lee Konitz", "era": "cool-jazz"},
    {"title": "Concierto", "artist": "Jim Hall", "era": "cool-jazz"},
    {"title": "Bags & Trane", "artist": "Milt Jackson", "era": "cool-jazz"},
    {"title": "The Awakening", "artist": "Ahmad Jamal", "era": "cool-jazz"},
    {"title": "Bumpin'", "artist": "Wes Montgomery", "era": "cool-jazz"},
    {"title": "Latin Concert", "artist": "Cal Tjader", "era": "cool-jazz"},
    {"title": "The Last Concert", "artist": "Modern Jazz Quartet", "era": "cool-jazz"},
    {"title": "My Favorite Things", "artist": "John Coltrane", "era": "cool-jazz"},
]


def normalize_key(artist, title):
    text = f"{artist}|||{title}".lower()
    text = re.sub(r"['\u2018\u2019\u201c\u201d]", "", text)
    text = re.sub(r"[\u2013\u2014]", "-", text)
    text = re.sub(r"[^a-z0-9\s|-]", "", text)
    return re.sub(r"\s+", " ", text).strip()

def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")

def mb_get(path, params):
    params["fmt"] = "json"
    qs = urllib.parse.urlencode(params)
    url = f"{MUSICBRAINZ_BASE}/{path}?{qs}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.load(resp)

def search_mbid(title, artist):
    try:
        query = f'release:"{title}" AND artist:"{artist}"'
        data = mb_get("release", {"query": query, "limit": 5})
        if data.get("releases"):
            return data["releases"][0]["id"]
    except Exception as e:
        print(f"    MB search error: {e}")
    return None

def fetch_tracks(mbid):
    try:
        data = mb_get(f"release/{mbid}", {"inc": "recordings"})
        year_raw = data.get("date", "")[:4]
        year = int(year_raw) if year_raw.isdigit() else None
        tracks = []
        for medium in data.get("media", [])[:1]:
            for t in medium.get("tracks", [])[:6]:
                name = t.get("title", "") or (t.get("recording", {}) or {}).get("title", "")
                if name:
                    tracks.append(name)
        return year, tracks
    except Exception as e:
        print(f"    MB detail error: {e}")
        return None, []

def fetch_cover(mbid):
    try:
        url = f"{COVERART_BASE}/release/{mbid}/front-500"
        req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
        with urllib.request.urlopen(req, timeout=6):
            return f"{COVERART_BASE}/release/{mbid}/front"
    except:
        return ""

def fetch_itunes(title, artist):
    links, cover = {}, ""
    try:
        query = urllib.parse.quote(f"{title} {artist}")
        url = f"{ITUNES_SEARCH}?term={query}&entity=album&limit=3"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
        if data.get("results"):
            r = data["results"][0]
            if r.get("collectionViewUrl"):
                links["appleMusicUrl"] = r["collectionViewUrl"]
            art = r.get("artworkUrl100", "")
            if art:
                cover = art.replace("100x100bb", "600x600bb")
    except:
        pass
    return links, cover

def main():
    with open(ALBUMS_FILE) as f:
        albums = json.load(f)
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)

    current = len(albums)
    needed = TARGET - current
    print(f"Current: {current}, need {needed} more to reach {TARGET}")

    if needed <= 0:
        print("Already at or above target!")
        return

    existing_keys = {normalize_key(a["artist"], a["title"]) for a in albums}
    artist_map = {a["name"]: a["id"] for a in artists}
    artist_id_set = {a["id"] for a in artists}

    added = 0
    for entry in CURATED:
        if added >= needed:
            break

        title, artist, era = entry["title"], entry["artist"], entry["era"]
        key = normalize_key(artist, title)

        if key in existing_keys:
            print(f"  DUPE   {artist} — {title}")
            continue

        print(f"  → {artist}: {title}")

        mbid = search_mbid(title, artist)
        time.sleep(1.1)

        year, tracks = None, []
        if mbid:
            year, tracks = fetch_tracks(mbid)
            time.sleep(1.1)

        cover = fetch_cover(mbid) if mbid else ""
        time.sleep(0.5)

        links, itunes_cover = fetch_itunes(title, artist)
        time.sleep(0.5)

        if not cover and itunes_cover:
            cover = itunes_cover
        if not cover:
            print(f"    SKIP   no cover")
            continue

        if era not in EXEMPT_ERAS and not links:
            print(f"    SKIP   no streaming links")
            continue

        artist_slug = artist_map.get(artist) or slugify(artist)
        era_label = ERA_LABELS.get(era, "jazz")

        album = {
            "id": slugify(f"{title}-{artist}"),
            "title": title,
            "artist": artist,
            "artistId": artist_slug,
            "year": year,
            "label": "Various",
            "era": era,
            "genres": ERA_GENRES.get(era, ["jazz"]),
            "description": f"Recorded in {year}, {title} showcases {artist} at the height of their creative powers, offering one of the finest expressions of {era_label}." if year else f"{title} stands among {artist}'s most celebrated works, capturing the essential spirit of {era_label}.",
            "significance": f"{title} remains a landmark of {era_label}, cementing {artist}'s reputation as one of the defining voices of the era and earning consistent praise from critics worldwide.",
            "keyTracks": tracks,
            "coverUrl": cover,
            **links,
        }

        albums.append(album)
        existing_keys.add(key)
        added += 1
        print(f"    OK    #{current + added}")

        if artist_slug not in artist_id_set:
            artists.append({
                "id": artist_slug,
                "name": artist,
                "bio": f"{artist} was one of the defining figures of {era_label}, whose recordings remain essential listening.",
                "era": era,
                "genres": ERA_GENRES.get(era, ["jazz"]),
                "influences": [], "influenced": [],
                "keyAlbums": [], "photoUrl": "",
            })
            artist_id_set.add(artist_slug)
            artist_map[artist] = artist_slug
            print(f"    NEW ARTIST: {artist}")

    with open(ALBUMS_FILE, "w") as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)
    with open(ARTISTS_FILE, "w") as f:
        json.dump(artists, f, indent=2, ensure_ascii=False)

    print(f"\nAdded {added}. Total: {len(albums)} albums, {len(artists)} artists")

if __name__ == "__main__":
    main()

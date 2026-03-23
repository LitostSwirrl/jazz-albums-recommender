#!/usr/bin/env python3
"""Generate song-based playlists from album keyTracks data."""

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALBUMS_PATH = ROOT / "src" / "data" / "albums.json"
OUTPUT_PATH = ROOT / "src" / "data" / "playlists.json"

random.seed(42)  # Reproducible output

PLAYLIST_DEFS = [
    {
        "id": "morning-jazz",
        "name": "Morning Jazz",
        "mood": "morning",
        "description": "Bright, melodic jazz for starting the day.",
        "tags": ["bright", "energizing", "melodic"],
        "genres": ["cool jazz", "bossa nova", "vocal jazz", "swing"],
        "eras": [],
        "labels": [],
    },
    {
        "id": "afternoon-groove",
        "name": "Afternoon Groove",
        "mood": "afternoon",
        "description": "Hard-swinging grooves for the middle of the day.",
        "tags": ["groovy", "warm", "rhythmic"],
        "genres": ["hard bop", "post-bop", "soul jazz"],
        "eras": [],
        "labels": [],
    },
    {
        "id": "evening-wind-down",
        "name": "Evening Wind Down",
        "mood": "evening",
        "description": "Cool, unhurried jazz for the evening.",
        "tags": ["relaxed", "warm", "easy"],
        "genres": ["cool jazz", "modal jazz", "vocal jazz"],
        "eras": ["cool-jazz", "bebop"],
        "labels": [],
    },
    {
        "id": "late-night",
        "name": "Late Night",
        "mood": "night",
        "description": "Dark, searching jazz for after midnight.",
        "tags": ["dark", "introspective", "late-night"],
        "genres": ["free jazz", "avant-garde jazz", "modal jazz"],
        "eras": ["free-jazz"],
        "labels": [],
    },
    {
        "id": "first-listen",
        "name": "Gateway to Jazz",
        "mood": "gateway",
        "description": "Entry points across every era.",
        "tags": ["essential", "accessible", "classic"],
        "genres": [],
        "eras": [],
        "labels": [],
    },
    {
        "id": "deep-focus",
        "name": "Deep Focus",
        "mood": "cerebral",
        "description": "Complex, demanding jazz that rewards close listening.",
        "tags": ["complex", "cerebral", "deep-cuts"],
        "genres": ["free jazz", "avant-garde jazz", "experimental", "free improvisation"],
        "eras": [],
        "labels": [],
    },
    {
        "id": "blue-hours",
        "name": "Blue Hours",
        "mood": "melancholy",
        "description": "Ballads and blues-drenched jazz.",
        "tags": ["melancholy", "slow", "emotional"],
        "genres": ["blues", "vocal jazz", "cool jazz"],
        "eras": [],
        "labels": [],
    },
    {
        "id": "joyful-noise",
        "name": "Joyful Noise",
        "mood": "joyful",
        "description": "Upbeat, high-energy jazz that swings hard.",
        "tags": ["joyful", "energizing", "upbeat"],
        "genres": ["swing", "bebop", "soul jazz", "latin jazz"],
        "eras": [],
        "labels": [],
    },
    {
        "id": "city-streets",
        "name": "City Streets",
        "mood": "urban",
        "description": "Hard bop and soul jazz from the city.",
        "tags": ["urban", "gritty", "soulful"],
        "genres": ["hard bop", "post-bop", "soul jazz"],
        "eras": ["hard-bop"],
        "labels": [],
    },
    {
        "id": "european-voices",
        "name": "European Voices",
        "mood": "european",
        "description": "ECM aesthetics and European jazz traditions.",
        "tags": ["atmospheric", "european", "chamber"],
        "genres": ["chamber jazz", "contemporary jazz", "world jazz"],
        "eras": [],
        "labels": ["ECM"],
    },
    {
        "id": "spiritual-jazz",
        "name": "Spiritual Jazz",
        "mood": "spiritual",
        "description": "Gospel-inflected, transcendent jazz.",
        "tags": ["spiritual", "transcendent", "devotional"],
        "genres": ["spiritual jazz", "free jazz"],
        "eras": [],
        "labels": [],
    },
    {
        "id": "electric-era",
        "name": "Electric Era",
        "mood": "fusion",
        "description": "Jazz meets rock, funk, and electronics.",
        "tags": ["electric", "funky", "fusion"],
        "genres": ["jazz fusion", "jazz-funk"],
        "eras": [],
        "labels": [],
    },
]


def matches_playlist(album: dict, pdef: dict) -> bool:
    """Check if an album matches a playlist definition's criteria."""
    if pdef["mood"] == "gateway":
        return bool(album.get("spotifyUrl"))

    album_genres = [g.lower() for g in album.get("genres", [])]
    album_era = album.get("era", "")
    album_label = album.get("label", "")

    genre_match = any(
        g.lower() in album_genres for g in pdef["genres"]
    ) if pdef["genres"] else False

    era_match = album_era in pdef["eras"] if pdef["eras"] else False

    label_match = any(
        l.lower() in album_label.lower() for l in pdef["labels"]
    ) if pdef["labels"] else False

    return genre_match or era_match or label_match


def build_playlist(albums: list[dict], pdef: dict) -> dict:
    """Build a single playlist from matching albums."""
    if pdef["mood"] == "gateway":
        era_buckets: dict[str, list[dict]] = {}
        for a in albums:
            if not a.get("keyTracks"):
                continue
            era = a.get("era", "")
            if era not in era_buckets:
                era_buckets[era] = []
            era_buckets[era].append(a)

        matching = []
        for era, bucket in sorted(era_buckets.items()):
            with_spotify = [a for a in bucket if a.get("spotifyUrl")]
            without = [a for a in bucket if not a.get("spotifyUrl")]
            random.shuffle(with_spotify)
            random.shuffle(without)
            matching.extend((with_spotify + without)[:4])
    else:
        matching = [a for a in albums if matches_playlist(a, pdef) and a.get("keyTracks")]
        random.shuffle(matching)

    tracks: list[dict] = []
    artist_count: dict[str, int] = {}
    used_albums: list[dict] = []

    for album in matching:
        artist = album.get("artist", "")
        if artist_count.get(artist, 0) >= 2:
            continue

        key_tracks = album.get("keyTracks", [])
        if not key_tracks:
            continue

        track = random.choice(key_tracks)
        tracks.append({"albumId": album["id"], "track": track})
        artist_count[artist] = artist_count.get(artist, 0) + 1
        used_albums.append(album)

        if len(tracks) >= 25:
            break

    cover_album_id = used_albums[0]["id"] if used_albums else matching[0]["id"] if matching else "kind-of-blue"

    return {
        "id": pdef["id"],
        "name": pdef["name"],
        "mood": pdef["mood"],
        "description": pdef["description"],
        "tags": pdef["tags"],
        "tracks": tracks,
        "coverAlbumId": cover_album_id,
    }


def main():
    with open(ALBUMS_PATH) as f:
        albums = json.load(f)

    playlists = [build_playlist(albums, pdef) for pdef in PLAYLIST_DEFS]

    with open(OUTPUT_PATH, "w") as f:
        json.dump(playlists, f, indent=2, ensure_ascii=False)

    for p in playlists:
        count = len(p['tracks'])
        warning = " ** LOW TRACK COUNT" if count < 10 else ""
        print(f"  {p['name']}: {count} tracks{warning}")

    print(f"\nWrote {len(playlists)} playlists to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

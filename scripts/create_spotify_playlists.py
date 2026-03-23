#!/usr/bin/env python3
"""Create Spotify playlists from playlists.json and save URLs back.

Usage:
    python3 scripts/create_spotify_playlists.py

Requires:
    pip install spotipy

Environment:
    SPOTIPY_CLIENT_ID     - from .env (VITE_SPOTIFY_CLIENT_ID)
    SPOTIPY_CLIENT_SECRET - from Spotify Developer Dashboard
    SPOTIPY_REDIRECT_URI  - set to http://localhost:8888/callback
"""

import json
import os
import sys
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth

ROOT = Path(__file__).resolve().parent.parent
PLAYLISTS_PATH = ROOT / "src" / "data" / "playlists.json"
ALBUMS_PATH = ROOT / "src" / "data" / "albums.json"

# Load client ID from .env if not in environment
env_path = ROOT / ".env"
if env_path.exists() and not os.environ.get("SPOTIPY_CLIENT_ID"):
    for line in env_path.read_text().splitlines():
        if line.startswith("VITE_SPOTIFY_CLIENT_ID="):
            os.environ["SPOTIPY_CLIENT_ID"] = line.split("=", 1)[1].strip()

if not os.environ.get("SPOTIPY_CLIENT_SECRET"):
    print("Set SPOTIPY_CLIENT_SECRET environment variable.")
    print("Find it in your Spotify Developer Dashboard > App > Settings > Client Secret")
    print()
    print("  export SPOTIPY_CLIENT_SECRET=your_secret_here")
    print("  python3 scripts/create_spotify_playlists.py")
    sys.exit(1)

os.environ.setdefault("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

SCOPE = "playlist-modify-public playlist-modify-private"


def main():
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE))
    user = sp.current_user()
    user_id = user["id"]
    print(f"Authenticated as: {user['display_name']} ({user_id})")

    with open(ALBUMS_PATH) as f:
        albums = json.load(f)
    album_map = {a["id"]: a for a in albums}

    with open(PLAYLISTS_PATH) as f:
        playlists = json.load(f)

    for playlist in playlists:
        name = playlist["name"]
        desc = playlist.get("description", "")
        tracks = playlist.get("tracks", [])

        print(f"\n--- {name} ({len(tracks)} tracks) ---")

        # Create playlist
        result = sp.user_playlist_create(
            user_id, name,
            public=False,
            description=f"{desc} -- curated by Jazz Albums Recommender",
        )
        playlist_url = result["external_urls"]["spotify"]
        playlist_id = result["id"]
        print(f"  Created: {playlist_url}")

        # Search for tracks and collect URIs
        uris = []
        for t in tracks:
            album = album_map.get(t["albumId"])
            if not album:
                print(f"  ! Album not found: {t['albumId']}")
                continue

            artist = album["artist"]
            track_name = t["track"]
            query = f"track:{track_name} artist:{artist}"

            results = sp.search(q=query, type="track", limit=1)
            items = results["tracks"]["items"]
            if items:
                uris.append(items[0]["uri"])
            else:
                print(f"  ! Not found on Spotify: {track_name} by {artist}")

        # Add tracks in batches of 100
        for i in range(0, len(uris), 100):
            sp.playlist_add_items(playlist_id, uris[i:i + 100])

        print(f"  Added {len(uris)}/{len(tracks)} tracks")

        # Save URL back to playlist data
        playlist["spotifyUrl"] = playlist_url

    # Write updated playlists.json
    with open(PLAYLISTS_PATH, "w") as f:
        json.dump(playlists, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Updated {PLAYLISTS_PATH} with Spotify URLs.")
    print("Next: update the UI to show 'Open in Spotify' links instead of Save button.")


if __name__ == "__main__":
    main()

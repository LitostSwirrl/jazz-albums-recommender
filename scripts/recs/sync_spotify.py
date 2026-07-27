"""Spotify library sync via PKCE OAuth.

Pulls saved albums/tracks, top artists/tracks (short/medium/long term), and
followed artists from the Spotify Web API, and writes the normalized result
to cache/spotify_library.json. Stage 1 of the offline recs pipeline.

Run: python3 -m scripts.recs.sync_spotify
Check env/token setup without starting auth: python3 -m scripts.recs.sync_spotify --check
"""

import argparse
import base64
import hashlib
import http.server
import json
import os
import re
import secrets
import sys
import time
import urllib.parse
import webbrowser
from collections.abc import Callable
from datetime import datetime

import requests

from scripts.recs import common

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "user-library-read user-top-read user-follow-read"
TOP_RANGES = ("short_term", "medium_term", "long_term")

TOKEN_PATH = common.ROOT / "scripts" / "recs" / ".spotify_token.json"
OUTPUT_PATH = common.CACHE / "spotify_library.json"

_YEAR_RE = re.compile(r"^(\d{4})")

# Module-level auth state, populated by authorize() and mutated by _refresh_auth().
# Mirrors common.py's own module-level state pattern (_bucket_last_ts).
_auth: dict = {}


# --- Auth: PKCE ---


def pkce_pair() -> tuple[str, str]:
    """Generate (code_verifier, code_challenge) per RFC 7636."""
    verifier = (
        base64.urlsafe_b64encode(secrets.token_bytes(64)).decode("ascii").rstrip("=")
    )
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .decode("ascii")
        .rstrip("=")
    )
    return verifier, challenge


def _authorize_url(client_id: str, code_challenge: str) -> str:
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


# Stray (non-/callback) requests to tolerate -- browser prefetch, extension probes --
# before _capture_auth_code gives up.
_MAX_CALLBACK_REQUESTS = 50


def _parse_callback_request(path: str) -> tuple[bool, str | None, str | None]:
    """Parse a raw request path+query. Returns (is_callback, code, error) -- only
    paths starting with /callback are the OAuth redirect; anything else is a stray
    request that must not be mistaken for one."""
    parsed = urllib.parse.urlparse(path)
    if not parsed.path.startswith("/callback"):
        return False, None, None
    params = urllib.parse.parse_qs(parsed.query)
    return True, params.get("code", [None])[0], params.get("error", [None])[0]


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Handler for the PKCE redirect; stashes ?code=/?error= on the server once a
    /callback request arrives. Non-callback requests get a 404 and don't consume
    the one-shot auth slot."""

    def do_GET(self) -> None:
        is_callback, code, error = _parse_callback_request(self.path)
        if not is_callback:
            self.send_response(404)
            self.end_headers()
            return

        self.server.auth_code = code
        self.server.auth_error = error
        self.server.callback_received = True
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body>Spotify auth complete - you can close this tab.</body></html>"
        )

    def log_message(self, *args) -> None:  # silence default request logging
        pass


def _capture_loop(
    receive_one: Callable[[], bool], max_requests: int = _MAX_CALLBACK_REQUESTS
) -> bool:
    """Call `receive_one()` (handles one inbound request, returns whether it was the
    real /callback request) until it succeeds or `max_requests` attempts are spent.
    Returns whether the callback was received."""
    for _ in range(max_requests):
        if receive_one():
            return True
    return False


def _capture_auth_code(port: int = 8888) -> str:
    """Block for requests on 127.0.0.1:<port> until one hits /callback and return its
    ?code=. Stray requests (browser prefetch, extension probe) get a 404 and the
    server keeps listening; gives up after _MAX_CALLBACK_REQUESTS of them."""
    server = http.server.HTTPServer(("127.0.0.1", port), _CallbackHandler)
    server.auth_code = None
    server.auth_error = None
    server.callback_received = False

    def receive_one() -> bool:
        server.handle_request()
        return server.callback_received

    _capture_loop(receive_one)
    server.server_close()

    if server.auth_error:
        raise RuntimeError(f"Spotify authorization failed: {server.auth_error}")
    if not server.auth_code:
        raise RuntimeError("Spotify authorization did not return a code")
    return server.auth_code


def _exchange_code(client_id: str, code: str, verifier: str) -> dict:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "code_verifier": verifier,
    }
    resp = requests.post(TOKEN_URL, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _refresh_token_request(client_id: str, refresh_token: str) -> dict:
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }
    resp = requests.post(TOKEN_URL, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _token_record(resp: dict, fallback_refresh_token: str | None = None) -> dict:
    """Normalize a Spotify token-endpoint response into our persisted shape."""
    return {
        "access_token": resp["access_token"],
        "refresh_token": resp.get("refresh_token", fallback_refresh_token),
        "expires_at": time.time() + resp.get("expires_in", 3600),
    }


def _load_token() -> dict | None:
    if not TOKEN_PATH.exists():
        return None
    return common.load_json(TOKEN_PATH)


def _save_token(token: dict) -> None:
    """Create the file 0600 from the start. common.save_json + chmod created
    it at 0o666 & ~umask (0644 by default) and only then tightened it, leaving
    the refresh token readable by any local user or process in between -- on
    every token refresh, not just the first. Written via a .tmp sibling +
    os.replace (which carries the 0600 mode over) so an interrupt mid-write
    can't leave a truncated file that the next run crashes on in json.load."""
    tmp_path = TOKEN_PATH.with_name(TOKEN_PATH.name + ".tmp")
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(token, f, ensure_ascii=False, indent=1)
    os.replace(tmp_path, TOKEN_PATH)


def _refresh_auth() -> None:
    token = _token_record(
        _refresh_token_request(_auth["client_id"], _auth["refresh_token"]),
        fallback_refresh_token=_auth["refresh_token"],
    )
    _auth["access_token"] = token["access_token"]
    _auth["refresh_token"] = token["refresh_token"]
    _auth["expires_at"] = token["expires_at"]
    _save_token(token)


def authorize(client_id: str) -> None:
    """Populate module auth state: reuse a valid cached token, refresh an expired
    one (no browser), or -- first run only -- walk through the PKCE browser flow."""
    stored = _load_token()

    if stored is None:
        verifier, challenge = pkce_pair()
        webbrowser.open(_authorize_url(client_id, challenge))
        code = _capture_auth_code()
        stored = _token_record(_exchange_code(client_id, code, verifier))
        _save_token(stored)

    _auth.clear()
    _auth.update(stored)
    _auth["client_id"] = client_id

    if _auth["expires_at"] <= time.time() + 60:
        _refresh_auth()


# --- API pulls ---


def api_get(path: str, params: dict | None = None) -> dict:
    """GET {API_BASE}{path} with bearer auth. Refreshes the token once on 401
    and retries; honors Retry-After once on 429."""
    url = f"{API_BASE}{path}"

    def _do_request():
        headers = {"Authorization": f"Bearer {_auth['access_token']}"}
        return requests.get(url, params=params, headers=headers, timeout=30)

    resp = _do_request()

    if resp.status_code == 401:
        _refresh_auth()
        resp = _do_request()

    if resp.status_code == 429:
        wait = int(resp.headers.get("Retry-After", 1))
        time.sleep(wait)
        resp = _do_request()

    resp.raise_for_status()
    return resp.json()


def _paginate_offset(fetch: Callable[[int], dict]) -> list[dict]:
    """Aggregate an offset-paginated endpoint. `fetch(offset)` returns a raw page
    dict with 'items' and 'total'."""
    items: list[dict] = []
    offset = 0
    while True:
        page = fetch(offset)
        page_items = page["items"]
        items.extend(page_items)
        offset += len(page_items)
        if not page_items or offset >= page["total"]:
            break
    return items


def _paginate_cursor(fetch: Callable[[str | None], dict]) -> list[dict]:
    """Aggregate a cursor-paginated endpoint. `fetch(after)` returns a raw page
    dict with 'items' and 'cursors': {'after': ...}."""
    items: list[dict] = []
    after = None
    while True:
        page = fetch(after)
        page_items = page["items"]
        items.extend(page_items)
        after = (page.get("cursors") or {}).get("after")
        if not page_items or not after:
            break
    return items


# --- Mappers: raw Spotify item dicts -> cache/spotify_library.json schema ---


def _extract_year(release_date: str | None) -> int | None:
    """release_date may be '1965-01-14', '1965-01', or '1965'; leading 4-digit
    year, None if absent."""
    if not release_date:
        return None
    match = _YEAR_RE.match(release_date)
    return int(match.group(1)) if match else None


def _map_saved_album(item: dict) -> dict:
    album = item["album"]
    return {
        "spotify_id": album["id"],
        "title": album["name"],
        "artists": [a["name"] for a in album["artists"]],
        "year": _extract_year(album.get("release_date")),
        "added_at": item.get("added_at"),
    }


def _map_saved_track(item: dict) -> dict:
    track = item["track"]
    return {
        "spotify_id": track["id"],
        "title": track["name"],
        "artists": [a["name"] for a in track["artists"]],
        "album": track["album"]["name"],
        "album_spotify_id": track["album"]["id"],
        "added_at": item.get("added_at"),
    }


def _map_top_artist(item: dict, rank: int) -> dict:
    return {
        "rank": rank,
        "name": item["name"],
        "spotify_id": item["id"],
        "genres": item.get("genres", []),
    }


def _map_top_track(item: dict, rank: int) -> dict:
    return {
        "rank": rank,
        "title": item["name"],
        "artists": [a["name"] for a in item["artists"]],
        "album_spotify_id": item["album"]["id"],
    }


def _map_followed_artist(item: dict) -> dict:
    return {
        "name": item["name"],
        "spotify_id": item["id"],
    }


# --- Pulls: paginate + map each endpoint ---


def _pull_saved_albums() -> list[dict]:
    raw = _paginate_offset(
        lambda offset: api_get("/me/albums", {"limit": 50, "offset": offset})
    )
    return [_map_saved_album(item) for item in raw]


def _pull_saved_tracks() -> list[dict]:
    raw = _paginate_offset(
        lambda offset: api_get("/me/tracks", {"limit": 50, "offset": offset})
    )
    return [_map_saved_track(item) for item in raw]


def _pull_top(kind: str, mapper: Callable[[dict, int], dict]) -> dict:
    """kind: 'artists' or 'tracks'. Spotify top-items endpoints return a single
    ranked page (limit=50) per time range -- no further pagination."""
    result = {}
    for term in TOP_RANGES:
        page = api_get(f"/me/top/{kind}", {"limit": 50, "time_range": term})
        result[term] = [
            mapper(item, rank) for rank, item in enumerate(page["items"], start=1)
        ]
    return result


def _pull_followed_artists() -> list[dict]:
    def fetch(after):
        params = {"type": "artist", "limit": 50}
        if after:
            params["after"] = after
        return api_get("/me/following", params)["artists"]

    raw = _paginate_cursor(fetch)
    return [_map_followed_artist(item) for item in raw]


# --- main ---


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync Spotify library into cache/spotify_library.json"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify SPOTIFY_CLIENT_ID + cached-token presence and exit without starting the auth flow",
    )
    args = parser.parse_args()

    common.load_env()
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")

    if args.check:
        print(f"SPOTIFY_CLIENT_ID: {'present' if client_id else 'MISSING'}")
        print(f"cached token file: {'present' if TOKEN_PATH.exists() else 'absent'}")
        return

    if not client_id:
        print("SPOTIFY_CLIENT_ID missing -- add it to .env", file=sys.stderr)
        sys.exit(1)

    authorize(client_id)

    saved_albums = _pull_saved_albums()
    saved_tracks = _pull_saved_tracks()
    top_artists = _pull_top("artists", _map_top_artist)
    top_tracks = _pull_top("tracks", _map_top_track)
    followed_artists = _pull_followed_artists()

    library = {
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "saved_albums": saved_albums,
        "saved_tracks": saved_tracks,
        "top_artists": top_artists,
        "top_tracks": top_tracks,
        "followed_artists": followed_artists,
    }

    common.CACHE.mkdir(parents=True, exist_ok=True)
    common.save_json(OUTPUT_PATH, library)

    top_artists_summary = "+".join(str(len(top_artists[t])) for t in TOP_RANGES)
    top_tracks_summary = "+".join(str(len(top_tracks[t])) for t in TOP_RANGES)
    print(
        f"saved_albums: {len(saved_albums)} / saved_tracks: {len(saved_tracks)} / "
        f"top_artists: {top_artists_summary} / top_tracks: {top_tracks_summary} / "
        f"followed: {len(followed_artists)}"
    )


if __name__ == "__main__":
    main()

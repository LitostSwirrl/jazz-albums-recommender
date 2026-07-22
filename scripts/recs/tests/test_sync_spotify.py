import base64
import hashlib
import json
import re
import time

import pytest
import requests

from scripts.recs import sync_spotify

UNRESERVED_RE = re.compile(r"^[A-Za-z0-9\-._~]+$")


@pytest.fixture(autouse=True)
def _reset_auth_state():
    """sync_spotify._auth is module-level state mutated by authorize()/_refresh_auth();
    clear it before and after every test so tests can't leak tokens into each other."""
    sync_spotify._auth.clear()
    yield
    sync_spotify._auth.clear()


class FakeResp:
    """Fake requests.Response, modeled on the fake-response pattern in
    test_common.py::test_cached_get_json_params_in_key -- hoisted to module scope
    here since several api_get tests share it."""

    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = {} if payload is None else payload
        self.headers = headers or {}
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)


# --- Fixtures modeled on real Spotify Web API response shapes ---

SAVED_ALBUM_ITEM = {
    "added_at": "2023-05-01T12:00:00Z",
    "album": {
        "id": "2e2E6QiOO95idJELO2MnKb",
        "name": "A Love Supreme",
        "artists": [{"name": "John Coltrane", "id": "abc123"}],
        "release_date": "1965-01-14",
        "release_date_precision": "day",
    },
}

SAVED_TRACK_ITEM = {
    "added_at": "2023-06-02T08:30:00Z",
    "track": {
        "id": "4d4nqwrIfBv6nJpV7bY7Zy",
        "name": "So What",
        "artists": [{"name": "Miles Davis", "id": "0kbYTNQb4Pb1rPbbaF0pT4"}],
        "album": {"id": "1weenld61qoidwYuZ1GESA", "name": "Kind of Blue"},
    },
}

TOP_ARTIST_ITEM = {
    "id": "0kbYTNQb4Pb1rPbbaF0pT4",
    "name": "Herbie Hancock",
    "genres": ["jazz", "jazz fusion"],
}

TOP_TRACK_ITEM = {
    "id": "3JIxjvbbDrA9ztYlNcp3yL",
    "name": "Cantaloupe Island",
    "artists": [{"name": "Herbie Hancock", "id": "0kbYTNQb4Pb1rPbbaF0pT4"}],
    "album": {"id": "6PPWvVQxxHOSMB6Mvhqvw3", "name": "Empyrean Isles"},
}

FOLLOWED_ARTIST_ITEM = {
    "id": "1Yox196W7Bt1TL8LiHTsfV",
    "name": "Wayne Shorter",
    "genres": ["jazz"],
}


# --- (a) pkce_pair() ---


def test_pkce_pair_verifier_length_and_charset():
    verifier, _ = sync_spotify.pkce_pair()
    assert 43 <= len(verifier) <= 128
    assert UNRESERVED_RE.match(verifier)


def test_pkce_pair_verifier_random_each_call():
    v1, _ = sync_spotify.pkce_pair()
    v2, _ = sync_spotify.pkce_pair()
    assert v1 != v2


def test_pkce_pair_challenge_matches_spec():
    verifier, challenge = sync_spotify.pkce_pair()
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .decode("ascii")
        .rstrip("=")
    )
    assert challenge == expected
    assert "=" not in challenge


def test_authorize_url_contains_pkce_params():
    url = sync_spotify._authorize_url("test-client-id", "test-challenge")
    assert url.startswith("https://accounts.spotify.com/authorize?")
    assert "client_id=test-client-id" in url
    assert "response_type=code" in url
    assert "code_challenge_method=S256" in url
    assert "code_challenge=test-challenge" in url
    assert "redirect_uri=http%3A%2F%2F127.0.0.1%3A8888%2Fcallback" in url


# --- (b) mappers ---


def test_extract_year_variants():
    assert sync_spotify._extract_year("1965-01-14") == 1965
    assert sync_spotify._extract_year("1965-01") == 1965
    assert sync_spotify._extract_year("1965") == 1965
    assert sync_spotify._extract_year("") is None
    assert sync_spotify._extract_year(None) is None


def test_map_saved_album_full_precision_date():
    result = sync_spotify._map_saved_album(SAVED_ALBUM_ITEM)
    assert result == {
        "spotify_id": "2e2E6QiOO95idJELO2MnKb",
        "title": "A Love Supreme",
        "artists": ["John Coltrane"],
        "year": 1965,
        "added_at": "2023-05-01T12:00:00Z",
    }


def test_map_saved_album_multi_artist_and_year_only_date():
    item = {
        "added_at": "2023-05-01T12:00:00Z",
        "album": {
            "id": "xyz",
            "name": "Money Jungle",
            "artists": [
                {"name": "Duke Ellington"},
                {"name": "Charles Mingus"},
                {"name": "Max Roach"},
            ],
            "release_date": "1963",
        },
    }
    result = sync_spotify._map_saved_album(item)
    assert result["artists"] == ["Duke Ellington", "Charles Mingus", "Max Roach"]
    assert result["year"] == 1963


def test_map_saved_album_missing_release_date():
    item = {
        "added_at": "2023-05-01T12:00:00Z",
        "album": {
            "id": "xyz",
            "name": "No Date Album",
            "artists": [{"name": "Someone"}],
        },
    }
    result = sync_spotify._map_saved_album(item)
    assert result["year"] is None


def test_map_saved_track():
    result = sync_spotify._map_saved_track(SAVED_TRACK_ITEM)
    assert result == {
        "spotify_id": "4d4nqwrIfBv6nJpV7bY7Zy",
        "title": "So What",
        "artists": ["Miles Davis"],
        "album": "Kind of Blue",
        "album_spotify_id": "1weenld61qoidwYuZ1GESA",
        "added_at": "2023-06-02T08:30:00Z",
    }


def test_map_top_artist_assigns_rank():
    result = sync_spotify._map_top_artist(TOP_ARTIST_ITEM, 3)
    assert result == {
        "rank": 3,
        "name": "Herbie Hancock",
        "spotify_id": "0kbYTNQb4Pb1rPbbaF0pT4",
        "genres": ["jazz", "jazz fusion"],
    }


def test_map_top_artist_missing_genres_defaults_empty():
    item = {"id": "abc", "name": "No Genre Artist"}
    result = sync_spotify._map_top_artist(item, 1)
    assert result["genres"] == []


def test_map_top_track_assigns_rank():
    result = sync_spotify._map_top_track(TOP_TRACK_ITEM, 1)
    assert result == {
        "rank": 1,
        "title": "Cantaloupe Island",
        "artists": ["Herbie Hancock"],
        "album_spotify_id": "6PPWvVQxxHOSMB6Mvhqvw3",
    }


def test_map_followed_artist():
    result = sync_spotify._map_followed_artist(FOLLOWED_ARTIST_ITEM)
    assert result == {"name": "Wayne Shorter", "spotify_id": "1Yox196W7Bt1TL8LiHTsfV"}


# --- (c) pagination loop logic ---


def test_paginate_offset_aggregates_all_pages_and_calls_expected_offsets():
    pages = {
        0: {"items": [{"id": 1}, {"id": 2}], "total": 5},
        2: {"items": [{"id": 3}, {"id": 4}], "total": 5},
        4: {"items": [{"id": 5}], "total": 5},
    }
    calls = []

    def fetch(offset):
        calls.append(offset)
        return pages[offset]

    result = sync_spotify._paginate_offset(fetch)
    assert [item["id"] for item in result] == [1, 2, 3, 4, 5]
    assert calls == [0, 2, 4]


def test_paginate_offset_single_page():
    def fetch(offset):
        assert offset == 0
        return {"items": [{"id": "only"}], "total": 1}

    result = sync_spotify._paginate_offset(fetch)
    assert result == [{"id": "only"}]


def test_paginate_offset_empty_library_makes_one_call():
    calls = []

    def fetch(offset):
        calls.append(offset)
        return {"items": [], "total": 0}

    result = sync_spotify._paginate_offset(fetch)
    assert result == []
    assert calls == [0]


def test_paginate_cursor_aggregates_until_no_after():
    pages = {
        None: {"items": [{"id": "a"}, {"id": "b"}], "cursors": {"after": "cursor1"}},
        "cursor1": {"items": [{"id": "c"}], "cursors": {"after": "cursor2"}},
        "cursor2": {"items": [{"id": "d"}], "cursors": {"after": None}},
    }
    calls = []

    def fetch(after):
        calls.append(after)
        return pages[after]

    result = sync_spotify._paginate_cursor(fetch)
    assert [item["id"] for item in result] == ["a", "b", "c", "d"]
    assert calls == [None, "cursor1", "cursor2"]


def test_paginate_cursor_single_page_no_after():
    def fetch(after):
        assert after is None
        return {"items": [{"id": "x"}], "cursors": {"after": None}}

    result = sync_spotify._paginate_cursor(fetch)
    assert result == [{"id": "x"}]


def test_paginate_cursor_empty():
    def fetch(after):
        return {"items": [], "cursors": {}}

    result = sync_spotify._paginate_cursor(fetch)
    assert result == []


# --- (d) callback path routing + capture loop (Finding 1) ---


def test_parse_callback_request_stray_path_is_not_callback():
    is_callback, code, error = sync_spotify._parse_callback_request("/favicon.ico?x=1")
    assert is_callback is False
    assert code is None
    assert error is None


def test_parse_callback_request_extracts_code():
    is_callback, code, error = sync_spotify._parse_callback_request(
        "/callback?code=abc123&state=xyz"
    )
    assert is_callback is True
    assert code == "abc123"
    assert error is None


def test_parse_callback_request_extracts_error():
    is_callback, code, error = sync_spotify._parse_callback_request(
        "/callback?error=access_denied"
    )
    assert is_callback is True
    assert code is None
    assert error == "access_denied"


def test_capture_loop_stops_once_receive_one_succeeds():
    results = iter([False, False, True])
    calls = []

    def receive_one():
        calls.append(1)
        return next(results)

    found = sync_spotify._capture_loop(receive_one, max_requests=50)
    assert found is True
    assert len(calls) == 3


def test_capture_loop_gives_up_after_max_requests_no_infinite_loop():
    calls = []

    def receive_one():
        calls.append(1)
        return False

    found = sync_spotify._capture_loop(receive_one, max_requests=5)
    assert found is False
    assert len(calls) == 5


def test_capture_loop_stray_request_then_real_callback():
    """A stray GET (browser prefetch/extension probe) must not consume the
    one-shot slot -- the loop keeps going until the real /callback request, using
    the real path-parsing logic (_parse_callback_request), not a re-implementation
    of it."""
    incoming = ["/favicon.ico", "/robots.txt", "/callback?code=xyz789"]
    captured = {"code": None, "error": None}

    def receive_one():
        path = incoming.pop(0)
        is_callback, code, error = sync_spotify._parse_callback_request(path)
        if not is_callback:
            return False
        captured["code"] = code
        captured["error"] = error
        return True

    found = sync_spotify._capture_loop(receive_one, max_requests=50)
    assert found is True
    assert captured == {"code": "xyz789", "error": None}
    assert incoming == []  # exactly 3 requests consumed -- no extras, no shortfall


# --- (e) api_get retry paths (Finding 2) ---


def test_api_get_401_refreshes_once_and_retries_with_new_token(monkeypatch):
    sync_spotify._auth.update(
        {
            "client_id": "test-client",
            "access_token": "old-access-token",
            "refresh_token": "old-refresh-token",
            "expires_at": time.time() + 3600,
        }
    )

    get_calls = []
    post_calls = []
    saved_tokens = []

    def fake_get(url, params=None, headers=None, timeout=None):
        get_calls.append(headers["Authorization"])
        if headers["Authorization"] == "Bearer old-access-token":
            return FakeResp(401)
        return FakeResp(200, {"items": [], "total": 0})

    def fake_post(url, data=None, timeout=None):
        post_calls.append(data)
        return FakeResp(
            200,
            {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600,
            },
        )

    def fake_save_token(token):
        saved_tokens.append(token)

    monkeypatch.setattr(sync_spotify.requests, "get", fake_get)
    monkeypatch.setattr(sync_spotify.requests, "post", fake_post)
    monkeypatch.setattr(sync_spotify, "_save_token", fake_save_token)

    result = sync_spotify.api_get("/me/albums", {"limit": 50, "offset": 0})

    assert result == {"items": [], "total": 0}
    # retried request used the refreshed bearer token, not the stale one
    assert get_calls == ["Bearer old-access-token", "Bearer new-access-token"]
    # refresh happened exactly once
    assert len(post_calls) == 1
    assert post_calls[0]["refresh_token"] == "old-refresh-token"
    # rotated tokens landed in module auth state
    assert sync_spotify._auth["access_token"] == "new-access-token"
    assert sync_spotify._auth["refresh_token"] == "new-refresh-token"
    # ... and were persisted (rotated refresh token included, per Spotify's rotation)
    assert len(saved_tokens) == 1
    assert saved_tokens[0]["access_token"] == "new-access-token"
    assert saved_tokens[0]["refresh_token"] == "new-refresh-token"


def test_api_get_401_then_refresh_then_second_401_raises_no_infinite_loop(
    monkeypatch,
):
    sync_spotify._auth.update(
        {
            "client_id": "test-client",
            "access_token": "old-access-token",
            "refresh_token": "old-refresh-token",
            "expires_at": time.time() + 3600,
        }
    )

    get_calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        get_calls.append(headers["Authorization"])
        return FakeResp(401)

    def fake_post(url, data=None, timeout=None):
        return FakeResp(
            200,
            {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600,
            },
        )

    monkeypatch.setattr(sync_spotify.requests, "get", fake_get)
    monkeypatch.setattr(sync_spotify.requests, "post", fake_post)
    monkeypatch.setattr(sync_spotify, "_save_token", lambda token: None)

    with pytest.raises(requests.HTTPError):
        sync_spotify.api_get("/me/albums")

    # exactly two attempts -- the retry after refresh does not itself retry
    assert len(get_calls) == 2
    assert get_calls == ["Bearer old-access-token", "Bearer new-access-token"]


def test_api_get_429_sleeps_retry_after_seconds_then_retries(monkeypatch):
    sync_spotify._auth.update({"access_token": "tok"})

    call_count = {"n": 0}

    def fake_get(url, params=None, headers=None, timeout=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return FakeResp(429, headers={"Retry-After": "3"})
        return FakeResp(200, {"ok": True})

    sleeps = []
    monkeypatch.setattr(sync_spotify.requests, "get", fake_get)
    monkeypatch.setattr(sync_spotify.time, "sleep", lambda s: sleeps.append(s))

    result = sync_spotify.api_get("/me/tracks")

    assert result == {"ok": True}
    assert sleeps == [3]  # slept for exactly the Retry-After value, not the default
    assert call_count["n"] == 2

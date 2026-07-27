import pytest
import requests

from scripts.recs import common


def test_norm_basic():
    assert common.norm("The Jazz Messengers") == "jazz messengers"
    assert common.norm("Météo") == "meteo"


def test_norm_title_strips_editions():
    assert common.norm_title("Blue Train (Remastered 2003)") == "blue train"
    assert common.norm_title("Speak No Evil [RVG Edition]") == "speak no evil"


def test_norm_title_keeps_real_parens():
    assert common.norm_title("Money Jungle (Provocative in Blue)") != "money jungle"


def test_norm_key():
    assert (
        common.norm_key("The Bill Evans Trio", "Portrait in Jazz (OJC)")
        == "bill evans trio::portrait in jazz"
    )


def test_spotify_album_id():
    assert (
        common.spotify_album_id("https://open.spotify.com/album/2e2E6QiOO95idJELO2MnKb")
        == "2e2E6QiOO95idJELO2MnKb"
    )
    assert common.spotify_album_id("") is None


def test_http_stats_cache_hit_vs_api_call(monkeypatch, tmp_path):
    import json as json_module

    class FakeResp:
        status_code = 200
        headers = {}

        def __init__(self, payload):
            self._payload = payload
            self.text = json_module.dumps(payload)

        def json(self):
            return self._payload

    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(url)
        return FakeResp({"ok": True})

    monkeypatch.setattr(common, "CACHE", tmp_path)
    monkeypatch.setattr(common.requests, "get", fake_get)
    common.http_stats.clear()

    common.cached_get_json("b", "https://x/one", min_interval=0)  # miss
    common.cached_get_json("b", "https://x/one", min_interval=0)  # same key -> hit

    assert common.http_stats["api_calls"] == 1
    assert common.http_stats["cache_hits"] == 1
    assert len(calls) == 1


def test_http_stats_429_retry_counts_as_one_api_call(monkeypatch, tmp_path):
    import json as json_module

    class FakeResp:
        def __init__(self, status_code, payload, headers=None):
            self.status_code = status_code
            self._payload = payload
            self.text = json_module.dumps(payload)
            self.headers = headers or {}

        def json(self):
            return self._payload

    responses = [
        FakeResp(429, {}, headers={"Retry-After": "0"}),
        FakeResp(200, {"ok": True}),
    ]

    def fake_get(url, params=None, headers=None, timeout=None):
        return responses.pop(0)

    monkeypatch.setattr(common, "CACHE", tmp_path)
    monkeypatch.setattr(common.requests, "get", fake_get)
    common.http_stats.clear()

    common.cached_get_json("b", "https://x/two", min_interval=0)

    assert common.http_stats["api_calls"] == 1
    assert common.http_stats["cache_hits"] == 0


def test_cached_get_json_params_in_key(monkeypatch, tmp_path):
    import json as json_module

    calls = []

    class FakeResp:
        status_code = 200
        headers = {}

        def __init__(self, payload):
            self._payload = payload
            self.text = json_module.dumps(payload)

        def json(self):
            return self._payload

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(params)
        return FakeResp({"echo": params})

    monkeypatch.setattr(common, "CACHE", tmp_path)
    monkeypatch.setattr(common.requests, "get", fake_get)
    a = common.cached_get_json(
        "b", "https://x/search", params={"q": "kind of blue"}, min_interval=0
    )
    b = common.cached_get_json(
        "b", "https://x/search", params={"q": "giant steps"}, min_interval=0
    )
    assert len(calls) == 2
    assert a != b


# --- Finding 3: every request carries a connect/read timeout ---


def test_cached_get_json_sets_timeout_on_first_call_and_429_retry(
    monkeypatch, tmp_path
):
    """requests has no default timeout: a server that accepts the connection
    and never answers hangs an unattended multi-hour run with no output."""
    import json as json_module

    timeouts = []

    class FakeResp:
        def __init__(self, status_code, payload, headers=None):
            self.status_code = status_code
            self._payload = payload
            self.text = json_module.dumps(payload)
            self.headers = headers or {}

        def json(self):
            return self._payload

    responses = [
        FakeResp(429, {}, headers={"Retry-After": "0"}),
        FakeResp(200, {"ok": True}),
    ]

    def fake_get(url, params=None, headers=None, timeout=None):
        timeouts.append(timeout)
        return responses.pop(0)

    monkeypatch.setattr(common, "CACHE", tmp_path)
    monkeypatch.setattr(common.requests, "get", fake_get)

    common.cached_get_json("b", "https://x/slow", min_interval=0)

    assert timeouts == [(10, 30), (10, 30)]


# --- Finding 1: never cache a body that is not what the caller asked for ---


def test_cached_get_json_does_not_cache_json_error_body(monkeypatch, tmp_path):
    """Last.fm answers rate limits (code 29) and outages (8/16) with HTTP 200
    and a JSON error body. Caching one makes the skip permanent: every later
    run reads it as a hit and no rerun can heal it."""
    import json as json_module

    error_body = {"error": 29, "message": "Rate limit exceeded"}

    class FakeResp:
        status_code = 200
        headers: dict = {}
        text = json_module.dumps(error_body)

        def json(self):
            return error_body

    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(url)
        return FakeResp()

    monkeypatch.setattr(common, "CACHE", tmp_path)
    monkeypatch.setattr(common.requests, "get", fake_get)

    first = common.cached_get_json("lastfm", "https://x/tags", min_interval=0)
    second = common.cached_get_json("lastfm", "https://x/tags", min_interval=0)

    assert first == error_body
    assert second == error_body
    assert list((tmp_path / "http" / "lastfm").glob("*.json")) == []
    assert len(calls) == 2  # not served from a poisoned cache


def test_cached_get_json_does_not_cache_non_json_200(monkeypatch, tmp_path):
    """A proxy interstitial or captive-portal page returned as HTTP 200 must
    not land in the permanent cache -- otherwise every later run re-reads it
    and raises identically until someone finds the SHA-1-named file."""
    interstitial = "<html><body>sign in to continue</body></html>"

    class FakeResp:
        status_code = 200
        headers: dict = {}
        text = interstitial

        def json(self):
            raise requests.exceptions.JSONDecodeError(
                "Expecting value", interstitial, 0
            )

    monkeypatch.setattr(common, "CACHE", tmp_path)
    monkeypatch.setattr(common.requests, "get", lambda *a, **k: FakeResp())

    with pytest.raises(requests.RequestException):
        common.cached_get_json("lastfm", "https://x/portal", min_interval=0)

    assert list((tmp_path / "http" / "lastfm").glob("*.json")) == []


def test_cached_get_json_still_caches_a_normal_json_body(monkeypatch, tmp_path):
    """Guard against over-correcting: an ordinary payload is still cached, so
    a warm rerun stays free."""
    import json as json_module

    payload = {"artist": {"name": "Miles Davis"}}

    class FakeResp:
        status_code = 200
        headers: dict = {}
        text = json_module.dumps(payload)

        def json(self):
            return payload

    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(url)
        return FakeResp()

    monkeypatch.setattr(common, "CACHE", tmp_path)
    monkeypatch.setattr(common.requests, "get", fake_get)

    common.cached_get_json("lastfm", "https://x/ok", min_interval=0)
    common.cached_get_json("lastfm", "https://x/ok", min_interval=0)

    assert len(calls) == 1
    assert len(list((tmp_path / "http" / "lastfm").glob("*.json"))) == 1


# --- Finding 4: writes land atomically, never as a truncated file ---


def _interrupt(*_args, **_kwargs):
    raise KeyboardInterrupt


def test_cached_get_json_interrupted_write_leaves_no_cache_hit(monkeypatch, tmp_path):
    """Ctrl-C mid-write must leave no file at the cache path: a truncated
    text bucket (a Pitchfork listing page, a Reddit RSS feed) reads back as a
    perfectly good short page and silently truncates the next crawl."""

    class FakeResp:
        status_code = 200
        headers: dict = {}
        text = "<html>a very long listing page</html>"

        def json(self):
            return {}

    monkeypatch.setattr(common, "CACHE", tmp_path)
    monkeypatch.setattr(common.requests, "get", lambda *a, **k: FakeResp())
    monkeypatch.setattr(common.os, "replace", _interrupt)

    with pytest.raises(KeyboardInterrupt):
        common.cached_get_json(
            "pitchfork", "https://x/listing", min_interval=0, as_text=True
        )

    assert list((tmp_path / "http" / "pitchfork").glob("*.json")) == []


def test_save_json_interrupted_write_leaves_previous_file_intact(monkeypatch, tmp_path):
    """cache/discogs.json is 868KB of expensive-to-rebuild data with no
    backup -- an interrupt must not destroy the previous good file."""
    path = tmp_path / "discogs.json"
    common.save_json(path, {"releases": [1, 2, 3]})

    monkeypatch.setattr(common.os, "replace", _interrupt)
    with pytest.raises(KeyboardInterrupt):
        common.save_json(path, {"releases": []})

    assert common.load_json(path) == {"releases": [1, 2, 3]}


def test_save_json_leaves_no_tmp_sibling_behind(tmp_path):
    path = tmp_path / "out.json"
    common.save_json(path, {"a": 1})

    assert common.load_json(path) == {"a": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["out.json"]


# --- Finding 8: the error line can never carry a query string ---


def test_cached_get_json_error_line_omits_query_string(monkeypatch, tmp_path, capsys):
    """api keys ride in query params on some buckets, and fetch_reddit builds
    URLs with inline query strings -- this line must be structurally unable to
    print one."""
    placeholder = "PLACEHOLDER-MUST-NOT-BE-PRINTED"

    class FakeResp:
        status_code = 500
        headers: dict = {}
        text = "server error"

        def json(self):
            return {}

        def raise_for_status(self):
            raise requests.HTTPError("500 Server Error", response=self)

    monkeypatch.setattr(common, "CACHE", tmp_path)
    monkeypatch.setattr(common.requests, "get", lambda *a, **k: FakeResp())

    with pytest.raises(requests.HTTPError):
        common.cached_get_json(
            "lastfm",
            f"https://ws.audioscrobbler.com/2.0/?api_key={placeholder}",
            min_interval=0,
        )

    out = capsys.readouterr().out
    assert placeholder not in out
    assert "api_key" not in out
    assert "ws.audioscrobbler.com/2.0/" in out
    assert "500" in out


# --- Finding 9: the pipeline never holds Reddit credentials ---


def test_env_example_lists_no_reddit_credentials():
    """Reddit closed self-service API access; fetch_reddit uses unauthenticated
    RSS by design. Names in the template only invite creating credentials that
    add exposure and nothing else."""
    text = (common.ROOT / ".env.example").read_text(encoding="utf-8")
    assert "REDDIT_CLIENT_ID" not in text
    assert "REDDIT_CLIENT_SECRET" not in text

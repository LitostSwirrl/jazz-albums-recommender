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

    def fake_get(url, params=None, headers=None):
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

    def fake_get(url, params=None, headers=None):
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

    def fake_get(url, params=None, headers=None):
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

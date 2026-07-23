from collections import Counter

import requests

from scripts.recs import fetch_lastfm as fl


# --- top_tags: lowercase every tag name, cap at top 10 in API (count-descending) order ---


def test_top_tags_lowercases():
    tags = [{"name": "Hard Bop", "count": 50}, {"name": "GUITAR", "count": 10}]
    assert fl.top_tags(tags) == ["hard bop", "guitar"]


def test_top_tags_caps_at_ten_keeping_api_order():
    tags = [{"name": f"tag{i}", "count": 100 - i} for i in range(15)]
    result = fl.top_tags(tags)
    assert len(result) == 10
    assert result == [f"tag{i}" for i in range(10)]


def test_top_tags_empty_list_no_crash():
    assert fl.top_tags([]) == []


# --- coerce_match: Last.fm returns similarity 'match' as a string -- store float ---


def test_coerce_match_string_to_float():
    assert fl.coerce_match("0.87") == 0.87


def test_coerce_match_whole_number_string():
    assert fl.coerce_match("1") == 1.0


# --- is_soft_error: Last.fm often answers HTTP 200 with a JSON error body ---


def test_is_soft_error_true_when_error_key_present():
    body = {"error": 6, "message": "The artist you supplied could not be found"}
    assert fl.is_soft_error(body) is True


def test_is_soft_error_false_for_normal_response():
    body = {"similarartists": {"artist": []}}
    assert fl.is_soft_error(body) is False


# --- _build_tag_album_entry: norm_key construction from a Last.fm album entry ---


def test_build_tag_album_entry_constructs_norm_key():
    album = {"name": "The Colours Of Chloë", "artist": {"name": "Eberhard Weber"}}
    entry = fl._build_tag_album_entry(album)
    assert entry == {
        "artist": "Eberhard Weber",
        "title": "The Colours Of Chloë",
        "norm_key": "eberhard weber::colours of chloe",
    }


# --- _dedupe_target_names: empty-norm skip decisions + dedup by norm() ---


def test_dedupe_target_names_drops_empty_norm_and_counts():
    """common.norm() strips CJK entirely (e.g. 以莉.高露 -> "") -- an
    empty-norm name must never reach the gettoptags target list."""
    stats: Counter = Counter()
    result = fl._dedupe_target_names([["以莉.高露", "Grant Green"]], stats)
    assert result == ["Grant Green"]
    assert stats["artist_tags_skipped_empty_norm"] == 1


def test_dedupe_target_names_dedupes_by_norm_keeps_first_seen():
    stats: Counter = Counter()
    result = fl._dedupe_target_names(
        [["Grant Green"], ["The Grant Green", "Kenny Burrell"]], stats
    )
    # "Grant Green" and "The Grant Green" collide on common.norm() (leading
    # "the " is stripped) -- first-seen display name wins.
    assert result == ["Grant Green", "Kenny Burrell"]


def test_target_artist_names_unions_similar_and_tag_albums_artists():
    stats: Counter = Counter()
    similar = {"grant green": [{"name": "Kenny Burrell", "match": 0.9}]}
    tag_albums = {"ecm": [{"artist": "Eberhard Weber", "title": "X", "norm_key": "y"}]}
    result = fl._target_artist_names(similar, tag_albums, stats)
    assert set(result) == {"Kenny Burrell", "Eberhard Weber"}


# --- sweep_similar orchestration (network boundary mocked at _get, not requests) ---


def test_sweep_similar_skips_empty_norm_before_any_api_call(monkeypatch):
    def fake_get(params):
        raise AssertionError("must not call the API for an empty-norm artist")

    monkeypatch.setattr(fl, "_get", fake_get)
    stats: Counter = Counter()
    result = fl.sweep_similar([{"name": "以莉.高露"}], stats)

    assert result == {}
    assert stats["similar_skipped_empty_norm"] == 1


def test_sweep_similar_counts_soft_error_and_continues(monkeypatch):
    monkeypatch.setattr(fl, "_get", lambda params: {"error": 6, "message": "x"})
    stats: Counter = Counter()
    result = fl.sweep_similar([{"name": "Nobody Jazz"}], stats)

    assert result == {}
    assert stats["similar_skipped_not_found"] == 1


def test_sweep_similar_counts_http_error_and_continues(monkeypatch):
    def fake_get(params):
        raise requests.HTTPError("boom")

    monkeypatch.setattr(fl, "_get", fake_get)
    stats: Counter = Counter()
    result = fl.sweep_similar([{"name": "Grant Green"}], stats)

    assert result == {}
    assert stats["similar_skipped_error"] == 1


def test_sweep_similar_counts_connection_error_and_continues(monkeypatch):
    """Not just requests.HTTPError -- a lower-level requests.RequestException
    (e.g. ConnectionError/Timeout) must be caught too. Left uncaught, its
    default str() embeds the full attempted URL, and the api_key travels as
    a query param -- an uncaught exception here would print the key."""

    def fake_get(params):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(fl, "_get", fake_get)
    stats: Counter = Counter()
    result = fl.sweep_similar([{"name": "Grant Green"}], stats)

    assert result == {}
    assert stats["similar_skipped_error"] == 1


def test_sweep_similar_stores_coerced_match_floats(monkeypatch):
    def fake_get(params):
        assert params["method"] == "artist.getsimilar"
        return {
            "similarartists": {"artist": [{"name": "Kenny Burrell", "match": "0.87"}]}
        }

    monkeypatch.setattr(fl, "_get", fake_get)
    stats: Counter = Counter()
    result = fl.sweep_similar([{"name": "Grant Green"}], stats)

    assert result == {"grant green": [{"name": "Kenny Burrell", "match": 0.87}]}


# --- sweep_tag_albums orchestration: all 12 tags always present as keys ---


def test_sweep_tag_albums_all_twelve_keys_present_even_on_error(monkeypatch):
    def fake_get(params):
        if params["tag"] == fl.TAGS[0]:
            raise requests.HTTPError("boom")
        return {"albums": {"album": []}}

    monkeypatch.setattr(fl, "_get", fake_get)
    stats: Counter = Counter()
    result = fl.sweep_tag_albums(stats)

    assert set(result.keys()) == set(fl.TAGS)
    assert result[fl.TAGS[0]] == []
    assert stats["tag_albums_skipped_error"] == 1


def test_sweep_tag_albums_counts_connection_error_and_continues(monkeypatch):
    def fake_get(params):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(fl, "_get", fake_get)
    stats: Counter = Counter()
    result = fl.sweep_tag_albums(stats)

    assert set(result.keys()) == set(fl.TAGS)
    assert all(v == [] for v in result.values())
    assert stats["tag_albums_skipped_error"] == len(fl.TAGS)


# --- sweep_artist_tags orchestration ---


def test_sweep_artist_tags_stores_lowercased_capped_tags(monkeypatch):
    def fake_get(params):
        assert params["method"] == "artist.gettoptags"
        return {"toptags": {"tag": [{"name": "Hard Bop"}, {"name": "Guitar"}]}}

    monkeypatch.setattr(fl, "_get", fake_get)
    stats: Counter = Counter()
    result = fl.sweep_artist_tags(["Kenny Burrell"], stats)

    assert result == {"kenny burrell": ["hard bop", "guitar"]}
    assert stats["artist_tags_swept"] == 1


def test_sweep_artist_tags_counts_http_error_and_continues(monkeypatch):
    def fake_get(params):
        raise requests.HTTPError("boom")

    monkeypatch.setattr(fl, "_get", fake_get)
    stats: Counter = Counter()
    result = fl.sweep_artist_tags(["Ghost Artist"], stats)

    assert result == {}
    assert stats["artist_tags_skipped_error"] == 1


def test_sweep_artist_tags_counts_connection_error_and_continues(monkeypatch):
    def fake_get(params):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(fl, "_get", fake_get)
    stats: Counter = Counter()
    result = fl.sweep_artist_tags(["Ghost Artist"], stats)

    assert result == {}
    assert stats["artist_tags_skipped_error"] == 1

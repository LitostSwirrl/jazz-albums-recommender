from collections import Counter

from scripts.recs import fetch_discogs as fd


# --- clean_discogs_name: Discogs homonym '(2)' / name-variant '*' suffixes ---


def test_clean_discogs_name_no_markers():
    assert fd.clean_discogs_name("Charles Tolliver") == "Charles Tolliver"


def test_clean_discogs_name_strips_homonym_index():
    assert fd.clean_discogs_name("Bob James (2)") == "Bob James"


def test_clean_discogs_name_strips_variant_marker():
    assert fd.clean_discogs_name("John Coltrane*") == "John Coltrane"


def test_clean_discogs_name_strips_both_combined():
    assert fd.clean_discogs_name("Sonny Rollins (2)*") == "Sonny Rollins"


def test_clean_discogs_name_keeps_real_parenthetical():
    """Only a digit-only paren is a Discogs homonym marker -- a genuine
    descriptive parenthetical in a name must survive untouched."""
    assert fd.clean_discogs_name("Tribe (Chicago)") == "Tribe (Chicago)"


# --- year_spread: candidate-pool spread picker ---


def test_year_spread_returns_all_when_fewer_than_n():
    entries = [{"year": 1965, "id": 1}, {"year": 1960, "id": 2}]
    result = fd.year_spread(entries, 5)
    assert [e["id"] for e in result] == [2, 1]  # sorted ascending by year


def test_year_spread_picks_n_including_endpoints():
    entries = [{"year": y, "id": y} for y in range(1960, 1980)]  # 20 entries
    result = fd.year_spread(entries, 5)
    assert len(result) == 5
    years = [e["year"] for e in result]
    assert years[0] == 1960
    assert years[-1] == 1979
    assert years == sorted(years)


def test_year_spread_undated_entries_fill_remaining_slots_at_end():
    dated = [{"year": 1965, "id": 1}, {"year": 1970, "id": 2}]
    undated = [{"id": 3}, {"id": 4}, {"id": 5}]
    result = fd.year_spread(dated + undated, 4)
    assert [e["id"] for e in result[:2]] == [1, 2]
    assert {e["id"] for e in result[2:]} <= {3, 4, 5}
    assert len(result) == 4


def test_year_spread_all_undated_no_crash():
    entries = [{"id": 1}, {"id": 2}]
    result = fd.year_spread(entries, 5)
    assert {e["id"] for e in result} == {1, 2}


def test_year_spread_n_zero_returns_empty():
    entries = [{"year": 1965, "id": 1}]
    assert fd.year_spread(entries, 0) == []


# --- dedupe_releases: first-encountered wins, keyed by discogs_release_id ---


def test_dedupe_releases_keeps_first_encountered():
    releases = [
        {"discogs_release_id": 1, "via": "artist:A"},
        {"discogs_release_id": 2, "via": "artist:B"},
        {"discogs_release_id": 1, "via": "label:C"},
    ]
    result = fd.dedupe_releases(releases)
    assert len(result) == 2
    assert result[0]["via"] == "artist:A"


# --- _filter_main_role: artist listings carry 'role'; label listings don't ---


def test_filter_main_role_keeps_main_and_missing_role():
    entries = [
        {"role": "Main", "id": 1},
        {"role": "TrackAppearance", "id": 2},
        {"id": 3},  # no role key at all -- real shape of label-release listings
    ]
    result = fd._filter_main_role(entries)
    assert {e["id"] for e in result} == {1, 3}


# --- fix round 1: _label_query alias (Riverside -> Riverside Records) ---


def test_label_query_applies_riverside_alias():
    assert fd._label_query("Riverside") == "Riverside Records"


def test_label_query_passthrough_for_unaliased_names():
    assert fd._label_query("Blue Note") == "Blue Note"


# --- fix round 1: _build_release_entry derives artist from primary credit ---


def _fake_release(release_id, title, artists, **extra):
    base = {
        "id": release_id,
        "title": title,
        "artists": [{"name": n} for n in artists],
        "year": 1971,
        "community": {"have": 1, "want": 1, "rating": {"average": 4.5, "count": 10}},
        "labels": [],
        "extraartists": [],
        "tracklist": [],
    }
    base.update(extra)
    return base


def test_build_release_entry_uses_primary_credit_artist_not_via():
    """norm_key is the cross-source join key downstream -- artist/norm_key
    must come from the release's own primary credit (artists[0]), not
    whichever artist's/label's sweep happened to surface the release. `via`
    stays untouched, since it records provenance, not attribution."""
    release = _fake_release(
        549847, "Journey In Satchidananda", ["Alice Coltrane", "Pharoah Sanders"]
    )
    entry = fd._build_release_entry(release, "artist:Pharoah Sanders")
    assert entry["artist"] == "Alice Coltrane"
    assert entry["norm_key"] == "alice coltrane::journey in satchidananda"
    assert entry["via"] == "artist:Pharoah Sanders"


def test_build_release_entry_cleans_primary_artist_name():
    release = _fake_release(1, "Some Album", ["Bob James (2)"])
    entry = fd._build_release_entry(release, "artist:X")
    assert entry["artist"] == "Bob James"


# --- fix round 1: post-detail owned re-check (second gate, not a replacement) ---


def test_fetch_artist_release_post_detail_owned_recheck_drops_and_counts(monkeypatch):
    """Pre-detail check uses the swept artist's name + listing title, so it
    cannot see that Discogs actually credits this release primarily to
    Alice Coltrane -- confirmed below the pre-check legitimately misses it
    (owned_keys only has the Alice Coltrane key). The post-detail recheck,
    using the corrected norm_key, must catch it: drop the record, count
    owned_skipped."""
    candidate = {"id": 999, "title": "Journey In Satchidananda"}
    owned_keys = {"alice coltrane::journey in satchidananda"}
    stats: Counter[str] = Counter()
    pre_check_key = fd.common.norm_key("Pharoah Sanders", candidate["title"])
    assert pre_check_key not in owned_keys  # pre-check alone would not catch this

    def fake_get(url, params=None):
        if "/masters/" in url:
            return {"main_release": 549847}
        return _fake_release(
            549847, "Journey In Satchidananda", ["Alice Coltrane", "Pharoah Sanders"]
        )

    monkeypatch.setattr(fd, "_get", fake_get)
    result = fd._fetch_artist_release(candidate, "Pharoah Sanders", owned_keys, stats)

    assert result is None
    assert stats["owned_skipped"] == 1


def test_fetch_artist_release_keeps_corrected_artist_when_not_owned(monkeypatch):
    candidate = {"id": 999, "title": "Journey In Satchidananda"}
    owned_keys: set[str] = set()
    stats: Counter[str] = Counter()

    def fake_get(url, params=None):
        if "/masters/" in url:
            return {"main_release": 549847}
        return _fake_release(
            549847, "Journey In Satchidananda", ["Alice Coltrane", "Pharoah Sanders"]
        )

    monkeypatch.setattr(fd, "_get", fake_get)
    result = fd._fetch_artist_release(candidate, "Pharoah Sanders", owned_keys, stats)

    assert result is not None
    assert result["artist"] == "Alice Coltrane"
    assert result["norm_key"] == "alice coltrane::journey in satchidananda"
    assert result["via"] == "artist:Pharoah Sanders"
    assert stats["owned_skipped"] == 0


def test_fetch_label_release_post_detail_owned_recheck_drops_and_counts(monkeypatch):
    """Same second-gate wiring, label-sweep path: the listing's `artist`
    field can also diverge from the release detail's real primary credit."""
    candidate = {
        "id": 999,
        "title": "Journey In Satchidananda",
        "artist": "Pharoah Sanders",
    }
    owned_keys = {"alice coltrane::journey in satchidananda"}
    stats: Counter[str] = Counter()

    def fake_get(url, params=None):
        return _fake_release(
            549847, "Journey In Satchidananda", ["Alice Coltrane", "Pharoah Sanders"]
        )

    monkeypatch.setattr(fd, "_get", fake_get)
    result = fd._fetch_label_release(candidate, "Impulse!", owned_keys, stats)

    assert result is None
    assert stats["owned_skipped"] == 1

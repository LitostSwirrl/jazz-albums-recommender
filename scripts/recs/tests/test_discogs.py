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

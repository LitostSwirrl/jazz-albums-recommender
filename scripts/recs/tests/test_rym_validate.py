import pytest

from scripts.recs import common
from scripts.recs import validate_rym as vr


# --- fixtures: small synthetic RYM chart entries ---


def _spiritual_jazz_entries() -> list[dict]:
    return [
        {
            "rank": 1,
            "artist": "Pharoah Sanders",
            "album": "Karma",
            "year": 1969,
            "rating": 4.35,
            "rating_count": 6200,
        },
        {
            "rank": 2,
            "artist": "Alice Coltrane",
            "album": "Journey in Satchidananda",
            "year": 1971,
            "rating": 4.22,
            "rating_count": 5100,
        },
    ]


def _spiritual_jazz_expected() -> list[dict]:
    return [
        {
            "rank": 1,
            "norm_key": "pharoah sanders::karma",
            "artist": "Pharoah Sanders",
            "title": "Karma",
            "year": 1969,
            "rating": 4.35,
            "rating_count": 6200,
        },
        {
            "rank": 2,
            "norm_key": "alice coltrane::journey in satchidananda",
            "artist": "Alice Coltrane",
            "title": "Journey in Satchidananda",
            "year": 1971,
            "rating": 4.22,
            "rating_count": 5100,
        },
    ]


# --- validate_and_normalize: valid input -> normalized shape (plan-mandated, REQUIRED) ---


def test_validate_and_normalize_two_entry_chart_returns_normalized_shape():
    result = vr.validate_and_normalize("spiritual-jazz", _spiritual_jazz_entries())

    assert result == _spiritual_jazz_expected()


def test_validate_and_normalize_missing_rating_fails_naming_chart_and_rank():
    entries = [
        _spiritual_jazz_entries()[0],
        {
            "rank": 2,
            "artist": "Alice Coltrane",
            "album": "Journey in Satchidananda",
            "year": 1971,
            # "rating" missing
            "rating_count": 5100,
        },
    ]

    with pytest.raises(ValueError) as exc_info:
        vr.validate_and_normalize("spiritual-jazz", entries)

    message = str(exc_info.value)
    assert "spiritual-jazz" in message
    assert "rank 2" in message


# --- other real validation branches the contract implies ---


def test_validate_and_normalize_rating_out_of_range_fails():
    entries = [
        {
            "rank": 3,
            "artist": "Art Blakey",
            "album": "Moanin",
            "year": 1959,
            "rating": 5.5,
            "rating_count": 100,
        }
    ]

    with pytest.raises(ValueError) as exc_info:
        vr.validate_and_normalize("hard-bop", entries)

    message = str(exc_info.value)
    assert "hard-bop" in message
    assert "rank 3" in message


def test_validate_and_normalize_rating_count_zero_fails():
    entries = [
        {
            "rank": 5,
            "artist": "Art Blakey",
            "album": "Moanin",
            "year": 1959,
            "rating": 4.0,
            "rating_count": 0,
        }
    ]

    with pytest.raises(ValueError) as exc_info:
        vr.validate_and_normalize("hard-bop", entries)

    message = str(exc_info.value)
    assert "hard-bop" in message
    assert "rank 5" in message


def test_validate_and_normalize_year_null_passes():
    entries = [
        {
            "rank": 1,
            "artist": "Sun Ra",
            "album": "Space Is the Place",
            "year": None,
            "rating": 4.1,
            "rating_count": 900,
        }
    ]

    result = vr.validate_and_normalize("avant-garde-jazz", entries)

    assert result[0]["year"] is None


def test_validate_and_normalize_year_non_int_fails():
    """year present-and-not-null must be int -- a stray string must not pass
    through un-validated into rym.json (contract: 'if present-and-not-null
    it must be int')."""
    entries = [
        {
            "rank": 1,
            "artist": "Sun Ra",
            "album": "Space Is the Place",
            "year": "1973",
            "rating": 4.1,
            "rating_count": 900,
        }
    ]

    with pytest.raises(ValueError) as exc_info:
        vr.validate_and_normalize("avant-garde-jazz", entries)

    message = str(exc_info.value)
    assert "avant-garde-jazz" in message
    assert "rank 1" in message


def test_validate_and_normalize_int_rating_passes():
    """Contract: rating is 'a number (int or float) in the range 0.0-5.0' --
    a whole-number rating captured as a bare JSON int must not be rejected."""
    entries = [
        {
            "rank": 1,
            "artist": "Art Blakey",
            "album": "Moanin",
            "year": 1959,
            "rating": 4,
            "rating_count": 100,
        }
    ]

    result = vr.validate_and_normalize("hard-bop", entries)

    assert result[0]["rating"] == 4


def test_validate_and_normalize_norm_key_strips_edition_marker():
    entries = [
        {
            "rank": 1,
            "artist": "The Bill Evans Trio",
            "album": "Portrait in Jazz (OJC)",
            "year": 1960,
            "rating": 4.5,
            "rating_count": 3000,
        }
    ]

    result = vr.validate_and_normalize("hard-bop", entries)

    assert result[0]["norm_key"] == "bill evans trio::portrait in jazz"


# --- main(): loads every cache/rym_charts/*.json, writes cache/rym.json,
# prints per-chart counts + a total ---


def test_main_writes_rym_json_and_prints_per_chart_counts_and_total(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr(vr.common, "CACHE", tmp_path)
    charts_dir = tmp_path / "rym_charts"
    charts_dir.mkdir()
    common.save_json(charts_dir / "spiritual-jazz.json", _spiritual_jazz_entries())
    common.save_json(
        charts_dir / "hard-bop.json",
        [
            {
                "rank": 1,
                "artist": "Art Blakey",
                "album": "Moanin",
                "year": 1959,
                "rating": 4.4,
                "rating_count": 8000,
            }
        ],
    )

    vr.main()

    written = common.load_json(tmp_path / "rym.json")
    assert written == {
        "charts": {
            "spiritual-jazz": _spiritual_jazz_expected(),
            "hard-bop": [
                {
                    "rank": 1,
                    "norm_key": common.norm_key("Art Blakey", "Moanin"),
                    "artist": "Art Blakey",
                    "title": "Moanin",
                    "year": 1959,
                    "rating": 4.4,
                    "rating_count": 8000,
                }
            ],
        }
    }

    out = capsys.readouterr().out
    assert "spiritual-jazz: 2 entries" in out
    assert "hard-bop: 1 entries" in out
    assert "total: 3 entries across 2 charts" in out


def test_main_missing_dir_exits_with_stderr_message(monkeypatch, tmp_path, capsys):
    """cache/rym_charts/ absent entirely (Step 2 capture never run yet) ->
    one-line stderr instruction + exit 1, no rym.json written."""
    monkeypatch.setattr(vr.common, "CACHE", tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        vr.main()

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "cache/rym_charts/ has no chart files" in err
    assert not (tmp_path / "rym.json").exists()

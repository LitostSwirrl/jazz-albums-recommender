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


# --- validate_charts: valid input -> normalized shape (title/norm_key mapping) ---


def test_validate_charts_two_entry_chart_returns_normalized_shape(tmp_path):
    common.save_json(tmp_path / "spiritual-jazz.json", _spiritual_jazz_entries())

    charts = vr.validate_charts(tmp_path)

    assert charts == {"spiritual-jazz": _spiritual_jazz_expected()}


# --- main: writes cache/rym.json {"charts": {...}} + prints per-chart counts ---


def test_main_writes_rym_json_and_prints_per_chart_counts(
    monkeypatch, tmp_path, capsys
):
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
    output_path = tmp_path / "rym.json"
    monkeypatch.setattr(vr, "CHARTS_DIR", charts_dir)
    monkeypatch.setattr(vr, "OUTPUT_PATH", output_path)

    vr.main()

    written = common.load_json(output_path)
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


# --- contract (b): missing rating fails loud naming chart+rank, no output written ---


def test_main_missing_rating_fails_loud_no_output_written(
    monkeypatch, tmp_path, capsys
):
    charts_dir = tmp_path / "rym_charts"
    charts_dir.mkdir()
    common.save_json(
        charts_dir / "spiritual-jazz.json",
        [
            _spiritual_jazz_entries()[0],
            {
                "rank": 2,
                "artist": "Alice Coltrane",
                "album": "Journey in Satchidananda",
                "year": 1971,
                # "rating" missing
                "rating_count": 5100,
            },
        ],
    )
    output_path = tmp_path / "rym.json"
    monkeypatch.setattr(vr, "CHARTS_DIR", charts_dir)
    monkeypatch.setattr(vr, "OUTPUT_PATH", output_path)

    with pytest.raises(SystemExit) as exc_info:
        vr.main()

    assert exc_info.value.code == 1
    out = capsys.readouterr().out
    assert "spiritual-jazz" in out
    assert "rank 2" in out
    assert not output_path.exists()


# --- edge cases the contract implies ---


def test_validate_charts_rating_out_of_range_fails_naming_chart_and_rank(
    tmp_path, capsys
):
    common.save_json(
        tmp_path / "hard-bop.json",
        [
            {
                "rank": 3,
                "artist": "Art Blakey",
                "album": "Moanin",
                "year": 1959,
                "rating": 5.5,
                "rating_count": 100,
            }
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        vr.validate_charts(tmp_path)

    assert exc_info.value.code == 1
    out = capsys.readouterr().out
    assert "hard-bop" in out
    assert "rank 3" in out


def test_validate_charts_rating_count_zero_fails_naming_chart_and_rank(
    tmp_path, capsys
):
    common.save_json(
        tmp_path / "hard-bop.json",
        [
            {
                "rank": 5,
                "artist": "Art Blakey",
                "album": "Moanin",
                "year": 1959,
                "rating": 4.0,
                "rating_count": 0,
            }
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        vr.validate_charts(tmp_path)

    assert exc_info.value.code == 1
    out = capsys.readouterr().out
    assert "hard-bop" in out
    assert "rank 5" in out


def test_validate_charts_empty_dir_fails_loud(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        vr.validate_charts(tmp_path)

    assert exc_info.value.code == 1

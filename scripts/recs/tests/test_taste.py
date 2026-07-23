import pytest

from scripts.recs import build_taste_profile as tp

FAKE_LIB = {
    "saved_albums": [
        {
            "spotify_id": "AAA",
            "title": "Idle Moments",
            "artists": ["Grant Green"],
            "year": 1964,
            "added_at": "",
        }
    ],
    "saved_tracks": [
        {
            "spotify_id": "t1",
            "title": "x",
            "artists": ["Grant Green"],
            "album": "y",
            "album_spotify_id": "",
            "added_at": "",
        }
    ]
    * 3,
    "top_artists": {
        "short_term": [
            {"rank": 1, "name": "Grant Green", "spotify_id": "g", "genres": []}
        ],
        "medium_term": [],
        "long_term": [],
    },
    "top_tracks": {"short_term": [], "medium_term": [], "long_term": []},
    "followed_artists": [{"name": "Grant Green", "spotify_id": "g"}],
}
FAKE_CATALOG = [
    {
        "id": "idle-moments",
        "title": "Idle Moments",
        "artist": "Grant Green",
        "spotifyUrl": "https://open.spotify.com/album/AAA",
        "label": "Blue Note",
        "genres": ["hard bop"],
    },
    {
        "id": "matador",
        "title": "The Matador",
        "artist": "Grant Green",
        "spotifyUrl": "",
        "label": "Blue Note",
        "genres": ["hard bop"],
    },
]


def test_affinity_weights():
    scores = tp.affinity_scores(FAKE_LIB)
    g = scores["grant green"]
    assert g["saved_albums"] == 1 and g["saved_tracks"] == 3 and g["followed"]
    assert g["score"] == 5.0 + 3.0 + (50 / 50 * 10 * 1.5) + 2.0  # 25.0


def test_match_owned_by_spotify_id():
    owned, unmatched = tp.match_owned(FAKE_LIB["saved_albums"], FAKE_CATALOG)
    assert owned["catalog_ids"] == ["idle-moments"] and unmatched == []


def test_unmatched_reported():
    lib = [
        {
            "spotify_id": "ZZZ",
            "title": "Nonexistent",
            "artists": ["Nobody"],
            "year": 0,
            "added_at": "",
        }
    ]
    owned, unmatched = tp.match_owned(lib, FAKE_CATALOG)
    assert len(unmatched) == 1


# --- own additions: real behavioral holes the brief's fixtures don't exercise ---


def test_affinity_credits_every_listed_artist():
    """Multi-artist saved album -- brief's FAKE_LIB only has single-artist
    entries, so 'credit EACH listed artist' (context bullet) is otherwise
    never exercised."""
    lib = {
        "saved_albums": [
            {
                "spotify_id": "MJ",
                "title": "Money Jungle",
                "artists": ["Duke Ellington", "Charles Mingus", "Max Roach"],
                "year": 1963,
                "added_at": "",
            }
        ],
        "saved_tracks": [],
        "top_artists": {"short_term": [], "medium_term": [], "long_term": []},
        "top_tracks": {"short_term": [], "medium_term": [], "long_term": []},
        "followed_artists": [],
    }
    scores = tp.affinity_scores(lib)
    assert scores["duke ellington"]["saved_albums"] == 1
    assert scores["charles mingus"]["saved_albums"] == 1
    assert scores["max roach"]["saved_albums"] == 1
    assert scores["duke ellington"]["score"] == 5.0


def test_match_owned_fuzzy_below_threshold_no_match():
    """'idle moxents' vs catalog 'idle moments' -- SequenceMatcher ratio is
    0.9167 (verified directly against common.norm_title + difflib), just
    under FUZZY_TITLE_THRESHOLD (0.92): must NOT match."""
    lib = [
        {
            "spotify_id": "TYPO1",
            "title": "Idle Moxents",
            "artists": ["Grant Green"],
            "year": 1964,
            "added_at": "",
        }
    ]
    owned, unmatched = tp.match_owned(lib, FAKE_CATALOG)
    assert owned["catalog_ids"] == []
    assert len(unmatched) == 1


def test_match_owned_fuzzy_at_threshold_matches():
    """'idle momentss' vs catalog 'idle moments' -- ratio 0.96, over
    FUZZY_TITLE_THRESHOLD (0.92): must match despite no exact norm_key hit."""
    lib = [
        {
            "spotify_id": "TYPO2",
            "title": "Idle Momentss",
            "artists": ["Grant Green"],
            "year": 1964,
            "added_at": "",
        }
    ]
    owned, unmatched = tp.match_owned(lib, FAKE_CATALOG)
    assert owned["catalog_ids"] == ["idle-moments"]
    assert unmatched == []


def test_match_owned_catalog_missing_spotify_url_key():
    """Real catalog data (src/data/albums.json) has 28/1000 records where
    'spotifyUrl' is absent entirely, not just empty (verified directly against
    the file) -- the brief's FAKE_CATALOG always includes the key, so this
    never gets exercised there. Must fall through to tier 2, not crash."""
    catalog = [
        {
            "id": "no-url-album",
            "title": "Idle Moments",
            "artist": "Grant Green",
            "label": "Blue Note",
            "genres": ["hard bop"],
        }  # no "spotifyUrl" key at all
    ]
    lib = [
        {
            "spotify_id": "AAA",
            "title": "Idle Moments",
            "artists": ["Grant Green"],
            "year": 1964,
            "added_at": "",
        }
    ]
    owned, unmatched = tp.match_owned(lib, catalog)
    assert owned["catalog_ids"] == ["no-url-album"]
    assert unmatched == []


def test_main_exits_when_library_missing(monkeypatch, tmp_path, capsys):
    """cache/spotify_library.json absent -> one-line stderr instruction +
    exit 1, no traceback."""
    monkeypatch.setattr(tp.common, "CACHE", tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        tp.main()
    assert exc_info.value.code == 1
    assert "sync_spotify" in capsys.readouterr().err


# --- _build_styles: zero coverage per review (Task 3 finding) ---


def test_build_styles_catalog_only_no_lastfm(monkeypatch, tmp_path):
    """No cache/lastfm.json -> source stays 'catalog' and tag_weight is a
    plain count of genres across matched catalog albums, normalized to a
    share of the total. CACHE is monkeypatched to an empty tmp_path (same
    pattern as test_main_exits_when_library_missing) so the branch decision
    is driven explicitly, not by the absence of a real cache/ dir.

    Derived by hand from 3 albums with overlapping genres:
      hard bop appears in all 3 albums   -> count 3
      soul jazz appears in 2 of them     -> count 2
      latin jazz appears in 1            -> count 1
      total = 6 -> weights 3/6=0.5, 2/6=0.3333->0.33, 1/6=0.1667->0.17
    """
    monkeypatch.setattr(tp.common, "CACHE", tmp_path)
    matched_albums = [
        {"id": "a", "artist": "X", "title": "A", "genres": ["hard bop", "soul jazz"]},
        {"id": "b", "artist": "X", "title": "B", "genres": ["hard bop"]},
        {
            "id": "c",
            "artist": "X",
            "title": "C",
            "genres": ["hard bop", "soul jazz", "latin jazz"],
        },
    ]

    styles, source = tp._build_styles(matched_albums, scores={})

    assert source == "catalog"
    assert styles == [
        {"tag": "hard bop", "weight": 0.5},
        {"tag": "soul jazz", "weight": 0.33},
        {"tag": "latin jazz", "weight": 0.17},
    ]


def test_build_styles_lastfm_merge_weighted_by_affinity(monkeypatch, tmp_path):
    """cache/lastfm.json present -> source flips to 'catalog+lastfm' and each
    artist's Last.fm tags are added in at scores[norm]['score'] / max_score
    (that artist's affinity relative to the top scorer in the whole
    profile) -- so a higher-affinity artist's tags weigh more than a
    lower-affinity artist's, and catalog-derived tags still contribute
    alongside them.

    Derived by hand:
      catalog: 2 albums both tagged 'hard bop' -> count 2
      grant green score 80.0 == max_score      -> weight 80/80 = 1.0
        -> tag_weight['soul jazz'] += 1.0
      duke ellington score 20.0 (lower affinity) -> weight 20/80 = 0.25
        -> tag_weight['big band'] += 0.25
      tag_weight = {hard bop: 2, soul jazz: 1.0, big band: 0.25}, total 3.25
      weights: 2/3.25=0.6154->0.62, 1/3.25=0.3077->0.31, 0.25/3.25=0.0769->0.08
    """
    monkeypatch.setattr(tp.common, "CACHE", tmp_path)
    tp.common.save_json(
        tmp_path / "lastfm.json",
        {
            "artist_tags": {
                "grant green": ["soul jazz"],
                "duke ellington": ["big band"],
            }
        },
    )
    matched_albums = [{"genres": ["hard bop"]}, {"genres": ["hard bop"]}]
    scores = {
        "grant green": {"score": 80.0},
        "duke ellington": {"score": 20.0},
    }

    styles, source = tp._build_styles(matched_albums, scores)

    assert source == "catalog+lastfm"
    assert styles == [
        {"tag": "hard bop", "weight": 0.62},  # catalog genres still contribute
        {"tag": "soul jazz", "weight": 0.31},  # grant green: affinity weight 1.0
        {"tag": "big band", "weight": 0.08},  # duke ellington: affinity weight 0.25
    ]
    soul_jazz_weight = next(s["weight"] for s in styles if s["tag"] == "soul jazz")
    big_band_weight = next(s["weight"] for s in styles if s["tag"] == "big band")
    assert soul_jazz_weight > big_band_weight  # higher-affinity artist weighs more

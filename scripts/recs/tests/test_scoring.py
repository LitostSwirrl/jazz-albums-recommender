"""Tests for build_recommendations: deterministic scoring, cache-traceable
reasons, and the zero-hallucination integrity gate.

Mirrors the test_rym_validate idiom: pure functions are driven with tiny
inline fixtures; the integrity checker is driven by monkeypatching
common.CACHE to a tmp dir and dropping fixture caches in (exactly how the
build reloads caches FRESH at check time).
"""

import pytest

from scripts.recs import build_recommendations as br
from scripts.recs import common


# --- (d) render_reason: exact template incl. the em-dash in the label reason ---


def test_render_reason_label_exact_em_dash_string():
    detail = br.render_reason("label", {"label": "Strata-East", "n": 6})
    assert detail == "On Strata-East — you have 6 albums from this label"


# --- (a) corroboration bonus: +0.05 per quality source beyond the first, cap +0.15 ---


def test_corroboration_bonus_adds_005_per_source_capped_015():
    # k=1 -> no bonus (mean only)
    assert br.compute_quality([0.5]) == pytest.approx(0.5)
    # k=2 -> +0.05
    assert br.compute_quality([0.5, 0.5]) == pytest.approx(0.55)
    # k=3 -> +0.10
    assert br.compute_quality([0.5, 0.5, 0.5]) == pytest.approx(0.60)
    # k=4 -> +0.15 (the cap boundary)
    assert br.compute_quality([0.5, 0.5, 0.5, 0.5]) == pytest.approx(0.65)
    # k=5 -> cap holds at +0.15, not +0.20
    assert br.compute_quality([0.5, 0.5, 0.5, 0.5, 0.5]) == pytest.approx(0.65)
    # the mean is real (not ignored): differing values still average
    assert br.compute_quality([0.4, 0.6]) == pytest.approx(0.55)
    # empty -> 0.0, no bonus
    assert br.compute_quality([]) == 0.0


# --- (c) mega-canon (haves > 25000) halves novelty ---


def test_mega_canon_halves_novelty():
    mega = {
        "haves": 30000,
        "rating": 4.0,
        "credits": [],
        "labels": [],
        "discogs_release_id": 1,
    }
    # inCatalog so the +0.1 new-to-site bonus does NOT confound -> exactly 0.5
    assert br.compute_novelty(mega, in_catalog=True) == 0.5
    # a non-mega inCatalog release stays at 1.0
    normal = {
        "haves": 100,
        "rating": 4.0,
        "credits": [],
        "labels": [],
        "discogs_release_id": 2,
    }
    assert br.compute_novelty(normal, in_catalog=True) == 1.0
    # external mega-canon: 0.5 halved, then +0.1 new-to-site -> 0.6
    assert br.compute_novelty(mega, in_catalog=False) == pytest.approx(0.6)


# --- (b) an owned candidate is excluded before scoring and never emitted ---


def test_owned_candidate_never_emitted():
    owned_key = common.norm_key("Miles Davis", "Kind of Blue")
    free_key = common.norm_key("Grant Green", "Idle Moments")
    discogs = {
        "releases": [
            {
                "norm_key": owned_key,
                "artist": "Miles Davis",
                "title": "Kind of Blue",
                "year": 1959,
                "labels": ["Columbia"],
                "rating": 4.5,
                "rating_count": 5000,
                "haves": 9000,
                "wants": 1,
                "credits": [],
                "discogs_release_id": 11,
                "via": "x",
            },
            {
                "norm_key": free_key,
                "artist": "Grant Green",
                "title": "Idle Moments",
                "year": 1965,
                "labels": ["Blue Note"],
                "rating": 4.4,
                "rating_count": 3000,
                "haves": 4000,
                "wants": 1,
                "credits": [],
                "discogs_release_id": 22,
                "via": "x",
            },
        ]
    }
    empty_rym = {"charts": {}}
    empty_lastfm = {"similar": {}, "tag_albums": {}, "artist_tags": {}}

    raw = br.assemble_candidates(
        discogs, empty_rym, empty_lastfm, {"reviews": []}, {"mentions": []}, {owned_key}
    )
    # excluded before scoring
    assert owned_key not in raw
    assert free_key in raw

    profile = {
        "artists": [],
        "labels": [],
        "styles": [],
        "owned": {"norm_keys": [owned_key]},
    }
    ctx = br.build_context(profile, empty_lastfm, {}, empty_rym)
    scored = [br.score_candidate(raw[k], ctx) for k in sorted(raw)]
    emitted = br.select_top(scored, br.EMIT_LIMIT)

    ids = {c["id"] for c in emitted}
    assert "ext-" + common.slugify("Miles Davis Kind of Blue") not in ids
    assert "ext-" + common.slugify("Grant Green Idle Moments") in ids


# --- (f) same norm_key in BOTH rym and discogs -> ONE candidate, BOTH badges ---


def test_rym_and_discogs_same_key_merge_one_candidate_both_badges():
    key = common.norm_key("Pharoah Sanders", "Karma")
    discogs = {
        "releases": [
            {
                "norm_key": key,
                "artist": "Pharoah Sanders",
                "title": "Karma",
                "year": 1969,
                "labels": ["Impulse!"],
                "rating": 4.3,
                "rating_count": 4000,
                "haves": 6000,
                "wants": 1,
                "credits": [],
                "discogs_release_id": 77,
                "via": "x",
            }
        ]
    }
    rym = {
        "charts": {
            "spiritual-jazz": [
                {
                    "rank": 1,
                    "norm_key": key,
                    "artist": "Pharoah Sanders",
                    "title": "Karma",
                    "year": 1969,
                    "rating": 4.35,
                    "rating_count": 6200,
                }
            ]
        }
    }
    empty_lastfm = {"similar": {}, "tag_albums": {}, "artist_tags": {}}

    raw = br.assemble_candidates(
        discogs, rym, empty_lastfm, {"reviews": []}, {"mentions": []}, set()
    )
    # merged into exactly one candidate
    assert list(raw.keys()) == [key]
    assert raw[key]["discogs"] is not None
    assert raw[key]["in_rym"] is True

    badges = br.build_badges(raw[key], rym)
    assert "rym" in badges and "discogs" in badges
    assert badges["rym"]["chart"] == "spiritual-jazz"
    assert badges["rym"]["rating"] == 4.35
    assert badges["discogs"]["haves"] == 6000


# --- (e) integrity gate: a tampered reason detail must sys.exit ---


def test_integrity_checker_raises_on_tampered_detail(monkeypatch, tmp_path):
    # the checker reloads caches FRESH from common.CACHE -> point it at tmp
    monkeypatch.setattr(br.common, "CACHE", tmp_path)
    common.save_json(
        tmp_path / "taste_profile.json",
        {
            "artists": [],
            "labels": [{"name": "Strata-East", "count": 6}],
            "styles": [],
            "owned": {"norm_keys": []},
        },
    )
    album = {
        "id": "ext-charles-tolliver-live-at-slugs",
        "artist": "Charles Tolliver",
        "title": "Live at Slug's",
        "year": 1972,
        "reasons": [
            {
                "type": "label",
                "detail": "On Strata-East — you have 6 albums from this label",
                "src": "taste_profile",
                "ref": "Strata-East",
            }
        ],
    }

    # a faithful reason reconstructs identically -> no raise
    br.run_integrity_check([album])

    # tamper the count in the rendered detail -> reconstruction mismatch -> exit 1
    album["reasons"][0]["detail"] = (
        "On Strata-East — you have 99 albums from this label"
    )
    with pytest.raises(SystemExit) as exc_info:
        br.run_integrity_check([album])
    assert exc_info.value.code == 1


# ======================================================================
# Task 11a — taste-gate tuning changes
# ======================================================================


# --- Change 1: affinity ceiling + rank skip empty-norm artist ---


def _profile_with_empty_norm_top():
    """Profile whose #1-by-score artist has an empty norm (CJK name that can
    never match a candidate) -- the real taste_profile shape."""
    return {
        "artists": [
            {"name": "以莉.高露", "norm": "", "score": 171.0, "rank": 1},
            {"name": "Chet Baker", "norm": "chet baker", "score": 137.45, "rank": 2},
            {"name": "Paul Desmond", "norm": "paul desmond", "score": 91.2, "rank": 3},
        ],
        "labels": [],
        "styles": [],
        "owned": {"norm_keys": [], "catalog_ids": []},
    }


def test_usable_artists_reranks_skipping_empty_norm():
    usable = br.usable_artists(_profile_with_empty_norm_top())
    # the empty-norm artist is dropped and everyone below is re-ranked 1-based
    assert [u["name"] for u in usable] == ["Chet Baker", "Paul Desmond"]
    assert [u["rank"] for u in usable] == [1, 2]
    assert usable[0]["score"] == pytest.approx(137.45)


def test_affinity_ceiling_is_top_non_empty_norm_score():
    profile = _profile_with_empty_norm_top()
    empty_lastfm = {"similar": {}, "tag_albums": {}, "artist_tags": {}}
    ctx = br.build_context(profile, empty_lastfm, {}, {"charts": {}})
    # ceiling is Chet Baker's 137.45, NOT the empty-norm artist's 171.0
    assert ctx.max_affinity == pytest.approx(137.45)


def test_max_affinity_is_true_max_when_stored_ranks_not_score_desc():
    """Review fix: max_affinity must be the true max over usable artists, not
    usable[0]["score"] (positional). usable_artists sorts by stored rank, so
    if a cache's stored rank were ever NOT score-descending, the first entry
    would not be the max -- this profile deliberately violates that."""
    profile = {
        "artists": [
            {"name": "Obscure", "norm": "obscure", "score": 10.0, "rank": 1},
            {"name": "Mid", "norm": "mid", "score": 50.0, "rank": 2},
            {"name": "Chet Baker", "norm": "chet baker", "score": 137.45, "rank": 3},
        ],
        "labels": [],
        "styles": [],
        "owned": {"norm_keys": [], "catalog_ids": []},
    }
    empty_lastfm = {"similar": {}, "tag_albums": {}, "artist_tags": {}}
    ctx = br.build_context(profile, empty_lastfm, {}, {"charts": {}})
    # true max is Chet Baker's 137.45 (stored rank 3), NOT the first-ranked
    # entry's score (Obscure, stored rank 1, score 10.0)
    assert ctx.max_affinity == pytest.approx(137.45)


def test_artist_reason_rank_matches_library_display():
    profile = _profile_with_empty_norm_top()
    empty_lastfm = {"similar": {}, "tag_albums": {}, "artist_tags": {}}
    ctx = br.build_context(profile, empty_lastfm, {}, {"charts": {}})
    key = common.norm_key("Chet Baker", "Chet")
    raw = {
        "norm_key": key,
        "discogs": None,
        "pitchfork": None,
        "reddit": None,
        "tag_album": {
            "norm_key": key,
            "artist": "Chet Baker",
            "title": "Chet",
            "year": 1959,
        },
        "in_rym": False,
    }
    scored = br.score_candidate(raw, ctx)
    artist_reasons = [r for r in scored["reasons"] if r["type"] == "artist"]
    assert artist_reasons
    # #1, not #2 -- matches assemble_library's displayed topArtists position
    assert artist_reasons[0]["detail"] == "Chet Baker is your #1 artist"

    library = br.assemble_library(
        {"saved_albums": [], "saved_tracks": []}, profile, [], "2026-07-27"
    )
    assert library["topArtists"][0]["name"] == "Chet Baker"


# --- Change 2: exclude compilations / box-sets / "Various" ---


def _cand(artist, title):
    return {
        "artist": artist,
        "title": title,
        "norm_key": common.norm_key(artist, title),
    }


def test_comp_excluded_by_title_regex():
    assert br._is_comp(_cand("Grant Green", "The Best Of Grant Green Vol. 1"))
    assert br._is_comp(_cand("Miles Davis", "The Complete Birth of the Cool"))
    assert br._is_comp(_cand("Thelonious Monk", "Monk's Greatest Hits"))
    assert br._is_comp(_cand("John Coltrane", "The Prestige Recordings"))


def test_comp_excluded_by_various_artist():
    assert br._is_comp(_cand("Various", "The Famous Sound of Three Blind Mice"))
    assert br._is_comp(_cand("Various Artists", "Some Sampler"))
    assert br._is_comp(_cand("unknown artist", "Untitled"))


def test_real_album_not_excluded_as_comp():
    assert not br._is_comp(_cand("Alice Coltrane", "Journey in Satchidananda"))
    assert not br._is_comp(_cand("Sonny Sharrock", "Ask the Ages"))
    assert not br._is_comp(_cand("Grant Green", "Idle Moments"))


def test_comp_partition_reports_count():
    scored = [
        _cand("Grant Green", "The Best Of Grant Green Vol. 1"),
        _cand("Grant Green", "Idle Moments"),
        _cand("Various", "Some Sampler"),
    ]
    comps = [c for c in scored if br._is_comp(c)]
    kept = [c for c in scored if not br._is_comp(c)]
    assert len(comps) == 2
    assert {c["title"] for c in kept} == {"Idle Moments"}


# --- Change 3: leaders matcher (artist-only) ---


def test_leaders_matcher_is_artist_only():
    leader = {"artist": "Art Blakey", "_credits": [], "_labels": [], "_tags": set()}
    sideman = {
        "artist": "Lee Morgan",
        "_credits": ["Art Blakey"],
        "_labels": [],
        "_tags": set(),
    }
    leaders_matcher = {"leaders": ["Art Blakey", "Max Roach"]}
    players_matcher = {"players": ["Art Blakey", "Max Roach"]}
    # artist-led matches a leaders matcher
    assert br._shelf_match(leader, leaders_matcher)
    # a sideman (leader only in credits) does NOT match a leaders matcher
    assert not br._shelf_match(sideman, leaders_matcher)
    # ...but the SAME sideman WOULD match a players matcher (locks the distinction)
    assert br._shelf_match(sideman, players_matcher)


# --- Change 4: shelves over full pool with a per-artist cap ---


def _shelf_cand(artist, title, score, tags):
    return {
        "id": common.slugify(f"{artist} {title}"),
        "artist": artist,
        "title": title,
        "score": score,
        "norm_key": common.norm_key(artist, title),
        "_labels": [],
        "_tags": set(tags),
        "_credits": [],
    }


def test_shelf_per_artist_cap_admits_lower_scored_others():
    # dominant artist: 6 matching albums, all higher-scored than the others
    pool = [
        _shelf_cand("Pharoah Sanders", f"Album {i}", 90 - i, ["spiritual jazz"])
        for i in range(6)
    ]
    pool += [
        _shelf_cand("Alice Coltrane", "Journey", 50, ["spiritual jazz"]),
        _shelf_cand("Don Cherry", "Brown Rice", 49, ["spiritual jazz"]),
        _shelf_cand("Sun Ra", "Space Is the Place", 48, ["spiritual jazz"]),
    ]
    shelf_defs = [
        {
            "id": "sj",
            "title": "SJ",
            "blurb": "b",
            "type": "scene",
            "matcher": {"tags": ["spiritual jazz"]},
        }
    ]
    items = br.build_shelves(pool, shelf_defs)[0]["items"]
    dominant = [i for i in items if i.startswith(common.slugify("Pharoah Sanders"))]
    # at most SHELF_PER_ARTIST from the dominant artist
    assert len(dominant) == br.SHELF_PER_ARTIST
    assert len(dominant) <= br.SHELF_PER_ARTIST
    # the dominant artist's 4th (higher-scored) is dropped in favor of the cap...
    assert common.slugify("Pharoah Sanders Album 3") not in items
    # ...and the lower-scored other-artist albums are included
    assert common.slugify("Alice Coltrane Journey") in items
    assert common.slugify("Don Cherry Brown Rice") in items
    assert common.slugify("Sun Ra Space Is the Place") in items


# --- Change 5: albums dict = emitted ∪ shelf items; integrity covers all ---


def test_shelf_only_item_in_output_union_and_integrity_covers_it(monkeypatch, tmp_path):
    monkeypatch.setattr(br.common, "CACHE", tmp_path)
    common.save_json(
        tmp_path / "taste_profile.json",
        {
            # empty-norm artist ranked ABOVE a real one (the real taste_profile
            # shape) -- proves an artist reason's rank reconstructs through the
            # re-ranked usable view, not the raw stored rank.
            "artists": [
                {"name": "以莉.高露", "norm": "", "score": 171.0, "rank": 1},
                {
                    "name": "Chet Baker",
                    "norm": "chet baker",
                    "score": 137.45,
                    "rank": 2,
                },
            ],
            "labels": [{"name": "Strata-East", "count": 6}],
            "styles": [],
            "owned": {"norm_keys": []},
        },
    )
    emitted_item = {
        "id": "emit-1",
        "artist": "A",
        "title": "Emitted",
        "norm_key": "a::emitted",
        "score": 90.0,
        "reasons": [],
        "_labels": [],
        "_tags": set(),
        "_credits": [],
    }
    # a sub-emit shelf-only item carrying a label reason AND a rank-bearing
    # artist reason -- both must reconstruct through the integrity gate.
    shelf_item = {
        "id": "shelf-1",
        "artist": "Charles Tolliver",
        "title": "Live at Slug's",
        "norm_key": common.norm_key("Charles Tolliver", "Live at Slug's"),
        "score": 10.0,
        "reasons": [
            {
                "type": "label",
                "detail": "On Strata-East — you have 6 albums from this label",
                "src": "taste_profile",
                "ref": "Strata-East",
            },
            {
                "type": "artist",
                "detail": "Chet Baker is your #1 artist",
                "src": "taste_profile",
                "ref": "chet baker",
            },
        ],
        "_labels": ["Strata-East"],
        "_tags": set(),
        "_credits": [],
    }
    pool = [emitted_item, shelf_item]
    emitted = [emitted_item]  # shelf_item is OUTSIDE emitted
    shelf_defs = [
        {
            "id": "se",
            "title": "SE",
            "blurb": "b",
            "type": "label",
            "matcher": {"labels": ["Strata-East"]},
        }
    ]
    shelves = br.build_shelves(pool, shelf_defs)
    assert "shelf-1" in shelves[0]["items"]

    album_cands = br.collect_output_albums(emitted, shelves, pool)
    # the sub-emit shelf item is in the output union...
    assert "shelf-1" in {c["id"] for c in album_cands}

    # ...and the integrity gate visits it: faithful passes -- including the
    # artist reason, whose rank is 1 (the re-ranked usable position), NOT the
    # stored rank 2, since the empty-norm artist above it is skipped.
    br.run_integrity_check(album_cands)

    # flipping the artist reason's rank alone must be caught -- this is the
    # rank-bearing reason type the change-1 re-ranking fix exists to lock.
    shelf_item["reasons"][1]["detail"] = "Chet Baker is your #2 artist"
    with pytest.raises(SystemExit) as exc_info:
        br.run_integrity_check(album_cands)
    assert exc_info.value.code == 1
    shelf_item["reasons"][1]["detail"] = "Chet Baker is your #1 artist"  # restore

    shelf_item["reasons"][0]["detail"] = (
        "On Strata-East — you have 99 albums from this label"
    )
    with pytest.raises(SystemExit):
        br.run_integrity_check(album_cands)


# --- Change 6: per-artist cap on the 8 hero topPicks ---


def test_top_picks_per_artist_cap():
    def pick(artist, title, score):
        return {
            "id": common.slugify(f"{artist} {title}"),
            "artist": artist,
            "title": title,
            "score": score,
            "norm_key": common.norm_key(artist, title),
        }

    # the top 6 by score are all one artist, then six distinct others
    emitted = [pick("Miles Davis", f"M{i}", 100 - i) for i in range(6)]
    emitted += [
        pick("Bill Evans", "Waltz for Debby", 50),
        pick("John Coltrane", "Giant Steps", 49),
        pick("Chet Baker", "Chet", 48),
        pick("Sonny Rollins", "Way Out West", 47),
        pick("Herbie Hancock", "Maiden Voyage", 46),
        pick("Wayne Shorter", "Speak No Evil", 45),
    ]
    emitted = br.select_top(emitted, br.EMIT_LIMIT)
    picks = br.select_top_picks(emitted)
    assert len(picks) == br.TOP_PICKS
    miles = [p for p in picks if p.startswith(common.slugify("Miles Davis"))]
    assert len(miles) == br.TOP_PICKS_PER_ARTIST
    assert len(picks) - len(miles) == 6

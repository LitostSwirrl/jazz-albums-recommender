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


# ======================================================================
# Task 11b — taste-gate round 2 changes
# ======================================================================


def _sel_cand(artist, title, score):
    """Minimal candidate for the selection helpers (score + cap key + id)."""
    return {
        "id": common.slugify(f"{artist} {title}"),
        "artist": artist,
        "title": title,
        "score": score,
        "norm_key": common.norm_key(artist, title),
    }


# --- Change 1: per-artist cap on the emitted list ---


def test_emit_per_artist_cap_admits_lower_scored_others():
    # one artist holds the top 10 scores
    pool = [_sel_cand("Miles Davis", f"M{i}", 100 - i) for i in range(10)]
    pool += [
        _sel_cand("Bill Evans", "Waltz for Debby", 50),
        _sel_cand("John Coltrane", "Giant Steps", 49),
        _sel_cand("Chet Baker", "Chet", 48),
    ]
    emitted = br.select_emitted(pool, br.EMIT_LIMIT)
    miles = [c for c in emitted if c["artist"] == "Miles Davis"]
    # at most EMIT_PER_ARTIST of them survive...
    assert len(miles) == br.EMIT_PER_ARTIST
    assert [c["title"] for c in miles] == [f"M{i}" for i in range(br.EMIT_PER_ARTIST)]
    # ...and the lower-scored other artists are admitted in their place
    assert {c["artist"] for c in emitted} == {
        "Miles Davis",
        "Bill Evans",
        "John Coltrane",
        "Chet Baker",
    }


def test_select_emitted_respects_the_emit_limit():
    pool = [_sel_cand(f"Artist {i}", "X", 100 - i) for i in range(20)]
    emitted = br.select_emitted(pool, 5)
    assert len(emitted) == 5
    assert [c["artist"] for c in emitted] == [f"Artist {i}" for i in range(5)]


# --- Change 2: edition-duplicate merge ---


def _merge_cand(artist, title, score, badges=None, reasons=None):
    return {
        "id": common.slugify(f"{artist} {title}"),
        "norm_key": common.norm_key(artist, title),
        "artist": artist,
        "title": title,
        "score": score,
        "badges": badges or {},
        "reasons": reasons or [],
    }


def _reason(rtype, detail, ref, contribution):
    return {
        "type": rtype,
        "detail": detail,
        "src": "src",
        "ref": ref,
        "_contribution": contribution,
    }


def test_merge_key_unifies_the_four_edition_variants():
    pairs = [
        (
            "Herbie Hancock",
            "Head Hunters",
            "Headhunters",
            "herbie hancock::headhunters",
        ),
        (
            "Chet Baker",
            "In New York",
            "Chet Baker In New York",
            "chet baker::innewyork",
        ),
        ("Miles Davis", "Live Evil", "Live-Evil", "miles davis::liveevil"),
        (
            "Miles Davis",
            "A Tribute to Jack Johnson",
            "The Tribute To Jack Johnson",
            "miles davis::tributetojackjohnson",
        ),
    ]
    for artist, title_a, title_b, expected in pairs:
        assert br.merge_key(common.norm_key(artist, title_a)) == expected
        assert br.merge_key(common.norm_key(artist, title_b)) == expected


def test_merge_key_keeps_distinct_albums_apart():
    # the substring-containment trap: these must NOT collapse
    assert br.merge_key(common.norm_key("Joe Pass", "Virtuoso")) != br.merge_key(
        common.norm_key("Joe Pass", "Virtuoso #3")
    )
    assert br.merge_key(common.norm_key("Wes Montgomery", "Go!")) != br.merge_key(
        common.norm_key("Wes Montgomery", "The History Of Wes Montgomery")
    )


def test_merge_editions_keeps_higher_scored_and_unions_badges_and_reasons():
    high = _merge_cand(
        "Herbie Hancock",
        "Head Hunters",
        69.6,
        badges={"rym": {"chart": "jazz-fusion"}},
        reasons=[_reason("reddit", "Mentioned in 9 r/jazz threads", "hh::hh", 0.30)],
    )
    low = _merge_cand(
        "Herbie Hancock",
        "Headhunters",
        59.6,
        badges={"reddit": {"mentions": 4}},
        reasons=[_reason("similar", "Last.fm: similar to X (your #2)", "x", 0.20)],
    )
    merged, log = br.merge_editions([high, low])

    assert len(merged) == 1
    rec = merged[0]
    # identity comes from the higher-scored record
    assert (rec["id"], rec["title"], rec["score"]) == (high["id"], "Head Hunters", 69.6)
    # badges union
    assert set(rec["badges"]) == {"rym", "reddit"}
    # reasons union, ordered by the file's existing contribution ordering
    assert [r["type"] for r in rec["reasons"]] == ["reddit", "similar"]
    assert [entry["key"] for entry in log] == ["herbie hancock::headhunters"]


def test_merge_editions_respects_the_three_reason_cap():
    high = _merge_cand(
        "Miles Davis",
        "A Tribute to Jack Johnson",
        50.7,
        reasons=[
            _reason("reddit", "Mentioned in 9 r/jazz threads", "a", 0.30),
            _reason("artist", "Miles Davis is your #1 artist", "miles davis", 0.28),
        ],
    )
    low = _merge_cand(
        "Miles Davis",
        "The Tribute To Jack Johnson",
        50.7,
        reasons=[
            _reason("sideman", "A and B appear on albums you saved", "release:1", 0.29),
            _reason("similar", "Last.fm: similar to X (your #2)", "x", 0.01),
        ],
    )
    merged, _log = br.merge_editions([high, low])
    reasons = merged[0]["reasons"]
    assert len(reasons) == 3
    # top three by contribution, the 0.01 similar is dropped
    assert [r["type"] for r in reasons] == ["reddit", "sideman", "artist"]


def test_merge_keeps_one_reason_per_type():
    """Both spellings carry their own reddit count. Generation never emits two
    reasons of one type, so the merge must not be the one place it happens --
    the higher-contribution one wins."""
    high = _merge_cand(
        "Herbie Hancock",
        "Head Hunters",
        69.6,
        reasons=[
            _reason(
                "reddit", "Mentioned in 10 r/jazz threads", "hh::head hunters", 0.30
            )
        ],
    )
    low = _merge_cand(
        "Herbie Hancock",
        "Headhunters",
        59.6,
        reasons=[
            _reason("reddit", "Mentioned in 7 r/jazz threads", "hh::headhunters", 0.21),
            _reason("similar", "Last.fm: similar to X (your #2)", "x", 0.05),
        ],
    )
    reasons = br.merge_editions([high, low])[0][0]["reasons"]
    assert [r["type"] for r in reasons] == ["reddit", "similar"]
    assert reasons[0]["detail"] == "Mentioned in 10 r/jazz threads"


def test_merge_does_not_transfer_a_norm_key_bound_chart_reason():
    """A chart reason reconstructs against the album's OWN norm_key, so it
    cannot ride along to the kept record -- the integrity gate would fail."""
    high = _merge_cand(
        "Miles Davis",
        "Live Evil",
        65.7,
        reasons=[
            _reason("artist", "Miles Davis is your #1 artist", "miles davis", 0.4)
        ],
    )
    low = _merge_cand(
        "Miles Davis",
        "Live-Evil",
        65.7,
        reasons=[
            _reason(
                "chart", "#3 in RYM fusion chart (4.0 from 100 ratings)", "fusion", 0.9
            )
        ],
    )
    merged, _log = br.merge_editions([high, low])
    assert [r["type"] for r in merged[0]["reasons"]] == ["artist"]


def test_merge_ties_break_deterministically_on_norm_key():
    a = _merge_cand("Miles Davis", "Live Evil", 65.7)
    b = _merge_cand("Miles Davis", "Live-Evil", 65.7)
    # input order must not decide the winner
    assert br.merge_editions([a, b])[0][0]["title"] == "Live Evil"
    assert br.merge_editions([b, a])[0][0]["title"] == "Live Evil"


def test_virtuoso_variants_survive_the_merge_separately():
    pool = [
        _merge_cand("Joe Pass", "Virtuoso", 52.0),
        _merge_cand("Joe Pass", "Virtuoso #3", 57.9),
    ]
    merged, log = br.merge_editions(pool)
    assert {c["title"] for c in merged} == {"Virtuoso", "Virtuoso #3"}
    assert log == []


def test_near_duplicate_pairs_reports_subtitle_extensions_without_merging():
    albums = [
        _merge_cand("Miles Davis", "Relaxin'", 50.7),
        _merge_cand("Miles Davis", "Relaxin' with the Miles Davis Quintet", 60.7),
        _merge_cand("John Coltrane", "Live In Seattle", 51.4),
        _merge_cand("John Coltrane", "A Love Supreme: Live in Seattle", 59.7),
        _merge_cand("Wes Montgomery", "Go!", 40.0),
        _merge_cand("Wes Montgomery", "The History Of Wes Montgomery", 30.0),
    ]
    pairs = {(a["title"], b["title"]) for a, b in br.near_duplicate_pairs(albums)}
    # word-boundary extensions in both directions are reported
    assert ("Relaxin'", "Relaxin' with the Miles Davis Quintet") in pairs
    assert ("Live In Seattle", "A Love Supreme: Live in Seattle") in pairs
    # the substring trap ("go" inside "montgomery") is not a near pair
    assert not any("Go!" in pair for pair in pairs)
    # reporting them does not merge them
    assert len(br.merge_editions(albums)[0]) == len(albums)


# --- Change 5: cap-key canonicalization ---


def test_cap_key_canonicalizes_ensemble_suffix_and_last_first():
    assert br.cap_key("Pat Metheny Group") == br.cap_key("Pat Metheny")
    assert br.cap_key("Keith Jarrett Trio") == br.cap_key("Keith Jarrett")
    assert br.cap_key("Davis, Miles") == br.cap_key("Miles Davis")
    assert br.cap_key("The Miles Davis Sextet") == br.cap_key("Miles Davis")
    # a name with no ensemble suffix is unaffected beyond case/whitespace
    assert br.cap_key("Sonny Rollins") == "sonny rollins"
    assert br.cap_key("  Bill   Evans ") == "bill evans"
    # an ensemble word that is not trailing stays put
    assert br.cap_key("Art Ensemble of Chicago") == "art ensemble of chicago"


def test_emit_cap_key_shares_one_allowance_across_name_variants():
    pool = [
        _sel_cand("Pat Metheny", "Watercolors", 90),
        _sel_cand("Pat Metheny Group", "Offramp", 89),
        _sel_cand("Pat Metheny", "Rejoicing", 88),
        _sel_cand("Pat Metheny Group", "Still Life", 87),
        _sel_cand("Pat Metheny", "New Chautauqua", 86),
        _sel_cand("Bill Evans", "Undercurrent", 10),
    ]
    emitted = br.select_emitted(pool, br.EMIT_LIMIT)
    metheny = [c for c in emitted if c["artist"].startswith("Pat Metheny")]
    assert len(metheny) == br.EMIT_PER_ARTIST
    assert "Bill Evans" in {c["artist"] for c in emitted}


def test_top_picks_cap_key_shares_one_allowance_across_name_variants():
    emitted = [
        _sel_cand("Pat Metheny", "Watercolors", 99),
        _sel_cand("Pat Metheny Group", "Offramp", 98),
        _sel_cand("Pat Metheny", "Rejoicing", 97),
        _sel_cand("Davis, Miles", "Big Fun", 96),
        _sel_cand("Miles Davis", "Live Evil", 95),
        _sel_cand("Miles Davis Quintet", "Relaxin'", 94),
        _sel_cand("Bill Evans", "Undercurrent", 93),
        _sel_cand("John Coltrane", "Giant Steps", 92),
        _sel_cand("Chet Baker", "Chet", 91),
        _sel_cand("Sonny Rollins", "Way Out West", 90),
        _sel_cand("Grant Green", "Idle Moments", 89),
    ]
    picks = br.select_top_picks(emitted)
    assert len(picks) == br.TOP_PICKS
    metheny = [p for p in picks if p.startswith(common.slugify("Pat Metheny"))]
    assert len(metheny) == br.TOP_PICKS_PER_ARTIST
    miles = [p for p in picks if "davis" in p or "miles" in p]
    assert len(miles) == br.TOP_PICKS_PER_ARTIST


def test_shelf_cap_key_shares_one_allowance_across_name_variants():
    pool = [
        _shelf_cand("Pat Metheny", "Watercolors", 90, ["jazz guitar"]),
        _shelf_cand("Pat Metheny Group", "Offramp", 89, ["jazz guitar"]),
        _shelf_cand("Pat Metheny", "Rejoicing", 88, ["jazz guitar"]),
        _shelf_cand("Pat Metheny Group", "Still Life", 87, ["jazz guitar"]),
        _shelf_cand("Jim Hall", "Concierto", 10, ["jazz guitar"]),
    ]
    shelf_defs = [
        {
            "id": "g",
            "title": "G",
            "blurb": "b",
            "type": "lineage",
            "matcher": {"tags": ["jazz guitar"]},
        }
    ]
    items = br.build_shelves(pool, shelf_defs)[0]["items"]
    metheny = [i for i in items if i.startswith(common.slugify("Pat Metheny"))]
    assert len(metheny) == br.SHELF_PER_ARTIST
    assert common.slugify("Jim Hall Concierto") in items


# --- Change 6: shelf ordering, leaders before credits ---


def test_shelf_lists_leader_matches_before_credit_matches():
    def cand(artist, title, score, credits):
        return {
            "id": common.slugify(f"{artist} {title}"),
            "artist": artist,
            "title": title,
            "score": score,
            "norm_key": common.norm_key(artist, title),
            "_labels": [],
            "_tags": set(),
            "_credits": credits,
        }

    pool = [
        # a credit-match with the HIGHEST score
        cand("Chet Baker", "Chet", 99.0, ["Kenny Burrell"]),
        cand("Paul Desmond", "Easy Living", 98.0, ["Jim Hall"]),
        # leader-matches, lower scored
        cand("Grant Green", "Nigeria", 61.6, []),
        cand("Wes Montgomery", "Pretty Blue", 55.7, []),
    ]
    shelf_defs = [
        {
            "id": "guitar",
            "title": "G",
            "blurb": "b",
            "type": "lineage",
            "matcher": {
                "players": [
                    "Grant Green",
                    "Wes Montgomery",
                    "Kenny Burrell",
                    "Jim Hall",
                ]
            },
        }
    ]
    items = br.build_shelves(pool, shelf_defs)[0]["items"]
    assert items[:2] == [
        common.slugify("Grant Green Nigeria"),
        common.slugify("Wes Montgomery Pretty Blue"),
    ]
    # the credit-matches stay on the shelf, just not at the front
    assert items[2:] == [
        common.slugify("Chet Baker Chet"),
        common.slugify("Paul Desmond Easy Living"),
    ]


def test_tag_only_shelf_ordering_is_unchanged_by_the_leader_rule():
    pool = [
        _shelf_cand("Pharoah Sanders", "Karma", 90, ["spiritual jazz"]),
        _shelf_cand("Alice Coltrane", "Journey", 80, ["spiritual jazz"]),
        _shelf_cand("Sun Ra", "Space", 70, ["spiritual jazz"]),
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
    assert items == [
        common.slugify("Pharoah Sanders Karma"),
        common.slugify("Alice Coltrane Journey"),
        common.slugify("Sun Ra Space"),
    ]


# --- Change 7: singles filter ---


def test_single_excluded_by_the_a_side_b_side_marker():
    single = _cand(
        "Louis Armstrong", "Blueberry Hill / Baby, Won't You Say You Love Me"
    )
    assert br.exclusion_reason(single) == "single"
    # a slash without surrounding spaces is not the A-side/B-side form
    assert br.exclusion_reason(_cand("John Coltrane", "Africa/Brass")) is None
    assert br.exclusion_reason(_cand("Grant Green", "Idle Moments")) is None
    # a single is NOT counted as a compilation
    assert not br._is_comp(single)


# --- Change 10: comp filter recalibration, both directions ---


def test_comp_allowlist_rescues_real_albums_from_the_regex():
    rescued = [
        ("Don Cherry", "Complete Communion"),
        ("Chet Baker", "Plays the Best of Lerner & Loewe"),
        ("Chet Baker", "Chet Baker Plays the Best of Lerner and Loewe"),
        ("George Russell", "Ezz-thetics (Keepnews Collection) [Bonus Track Version]"),
        ("Rashied Ali", "Duo Exchange: Complete Sessions"),
    ]
    for artist, title in rescued:
        cand = _cand(artist, title)
        assert cand["norm_key"] in br.COMP_ALLOWLIST
        # the regex still matches, but the allowlist wins
        assert br.COMP_TITLE_RE.search(cand["title"])
        assert not br._is_comp(cand)
        assert br.exclusion_reason(cand) is None


def test_box_denylist_excludes_box_sets_the_regex_misses():
    for artist, title in [
        ("Sonny Rollins", "Go West!: The Contemporary Records Albums"),
        ("Ornette Coleman", "Round Trip: Ornette Coleman on Blue Note"),
        ("Eric Dolphy", "Musical Prophet: The Expanded 1963 New York Studio Sessions"),
    ]:
        cand = _cand(artist, title)
        assert cand["norm_key"] in br.BOX_DENYLIST
        assert br.exclusion_reason(cand) == "denylisted"
        assert br._is_comp(cand)


def test_bootleg_series_pattern_catches_the_archival_boxes():
    assert br._is_comp(_cand("Miles Davis", "The Bootleg Series Vol. 1"))
    assert br._is_comp(
        _cand(
            "Miles Davis", "That's What Happened 1982-1985: The Bootleg Series Vol. 7"
        )
    )


def test_exclusion_categories_partition_the_pool():
    pool = [
        _cand("Grant Green", "Idle Moments"),
        _cand("Various", "Some Sampler"),
        _cand("Grant Green", "The Best Of Grant Green Vol. 1"),
        _cand("Sonny Rollins", "Go West!: The Contemporary Records Albums"),
        _cand("Louis Armstrong", "Blueberry Hill / Baby, Won't You Say You Love Me"),
        _cand("Don Cherry", "Complete Communion"),
    ]
    by_reason = {}
    for cand in pool:
        by_reason.setdefault(br.exclusion_reason(cand), []).append(cand["title"])
    assert by_reason[None] == ["Idle Moments", "Complete Communion"]
    assert by_reason["comp-artist"] == ["Some Sampler"]
    assert by_reason["comp-title"] == ["The Best Of Grant Green Vol. 1"]
    assert by_reason["denylisted"] == ["Go West!: The Contemporary Records Albums"]
    assert by_reason["single"] == ["Blueberry Hill / Baby, Won't You Say You Love Me"]


# --- Change 11: Pitchfork box-score propagation ---


def _review(norm_key, title, score, url, artist="A", year=2020):
    return {
        "norm_key": norm_key,
        "artist": artist,
        "title": title,
        "score": score,
        "bnm": False,
        "year": year,
        "url": url,
    }


def test_pitchfork_box_url_suppressed_only_when_every_score_matches():
    pitchfork = {
        "reviews": [
            # one URL, two albums, ONE score -> a box review, both suppressed
            _review("a::poet", "The Poet", 7.5, "u-box"),
            _review("a::poet ii", "The Poet II", 7.5, "u-box"),
            # one URL, two albums, DIFFERENT scores -> genuine multi-album review
            _review("b::amaryllis", "Amaryllis", 7.5, "u-multi"),
            _review("b::belladonna", "Belladonna", 7.7, "u-multi"),
            # a plain single-album review
            _review("c::solo", "Solo", 8.0, "u-solo"),
        ]
    }
    kept = {r["norm_key"] for r in br.usable_reviews(pitchfork)}
    assert kept == {"b::amaryllis", "b::belladonna", "c::solo"}


def test_box_suppressed_review_is_no_quality_or_year_source():
    key = common.norm_key("Bobby Womack", "The Poet")
    pitchfork = {
        "reviews": [
            _review(key, "The Poet", 7.5, "u-box", artist="Bobby Womack", year=2021),
            _review(
                common.norm_key("Bobby Womack", "The Poet II"),
                "The Poet II",
                7.5,
                "u-box",
                artist="Bobby Womack",
                year=2021,
            ),
        ]
    }
    empty_lastfm = {"similar": {}, "tag_albums": {}, "artist_tags": {}}
    raw = br.assemble_candidates(
        {"releases": []},
        {"charts": {}},
        empty_lastfm,
        pitchfork,
        {"mentions": []},
        set(),
    )
    # the box-suppressed review does not create a candidate at all
    assert raw == {}


def test_integrity_reconstruction_applies_the_same_box_suppression(
    monkeypatch, tmp_path
):
    """Generation and reconstruction must share one derivation path: a reason
    referencing a box-suppressed review must not reconstruct."""
    monkeypatch.setattr(br.common, "CACHE", tmp_path)
    common.save_json(
        tmp_path / "pitchfork.json",
        {
            "reviews": [
                _review("bobby womack::poet", "The Poet", 7.5, "u-box", year=2021),
                _review(
                    "bobby womack::poet ii", "The Poet II", 7.5, "u-box", year=2021
                ),
                _review(
                    "mary halvorson::amaryllis", "Amaryllis", 7.5, "u-multi", year=2022
                ),
                _review(
                    "mary halvorson::belladonna",
                    "Belladonna",
                    7.7,
                    "u-multi",
                    year=2022,
                ),
            ]
        },
    )
    box_album = {
        "id": "ext-box",
        "artist": "Bobby Womack",
        "title": "The Poet",
        "reasons": [
            {
                "type": "pitchfork",
                "detail": "Pitchfork 7.5 (2021)",
                "src": "pitchfork",
                "ref": "bobby womack::poet",
            }
        ],
    }
    with pytest.raises(SystemExit) as exc_info:
        br.run_integrity_check([box_album])
    assert exc_info.value.code == 1

    # a genuine multi-album review still reconstructs
    kept_album = {
        "id": "ext-kept",
        "artist": "Mary Halvorson",
        "title": "Belladonna",
        "reasons": [
            {
                "type": "pitchfork",
                "detail": "Pitchfork 7.7 (2022)",
                "src": "pitchfork",
                "ref": "mary halvorson::belladonna",
            }
        ],
    }
    br.run_integrity_check([kept_album])


# ======================================================================
# Task 11c -- taste-gate round 2 follow-up (two hand corrections)
# ======================================================================


# --- Change A: singles-filter allowlist ---


def test_singles_allowlist_contains_exact_norm_keys():
    assert br.SINGLES_ALLOWLIST == {
        "john coltrane quartet::africa brass",
        "gerry mulligan::gerry mulligan paul desmond",
    }


def test_singles_allowlist_rescues_real_albums_from_the_marker():
    rescued = [
        ("The John Coltrane Quartet", "Africa / Brass"),
        ("Gerry Mulligan", "Gerry Mulligan / Paul Desmond"),
    ]
    for artist, title in rescued:
        cand = _cand(artist, title)
        assert cand["norm_key"] in br.SINGLES_ALLOWLIST
        # the marker still matches, but the allowlist wins
        assert br.SINGLE_MARKER in cand["title"]
        assert not br._is_comp(cand)
        assert br.exclusion_reason(cand) is None


def test_singles_allowlist_does_not_rescue_the_compilation_edition():
    # "Complete Africa / Brass" is a different norm_key from "Africa / Brass"
    # -- it is the 1991 compilation reissue, not the studio LP, and must stay
    # excluded even though it sits right next to the real album in the pool.
    pool = [
        _cand("The John Coltrane Quartet", "Africa / Brass"),
        _cand("The John Coltrane Quartet", "Complete Africa / Brass"),
        _cand("Louis Armstrong", "Blueberry Hill / Baby, Won't You Say You Love Me"),
    ]
    by_reason = {}
    for cand in pool:
        by_reason.setdefault(br.exclusion_reason(cand), []).append(cand["title"])
    assert by_reason[None] == ["Africa / Brass"]
    assert "john coltrane quartet::complete africa brass" not in br.SINGLES_ALLOWLIST
    assert by_reason["single"] == [
        "Complete Africa / Brass",
        "Blueberry Hill / Baby, Won't You Say You Love Me",
    ]


# --- Change B: hand-merge pair for "We Insist" ---


def test_hand_merges_contains_exactly_the_we_insist_pair():
    assert br.HAND_MERGES == {
        "max roach::we insist": "max roach::we insist max roachs freedom now suite",
    }


def test_merge_key_routes_the_hand_merged_absorbed_key_to_the_keeper():
    absorbed_key = common.norm_key("Max Roach", "We Insist")
    keeper_key = common.norm_key(
        "Max Roach", "We Insist! Max Roach's Freedom Now Suite"
    )
    assert br.merge_key(absorbed_key) == br.merge_key(keeper_key)


def test_we_insist_pair_merges_keeper_wins_badges_and_reasons_union():
    keeper = _merge_cand(
        "Max Roach",
        "We Insist! Max Roach's Freedom Now Suite",
        54.8,
        badges={"rym": {"chart": "avant-garde-jazz"}},
        reasons=[
            _reason(
                "chart",
                "#27 in RYM avant-garde-jazz chart (3.88 from 6000 ratings)",
                "avant-garde-jazz",
                0.9,
            ),
            _reason(
                "similar", "Last.fm: similar to Charles Mingus (your #27)", "x", 0.2
            ),
        ],
    )
    absorbed = _merge_cand(
        "Max Roach",
        "We Insist",
        34.6,
        badges={"reddit": {"mentions": 2}},
        reasons=[
            _reason(
                "similar", "Last.fm: similar to Charles Mingus (your #27)", "x", 0.2
            )
        ],
    )
    merged, log = br.merge_editions([keeper, absorbed])

    assert len(merged) == 1
    rec = merged[0]
    # identity/score comes from the higher-scored record
    assert (rec["title"], rec["score"]) == (
        "We Insist! Max Roach's Freedom Now Suite",
        54.8,
    )
    # badges union: the absorbed record's reddit badge is folded in
    assert set(rec["badges"]) == {"rym", "reddit"}
    # the identical similar reason de-dupes rather than doubling up
    assert [r["type"] for r in rec["reasons"]] == ["chart", "similar"]
    assert [entry["key"] for entry in log] == [
        "max roach::weinsistmaxroachsfreedomnowsuite"
    ]


def test_we_insist_absorbed_chart_reason_does_not_transfer_via_hand_merge():
    """Mirrors the generic-merge NORM_KEY_BOUND_REASONS test, but for the
    hand-merge path -- a chart reason on the record being ABSORBED must not
    ride along to the keeper either."""
    keeper = _merge_cand(
        "Max Roach",
        "We Insist! Max Roach's Freedom Now Suite",
        54.8,
        reasons=[
            _reason(
                "similar", "Last.fm: similar to Charles Mingus (your #27)", "x", 0.2
            )
        ],
    )
    absorbed = _merge_cand(
        "Max Roach",
        "We Insist",
        34.6,
        reasons=[
            _reason(
                "chart",
                "#9 in RYM protest-jazz chart (4.0 from 50 ratings)",
                "protest-jazz",
                0.9,
            )
        ],
    )
    merged, _log = br.merge_editions([keeper, absorbed])
    # the pair actually merged (not two untouched records that merely happen
    # to each carry one reason) -- and the chart reason did not ride along
    assert len(merged) == 1
    assert [r["type"] for r in merged[0]["reasons"]] == ["similar"]


def test_hand_merge_does_not_affect_other_near_duplicate_pairs():
    """The generic subtitle-extension rule stays untouched for every OTHER
    pair; only the one named hand-merge pair collapses, and it therefore
    drops out of the unmerged near-duplicate report."""
    albums = [
        _merge_cand("Miles Davis", "Relaxin'", 50.7),
        _merge_cand("Miles Davis", "Relaxin' with the Miles Davis Quintet", 60.7),
        _merge_cand("Max Roach", "We Insist", 34.6),
        _merge_cand("Max Roach", "We Insist! Max Roach's Freedom Now Suite", 54.8),
    ]
    merged, _log = br.merge_editions(albums)
    # the hand-merged pair collapses to one record...
    assert {c["title"] for c in merged} == {
        "Relaxin'",
        "Relaxin' with the Miles Davis Quintet",
        "We Insist! Max Roach's Freedom Now Suite",
    }
    # ...and the generic rule still leaves the Relaxin' pair alone
    pairs = {(a["title"], b["title"]) for a, b in br.near_duplicate_pairs(albums)}
    assert ("Relaxin'", "Relaxin' with the Miles Davis Quintet") in pairs
    # the We Insist pair is no longer reported as an unmerged near-pair
    assert not any("We Insist" in a or "We Insist" in b for a, b in pairs)


# ======================================================================
# Fix round 2 -- final pre-merge review findings
# ======================================================================


def _profile(*ranked, labels=None):
    """Profile from (name, score) pairs already in rank order."""
    return {
        "artists": [
            {"name": name, "norm": common.norm(name), "score": score, "rank": i}
            for i, (name, score) in enumerate(ranked, start=1)
        ],
        "labels": labels or [],
        "styles": [],
        "owned": {"norm_keys": [], "catalog_ids": []},
    }


def _credit(name, role):
    return {"name": name, "role": role}


# The real Discogs release 3469846 credit pool, verbatim from the HTTP cache.
# Miles Davis is on it as a COMPOSER, not a player.
_IN_NEW_YORK_CREDITS = [
    _credit("Paul Chambers (3)", "Bass"),
    _credit("Paul Bacon (2)", "Design [Cover]"),
    _credit('"Philly" Joe Jones', "Drums"),
    _credit("Jack Higgins", "Engineer"),
    _credit("Paul Weller (3)", "Photography By [Cover]"),
    _credit("Al Haig", "Piano"),
    _credit("Orrin Keepnews", "Producer, Liner Notes"),
    _credit("Johnny Griffin", "Tenor Saxophone"),
    _credit("Chet Baker", "Trumpet"),
    _credit("Miles Davis", "Written-By"),
]


# --- Critical 1: HAND_MERGES may never cross artists ---


def test_hand_merges_preserve_the_artist():
    """The live constant satisfies the invariant the merge relies on."""
    br.check_hand_merges(br.HAND_MERGES)


def test_check_hand_merges_rejects_a_cross_artist_pair():
    """The escape hatch a maintainer reaches for on a co-led duplicate. Left
    unguarded it produces a record displayed as Bill Evans -- Undercurrent
    carrying "Jim Hall is your #12 artist": `artist` is not in the
    non-transferable set, reconstruct_data resolves the stored ref against the
    taste profile without consulting album["artist"], so the integrity gate
    passes and a false attribution reaches disk."""
    with pytest.raises(AssertionError):
        br.check_hand_merges({"jim hall::undercurrent": "bill evans::undercurrent"})


def test_similar_reason_is_identity_bound_to_the_albums_own_artist(
    monkeypatch, tmp_path
):
    """The comment used to claim chart was the only identity-bound type. It is
    not: `similar` re-derives from album["artist"] at reconstruction, so a
    cross-artist merge would fail the gate loud rather than lie -- same class,
    different failure mode. This pins that behavior."""
    monkeypatch.setattr(br.common, "CACHE", tmp_path)
    common.save_json(tmp_path / "taste_profile.json", _profile(("Stan Getz", 100.0)))
    common.save_json(
        tmp_path / "lastfm.json",
        {
            "similar": {"stan getz": [{"name": "Chet Baker", "match": 0.9}]},
            "tag_albums": {},
            "artist_tags": {},
        },
    )
    reason = {
        "type": "similar",
        "detail": "Last.fm: similar to Stan Getz (your #1)",
        "src": "lastfm",
        "ref": "stan getz",
    }
    br.run_integrity_check(
        [{"id": "a", "artist": "Chet Baker", "title": "Chet", "reasons": [reason]}]
    )
    # the SAME reason on a different artist's record no longer reconstructs
    with pytest.raises(SystemExit) as exc_info:
        br.run_integrity_check(
            [
                {
                    "id": "b",
                    "artist": "Jim Hall",
                    "title": "Concierto",
                    "reasons": [reason],
                }
            ]
        )
    assert exc_info.value.code == 1


# --- Important 2: badges must not cross a merge unless a reason may ---


def test_merge_does_not_transfer_an_rym_badge_to_a_chartless_keeper():
    """The latent case: an absorbed record's chart badge landing on a keeper
    that charts nowhere makes exactly the claim NON_TRANSFERABLE_REASONS
    refuses to let a chart REASON make."""
    keeper = _merge_cand("Bill Evans", "Waltz for Debby", 70.0, badges={})
    absorbed = _merge_cand(
        "Bill Evans",
        "Waltzfor Debby",
        60.0,
        badges={"rym": {"chart": "cool-jazz", "rank": 3, "rating": 4.31}},
    )
    merged, log = br.merge_editions([keeper, absorbed])
    assert len(merged) == 1 and log  # the pair really merged
    assert merged[0]["badges"] == {}


def test_merge_does_not_transfer_a_discogs_badge_from_another_pressing():
    """The live case: Chet Baker -- In New York displayed
    discogs {rating 4.51, haves 277} absorbed from a different pressing, while
    its own candidate record has no Discogs release at all -- so its score was
    computed with no discogs quality term and no mega-canon novelty penalty.
    The card showed evidence that played no part in its own score."""
    keeper = _merge_cand("Chet Baker", "In New York", 66.5, badges={})
    absorbed = _merge_cand(
        "Chet Baker",
        "Chet Baker In New York",
        60.0,
        badges={"discogs": {"rating": 4.51, "haves": 277}},
    )
    merged, _log = br.merge_editions([keeper, absorbed])
    assert merged[0]["badges"] == {}


def test_merge_still_transfers_reddit_and_pitchfork_badges():
    """A badge crosses a merge exactly when a reason from the same source may.
    reddit/pitchfork key on artist+title -- the very identity the merge asserts
    the two records share -- and their reasons already transfer, so suppressing
    their badges would leave a card whose prose states what its badge row
    withholds."""
    keeper = _merge_cand("Max Roach", "We Insist Freedom Now", 54.8, badges={})
    absorbed = _merge_cand(
        "Max Roach",
        "WeInsist Freedom Now",
        34.6,
        badges={"reddit": {"mentions": 2}, "pitchfork": {"score": 8.4, "bnm": True}},
    )
    merged, _log = br.merge_editions([keeper, absorbed])
    assert set(merged[0]["badges"]) == {"reddit", "pitchfork"}


def test_merge_never_overwrites_a_badge_the_keeper_already_owns():
    keeper = _merge_cand(
        "Herbie Hancock", "Head Hunters", 69.6, badges={"reddit": {"mentions": 9}}
    )
    absorbed = _merge_cand(
        "Herbie Hancock", "Headhunters", 59.6, badges={"reddit": {"mentions": 4}}
    )
    merged, _log = br.merge_editions([keeper, absorbed])
    assert merged[0]["badges"] == {"reddit": {"mentions": 9}}


# --- Important 3: the sideman reason must be about performers ---


def test_is_performer_credit_rejects_the_non_performing_roles():
    for role in (
        "Written-By",
        "Producer",
        "Engineer",
        "Design",
        "Photography By",
        "Liner Notes",
        "Mastered By",
        "Mixed By",
        "Art Direction",
        "Composed By",
        "Arranged By",
    ):
        assert not br.is_performer_credit(_credit("X", role)), role


def test_is_performer_credit_accepts_performing_roles():
    for role in ("Bass", "Trumpet", "Tenor Saxophone", "Vocals", "Conductor", "Sitar"):
        assert br.is_performer_credit(_credit("X", role)), role


def test_is_performer_credit_keeps_a_credit_with_one_performing_role():
    """A compound role is performing if ANY of its parts is."""
    assert br.is_performer_credit(_credit("X", "Bass, Producer"))
    assert not br.is_performer_credit(_credit("X", "Producer, Liner Notes"))


def test_is_performer_credit_strips_bracket_qualifiers_before_splitting():
    """A qualifier can itself contain a comma, so brackets come off BEFORE the
    role is split -- otherwise "Technician [Technical Crew For Da Capo, Het
    Energiehuis]" yields the unknown part "Het Energiehuis]" and reads as a
    performer."""
    assert not br.is_performer_credit(_credit("X", "Design [Cover]"))
    assert not br.is_performer_credit(_credit("X", "Photography By [Booklet Pg 2, 19]"))
    assert not br.is_performer_credit(
        _credit("X", "Technician [Technical Crew For Da Capo, Het Energiehuis]")
    )
    assert br.is_performer_credit(_credit("X", "Saxophone [Tenor, Soprano]"))


def test_is_performer_credit_rejects_an_empty_role():
    assert not br.is_performer_credit(_credit("X", ""))


def test_performer_credits_filters_and_dedupes_by_name():
    release = {
        "credits": [
            _credit("Chet Baker", "Trumpet"),
            _credit("Chet Baker", "Written-By"),
            _credit("Orrin Keepnews", "Producer, Liner Notes"),
            _credit("Al Haig", "Piano"),
        ]
    }
    assert br.performer_credits(release) == ["Chet Baker", "Al Haig"]
    assert br.performer_credits(None) == []


def test_shared_sidemen_drops_a_composer_only_credit():
    """The live inaccuracy: Chet Baker -- In New York displayed "Chet Baker and
    Miles Davis appear on albums you saved". Miles composed; he did not play."""
    release = {"credits": _IN_NEW_YORK_CREDITS}
    profile = _profile(("Chet Baker", 137.0), ("Miles Davis", 120.0))
    assert br.shared_sidemen(release, profile) == [("Chet Baker", 1)]


def test_shared_sidemen_orders_by_profile_rank():
    release = {
        "credits": [
            _credit("Lee Morgan", "Trumpet"),
            _credit("Grant Green", "Guitar"),
            _credit("Chet Baker", "Trumpet"),
        ]
    }
    profile = _profile(
        ("Chet Baker", 130.0), ("Grant Green", 90.0), ("Lee Morgan", 50.0)
    )
    assert br.shared_sidemen(release, profile) == [
        ("Chet Baker", 1),
        ("Grant Green", 2),
        ("Lee Morgan", 3),
    ]


def test_shared_sidemen_ignores_artists_ranked_below_50():
    ranked = [(f"Artist {i:02d}", 100.0 - i) for i in range(60)]
    profile = _profile(*ranked)
    release = {
        "credits": [_credit("Artist 00", "Piano"), _credit("Artist 55", "Drums")]
    }
    assert br.shared_sidemen(release, profile) == [("Artist 00", 1)]


def test_shared_sidemen_refuses_a_homonym_indexed_credit_name():
    """ "(3)" is Discogs' entity disambiguator: "Paul Weller (3)" is a different
    person. The suffix must survive into the comparison, so a profile artist
    never matches an unrelated homonym -- even one holding a performing role."""
    release = {"credits": [_credit("Grant Green (2)", "Guitar")]}
    profile = _profile(("Grant Green", 90.0))
    assert br.shared_sidemen(release, profile) == []


def test_shared_sidemen_handles_a_missing_release():
    assert br.shared_sidemen(None, _profile(("Chet Baker", 1.0))) == []


def test_in_new_york_no_longer_earns_a_sideman_reason():
    """End to end on the real release: only one top-50 profile artist actually
    plays on it, and the reason needs two."""
    key = common.norm_key("Chet Baker", "In New York")
    raw = {
        "norm_key": key,
        "discogs": {
            "norm_key": key,
            "artist": "Chet Baker",
            "title": "In New York",
            "year": 1958,
            "labels": ["Riverside Records"],
            "rating": 4.51,
            "rating_count": 35,
            "haves": 277,
            "wants": 523,
            "credits": _IN_NEW_YORK_CREDITS,
            "discogs_release_id": 3469846,
        },
        "pitchfork": None,
        "reddit": None,
        "tag_album": None,
        "in_rym": False,
    }
    profile = _profile(("Chet Baker", 137.0), ("Miles Davis", 120.0))
    empty_lastfm = {"similar": {}, "tag_albums": {}, "artist_tags": {}}
    ctx = br.build_context(profile, empty_lastfm, {}, {"charts": {}})
    scored = br.score_candidate(raw, ctx)
    assert [r["type"] for r in scored["reasons"]] == ["artist"]
    # ...and the shelf matcher sees only the performers, not the photographer
    assert "Paul Weller (3)" not in scored["_credits"]
    assert "Chet Baker" in scored["_credits"]


# --- Important 4: the label reason may not ride a merge ---


def test_label_is_non_transferable():
    assert br.NON_TRANSFERABLE_REASONS == {"chart", "label"}


def test_merge_does_not_transfer_a_label_reason():
    """ "On Blue Note -- you have 5 albums from this label" makes two claims and
    reconstruction re-checks only the second (the owned count). An absorbed
    record's representative pressing can sit on a different label than the
    keeper's -- an original Riverside vs an OJC reissue is the ordinary case --
    so the album-to-label half would pass the gate while naming a label the
    keeper is not on."""
    keeper = _merge_cand(
        "Bill Evans",
        "Waltz for Debby",
        70.0,
        reasons=[_reason("artist", "Bill Evans is your #1 artist", "bill evans", 0.4)],
    )
    absorbed = _merge_cand(
        "Bill Evans",
        "Waltzfor Debby",
        60.0,
        reasons=[
            _reason(
                "label",
                "On Original Jazz Classics — you have 5 albums from this label",
                "Original Jazz Classics",
                0.9,
            )
        ],
    )
    merged, log = br.merge_editions([keeper, absorbed])
    assert len(merged) == 1 and log  # the pair really merged
    assert [r["type"] for r in merged[0]["reasons"]] == ["artist"]


# --- Minor 6: one selection key for both chart pickers ---


def _chart_entry(norm_key, rank, rating, count, title="T", artist="A"):
    return {
        "rank": rank,
        "norm_key": norm_key,
        "artist": artist,
        "title": title,
        "year": 1965,
        "rating": rating,
        "rating_count": count,
    }


def test_chart_data_for_picks_the_best_duplicate_row_not_file_order():
    """Real duplicate data exists: john coltrane::ascension appears twice in
    one chart ("[Edition I]"/"[Edition II]" collapsed by norm_title).
    best_chart_appearance picks by (rating, -rank); chart_data_for used to
    return whichever row came first in the file, so a re-scrape where the
    better-rated edition sits at a worse rank would make the displayed rank and
    the score come from different rows."""
    rym = {
        "charts": {
            "free-jazz": [
                _chart_entry("john coltrane::ascension", 12, 3.90, 5000),
                _chart_entry("john coltrane::ascension", 40, 4.10, 9000),
            ]
        }
    }
    data = br.chart_data_for("john coltrane::ascension", "free-jazz", rym)
    assert (data["rank"], data["rating"], data["count"]) == (40, 4.10, 9000)


def test_best_chart_appearance_returns_the_row_chart_data_for_renders():
    rym = {
        "charts": {
            "free-jazz": [
                _chart_entry("john coltrane::ascension", 12, 3.90, 5000),
                _chart_entry("john coltrane::ascension", 40, 4.10, 9000),
            ],
            "avant-garde-jazz": [
                _chart_entry("john coltrane::ascension", 3, 3.50, 100),
            ],
        }
    }
    slug, entry = br.best_chart_appearance("john coltrane::ascension", rym)
    data = br.chart_data_for("john coltrane::ascension", slug, rym)
    assert slug == "free-jazz"
    assert (entry["rank"], entry["rating"], entry["rating_count"]) == (
        data["rank"],
        data["rating"],
        data["count"],
    )


def test_best_chart_appearance_none_when_the_album_charts_nowhere():
    assert br.best_chart_appearance("x::y", {"charts": {}}) is None
    assert br.chart_data_for("x::y", "free-jazz", {"charts": {}}) is None


# --- Minor 7: output ids must be unique ---


def test_collect_output_albums_rejects_an_id_collision():
    """An external id is "ext-" + slugify(artist + " " + title), which discards
    the artist/title boundary, so two different norm_keys can collide into one
    id and by_id would last-win -- a shelf slot rendering a different album
    than it matched."""
    a = _sel_cand("Ron Carter", "Blues Farm", 50.0)
    b = _sel_cand("Ron", "Carter Blues Farm", 40.0)
    assert a["id"] == b["id"]  # the collision is real, not contrived
    with pytest.raises(AssertionError):
        br.collect_output_albums([], [], [a, b])


def test_collect_output_albums_accepts_a_clean_pool():
    a = _sel_cand("Ron Carter", "Blues Farm", 50.0)
    b = _sel_cand("Grant Green", "Idle Moments", 40.0)
    assert br.collect_output_albums([a], [], [a, b]) == [a]


# --- best_similar_seed: direct coverage ---


def _lastfm(similar):
    return {"similar": similar, "tag_albums": {}, "artist_tags": {}}


def test_best_similar_seed_picks_the_strongest_match():
    profile = _profile(("Chet Baker", 130.0), ("Stan Getz", 90.0))
    lastfm = _lastfm(
        {
            "chet baker": [{"name": "Jim Hall", "match": 0.42}],
            "stan getz": [{"name": "Jim Hall", "match": 0.77}],
        }
    )
    match, seed_key, name, rank = br.best_similar_seed("Jim Hall", lastfm, profile)
    assert (match, seed_key, name, rank) == (0.77, "stan getz", "Stan Getz", 2)


def test_best_similar_seed_ignores_seeds_ranked_below_30():
    ranked = [(f"Artist {i:02d}", 100.0 - i) for i in range(40)]
    profile = _profile(*ranked)
    lastfm = _lastfm(
        {
            "artist 35": [{"name": "Jim Hall", "match": 0.99}],
            "artist 05": [{"name": "Jim Hall", "match": 0.30}],
        }
    )
    match, seed_key, _name, rank = br.best_similar_seed("Jim Hall", lastfm, profile)
    assert (match, seed_key, rank) == (0.30, "artist 05", 6)


def test_best_similar_seed_ties_break_on_seed_rank_then_key():
    profile = _profile(("Chet Baker", 130.0), ("Stan Getz", 90.0), ("Joe Pass", 80.0))
    lastfm = _lastfm(
        {
            "stan getz": [{"name": "Jim Hall", "match": 0.6}],
            "joe pass": [{"name": "Jim Hall", "match": 0.6}],
        }
    )
    # equal match -> the better-ranked seed wins, whatever the dict order
    assert br.best_similar_seed("Jim Hall", lastfm, profile)[1] == "stan getz"


def test_best_similar_seed_none_when_nothing_matches():
    profile = _profile(("Chet Baker", 130.0))
    lastfm = _lastfm({"chet baker": [{"name": "Stan Getz", "match": 0.9}]})
    assert br.best_similar_seed("Jim Hall", lastfm, profile) is None
    # an empty norm can never match a candidate
    assert br.best_similar_seed("", lastfm, profile) is None


# ======================================================================
# integrity gate: the four reason types no test drove through it
# ======================================================================


def _gate_caches(tmp_path, **caches):
    for name, payload in caches.items():
        common.save_json(tmp_path / f"{name}.json", payload)


def test_gate_catches_a_tampered_sideman_reason(monkeypatch, tmp_path):
    """The only reason type whose sentence is a claim about the LIBRARY rather
    than about the album, so it is true wherever it lands. Reconstruction
    re-derives it through the same shared_sidemen -- which is exactly why the
    performer-role filter has to live in that shared helper: revert the filter
    and this faithful case starts naming Miles Davis again."""
    monkeypatch.setattr(br.common, "CACHE", tmp_path)
    _gate_caches(
        tmp_path,
        taste_profile=_profile(
            ("Chet Baker", 137.0), ("Miles Davis", 120.0), ("Al Haig", 60.0)
        ),
        discogs={
            "releases": [
                {"discogs_release_id": 3469846, "credits": _IN_NEW_YORK_CREDITS}
            ]
        },
    )
    album = {
        "id": "ext-chet-baker-in-new-york",
        "artist": "Chet Baker",
        "title": "In New York",
        "reasons": [
            {
                "type": "sideman",
                "detail": "Chet Baker and Al Haig appear on albums you saved",
                "src": "discogs",
                "ref": "release:3469846",
            }
        ],
    }
    br.run_integrity_check([album])

    # the pre-fix sentence -- Miles is on this release as Written-By only
    album["reasons"][0]["detail"] = (
        "Chet Baker and Miles Davis appear on albums you saved"
    )
    with pytest.raises(SystemExit) as exc_info:
        br.run_integrity_check([album])
    assert exc_info.value.code == 1


def test_gate_catches_a_sideman_reason_whose_release_vanished(monkeypatch, tmp_path):
    monkeypatch.setattr(br.common, "CACHE", tmp_path)
    _gate_caches(
        tmp_path,
        taste_profile=_profile(("Chet Baker", 137.0)),
        discogs={"releases": []},
    )
    album = {
        "id": "x",
        "artist": "Chet Baker",
        "title": "In New York",
        "reasons": [
            {
                "type": "sideman",
                "detail": "Chet Baker and Al Haig appear on albums you saved",
                "src": "discogs",
                "ref": "release:3469846",
            }
        ],
    }
    with pytest.raises(SystemExit):
        br.run_integrity_check([album])


def test_gate_catches_a_tampered_similar_reason(monkeypatch, tmp_path):
    monkeypatch.setattr(br.common, "CACHE", tmp_path)
    _gate_caches(
        tmp_path,
        taste_profile=_profile(("Chet Baker", 137.0), ("Stan Getz", 90.0)),
        lastfm=_lastfm({"stan getz": [{"name": "Jim Hall", "match": 0.77}]}),
    )
    album = {
        "id": "ext-jim-hall-concierto",
        "artist": "Jim Hall",
        "title": "Concierto",
        "reasons": [
            {
                "type": "similar",
                "detail": "Last.fm: similar to Stan Getz (your #2)",
                "src": "lastfm",
                "ref": "stan getz",
            }
        ],
    }
    br.run_integrity_check([album])

    album["reasons"][0]["detail"] = "Last.fm: similar to Stan Getz (your #1)"
    with pytest.raises(SystemExit) as exc_info:
        br.run_integrity_check([album])
    assert exc_info.value.code == 1


def test_gate_catches_a_similar_reason_below_the_emit_threshold(monkeypatch, tmp_path):
    """Generation only emits a similar reason at match >= 0.4, so
    reconstruction must apply the same floor -- otherwise a weakened Last.fm
    similarity would keep re-rendering the old sentence."""
    monkeypatch.setattr(br.common, "CACHE", tmp_path)
    _gate_caches(
        tmp_path,
        taste_profile=_profile(("Chet Baker", 137.0), ("Stan Getz", 90.0)),
        lastfm=_lastfm({"stan getz": [{"name": "Jim Hall", "match": 0.2}]}),
    )
    album = {
        "id": "x",
        "artist": "Jim Hall",
        "title": "Concierto",
        "reasons": [
            {
                "type": "similar",
                "detail": "Last.fm: similar to Stan Getz (your #2)",
                "src": "lastfm",
                "ref": "stan getz",
            }
        ],
    }
    with pytest.raises(SystemExit):
        br.run_integrity_check([album])


def test_gate_catches_a_tampered_reddit_reason(monkeypatch, tmp_path):
    monkeypatch.setattr(br.common, "CACHE", tmp_path)
    _gate_caches(
        tmp_path,
        reddit={
            "mentions": [
                {
                    "norm_key": "herbie hancock::head hunters",
                    "artist": "Herbie Hancock",
                    "title": "Head Hunters",
                    "count": 9,
                }
            ]
        },
    )
    album = {
        "id": "ext-herbie-hancock-head-hunters",
        "artist": "Herbie Hancock",
        "title": "Head Hunters",
        "reasons": [
            {
                "type": "reddit",
                "detail": "Mentioned in 9 r/jazz threads",
                "src": "reddit",
                "ref": "herbie hancock::head hunters",
            }
        ],
    }
    br.run_integrity_check([album])

    album["reasons"][0]["detail"] = "Mentioned in 99 r/jazz threads"
    with pytest.raises(SystemExit) as exc_info:
        br.run_integrity_check([album])
    assert exc_info.value.code == 1


def test_gate_catches_a_tampered_chart_reason(monkeypatch, tmp_path):
    monkeypatch.setattr(br.common, "CACHE", tmp_path)
    _gate_caches(
        tmp_path,
        rym={
            "charts": {
                "jazz-fusion": [
                    _chart_entry(
                        "herbie hancock::head hunters", 4, 3.96, 26000, "Head Hunters"
                    )
                ]
            }
        },
    )
    album = {
        "id": "ext-herbie-hancock-head-hunters",
        "artist": "Herbie Hancock",
        "title": "Head Hunters",
        "reasons": [
            {
                "type": "chart",
                "detail": "#4 in RYM jazz-fusion chart (3.96 from 26000 ratings)",
                "src": "rym",
                "ref": "jazz-fusion",
            }
        ],
    }
    br.run_integrity_check([album])

    album["reasons"][0]["detail"] = (
        "#1 in RYM jazz-fusion chart (3.96 from 26000 ratings)"
    )
    with pytest.raises(SystemExit) as exc_info:
        br.run_integrity_check([album])
    assert exc_info.value.code == 1


def test_a_reason_transferred_by_a_merge_still_reconstructs(monkeypatch, tmp_path):
    """NON_TRANSFERABLE_REASONS is the single guard between a future merge
    change and a gate failure. This drives a real merge -- absorbed record
    carries the reddit reason, keeper does not -- through the real gate, so a
    change that let the wrong type ride along would fail here rather than only
    in the live build."""
    monkeypatch.setattr(br.common, "CACHE", tmp_path)
    _gate_caches(
        tmp_path,
        reddit={
            "mentions": [
                {
                    "norm_key": "herbie hancock::headhunters",
                    "artist": "Herbie Hancock",
                    "title": "Headhunters",
                    "count": 7,
                }
            ]
        },
    )
    keeper = _merge_cand("Herbie Hancock", "Head Hunters", 69.6)
    absorbed = _merge_cand(
        "Herbie Hancock",
        "Headhunters",
        59.6,
        reasons=[
            _reason(
                "reddit",
                "Mentioned in 7 r/jazz threads",
                "herbie hancock::headhunters",
                0.21,
            )
        ],
    )
    merged, log = br.merge_editions([keeper, absorbed])
    assert log  # the pair really merged
    assert merged[0]["title"] == "Head Hunters"
    assert [r["type"] for r in merged[0]["reasons"]] == ["reddit"]

    # the transferred reason reconstructs against its OWN stored ref, which is
    # the absorbed record's norm_key -- not the keeper's
    br.run_integrity_check(merged)

    merged[0]["reasons"][0]["detail"] = "Mentioned in 70 r/jazz threads"
    with pytest.raises(SystemExit):
        br.run_integrity_check(merged)

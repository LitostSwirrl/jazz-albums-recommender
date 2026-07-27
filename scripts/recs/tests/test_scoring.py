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
            _reason(
                "label", "On Columbia — you have 9 albums from this label", "c", 0.29
            ),
            _reason("similar", "Last.fm: similar to X (your #2)", "x", 0.01),
        ],
    )
    merged, _log = br.merge_editions([high, low])
    reasons = merged[0]["reasons"]
    assert len(reasons) == 3
    # top three by contribution, the 0.01 similar is dropped
    assert [r["type"] for r in reasons] == ["reddit", "label", "artist"]


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

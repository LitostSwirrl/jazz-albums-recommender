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

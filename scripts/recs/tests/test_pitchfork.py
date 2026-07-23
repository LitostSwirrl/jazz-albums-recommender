import json
from collections import Counter
from datetime import date

import pytest
import requests

from scripts.recs import fetch_pitchfork as fp


# --- fixtures: small synthetic HTML modeled on the real listing/review markup ---


def _listing_item(slug: str, date_str: str) -> str:
    return (
        '<a class="summary-item-tracking__hed-link summary-item__hed-link" '
        f'href="/reviews/albums/{slug}/" target="_self"><h3>T</h3></a>'
        f'<time class="summary-item__publish-date">{date_str}</time>'
    )


LISTING_PAGE_1 = (
    "<html><body>"
    + _listing_item("album-one", "July 8, 2026")
    + _listing_item("album-two", "June 25, 2026")
    + "</body></html>"
)

LISTING_PAGE_REPEAT = (
    LISTING_PAGE_1  # identical links -- simulates a dead-end/sticky repeat
)

LISTING_PAGE_MIXED_YEARS = (
    "<html><body>"
    + _listing_item("album-new", "January 5, 2019")
    + _listing_item("album-old", "December 1, 2017")
    + "</body></html>"
)

LISTING_PAGE_ALL_PRE_2018 = (
    "<html><body>"
    + _listing_item("album-a", "December 1, 2017")
    + _listing_item("album-b", "January 1, 2010")
    + "</body></html>"
)


def _hed_link_only(slug: str) -> str:
    """Hed-link anchor with no matching publish-date time tag -- used to
    build a mismatched-count listing fixture (Finding 3)."""
    return (
        '<a class="summary-item-tracking__hed-link summary-item__hed-link" '
        f'href="/reviews/albums/{slug}/" target="_self"><h3>T</h3></a>'
    )


LISTING_PAGE_MISMATCHED_COUNTS = (
    "<html><body>"
    + _hed_link_only("album-x")
    + _hed_link_only("album-y")
    + _hed_link_only("album-z")
    + '<time class="summary-item__publish-date">July 8, 2026</time>'
    + '<time class="summary-item__publish-date">June 25, 2026</time>'
    + "</body></html>"
)


def _review_html(
    *, date_published: str, artists: list[dict], items: list[dict], extra: str = ""
) -> str:
    """Build a minimal review page: a real JSON-LD Review block (datePublished
    only -- reviewRating is null on the live site so it's never emitted here)
    plus a window.__PRELOADED_STATE__ blob carrying the two arrays our parser
    locates by substring search, not by exact tree position."""
    jsonld = json.dumps(
        {
            "@context": "http://schema.org",
            "@type": "Review",
            "datePublished": date_published,
        }
    )
    state = json.dumps({"artists": artists, "itemsReviewed": items})
    return (
        f'<script type="application/ld+json">{jsonld}</script>'
        f"<script>window.__PRELOADED_STATE__ = {state};</script>{extra}"
    )


# A hand-authored fixture mirroring the real Shabaka sample closely, including
# the backslash-escaped unicode slash (/) verified in the live raw HTML.
SHABAKA_HTML = (
    '<script type="application/ld+json">'
    '{"@type":"Review","datePublished":"2026-03-12T00:02:00.000-04:00"}'
    "</script>"
    "<script>window.__PRELOADED_STATE__ = "
    '{"transformed":{"review":{'
    '"headerProps":{"artists":[{"genres":[{"node":{"name":"Jazz"}}],'
    '"name":" Shabaka","uri":"artists\\u002Fshabaka-hutchings\\u002F"}]},'
    '"multiReviewHeaderProps":{"itemsReviewed":[{"albumId":"x",'
    '"dangerousHed":"Of the Earth\\u002FReprise","publisher":"Shabaka",'
    '"releaseYear":"2026","musicRating":{"isBestNewMusic":false,'
    '"isBestNewReissue":false,"score":7.9}}]}}}};'
    "</script>"
)


# --- parse_listing: links + dates paired, in document order ---


def test_parse_listing_extracts_absolute_urls_and_dates_in_order():
    pairs = fp.parse_listing(LISTING_PAGE_1)
    assert pairs == [
        ("https://pitchfork.com/reviews/albums/album-one/", date(2026, 7, 8)),
        ("https://pitchfork.com/reviews/albums/album-two/", date(2026, 6, 25)),
    ]


def test_parse_listing_empty_page_returns_empty():
    assert fp.parse_listing("<html><body>nothing here</body></html>") == []


def test_parse_listing_returns_none_on_href_date_count_mismatch():
    """Finding 3: 3 hed-links but 2 publish-dates -- a bare zip() would
    silently mispair/truncate; must signal the mismatch instead of guessing."""
    assert fp.parse_listing(LISTING_PAGE_MISMATCHED_COUNTS) is None


# --- dedupe_new: sticky/featured item repeat across pages ---


def test_dedupe_new_drops_seen_and_mutates_seen_set():
    seen = {"https://pitchfork.com/reviews/albums/album-one/"}
    pairs = fp.parse_listing(LISTING_PAGE_1)
    result = fp.dedupe_new(pairs, seen)

    assert result == [
        ("https://pitchfork.com/reviews/albums/album-two/", date(2026, 6, 25))
    ]
    assert "https://pitchfork.com/reviews/albums/album-two/" in seen


def test_dedupe_new_all_seen_returns_empty():
    pairs = fp.parse_listing(LISTING_PAGE_1)
    seen = {url for url, _ in pairs}
    assert fp.dedupe_new(pairs, seen) == []


# --- collect_review_urls: pagination stop conditions ---


def test_collect_review_urls_stops_on_no_new_links(monkeypatch):
    calls = []

    def fake_fetch(page):
        calls.append(page)
        return LISTING_PAGE_1 if page == 1 else LISTING_PAGE_REPEAT

    monkeypatch.setattr(fp, "_fetch_listing_page", fake_fetch)
    stats: Counter = Counter()
    pairs, _first_html = fp.collect_review_urls(stats, max_pages=5)

    assert calls == [1, 2]
    assert len(pairs) == 2
    assert stats["listing_stopped_no_new_links"] == 1


def test_collect_review_urls_stops_when_page_all_pre_2018(monkeypatch):
    calls = []

    def fake_fetch(page):
        calls.append(page)
        return LISTING_PAGE_ALL_PRE_2018

    monkeypatch.setattr(fp, "_fetch_listing_page", fake_fetch)
    stats: Counter = Counter()
    pairs, _first_html = fp.collect_review_urls(stats, max_pages=5)

    assert calls == [1]
    assert pairs == []
    assert stats["listing_stopped_pre_2018"] == 1


def test_collect_review_urls_mixed_page_excludes_pre_2018_but_keeps_paginating(
    monkeypatch,
):
    calls = []

    def fake_fetch(page):
        calls.append(page)
        return LISTING_PAGE_MIXED_YEARS  # same page twice -> page 2 is "no new links"

    monkeypatch.setattr(fp, "_fetch_listing_page", fake_fetch)
    stats: Counter = Counter()
    pairs, _first_html = fp.collect_review_urls(stats, max_pages=5)

    assert calls == [1, 2]
    assert len(pairs) == 1
    assert (
        pairs[0][1].year == 2019
    )  # the 2017 item was excluded, not just the stop trigger
    assert stats["listing_stopped_no_new_links"] == 1
    assert stats["listing_stopped_pre_2018"] == 0


def test_collect_review_urls_respects_max_pages_cap(monkeypatch):
    calls = []

    def fake_fetch(page):
        calls.append(page)
        return (
            "<html><body>"
            + _listing_item(f"unique-{page}", "January 1, 2026")
            + "</body></html>"
        )

    monkeypatch.setattr(fp, "_fetch_listing_page", fake_fetch)
    stats: Counter = Counter()
    pairs, _first_html = fp.collect_review_urls(stats, max_pages=2)

    assert calls == [1, 2]
    assert len(pairs) == 2


def test_collect_review_urls_fails_loud_on_listing_href_date_mismatch(
    monkeypatch, tmp_path
):
    """Finding 3, orchestration level: a listing page with mismatched
    href/date counts must terminate the crawl via _fail_loud (dumping the
    LISTING page's HTML), not silently continue with mispaired or missing
    dates."""
    monkeypatch.setattr(
        fp, "_fetch_listing_page", lambda page: LISTING_PAGE_MISMATCHED_COUNTS
    )
    monkeypatch.setattr(fp, "PARSE_FAIL_PATH", tmp_path / "fail.html")
    stats: Counter = Counter()

    with pytest.raises(SystemExit) as exc_info:
        fp.collect_review_urls(stats, max_pages=5)

    assert exc_info.value.code == 1
    assert (tmp_path / "fail.html").read_text(
        encoding="utf-8"
    ) == LISTING_PAGE_MISMATCHED_COUNTS


# --- extract_items_reviewed / extract_artist_names: embedded-state parsing ---


def test_extract_items_reviewed_parses_embedded_array():
    html = _review_html(
        date_published="2026-01-01T00:00:00.000-04:00",
        artists=[{"name": "A"}],
        items=[
            {
                "dangerousHed": "T",
                "musicRating": {"isBestNewMusic": False, "score": 5.0},
            }
        ],
    )
    items = fp.extract_items_reviewed(html)
    assert items == [
        {"dangerousHed": "T", "musicRating": {"isBestNewMusic": False, "score": 5.0}}
    ]


def test_extract_items_reviewed_none_when_key_absent():
    assert fp.extract_items_reviewed("<html>nothing here</html>") is None


def test_extract_artist_names_strips_leading_space():
    html = _review_html(
        date_published="2026-01-01T00:00:00.000-04:00",
        artists=[{"name": " Shabaka"}],
        items=[{"dangerousHed": "T"}],
    )
    assert fp.extract_artist_names(html) == ["Shabaka"]


def test_extract_artist_names_preserves_order_for_multiple_artists():
    html = _review_html(
        date_published="2026-01-01T00:00:00.000-04:00",
        artists=[{"name": "Ambrose Akinmusire"}, {"name": "Mary Halvorson"}],
        items=[{"dangerousHed": "T"}],
    )
    assert fp.extract_artist_names(html) == ["Ambrose Akinmusire", "Mary Halvorson"]


def test_extract_artist_names_none_when_key_wholly_absent():
    """Finding 2: the "artists" key occurs exactly once on every real page
    (inside headerProps) -- wholly absent means markup drift, so this must
    signal a parse failure (None), not read the same as a valid-but-empty
    artists array."""
    assert fp.extract_artist_names("<html>nothing here</html>") is None


def test_extract_artist_names_empty_list_when_key_present_but_empty():
    """Contrast case: "artists":[] IS present (just credits nobody) -- this
    stays the pre-existing behavior, an empty list the caller counts as an
    empty-norm skip, not a fail-loud."""
    html = _review_html(
        date_published="2026-01-01T00:00:00.000-04:00",
        artists=[],
        items=[{"dangerousHed": "T"}],
    )
    assert fp.extract_artist_names(html) == []


def test_extract_items_reviewed_and_artists_handle_shabaka_fixture_with_escaped_slash():
    """The real raw HTML backslash-escapes unicode (\\u002F for '/') -- confirm
    our JSON parsing decodes it rather than leaving the literal escape in
    the title, and that the leading-space artist name is stripped."""
    items = fp.extract_items_reviewed(SHABAKA_HTML)
    assert items[0]["dangerousHed"] == "Of the Earth/Reprise"
    assert fp.extract_artist_names(SHABAKA_HTML) == ["Shabaka"]


# --- extract_score: primary musicRating.score, fallback regex ---


def test_extract_score_primary_from_musicrating():
    item = {"musicRating": {"score": 8.3, "isBestNewMusic": False}}
    assert fp.extract_score(item, "") == 8.3


def test_extract_score_fallback_regex_when_musicrating_missing():
    item = {"dangerousHed": "Test", "publisher": "Label"}
    html = 'blah blah "score": 6.5 more blah'
    assert fp.extract_score(item, html) == 6.5


def test_extract_score_fallback_disabled_on_multi_item_page():
    """Finding 1: on a multi-item page the whole-page fallback regex can't
    tell which item's score it's looking at (reproduced: item 2 silently
    inheriting item 1's 6.0) -- it must not fire even though a "score"
    string exists elsewhere on the page; the item resolves to None instead,
    for the caller's completeness gate to catch."""
    item = {"dangerousHed": "Test", "publisher": "Label"}
    html = 'blah blah "score": 6.5 more blah'
    assert fp.extract_score(item, html, total_items=2) is None


def test_extract_score_none_when_nothing_found():
    item = {"dangerousHed": "Test"}
    assert fp.extract_score(item, "no score anywhere") is None


def test_extract_score_zero_is_not_treated_as_missing():
    item = {"musicRating": {"score": 0.0}}
    assert fp.extract_score(item, "") == 0.0


# --- extract_bnm: isBestNewMusic detection ---


def test_extract_bnm_true():
    assert fp.extract_bnm({"musicRating": {"isBestNewMusic": True}}) is True


def test_extract_bnm_false_default_when_musicrating_missing():
    assert fp.extract_bnm({"dangerousHed": "x"}) is False


def test_extract_bnm_ignores_is_best_new_reissue():
    assert (
        fp.extract_bnm(
            {"musicRating": {"isBestNewMusic": False, "isBestNewReissue": True}}
        )
        is False
    )


# --- _strip_tags: defensive <em> stripping on dangerousHed ---


def test_strip_tags_removes_em_tags():
    assert fp._strip_tags("<em>Some Album</em>") == "Some Album"


def test_strip_tags_passthrough_plain_text():
    assert fp._strip_tags("Of the Earth") == "Of the Earth"


# --- extract_publish_year: JSON-LD primary, embedded-state fallback ---


def test_extract_publish_year_from_jsonld():
    html = (
        '<script type="application/ld+json">'
        '{"@type":"Review","datePublished":"2024-05-01T00:00:00.000-04:00"}'
        "</script>"
    )
    assert fp.extract_publish_year(html) == 2024


def test_extract_publish_year_fallback_to_modified_date_when_jsonld_missing():
    html = '<script>window.__PRELOADED_STATE__ = {"modifiedDate":"2019-08-01T00:00:00-04:00"};</script>'
    assert fp.extract_publish_year(html) == 2019


def test_extract_publish_year_none_when_nothing_found():
    assert fp.extract_publish_year("<html>nothing here</html>") is None


# --- pair_artists_to_items: positional pairing vs ambiguous fallback ---


def test_pair_artists_single_item_multiple_artists_uses_first_no_ambiguous_count():
    """A single reviewed item credited to two artists (a collab album) is
    the primary-credit convention, not an ambiguous multi-album roundup --
    verified against the real Akinmusire/Halvorson collab review."""
    stats: Counter = Counter()
    items = [{"dangerousHed": "Collab Album"}]
    artists = ["Ambrose Akinmusire", "Mary Halvorson"]
    result = fp.pair_artists_to_items(items, artists, stats)

    assert result == ["Ambrose Akinmusire"]
    assert stats["multi_item_ambiguous"] == 0


def test_pair_artists_multi_item_positional_when_counts_match():
    stats: Counter = Counter()
    items = [{"dangerousHed": "Album One"}, {"dangerousHed": "Album Two"}]
    artists = ["Artist One", "Artist Two"]
    result = fp.pair_artists_to_items(items, artists, stats)

    assert result == ["Artist One", "Artist Two"]
    assert stats["multi_item_ambiguous"] == 0


def test_pair_artists_multi_item_ambiguous_fallback_when_counts_mismatch():
    stats: Counter = Counter()
    items = [{"dangerousHed": "Album One"}, {"dangerousHed": "Album Two"}]
    artists = ["Only Artist"]
    result = fp.pair_artists_to_items(items, artists, stats)

    assert result == ["Only Artist", "Only Artist"]
    assert stats["multi_item_ambiguous"] == 2


def test_pair_artists_no_artists_found_returns_empty_strings():
    stats: Counter = Counter()
    items = [{"dangerousHed": "Album One"}]
    result = fp.pair_artists_to_items(items, [], stats)

    assert result == [""]
    assert stats["multi_item_ambiguous"] == 0


# --- parse_review_page: full integration over the embedded-state fixtures ---


def test_parse_review_page_single_artist_full_record():
    stats: Counter = Counter()
    records = fp.parse_review_page(
        SHABAKA_HTML,
        "https://pitchfork.com/reviews/albums/shabaka-of-the-earth/",
        stats,
    )

    assert records == [
        {
            "norm_key": "shabaka::of the earthreprise",
            "artist": "Shabaka",
            "title": "Of the Earth/Reprise",
            "score": 7.9,
            "bnm": False,
            "year": 2026,
            "url": "https://pitchfork.com/reviews/albums/shabaka-of-the-earth/",
        }
    ]


def test_parse_review_page_uses_artist_not_publisher_label():
    """Verified against the real Akinmusire/Halvorson review: publisher is
    the record label ('Nonesuch'), never the artist."""
    html = _review_html(
        date_published="2026-07-08T00:01:00.000-04:00",
        artists=[{"name": "Ambrose Akinmusire"}, {"name": "Mary Halvorson"}],
        items=[
            {
                "dangerousHed": "Slo-Mo Neon Luminate Hoverings",
                "publisher": "Nonesuch",
                "musicRating": {
                    "isBestNewMusic": False,
                    "isBestNewReissue": False,
                    "score": 7.2,
                },
            }
        ],
    )
    stats: Counter = Counter()
    records = fp.parse_review_page(
        html, "https://pitchfork.com/reviews/albums/x/", stats
    )

    assert len(records) == 1
    assert records[0]["artist"] == "Ambrose Akinmusire"
    assert records[0]["artist"] != "Nonesuch"
    assert records[0]["score"] == 7.2


def test_parse_review_page_multi_item_positional_pairing():
    html = _review_html(
        date_published="2026-01-01T00:00:00.000-04:00",
        artists=[{"name": "Artist One"}, {"name": "Artist Two"}],
        items=[
            {
                "dangerousHed": "Album One",
                "musicRating": {"isBestNewMusic": False, "score": 6.0},
            },
            {
                "dangerousHed": "Album Two",
                "musicRating": {"isBestNewMusic": True, "score": 8.5},
            },
        ],
    )
    stats: Counter = Counter()
    records = fp.parse_review_page(
        html, "https://pitchfork.com/reviews/albums/roundup/", stats
    )

    assert [r["artist"] for r in records] == ["Artist One", "Artist Two"]
    assert [r["title"] for r in records] == ["Album One", "Album Two"]
    assert [r["bnm"] for r in records] == [False, True]
    assert stats["multi_item_ambiguous"] == 0


def test_parse_review_page_multi_item_ambiguous_fallback_counted():
    html = _review_html(
        date_published="2026-01-01T00:00:00.000-04:00",
        artists=[{"name": "Artist One"}],
        items=[
            {
                "dangerousHed": "Album One",
                "musicRating": {"isBestNewMusic": False, "score": 6.0},
            },
            {
                "dangerousHed": "Album Two",
                "musicRating": {"isBestNewMusic": False, "score": 8.5},
            },
        ],
    )
    stats: Counter = Counter()
    records = fp.parse_review_page(
        html, "https://pitchfork.com/reviews/albums/roundup2/", stats
    )

    assert [r["artist"] for r in records] == ["Artist One", "Artist One"]
    assert stats["multi_item_ambiguous"] == 2


def test_parse_review_page_multi_item_missing_musicrating_does_not_copy_score():
    """Finding 1 (reviewer-reproduced): multi-item page where item two lacks
    musicRating and item one's "score": 6.0 text sits elsewhere on the page.
    Item two must resolve to score=None, never silently inherit item one's
    6.0 via the whole-page fallback regex."""
    html = _review_html(
        date_published="2026-01-01T00:00:00.000-04:00",
        artists=[{"name": "Artist One"}, {"name": "Artist Two"}],
        items=[
            {
                "dangerousHed": "Album One",
                "musicRating": {"isBestNewMusic": False, "score": 6.0},
            },
            {"dangerousHed": "Album Two", "publisher": "Label"},
        ],
    )
    stats: Counter = Counter()
    records = fp.parse_review_page(
        html, "https://pitchfork.com/reviews/albums/roundup3/", stats
    )

    assert [r["score"] for r in records] == [6.0, None]


def test_parse_review_page_fallback_score_regex_when_musicrating_absent():
    state = json.dumps(
        {
            "artists": [{"name": "Test Artist"}],
            "itemsReviewed": [
                {"dangerousHed": "Test Album", "publisher": "Test Label"}
            ],
        }
    )
    html = (
        '<script type="application/ld+json">'
        '{"@type":"Review","datePublished":"2026-01-01T00:00:00.000-04:00"}'
        "</script>"
        f"<script>window.__PRELOADED_STATE__ = {state};</script>"
        '<!-- legacy fallback marker "score": 6.4 -->'
    )
    stats: Counter = Counter()
    records = fp.parse_review_page(
        html, "https://pitchfork.com/reviews/albums/x/", stats
    )

    assert len(records) == 1
    assert records[0]["score"] == 6.4
    assert records[0]["artist"] == "Test Artist"
    assert records[0]["title"] == "Test Album"


def test_parse_review_page_skips_empty_norm_and_counts():
    """common.norm() strips CJK entirely -- an empty-sided norm_key must
    never be emitted, just skipped and counted."""
    html = _review_html(
        date_published="2026-01-01T00:00:00.000-04:00",
        artists=[{"name": "以莉高露"}],
        items=[
            {
                "dangerousHed": "Test Album",
                "musicRating": {"isBestNewMusic": False, "score": 5.0},
            }
        ],
    )
    stats: Counter = Counter()
    records = fp.parse_review_page(
        html, "https://pitchfork.com/reviews/albums/x/", stats
    )

    assert records == []
    assert stats["empty_norm"] == 1


def test_parse_review_page_returns_none_when_items_reviewed_missing():
    stats: Counter = Counter()
    assert (
        fp.parse_review_page("<html>nothing here</html>", "https://x/", stats) is None
    )


def test_parse_review_page_returns_none_when_artists_key_missing():
    """Finding 2 (reviewer-reproduced): itemsReviewed intact, but the
    "artists" key is wholly absent from the page -- must signal a parse
    failure (None), not silently degrade into an empty-norm skip."""
    html = (
        '<script type="application/ld+json">'
        '{"@type":"Review","datePublished":"2026-01-01T00:00:00.000-04:00"}'
        "</script>"
        "<script>window.__PRELOADED_STATE__ = "
        '{"itemsReviewed":[{"dangerousHed":"Test Album",'
        '"musicRating":{"isBestNewMusic":false,"score":5.0}}]};'
        "</script>"
    )
    stats: Counter = Counter()
    records = fp.parse_review_page(
        html, "https://pitchfork.com/reviews/albums/x/", stats
    )

    assert records is None
    assert stats["empty_norm"] == 0


def test_parse_review_page_artists_key_present_but_empty_counts_empty_norm():
    """Contrast case: "artists":[] IS present -- stays the pre-existing
    per-record empty-norm skip, counted, no exit."""
    html = _review_html(
        date_published="2026-01-01T00:00:00.000-04:00",
        artists=[],
        items=[
            {
                "dangerousHed": "Test Album",
                "musicRating": {"isBestNewMusic": False, "score": 5.0},
            }
        ],
    )
    stats: Counter = Counter()
    records = fp.parse_review_page(
        html, "https://pitchfork.com/reviews/albums/x/", stats
    )

    assert records == []
    assert stats["empty_norm"] == 1


# --- _page_is_complete: completeness gate (score=0.0 must not read as missing) ---


def test_page_is_complete_true_for_empty_list():
    assert fp._page_is_complete([]) is True


def test_page_is_complete_false_when_score_missing():
    record = {"artist": "A", "title": "T", "score": None, "year": 2020}
    assert fp._page_is_complete([record]) is False


def test_page_is_complete_true_when_score_is_zero():
    record = {"artist": "A", "title": "T", "score": 0.0, "year": 2020}
    assert fp._page_is_complete([record]) is True


def test_page_is_complete_false_when_artist_missing():
    record = {"artist": "", "title": "T", "score": 5.0, "year": 2020}
    assert fp._page_is_complete([record]) is False


# --- fetch_reviews: transport-fault skip vs fail-loud parse failure ---


def test_fetch_reviews_skips_request_exception_and_counts(monkeypatch):
    def fake_fetch(url):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(fp, "_fetch_review_page", fake_fetch)
    stats: Counter = Counter()
    result = fp.fetch_reviews(
        [("https://pitchfork.com/reviews/albums/x/", date(2026, 1, 1))], stats
    )

    assert result == []
    assert stats["fetch_failed"] == 1


def test_fetch_reviews_happy_path_returns_records(monkeypatch):
    monkeypatch.setattr(fp, "_fetch_review_page", lambda url: SHABAKA_HTML)
    stats: Counter = Counter()
    result = fp.fetch_reviews(
        [
            (
                "https://pitchfork.com/reviews/albums/shabaka-of-the-earth/",
                date(2026, 3, 12),
            )
        ],
        stats,
    )

    assert len(result) == 1
    assert result[0]["score"] == 7.9


def test_fetch_reviews_drops_record_whose_own_year_is_pre_2018(monkeypatch):
    """Defensive safety net: the listing's per-item date decides what to
    fetch (cheaper), but the review's OWN publish year is what actually
    governs emission -- a boundary mismatch between the two (e.g. a
    year-end timezone rollover) must not leak a pre-2018 review into the
    output just because its listing date looked like 2018+."""
    html = _review_html(
        date_published="2017-12-31T23:00:00.000-04:00",
        artists=[{"name": "Test Artist"}],
        items=[
            {
                "dangerousHed": "Test Album",
                "musicRating": {"isBestNewMusic": False, "score": 5.0},
            }
        ],
    )
    monkeypatch.setattr(fp, "_fetch_review_page", lambda url: html)
    stats: Counter = Counter()
    result = fp.fetch_reviews(
        [("https://pitchfork.com/reviews/albums/x/", date(2018, 1, 2))], stats
    )

    assert result == []
    assert stats["pre_2018_dropped"] == 1


def test_fetch_reviews_fails_loud_when_items_reviewed_block_missing(
    monkeypatch, tmp_path
):
    bad_html = "<html>no preloaded state here</html>"
    monkeypatch.setattr(fp, "_fetch_review_page", lambda url: bad_html)
    monkeypatch.setattr(fp, "PARSE_FAIL_PATH", tmp_path / "fail.html")
    stats: Counter = Counter()

    with pytest.raises(SystemExit) as exc_info:
        fp.fetch_reviews(
            [("https://pitchfork.com/reviews/albums/x/", date(2026, 1, 1))], stats
        )

    assert exc_info.value.code == 1
    assert (tmp_path / "fail.html").read_text(encoding="utf-8") == bad_html


def test_fetch_reviews_fails_loud_on_score_less_record(monkeypatch, tmp_path):
    """itemsReviewed is present (title/artist recoverable) but no musicRating
    and no raw score text anywhere -- both primary and fallback score
    extraction fail, so the completeness gate must trip, not silently drop
    the record."""
    html = _review_html(
        date_published="2026-01-01T00:00:00.000-04:00",
        artists=[{"name": "Test Artist"}],
        items=[{"dangerousHed": "Test Album", "publisher": "Label"}],
    )
    monkeypatch.setattr(fp, "_fetch_review_page", lambda url: html)
    monkeypatch.setattr(fp, "PARSE_FAIL_PATH", tmp_path / "fail.html")
    stats: Counter = Counter()

    with pytest.raises(SystemExit) as exc_info:
        fp.fetch_reviews(
            [("https://pitchfork.com/reviews/albums/y/", date(2026, 1, 1))], stats
        )

    assert exc_info.value.code == 1
    assert (tmp_path / "fail.html").exists()


def test_fetch_reviews_fails_loud_multi_item_page_score_not_misattributed(
    monkeypatch, tmp_path
):
    """Finding 1, fetch_reviews/fail-loud layer: item two's score=None must
    trip the completeness gate (exit 1) rather than get silently backfilled
    with item one's score by the whole-page fallback regex."""
    html = _review_html(
        date_published="2026-01-01T00:00:00.000-04:00",
        artists=[{"name": "Artist One"}, {"name": "Artist Two"}],
        items=[
            {
                "dangerousHed": "Album One",
                "musicRating": {"isBestNewMusic": False, "score": 6.0},
            },
            {"dangerousHed": "Album Two", "publisher": "Label"},
        ],
    )
    monkeypatch.setattr(fp, "_fetch_review_page", lambda url: html)
    monkeypatch.setattr(fp, "PARSE_FAIL_PATH", tmp_path / "fail.html")
    stats: Counter = Counter()

    with pytest.raises(SystemExit) as exc_info:
        fp.fetch_reviews(
            [("https://pitchfork.com/reviews/albums/roundup3/", date(2026, 1, 1))],
            stats,
        )

    assert exc_info.value.code == 1
    assert (tmp_path / "fail.html").exists()


def test_fetch_reviews_fails_loud_when_artists_key_missing(monkeypatch, tmp_path):
    """Finding 2 (reviewer-reproduced): intact itemsReviewed, but the
    "artists" key is wholly absent -- must fail loud (exit 1), not silently
    emit stats={'empty_norm': 1} with exit 0."""
    html = (
        '<script type="application/ld+json">'
        '{"@type":"Review","datePublished":"2026-01-01T00:00:00.000-04:00"}'
        "</script>"
        "<script>window.__PRELOADED_STATE__ = "
        '{"itemsReviewed":[{"dangerousHed":"Test Album",'
        '"musicRating":{"isBestNewMusic":false,"score":5.0}}]};'
        "</script>"
    )
    monkeypatch.setattr(fp, "_fetch_review_page", lambda url: html)
    monkeypatch.setattr(fp, "PARSE_FAIL_PATH", tmp_path / "fail.html")
    stats: Counter = Counter()

    with pytest.raises(SystemExit) as exc_info:
        fp.fetch_reviews(
            [("https://pitchfork.com/reviews/albums/x/", date(2026, 1, 1))], stats
        )

    assert exc_info.value.code == 1
    assert (tmp_path / "fail.html").read_text(encoding="utf-8") == html

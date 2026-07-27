import argparse
import subprocess
from collections import Counter

import pytest
import requests

from scripts.recs import common
from scripts.recs import fetch_reddit as fr

ATOM_NS = "http://www.w3.org/2005/Atom"


# --- fixtures: small synthetic Atom XML modeled on the real reddit.com feeds ---


def _entry_xml(
    entry_id: str, title: str, link: str, published: str, content_html: str
) -> str:
    return (
        "<entry>"
        f"<id>{entry_id}</id>"
        f"<title>{title}</title>"
        f'<link href="{link}"/>'
        f"<published>{published}</published>"
        f'<content type="html"><![CDATA[{content_html}]]></content>'
        "</entry>"
    )


def _wrap_feed(entries_xml: str) -> str:
    return f'<feed xmlns="{ATOM_NS}">{entries_xml}</feed>'


SAMPLE_ENTRY_XML = _entry_xml(
    "t3_1tnsh9b",
    "RIP Sonny Rollins",
    "https://www.reddit.com/r/Jazz/comments/1tnsh9b/rip_sonny_rollins/",
    "2026-05-26T01:40:20+00:00",
    "<table><tr><td>"
    '<a href="https://www.reddit.com/r/Jazz/comments/1tnsh9b/rip_sonny_rollins/">'
    '<img src="x.jpg" alt="RIP Sonny Rollins" /></a>'
    '</td><td> <!-- SC_OFF --><div class="md"><p>Rest in peace &amp; thank you Sonny.</p></div>'
    "<!-- SC_ON --> submitted by "
    '<a href="https://www.reddit.com/user/TennesseeTom">/u/TennesseeTom</a>'
    "</td></tr></table>",
)


class FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeHTTPResponse:
    def __init__(self, status_code):
        self.status_code = status_code


# --- Atom parsing: entry -> (id, title, link, published, raw content) ---


def test_parse_feed_extracts_core_fields():
    entries = fr.parse_feed(_wrap_feed(SAMPLE_ENTRY_XML))
    assert len(entries) == 1
    e = entries[0]
    assert e["id"] == "t3_1tnsh9b"
    assert e["title"] == "RIP Sonny Rollins"
    assert (
        e["link"] == "https://www.reddit.com/r/Jazz/comments/1tnsh9b/rip_sonny_rollins/"
    )
    assert e["published"] == "2026-05-26T01:40:20+00:00"
    assert "<table>" in e["content"]  # raw HTML -- html_to_text is a separate step


def test_parse_feed_multiple_entries_preserve_document_order():
    xml_text = _wrap_feed(
        _entry_xml(
            "t3_aaa", "First", "https://x/a", "2026-01-01T00:00:00+00:00", "<p>A</p>"
        )
        + _entry_xml(
            "t3_bbb", "Second", "https://x/b", "2026-01-02T00:00:00+00:00", "<p>B</p>"
        )
    )
    entries = fr.parse_feed(xml_text)
    assert [e["id"] for e in entries] == ["t3_aaa", "t3_bbb"]
    assert [e["title"] for e in entries] == ["First", "Second"]


def test_parse_feed_empty_feed_returns_empty_list():
    assert fr.parse_feed(_wrap_feed("")) == []


def test_strip_post_prefix_removes_t3():
    assert fr.strip_post_prefix("t3_1tnsh9b") == "1tnsh9b"


def test_strip_post_prefix_passthrough_without_prefix():
    assert fr.strip_post_prefix("1tnsh9b") == "1tnsh9b"


# --- html_to_text: stdlib-only HTML -> plain text ---


def test_html_to_text_strips_tags_and_unescapes_entities():
    raw = "<p>Check out <b>Kind of Blue</b> by Miles Davis &amp; friends</p>"
    assert fr.html_to_text(raw) == "Check out Kind of Blue by Miles Davis & friends"


def test_html_to_text_collapses_whitespace():
    raw = "<p>Line one</p>\n\n   <p>Line   two</p>"
    assert fr.html_to_text(raw) == "Line one Line two"


def test_html_to_text_empty_string_no_crash():
    assert fr.html_to_text("") == ""


def test_html_to_text_matches_real_reddit_table_wrapper_shape():
    """Modeled on the real content shape: a table wrapper around a thumbnail
    link plus the selftext rendered as HTML, comment markers, and a
    submitted-by footer -- confirm tags/comments/entities are all gone and
    the actual sentence survives."""
    raw = (
        "<table> <tr><td> "
        '<a href="https://x/comments/abc/post/">'
        '<img src="y.jpg" alt="Title" /></a> </td><td> <!-- SC_OFF -->'
        '<div class="md"><p>Great album: Kind of Blue by Miles Davis.</p></div>'
        "<!-- SC_ON --> &#32; submitted by &#32; "
        '<a href="https://x/user/z">/u/z</a> </td></tr></table>'
    )
    text = fr.html_to_text(raw)
    assert "Great album: Kind of Blue by Miles Davis." in text
    assert "<" not in text
    assert "&amp;" not in text


def test_html_to_text_does_not_let_escaped_tag_text_get_eaten():
    """Tags must be stripped BEFORE entities are unescaped -- a literal
    '&lt;3' in source text must survive as '<3', not get consumed as if it
    were a real tag (which unescape-then-strip would do)."""
    raw = "<p>I love this record &lt;3</p>"
    assert fr.html_to_text(raw) == "I love this record <3"


# --- collect_posts: cross-feed dedup + feeds[] provenance + sort determinism ---


def test_collect_posts_dedupes_across_feeds_with_feeds_provenance(monkeypatch):
    feed_a_xml = _wrap_feed(
        _entry_xml(
            "t3_shared",
            "Shared Post",
            "https://x/shared",
            "2026-01-01T00:00:00+00:00",
            "<p>Selftext</p>",
        )
    )
    feed_b_xml = _wrap_feed(
        _entry_xml(
            "t3_shared",
            "Shared Post",
            "https://x/shared",
            "2026-01-01T00:00:00+00:00",
            "<p>Selftext</p>",
        )
        + _entry_xml(
            "t3_only_b",
            "Only in B",
            "https://x/onlyb",
            "2026-01-02T00:00:00+00:00",
            "<p>B</p>",
        )
    )

    def fake_fetch_rss(url):
        return feed_a_xml if url == "URL_A" else feed_b_xml

    monkeypatch.setattr(fr, "_fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(
        fr, "LISTING_FEEDS", [("label_a", "URL_A"), ("label_b", "URL_B")]
    )

    posts = fr.collect_posts()

    assert set(posts.keys()) == {"shared", "only_b"}
    assert posts["shared"]["feeds"] == ["label_a", "label_b"]
    assert posts["only_b"]["feeds"] == ["label_b"]
    assert posts["shared"]["title"] == "Shared Post"
    assert posts["shared"]["url"] == "https://x/shared"
    assert posts["shared"]["selftext"] == "Selftext"


def test_collect_posts_single_feed_appearance_records_one_label(monkeypatch):
    xml_text = _wrap_feed(
        _entry_xml(
            "t3_only",
            "Only Post",
            "https://x/only",
            "2026-01-01T00:00:00+00:00",
            "<p>X</p>",
        )
    )
    monkeypatch.setattr(fr, "_fetch_rss", lambda url: xml_text)
    monkeypatch.setattr(fr, "LISTING_FEEDS", [("only_label", "URL")])

    posts = fr.collect_posts()

    assert posts["only"]["feeds"] == ["only_label"]


def test_collect_posts_keys_sort_deterministically(monkeypatch):
    xml_text = _wrap_feed(
        _entry_xml(
            "t3_zzz", "Z", "https://x/z", "2026-01-01T00:00:00+00:00", "<p>Z</p>"
        )
        + _entry_xml(
            "t3_aaa", "A", "https://x/a", "2026-01-01T00:00:00+00:00", "<p>A</p>"
        )
        + _entry_xml(
            "t3_mmm", "M", "https://x/m", "2026-01-01T00:00:00+00:00", "<p>M</p>"
        )
    )
    monkeypatch.setattr(fr, "_fetch_rss", lambda url: xml_text)
    monkeypatch.setattr(fr, "LISTING_FEEDS", [("label", "URL")])

    posts = fr.collect_posts()

    assert sorted(posts.keys()) == ["aaa", "mmm", "zzz"]


# --- collect_posts: 429 cooldown-retry, listing hard-abort on repeat failure ---


def test_collect_posts_listing_429_then_retry_succeeds_run_proceeds(
    monkeypatch, capsys
):
    xml_text = _wrap_feed(
        _entry_xml(
            "t3_ok", "OK Post", "https://x/ok", "2026-01-01T00:00:00+00:00", "<p>X</p>"
        )
    )
    calls = []

    def fake_fetch_rss(url):
        calls.append(url)
        if len(calls) == 1:
            raise requests.HTTPError("429", response=FakeHTTPResponse(429))
        return xml_text

    sleep_calls = []
    monkeypatch.setattr(fr, "_fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(fr.time, "sleep", lambda s: sleep_calls.append(s))
    monkeypatch.setattr(fr, "LISTING_FEEDS", [("only_label", "URL")])

    posts = fr.collect_posts()

    assert posts["ok"]["title"] == "OK Post"
    assert len(calls) == 2  # exactly one retry -- api accounting unaffected
    assert sleep_calls == [fr.RATE_LIMIT_COOLDOWN]
    assert "rate limited, cooling down 60s: only_label" in capsys.readouterr().out


def test_collect_posts_listing_429_twice_raises_systemexit(monkeypatch):
    def fake_fetch_rss(url):
        raise requests.HTTPError("429", response=FakeHTTPResponse(429))

    monkeypatch.setattr(fr, "_fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(fr.time, "sleep", lambda s: None)
    monkeypatch.setattr(fr, "LISTING_FEEDS", [("only_label", "URL")])

    with pytest.raises(SystemExit) as exc_info:
        fr.collect_posts()

    assert exc_info.value.code == 1


def test_collect_posts_listing_403_hard_stop_no_retry_single_attempt(monkeypatch):
    """A 403 is raised as SystemExit from inside the real _fetch_rss --
    simulated directly here (as the existing hard-stop tests do), since
    _fetch_rss's own 403 detection is covered separately."""
    calls = []

    def fake_fetch_rss(url):
        calls.append(url)
        raise SystemExit(1)

    sleep_calls = []
    monkeypatch.setattr(fr, "_fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(fr.time, "sleep", lambda s: sleep_calls.append(s))
    monkeypatch.setattr(fr, "LISTING_FEEDS", [("only_label", "URL")])

    with pytest.raises(SystemExit) as exc_info:
        fr.collect_posts()

    assert exc_info.value.code == 1
    assert sleep_calls == []
    assert len(calls) == 1  # no retry attempted


def test_collect_posts_listing_network_error_raises_systemexit_with_message(
    monkeypatch, capsys
):
    def fake_fetch_rss(url):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(fr, "_fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(fr, "LISTING_FEEDS", [("only_label", "URL")])

    with pytest.raises(SystemExit) as exc_info:
        fr.collect_posts()

    assert exc_info.value.code == 1
    out = capsys.readouterr().out
    assert "only_label" in out
    assert "aborting" in out


def test_collect_posts_listing_http_error_response_none_raises_systemexit(
    monkeypatch,
):
    """An HTTPError with no real response (e.g. a lower-level transport
    quirk) must be treated like a network error (rule 5), not crash with an
    AttributeError trying to read .status_code off None."""

    def fake_fetch_rss(url):
        raise requests.HTTPError("boom")  # no response kwarg -> response is None

    monkeypatch.setattr(fr, "_fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(fr, "LISTING_FEEDS", [("only_label", "URL")])

    with pytest.raises(SystemExit) as exc_info:
        fr.collect_posts()

    assert exc_info.value.code == 1


def test_collect_posts_listing_non_429_http_error_raises_systemexit(
    monkeypatch, capsys
):
    def fake_fetch_rss(url):
        raise requests.HTTPError("500", response=FakeHTTPResponse(500))

    monkeypatch.setattr(fr, "_fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(fr, "LISTING_FEEDS", [("only_label", "URL")])

    with pytest.raises(SystemExit) as exc_info:
        fr.collect_posts()

    assert exc_info.value.code == 1
    assert "only_label" in capsys.readouterr().out


# --- parse_thread_comments: exclude the post's own re-appearing entry ---


COMMENT_FEED_XML = _wrap_feed(
    _entry_xml(
        "t3_abc123",
        "Original Post Title",
        "https://x/comments/abc123/post/",
        "2026-01-01T00:00:00+00:00",
        "<p>Selftext here</p>",
    )
    + _entry_xml(
        "t1_c1",
        "",
        "https://x/comments/abc123/post/#c1",
        "2026-01-01T01:00:00+00:00",
        "<p>Comment one &amp; more.</p>",
    )
    + _entry_xml(
        "t1_c2",
        "",
        "https://x/comments/abc123/post/#c2",
        "2026-01-01T02:00:00+00:00",
        "<p>Comment two.</p>",
    )
)


def test_parse_thread_comments_excludes_own_post_entry():
    result = fr.parse_thread_comments(COMMENT_FEED_XML, "abc123")
    assert result == ["Comment one & more.", "Comment two."]


def test_parse_thread_comments_all_entries_when_own_post_entry_absent():
    xml_text = _wrap_feed(
        _entry_xml(
            "t1_c1",
            "",
            "https://x/1",
            "2026-01-01T00:00:00+00:00",
            "<p>Only comment</p>",
        )
    )
    assert fr.parse_thread_comments(xml_text, "abc123") == ["Only comment"]


# --- fetch_thread_comments_text: URL shape + transport-fault handling ---


def test_fetch_thread_comments_text_happy_path(monkeypatch):
    captured_urls = []

    def fake_fetch_rss(url):
        captured_urls.append(url)
        return COMMENT_FEED_XML

    monkeypatch.setattr(fr, "_fetch_rss", fake_fetch_rss)
    stats: Counter = Counter()
    result = fr.fetch_thread_comments_text("abc123", stats)

    assert result == ["Comment one & more.", "Comment two."]
    assert captured_urls == ["https://www.reddit.com/comments/abc123/.rss?limit=100"]
    assert stats["comments_fetch_failed"] == 0


def test_fetch_thread_comments_text_non_403_error_skips_and_counts_run_continues(
    monkeypatch,
):
    def fake_fetch_rss(url):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(fr, "_fetch_rss", fake_fetch_rss)
    stats: Counter = Counter()
    result = fr.fetch_thread_comments_text("abc123", stats)

    assert result == []
    assert stats["comments_fetch_failed"] == 1


def test_fetch_thread_comments_text_hard_stop_propagates_not_swallowed(monkeypatch):
    """_fetch_rss raises SystemExit itself on a 403 (see below) -- this must
    NOT be caught by fetch_thread_comments_text's RequestException handler
    (SystemExit isn't an Exception subclass, but assert it explicitly since
    this is the one hard-stop path that must never be swallowed)."""

    def fake_fetch_rss(url):
        raise SystemExit(1)

    monkeypatch.setattr(fr, "_fetch_rss", fake_fetch_rss)
    stats: Counter = Counter()
    with pytest.raises(SystemExit) as exc_info:
        fr.fetch_thread_comments_text("abc123", stats)
    assert exc_info.value.code == 1


# --- fetch_thread_comments_text: 429 cooldown-retry, rate_limited counter ---


def test_fetch_thread_comments_text_429_then_retry_succeeds(monkeypatch):
    calls = []

    def fake_fetch_rss(url):
        calls.append(url)
        if len(calls) == 1:
            raise requests.HTTPError("429", response=FakeHTTPResponse(429))
        return COMMENT_FEED_XML

    sleep_calls = []
    monkeypatch.setattr(fr, "_fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(fr.time, "sleep", lambda s: sleep_calls.append(s))
    stats: Counter = Counter()

    result = fr.fetch_thread_comments_text("abc123", stats)

    assert result == ["Comment one & more.", "Comment two."]
    assert stats["rate_limited"] == 0
    assert stats["comments_fetch_failed"] == 0
    assert sleep_calls == [fr.RATE_LIMIT_COOLDOWN]
    assert len(calls) == 2


def test_fetch_thread_comments_text_429_twice_counts_rate_limited_run_continues(
    monkeypatch,
):
    def fake_fetch_rss(url):
        raise requests.HTTPError("429", response=FakeHTTPResponse(429))

    sleep_calls = []
    monkeypatch.setattr(fr, "_fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(fr.time, "sleep", lambda s: sleep_calls.append(s))
    stats: Counter = Counter()

    result = fr.fetch_thread_comments_text("abc123", stats)

    assert result == []
    assert stats["rate_limited"] == 1
    assert stats["comments_fetch_failed"] == 0
    assert sleep_calls == [fr.RATE_LIMIT_COOLDOWN]


def test_fetch_thread_comments_text_403_hard_stop_no_retry_single_attempt(
    monkeypatch,
):
    calls = []

    def fake_fetch_rss(url):
        calls.append(url)
        raise SystemExit(1)

    sleep_calls = []
    monkeypatch.setattr(fr, "_fetch_rss", fake_fetch_rss)
    monkeypatch.setattr(fr.time, "sleep", lambda s: sleep_calls.append(s))
    stats: Counter = Counter()

    with pytest.raises(SystemExit) as exc_info:
        fr.fetch_thread_comments_text("abc123", stats)

    assert exc_info.value.code == 1
    assert sleep_calls == []
    assert len(calls) == 1


# --- _fetch_rss: 403 hard stop vs ordinary HTTP error propagation ---


def test_fetch_rss_403_triggers_hard_stop(monkeypatch):
    def fake_cached_get_json(*args, **kwargs):
        raise requests.HTTPError("403 Forbidden", response=FakeHTTPResponse(403))

    monkeypatch.setattr(fr.common, "cached_get_json", fake_cached_get_json)

    with pytest.raises(SystemExit) as exc_info:
        fr._fetch_rss("https://www.reddit.com/r/jazz/top.rss?t=year&limit=100")

    assert exc_info.value.code == 1


def test_fetch_rss_non_403_http_error_reraises_not_hard_stop(monkeypatch):
    def fake_cached_get_json(*args, **kwargs):
        raise requests.HTTPError("500 Server Error", response=FakeHTTPResponse(500))

    monkeypatch.setattr(fr.common, "cached_get_json", fake_cached_get_json)

    with pytest.raises(requests.HTTPError):
        fr._fetch_rss("https://www.reddit.com/r/jazz/top.rss?t=year&limit=100")


def test_fetch_rss_passes_params_none_and_headers(monkeypatch):
    captured = {}

    def fake_cached_get_json(bucket, url, **kwargs):
        captured["bucket"] = bucket
        captured["url"] = url
        captured["kwargs"] = kwargs
        return "<feed></feed>"

    monkeypatch.setattr(fr.common, "cached_get_json", fake_cached_get_json)
    fr._fetch_rss("https://www.reddit.com/r/jazz/top.rss?t=year&limit=100")

    assert captured["bucket"] == "reddit"
    assert captured["url"] == "https://www.reddit.com/r/jazz/top.rss?t=year&limit=100"
    assert captured["kwargs"]["as_text"] is True
    assert captured["kwargs"]["min_interval"] == 90.0
    assert "params" not in captured["kwargs"]


# --- _is_rate_limited: 429 detection, None-response guard (rule 5) ---


def test_is_rate_limited_true_for_429():
    exc = requests.HTTPError("429 Too Many Requests", response=FakeHTTPResponse(429))
    assert fr._is_rate_limited(exc) is True


def test_is_rate_limited_false_for_other_status():
    exc = requests.HTTPError("500 Server Error", response=FakeHTTPResponse(500))
    assert fr._is_rate_limited(exc) is False


def test_is_rate_limited_false_when_response_is_none():
    """A network-layer HTTPError (no real response) must never be treated
    as a 429 -- guard against exc.response being None (rule 5)."""
    exc = requests.HTTPError("boom")
    assert fr._is_rate_limited(exc) is False


# --- _fetch_rss_retrying_429: 429 cooldown-retry-once; 403 precedence unchanged ---


def test_fetch_rss_retrying_429_cooldown_then_retry_succeeds(monkeypatch, capsys):
    calls = []

    def fake_cached_get_json(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise requests.HTTPError(
                "429 Too Many Requests", response=FakeHTTPResponse(429)
            )
        return "<feed></feed>"

    sleep_calls = []
    monkeypatch.setattr(fr.common, "cached_get_json", fake_cached_get_json)
    monkeypatch.setattr(fr.time, "sleep", lambda s: sleep_calls.append(s))

    result = fr._fetch_rss_retrying_429("https://x/feed", "my_label")

    assert result == "<feed></feed>"
    assert len(calls) == 2  # original attempt + exactly one retry
    assert sleep_calls == [fr.RATE_LIMIT_COOLDOWN]
    out = capsys.readouterr().out
    assert f"rate limited, cooling down {fr.RATE_LIMIT_COOLDOWN}s: my_label" in out


def test_fetch_rss_retrying_429_second_429_propagates_after_one_retry(monkeypatch):
    calls = []

    def fake_cached_get_json(*args, **kwargs):
        calls.append(1)
        raise requests.HTTPError("429", response=FakeHTTPResponse(429))

    sleep_calls = []
    monkeypatch.setattr(fr.common, "cached_get_json", fake_cached_get_json)
    monkeypatch.setattr(fr.time, "sleep", lambda s: sleep_calls.append(s))

    with pytest.raises(requests.HTTPError):
        fr._fetch_rss_retrying_429("https://x/feed", "my_label")

    assert len(calls) == 2  # no infinite retry loop -- exactly once
    assert sleep_calls == [fr.RATE_LIMIT_COOLDOWN]  # cooled down once, not twice


def test_fetch_rss_retrying_429_non_429_http_error_no_cooldown_no_retry(monkeypatch):
    calls = []

    def fake_cached_get_json(*args, **kwargs):
        calls.append(1)
        raise requests.HTTPError("500 Server Error", response=FakeHTTPResponse(500))

    sleep_calls = []
    monkeypatch.setattr(fr.common, "cached_get_json", fake_cached_get_json)
    monkeypatch.setattr(fr.time, "sleep", lambda s: sleep_calls.append(s))

    with pytest.raises(requests.HTTPError):
        fr._fetch_rss_retrying_429("https://x/feed", "my_label")

    assert len(calls) == 1
    assert sleep_calls == []


def test_fetch_rss_retrying_429_403_takes_precedence_no_cooldown(monkeypatch):
    calls = []

    def fake_cached_get_json(*args, **kwargs):
        calls.append(1)
        raise requests.HTTPError("403 Forbidden", response=FakeHTTPResponse(403))

    sleep_calls = []
    monkeypatch.setattr(fr.common, "cached_get_json", fake_cached_get_json)
    monkeypatch.setattr(fr.time, "sleep", lambda s: sleep_calls.append(s))

    with pytest.raises(SystemExit) as exc_info:
        fr._fetch_rss_retrying_429("https://x/feed", "my_label")

    assert exc_info.value.code == 1
    assert len(calls) == 1  # no retry attempted
    assert sleep_calls == []


# --- strip_code_fence + _parse_llm_output: clean / fenced / invalid stdout ---


def test_strip_code_fence_removes_json_fence():
    raw = '```json\n[{"artist": "A", "album": "B"}]\n```'
    assert fr.strip_code_fence(raw) == '[{"artist": "A", "album": "B"}]'


def test_strip_code_fence_removes_plain_fence():
    raw = "```\n[1, 2, 3]\n```"
    assert fr.strip_code_fence(raw) == "[1, 2, 3]"


def test_strip_code_fence_passthrough_when_no_fence():
    assert fr.strip_code_fence("[1, 2]") == "[1, 2]"


def test_parse_llm_output_clean_array():
    result = FakeResult(returncode=0, stdout='[{"artist": "A", "album": "B"}]')
    assert fr._parse_llm_output(result) == [{"artist": "A", "album": "B"}]


def test_parse_llm_output_fenced_array():
    result = FakeResult(
        returncode=0, stdout='```json\n[{"artist": "A", "album": "B"}]\n```'
    )
    assert fr._parse_llm_output(result) == [{"artist": "A", "album": "B"}]


def test_parse_llm_output_none_on_nonzero_exit():
    result = FakeResult(returncode=1, stdout='[{"artist": "A", "album": "B"}]')
    assert fr._parse_llm_output(result) is None


def test_parse_llm_output_none_on_invalid_json():
    result = FakeResult(returncode=0, stdout="not json at all")
    assert fr._parse_llm_output(result) is None


def test_parse_llm_output_none_when_top_level_not_a_list():
    result = FakeResult(returncode=0, stdout='{"artist": "A", "album": "B"}')
    assert fr._parse_llm_output(result) is None


def test_parse_llm_output_none_for_none_result():
    assert fr._parse_llm_output(None) is None


def test_parse_llm_output_empty_array_with_trailing_prose():
    # Real Haiku output on a thread that names artists but no album titles:
    # a valid (empty) array, then an unsolicited explanation despite the
    # prompt's "no prose" rule. Regression for posts wrongly cached as
    # {"error": "unparseable"} (e.g. reddit post 150bv5).
    result = FakeResult(
        returncode=0,
        stdout="```json\n[]\n```\n\nThe thread mentions several artists "
        "(Vijay Iyer, Billy Hart) but does not specify album titles.",
    )
    assert fr._parse_llm_output(result) == []


def test_parse_llm_output_nonempty_array_with_trailing_prose():
    result = FakeResult(
        returncode=0,
        stdout='[{"artist": "A", "album": "B"}]\n\nThese are the albums found.',
    )
    assert fr._parse_llm_output(result) == [{"artist": "A", "album": "B"}]


def test_parse_llm_output_array_after_leading_prose():
    result = FakeResult(
        returncode=0,
        stdout='Here are the albums:\n[{"artist": "A", "album": "B"}]',
    )
    assert fr._parse_llm_output(result) == [{"artist": "A", "album": "B"}]


def test_parse_llm_output_none_when_only_non_json_brackets():
    # Reddit comment boilerplate ([link], [comments]) is not a JSON array;
    # extraction must fail rather than false-match a stray bracket.
    result = FakeResult(returncode=0, stdout="No albums here. [link] [comments]")
    assert fr._parse_llm_output(result) is None


# --- get_or_extract: cache-first, one retry, error record, llm_calls accounting ---


def test_get_or_extract_happy_path_single_call_no_retry(monkeypatch, tmp_path):
    monkeypatch.setattr(fr, "EXTRACTED_CACHE", tmp_path)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return FakeResult(
            returncode=0, stdout='[{"artist": "Miles Davis", "album": "Kind of Blue"}]'
        )

    monkeypatch.setattr(fr.subprocess, "run", fake_run)
    stats: Counter = Counter()
    result = fr.get_or_extract("post1", "some text", stats)

    assert result == [{"artist": "Miles Davis", "album": "Kind of Blue"}]
    assert len(calls) == 1
    assert stats["llm_calls"] == 1
    assert stats["unparseable"] == 0
    assert common.load_json(tmp_path / "post1.json") == [
        {"artist": "Miles Davis", "album": "Kind of Blue"}
    ]


def test_get_or_extract_retries_once_with_appended_sentence_on_parse_failure(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(fr, "EXTRACTED_CACHE", tmp_path)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return FakeResult(returncode=0, stdout="not json")

    monkeypatch.setattr(fr.subprocess, "run", fake_run)
    stats: Counter = Counter()
    result = fr.get_or_extract("post2", "some text", stats)

    assert result == {"error": "unparseable"}
    assert len(calls) == 2
    first_prompt, second_prompt = calls[0][-1], calls[1][-1]
    assert "Return valid JSON only." not in first_prompt
    assert second_prompt == first_prompt + fr.RETRY_SUFFIX
    assert (
        stats["llm_calls"] == 1
    )  # one post -> one llm_calls unit, regardless of retry
    assert stats["unparseable"] == 1
    assert common.load_json(tmp_path / "post2.json") == {"error": "unparseable"}


def test_get_or_extract_second_attempt_succeeds_no_error_record(monkeypatch, tmp_path):
    monkeypatch.setattr(fr, "EXTRACTED_CACHE", tmp_path)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if len(calls) == 1:
            return FakeResult(returncode=0, stdout="not json")
        return FakeResult(returncode=0, stdout='[{"artist": "A", "album": "B"}]')

    monkeypatch.setattr(fr.subprocess, "run", fake_run)
    stats: Counter = Counter()
    result = fr.get_or_extract("post3", "text", stats)

    assert result == [{"artist": "A", "album": "B"}]
    assert len(calls) == 2
    assert stats["unparseable"] == 0


# A TimeoutExpired now counts as a subprocess failure rather than a permanent
# error record -- see test_get_or_extract_timeout_is_not_persisted below.


def test_get_or_extract_existing_valid_cache_never_invokes_subprocess(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(fr, "EXTRACTED_CACHE", tmp_path)
    common.save_json(tmp_path / "post5.json", [{"artist": "A", "album": "B"}])

    def fake_run(cmd, **kwargs):
        raise AssertionError("subprocess must not be invoked when cache exists")

    monkeypatch.setattr(fr.subprocess, "run", fake_run)
    stats: Counter = Counter()
    result = fr.get_or_extract("post5", "text", stats)

    assert result == [{"artist": "A", "album": "B"}]
    assert stats["llm_calls"] == 0


def test_get_or_extract_existing_error_record_never_invokes_subprocess_and_counts(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(fr, "EXTRACTED_CACHE", tmp_path)
    common.save_json(tmp_path / "post6.json", {"error": "unparseable"})

    def fake_run(cmd, **kwargs):
        raise AssertionError("subprocess must not be invoked when cache exists")

    monkeypatch.setattr(fr.subprocess, "run", fake_run)
    stats: Counter = Counter()
    result = fr.get_or_extract("post6", "text", stats)

    assert result == {"error": "unparseable"}
    assert stats["llm_calls"] == 0
    assert stats["unparseable"] == 1


# --- build_llm_text: join + truncate ---


def test_build_llm_text_joins_title_selftext_comments():
    text = fr.build_llm_text("My Title", "My selftext", ["Comment A", "Comment B"])
    assert "My Title" in text
    assert "My selftext" in text
    assert "Comment A" in text
    assert "Comment B" in text


def test_build_llm_text_truncates_to_cap():
    long_selftext = "x" * 20000
    text = fr.build_llm_text("Title", long_selftext, [])
    assert len(text) == fr.TEXT_CAP


def test_build_llm_text_skips_empty_parts():
    text = fr.build_llm_text("Title", "", ["", "Real comment", ""])
    assert text == "Title\n\nReal comment"


# --- validate_items: shape validation, drop + count malformed ---


def test_validate_items_keeps_conforming_items():
    stats: Counter = Counter()
    items = [{"artist": "Miles Davis", "album": "Kind of Blue"}]
    result = fr.validate_items(items, stats)
    assert result == [{"artist": "Miles Davis", "album": "Kind of Blue"}]
    assert stats["malformed_items"] == 0


def test_validate_items_drops_malformed_and_counts():
    stats: Counter = Counter()
    items = [
        {"artist": "Miles Davis", "album": "Kind of Blue"},
        {"artist": "No Album Here"},
        {"album": "No Artist Here"},
        {"artist": "", "album": "Empty Artist"},
        {"artist": "Empty Album", "album": ""},
        {"artist": 123, "album": "Non-string artist"},
        "not even a dict",
    ]
    result = fr.validate_items(items, stats)
    assert result == [{"artist": "Miles Davis", "album": "Kind of Blue"}]
    assert stats["malformed_items"] == 6


def test_validate_items_non_list_input_returns_empty_no_crash():
    stats: Counter = Counter()
    assert fr.validate_items({"error": "unparseable"}, stats) == []
    assert stats["malformed_items"] == 0


def test_validate_items_strips_whitespace():
    stats: Counter = Counter()
    items = [{"artist": "  Miles Davis  ", "album": "  Kind of Blue  "}]
    result = fr.validate_items(items, stats)
    assert result == [{"artist": "Miles Davis", "album": "Kind of Blue"}]


# --- aggregate_mentions: within-post dedupe, distinct-post counting, sort, empty_norm ---


def test_aggregate_within_post_dedupe_by_norm_key():
    stats: Counter = Counter()
    items = [
        {"artist": "Grant Green", "album": "Idle Moments"},
        {"artist": "Grant Green", "album": "Idle Moments"},
        {"artist": "The Grant Green", "album": "Idle Moments"},  # same norm_key
    ]
    result = fr.aggregate_mentions([("post1", items)], stats)

    assert len(result) == 1
    assert result[0]["count"] == 1
    assert result[0]["post_ids"] == ["post1"]


def test_aggregate_counts_distinct_posts_not_total_mentions():
    stats: Counter = Counter()
    posts_items = [
        ("post1", [{"artist": "Grant Green", "album": "Idle Moments"}]),
        ("post2", [{"artist": "Grant Green", "album": "Idle Moments"}]),
    ]
    result = fr.aggregate_mentions(posts_items, stats)

    assert result[0]["count"] == 2
    assert result[0]["post_ids"] == ["post1", "post2"]


def test_aggregate_first_seen_surface_form_wins():
    stats: Counter = Counter()
    posts_items = [
        ("post1", [{"artist": "grant green", "album": "idle moments"}]),
        ("post2", [{"artist": "GRANT GREEN", "album": "IDLE MOMENTS"}]),
    ]
    result = fr.aggregate_mentions(posts_items, stats)

    assert result[0]["artist"] == "grant green"
    assert result[0]["title"] == "idle moments"


def test_aggregate_sort_order_count_desc_then_norm_key_asc():
    stats: Counter = Counter()
    posts_items = [
        ("post1", [{"artist": "Artist B", "album": "Album B"}]),
        ("post2", [{"artist": "Artist A", "album": "Album A"}]),
        ("post3", [{"artist": "Artist A", "album": "Album A"}]),
    ]
    result = fr.aggregate_mentions(posts_items, stats)

    assert [m["count"] for m in result] == [2, 1]
    assert result[0]["norm_key"] == common.norm_key("Artist A", "Album A")


def test_aggregate_post_ids_sorted():
    stats: Counter = Counter()
    posts_items = [
        ("post_z", [{"artist": "Grant Green", "album": "Idle Moments"}]),
        ("post_a", [{"artist": "Grant Green", "album": "Idle Moments"}]),
    ]
    result = fr.aggregate_mentions(posts_items, stats)

    assert result[0]["post_ids"] == ["post_a", "post_z"]


def test_aggregate_empty_norm_both_sides_skipped_and_counted():
    """common.norm() strips CJK entirely -- both sides empty."""
    stats: Counter = Counter()
    posts_items = [("post1", [{"artist": "以莉高露", "album": "某專輯"}])]
    result = fr.aggregate_mentions(posts_items, stats)

    assert result == []
    assert stats["empty_norm"] == 1


def test_aggregate_empty_norm_partial_side_also_skipped_and_counted():
    """Only the artist side strips to empty -- must still be skipped, not
    emitted with a blank artist."""
    stats: Counter = Counter()
    posts_items = [("post1", [{"artist": "以莉高露", "album": "Real English Title"}])]
    result = fr.aggregate_mentions(posts_items, stats)

    assert result == []
    assert stats["empty_norm"] == 1


def test_aggregate_empty_posts_items_returns_empty_list():
    stats: Counter = Counter()
    assert fr.aggregate_mentions([], stats) == []


# --- _print_summary: rate_limited joins the existing skip-counter line ---


def test_print_summary_includes_rate_limited_in_skip_line(capsys):
    stats: Counter = Counter(
        {
            "comments_fetch_failed": 2,
            "rate_limited": 3,
            "malformed_items": 1,
            "empty_norm": 0,
        }
    )
    fr._print_summary(5, [], stats)

    out = capsys.readouterr().out
    assert "rate_limited=3" in out


# --- Finding 7: a successful-but-empty listing feed is a hard stop ---


def test_collect_posts_hard_stops_on_empty_feed(monkeypatch, capsys):
    """jazz_search_best_albums is a search feed and the flakiest of the four.
    An HTTP 200 with zero entries used to pass through in silence -- a quarter
    of the post universe gone, and the empty 200 cached permanently."""
    monkeypatch.setattr(fr, "_fetch_rss", lambda url: _wrap_feed(""))
    monkeypatch.setattr(
        fr, "LISTING_FEEDS", [("jazz_search_best_albums", "URL_SEARCH")]
    )

    with pytest.raises(SystemExit) as exc_info:
        fr.collect_posts()

    assert exc_info.value.code == 1
    assert "jazz_search_best_albums" in capsys.readouterr().out


def test_collect_posts_hard_stops_on_empty_feed_after_a_good_one(monkeypatch, capsys):
    """The check is per feed, not on the run total -- three good feeds must
    not mask the fourth coming back empty."""
    good = _wrap_feed(
        _entry_xml(
            "t3_p1", "P1", "https://x/p1", "2026-01-01T00:00:00+00:00", "<p>S</p>"
        )
    )

    monkeypatch.setattr(
        fr, "_fetch_rss", lambda url: good if url == "URL_A" else _wrap_feed("")
    )
    monkeypatch.setattr(
        fr, "LISTING_FEEDS", [("label_a", "URL_A"), ("label_b", "URL_B")]
    )

    with pytest.raises(SystemExit) as exc_info:
        fr.collect_posts()

    assert exc_info.value.code == 1
    assert "label_b" in capsys.readouterr().out


# --- Finding 6: subprocess failure is not a permanent "unparseable" record ---


def test_get_or_extract_nonzero_exit_prints_stderr_and_is_not_persisted(
    monkeypatch, tmp_path, capsys
):
    """Not authenticated / API 429 / quota exhausted must stay retryable: the
    old code wrote {"error": "unparseable"} and by design never retried, so a
    blip 100 posts into a ~380-post run became 100 permanent holes."""
    monkeypatch.setattr(fr, "EXTRACTED_CACHE", tmp_path)

    def fake_run(cmd, **kwargs):
        return FakeResult(
            returncode=1, stderr="Invalid API key -- run /login\nstack frame two"
        )

    monkeypatch.setattr(fr.subprocess, "run", fake_run)
    stats: Counter = Counter()
    result = fr.get_or_extract("post_fail", "text", stats)

    assert not (tmp_path / "post_fail.json").exists()
    assert stats["llm_failed"] == 1
    assert stats["unparseable"] == 0
    assert fr.validate_items(result, stats) == []

    out = capsys.readouterr().out
    assert "Invalid API key -- run /login" in out
    assert "stack frame two" not in out  # first stderr line only


def test_get_or_extract_timeout_is_not_persisted(monkeypatch, tmp_path):
    """A timeout is the subprocess not succeeding, not a thread with nothing
    extractable -- and the module already records one false "unparseable"
    caused by a too-short timeout."""
    monkeypatch.setattr(fr, "EXTRACTED_CACHE", tmp_path)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=fr.LLM_TIMEOUT)

    monkeypatch.setattr(fr.subprocess, "run", fake_run)
    stats: Counter = Counter()
    result = fr.get_or_extract("post_timeout", "text", stats)

    assert len(calls) == 2
    assert not (tmp_path / "post_timeout.json").exists()
    assert stats["llm_failed"] == 1
    assert stats["unparseable"] == 0
    assert fr.validate_items(result, stats) == []


def test_get_or_extract_clean_exit_unparseable_output_still_persisted(
    monkeypatch, tmp_path
):
    """The other half of the finding: a junk thread the extractor genuinely
    could not parse keeps its permanent error record."""
    monkeypatch.setattr(fr, "EXTRACTED_CACHE", tmp_path)
    monkeypatch.setattr(
        fr.subprocess,
        "run",
        lambda cmd, **kwargs: FakeResult(returncode=0, stdout="no array here"),
    )
    stats: Counter = Counter()
    result = fr.get_or_extract("post_junk", "text", stats)

    assert result == {"error": "unparseable"}
    assert common.load_json(tmp_path / "post_junk.json") == {"error": "unparseable"}
    assert stats["unparseable"] == 1
    assert stats["llm_failed"] == 0


# --- Finding 6: abort when extraction is failing across the run ---


def test_abort_if_extraction_failing_hard_stops_above_share(capsys):
    stats: Counter = Counter({"llm_failed": 30, "unparseable": 0})

    with pytest.raises(SystemExit) as exc_info:
        fr._abort_if_extraction_failing(100, stats)

    assert exc_info.value.code == 1
    assert "30/100" in capsys.readouterr().out


def test_abort_if_extraction_failing_counts_both_failure_kinds():
    stats: Counter = Counter({"llm_failed": 11, "unparseable": 10})

    with pytest.raises(SystemExit):
        fr._abort_if_extraction_failing(100, stats)


def test_abort_if_extraction_failing_allows_share_below_threshold():
    stats: Counter = Counter({"llm_failed": 5, "unparseable": 10})
    fr._abort_if_extraction_failing(100, stats)  # 15% -- no abort


def test_abort_if_extraction_failing_ignores_small_sample():
    """One bad thread out of the first two is not evidence of an outage."""
    stats: Counter = Counter({"unparseable": 1})
    fr._abort_if_extraction_failing(2, stats)


def test_main_aborts_without_overwriting_output_when_extraction_fails(
    monkeypatch, tmp_path
):
    """End-to-end wiring: a systemic outage must not leave reddit.json
    overwritten with a thinned mention set at exit 0."""
    out_path = tmp_path / "reddit.json"
    common.save_json(out_path, {"mentions": [{"norm_key": "a::b", "count": 9}]})

    monkeypatch.setattr(fr, "OUTPUT_PATH", out_path)
    monkeypatch.setattr(fr, "THREADS_CACHE", tmp_path / "threads")
    monkeypatch.setattr(fr, "EXTRACTED_CACHE", tmp_path / "extracted")
    monkeypatch.setattr(fr.common, "CACHE", tmp_path)
    monkeypatch.setattr(fr, "_parse_args", lambda: argparse.Namespace(max_posts=None))
    monkeypatch.setattr(
        fr,
        "collect_posts",
        lambda: {
            f"post{i:02d}": {
                "id": f"post{i:02d}",
                "title": "T",
                "url": "https://x",
                "published": "2026-01-01T00:00:00+00:00",
                "feeds": ["jazz_top_all"],
                "selftext": "S",
            }
            for i in range(20)
        },
    )
    monkeypatch.setattr(fr, "fetch_thread_comments_text", lambda post_id, stats: [])
    monkeypatch.setattr(
        fr.subprocess,
        "run",
        lambda cmd, **kwargs: FakeResult(returncode=1, stderr="API error 529"),
    )

    with pytest.raises(SystemExit) as exc_info:
        fr.main()

    assert exc_info.value.code == 1
    assert common.load_json(out_path) == {
        "mentions": [{"norm_key": "a::b", "count": 9}]
    }


def test_print_summary_reports_llm_failed(capsys):
    stats: Counter = Counter({"unparseable": 2, "llm_failed": 3})
    fr._print_summary(10, [], stats)

    out = capsys.readouterr().out
    assert "llm_failed=3" in out
    assert "extracted: 5" in out

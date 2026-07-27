"""Reddit fetcher: mines r/jazz and r/jazzguitar for concrete "artist /
album" recommendations buried in post text and comments, extracted via a
cached Haiku subprocess call. Stage 3 of the offline recs pipeline
(parallel to Discogs/Last.fm/Pitchfork).

AMENDMENT (2026-07-23): Reddit closed self-service API access -- this
fetcher never has, and never will, hold Reddit credentials. Transport is
Reddit's public RSS/Atom feeds only, parsed with stdlib xml.etree
(no new dependencies). A 403 from ANY reddit RSS request is a hard stop:
print one line, exit 1 -- never escalated to JSON scraping, other
endpoints, mobile/app spoofing, or third-party mirrors. Other per-thread
HTTP failures (404, 5xx, timeouts) are ordinary skip+count events.

A 429 (rate limited) is retried once: print one line, sleep
RATE_LIMIT_COOLDOWN seconds, refetch (Reddit's anonymous RSS 429s carry no
usable Retry-After, so this cooldown is fixed rather than header-driven).
If that retry ALSO 429s -- or any other non-403 listing-feed fetch fails
outright -- the whole run hard-stops (print one line, exit 1): a listing
is a quarter of the post universe and the run is resumable from cache. A
per-thread comments fetch that exhausts its 429 retry, or fails for any
other non-403 reason, stays an ordinary skip+count instead.

A listing feed that returns HTTP 200 with zero entries hard-stops the same
way: a successful-but-empty feed is still a quarter of the post universe
gone, and the empty 200 would be cached permanently.

Four fixed listing feeds (r/jazz top/year, r/jazz top/all, r/jazzguitar
top/all, r/jazz search "best albums") are deduped by post id -- a post can
appear in more than one -- and processed in sorted-id order for
determinism. For each post: fetch its comments .rss, cache the raw thread
(selftext + comment bodies, HTML converted to plain text), then extract
album mentions via a cached `claude -p --model haiku` subprocess call
(never re-invoked once a post has an extraction file on disk, including a
stored error record -- a human deletes the file to force a retry). Only a
subprocess that RAN and returned unparseable output earns that permanent
record; one that failed outright (timeout, nonzero exit) is printed with its
first stderr line, left uncached so the next run retries it, and hard-stops
the run once such failures exceed EXTRACTION_FAIL_SHARE of posts processed.
The LLM is used for extraction only; all counting/aggregation is plain code.

Every HTTP call goes through common.cached_get_json (disk-cached,
rate-limited) -- a rerun after the cache is warm costs zero API calls and
zero LLM calls.

Run: python3 -m scripts.recs.fetch_reddit [--max-posts N]
"""

import argparse
import html
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter

import requests

from scripts.recs import common

ATOM_NS = "{http://www.w3.org/2005/Atom}"
BUCKET = "reddit"
MIN_INTERVAL = 90.0
RATE_LIMIT_COOLDOWN = 60
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}

LISTING_FEEDS = [
    ("jazz_top_year", "https://www.reddit.com/r/jazz/top.rss?t=year&limit=100"),
    ("jazz_top_all", "https://www.reddit.com/r/jazz/top.rss?t=all&limit=100"),
    (
        "jazzguitar_top_all",
        "https://www.reddit.com/r/jazzguitar/top.rss?t=all&limit=100",
    ),
    (
        "jazz_search_best_albums",
        "https://www.reddit.com/r/jazz/search.rss?q=best+albums&restrict_sr=1&sort=top&limit=100",
    ),
]
COMMENTS_URL_TMPL = "https://www.reddit.com/comments/{post_id}/.rss?limit=100"

TEXT_CAP = 12000
CLAUDE_MODEL = "haiku"
# 300s not 120s: album-rich threads make Haiku generate 100+ items, which
# takes time. A 12000-char thread (post 178in0e) measured 250s producing 118
# items; the old 120s cut it off and cached it as a false "unparseable".
# Unattended extraction runs faster than one competing with a live session,
# so most of this is headroom.
LLM_TIMEOUT = 300
PROMPT = (
    "Extract every specific music album recommendation from this Reddit "
    "thread text. Return ONLY a JSON array, no prose, no code fences: "
    '[{"artist": "...", "album": "..."}]. Rules: include only concrete '
    "album titles attributed to a specific artist; skip artist-only "
    "mentions; skip song titles. Text follows:"
)
RETRY_SUFFIX = " Return valid JSON only."
PROGRESS_EVERY = 10
# Share of processed posts that may yield no extraction before the run aborts,
# and the sample size below which the share is too noisy to act on.
EXTRACTION_FAIL_SHARE = 0.2
EXTRACTION_MIN_SAMPLE = 10

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_CODE_FENCE_RE = re.compile(r"^```[a-zA-Z]*\n?|\n?```$")

THREADS_CACHE = common.CACHE / "reddit_threads"
EXTRACTED_CACHE = common.CACHE / "reddit_extracted"
OUTPUT_PATH = common.CACHE / "reddit.json"


# --- pure helpers: HTML -> plain text ---


def html_to_text(raw: str) -> str:
    """Reddit's Atom <content> is HTML (a table wrapper around the post's
    rendered selftext, or a comment body). stdlib-only conversion: strip
    tags FIRST, then unescape entities -- reversing the order would let a
    literal '&lt;3' in the source unescape into '<3' and then get eaten by
    the tag regex. Finally collapse whitespace."""
    if not raw:
        return ""
    no_tags = _TAG_RE.sub(" ", raw)
    unescaped = html.unescape(no_tags)
    return _WS_RE.sub(" ", unescaped).strip()


# --- pure helpers: Atom parsing (stdlib xml.etree only) ---


def _entry_text(entry: ET.Element, tag: str) -> str:
    el = entry.find(f"{ATOM_NS}{tag}")
    return (el.text or "") if el is not None else ""


def parse_entry(entry: ET.Element) -> dict:
    """One Atom <entry> -> {id, title, link, published, content}. content
    stays raw HTML -- html_to_text() is a separate, independently testable
    conversion step."""
    link_el = entry.find(f"{ATOM_NS}link")
    return {
        "id": _entry_text(entry, "id"),
        "title": _entry_text(entry, "title"),
        "link": link_el.get("href", "") if link_el is not None else "",
        "published": _entry_text(entry, "published"),
        "content": _entry_text(entry, "content"),
    }


def parse_feed(xml_text: str) -> list[dict]:
    """Parse an Atom feed's <entry> elements, in document order."""
    root = ET.fromstring(xml_text)
    return [parse_entry(e) for e in root.findall(f"{ATOM_NS}entry")]


def strip_post_prefix(raw_id: str) -> str:
    """Atom entry id 't3_1tnsh9b' -> post id '1tnsh9b' -- used for cache
    filenames and to build the per-thread comments URL."""
    return raw_id[3:] if raw_id.startswith("t3_") else raw_id


def parse_thread_comments(xml_text: str, post_id: str) -> list[str]:
    """Every entry in a thread's comments .rss is a comment EXCEPT the
    post's own entry, which reddit includes as the feed's first item (id
    == t3_<post_id>) -- excluded here since selftext already comes from the
    listing feed, not re-derived per thread. If the post's own entry isn't
    present, every entry is treated as a comment (robust either way).
    Bodies are converted HTML -> plain text."""
    own_post_entry_id = f"t3_{post_id}"
    return [
        html_to_text(e["content"])
        for e in parse_feed(xml_text)
        if e["id"] != own_post_entry_id
    ]


# --- HTTP: 403 hard stop, everything else propagates to the caller ---


def _hard_stop_403(url: str) -> None:
    print(
        f"reddit RSS returned HTTP 403 (hard stop -- no fallback, no spoofing): {url}"
    )
    sys.exit(1)


def _fetch_rss(url: str) -> str:
    try:
        return common.cached_get_json(
            BUCKET, url, min_interval=MIN_INTERVAL, as_text=True, headers=HEADERS
        )
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 403:
            _hard_stop_403(url)
        raise


def _is_rate_limited(exc: requests.HTTPError) -> bool:
    """True only for an actual HTTP 429 response. exc.response can be None
    (a network-layer HTTPError, not a real response) -- that case must NOT
    be treated as a 429; it falls through to the plain-failure path
    (rule 4/5), same as any other non-403 error."""
    return exc.response is not None and exc.response.status_code == 429


def _fetch_rss_retrying_429(url: str, label: str) -> str:
    """Reddit's anonymous RSS 429s carry no usable Retry-After (quota-window
    "x-ratelimit-remaining: 0.0" style, confirmed live) -- common.py's own
    built-in single short retry is largely ineffective against it. On a
    first-attempt 429 (only): print one cooldown line naming `label`, sleep
    RATE_LIMIT_COOLDOWN seconds, then refetch exactly once (the failed
    attempt was never cached, so this is a genuine second network call, not
    a cache hit). A 403 still hard-stops first, unretried, inside
    _fetch_rss above -- unchanged, and unaffected by any of this since it
    exits the process before returning here. Anything else -- the retry
    also 429ing, or a non-429/non-403 error on the first attempt --
    propagates to the caller, which decides listing-hard-abort vs.
    thread-skip+count."""
    try:
        return _fetch_rss(url)
    except requests.HTTPError as exc:
        if not _is_rate_limited(exc):
            raise
        print(f"rate limited, cooling down {RATE_LIMIT_COOLDOWN}s: {label}")
        time.sleep(RATE_LIMIT_COOLDOWN)
        return _fetch_rss(url)


def _hard_stop_listing(label: str, reason: str) -> None:
    """A listing feed is a quarter of the post universe -- unlike a
    per-thread failure, a gap here is never silently acceptable. Print one
    clear line and exit 1; the run is resumable, since every fetch that
    already succeeded (listings and threads alike) stayed cached."""
    print(f"reddit RSS listing feed failed ({reason}), aborting: {label}")
    sys.exit(1)


# --- listing sweep: fetch the four fixed feeds, dedup posts across them ---


def collect_posts() -> dict[str, dict]:
    """Fetch the four listing feeds (fixed order); return
    {post_id: {"id", "title", "url", "published", "feeds", "selftext"}}
    deduped across feeds -- a post appearing in more than one keeps its
    first-seen title/url/published/selftext, with every feed it appeared in
    recorded (first-seen order) in "feeds".

    A listing fetch gets the same one-shot 429 cooldown-retry as a thread
    fetch (_fetch_rss_retrying_429). Anything that survives that -- a
    repeat 429, some other non-403 HTTP error, or a network error -- hard
    stops the whole run (_hard_stop_listing) instead of silently skipping a
    quarter of the post universe. A 403 hard-stops immediately, as always,
    inside _fetch_rss."""
    posts: dict[str, dict] = {}
    for label, url in LISTING_FEEDS:
        try:
            xml_text = _fetch_rss_retrying_429(url, label)
        except requests.HTTPError as exc:
            if _is_rate_limited(exc):
                _hard_stop_listing(label, "rate limited twice")
            elif exc.response is not None:
                _hard_stop_listing(label, f"HTTP {exc.response.status_code}")
            else:
                _hard_stop_listing(label, "network error")
        except requests.RequestException:
            _hard_stop_listing(label, "network error")

        entries = parse_feed(xml_text)
        if not entries:
            # HTTP 200 with zero entries used to pass through in silence:
            # nothing added, no counter moved, nothing printed -- and the empty
            # 200 cached permanently, so every rerun reproduced it. Same
            # hard-stop path as a transport failure; a feed is a quarter of the
            # post universe either way.
            _hard_stop_listing(label, "zero entries")

        for entry in entries:
            post_id = strip_post_prefix(entry["id"])
            if post_id not in posts:
                posts[post_id] = {
                    "id": post_id,
                    "title": entry["title"],
                    "url": entry["link"],
                    "published": entry["published"],
                    "feeds": [],
                    "selftext": html_to_text(entry["content"]),
                }
            if label not in posts[post_id]["feeds"]:
                posts[post_id]["feeds"].append(label)
    return posts


# --- per-thread comments fetch ---


def fetch_thread_comments_text(post_id: str, stats: Counter) -> list[str]:
    """Fetch and parse a thread's comments .rss. A 403 is the hard stop
    (raised inside _fetch_rss). A 429 gets one cooldown-retry
    (_fetch_rss_retrying_429); if that retry ALSO 429s, it's a per-thread
    skip counted separately (rate_limited) from other transport failures.
    Any other requests.RequestException (including a non-403, non-429
    HTTPError) is the existing per-thread skip: counted
    (comments_fetch_failed), logged by post id only -- the raw thread file
    still gets written by the caller, with comments=[]."""
    url = COMMENTS_URL_TMPL.format(post_id=post_id)
    try:
        xml_text = _fetch_rss_retrying_429(url, post_id)
    except requests.RequestException as exc:
        if isinstance(exc, requests.HTTPError) and _is_rate_limited(exc):
            stats["rate_limited"] += 1
            print(f"skip comments (rate limited twice): {post_id}")
        else:
            stats["comments_fetch_failed"] += 1
            print(f"skip comments (HTTP error): {post_id}")
        return []
    return parse_thread_comments(xml_text, post_id)


# --- LLM extraction: cached by post id, one retry, error record on failure ---


def strip_code_fence(s: str) -> str:
    """Strip a wrapping ``` or ```json markdown code fence, if present."""
    s = s.strip()
    if not s.startswith("```"):
        return s
    return _CODE_FENCE_RE.sub("", s).strip()


def _run_claude(prompt: str, text: str) -> subprocess.CompletedProcess | None:
    """One Haiku extraction subprocess call. Returns None on
    TimeoutExpired -- the caller treats that identically to any other
    parse failure (retry, then give up)."""
    try:
        return subprocess.run(
            ["claude", "-p", "--model", CLAUDE_MODEL, prompt],
            input=text,
            capture_output=True,
            text=True,
            timeout=LLM_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None


def _parse_llm_output(result: subprocess.CompletedProcess | None):
    """None (timeout) / nonzero exit / no decodable JSON array in stdout ->
    None, signalling the caller to retry (or give up). Otherwise the first
    top-level JSON array found in stdout, returned as-is and unvalidated --
    item shape validation is a separate, later step (validate_items)."""
    if result is None or result.returncode != 0:
        return None
    return _first_json_array(result.stdout)


def _first_json_array(stdout: str):
    """First decodable JSON array in `stdout`, ignoring prose or code fences
    before or after it. Haiku is asked for a bare array but, on empty or
    ambiguous threads, wraps it in a ```json fence and/or appends an
    explanation -- e.g. '```json\\n[]\\n```\\n\\nThe thread names artists but
    no album titles.' A whole-string json.loads rejected that valid output
    and cached it as {"error": "unparseable"}, dropping the (often empty but
    legitimate) result. Brackets that do not begin a JSON array (Reddit's
    '[link]' / '[comments]' comment boilerplate) fail to decode and are
    skipped. None if no array is present."""
    text = strip_code_fence(stdout)
    decoder = json.JSONDecoder()
    idx = text.find("[")
    while idx != -1:
        try:
            value, _ = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            idx = text.find("[", idx + 1)
            continue
        if isinstance(value, list):
            return value
        idx = text.find("[", idx + 1)
    return None


def _subprocess_failed(
    result: subprocess.CompletedProcess | None, post_id: str
) -> bool:
    """True when the extraction subprocess itself did not succeed: a timeout,
    or a nonzero exit (not authenticated, API 429 or 5xx, quota exhausted).
    stderr was discarded entirely before, which made a systemic outage
    indistinguishable from a thread that genuinely had nothing extractable --
    the first stderr line is printed so it is not."""
    if result is None:
        print(f"llm extraction failed (timeout after {LLM_TIMEOUT}s): {post_id}")
        return True
    if result.returncode != 0:
        lines = (result.stderr or "").strip().splitlines()
        detail = lines[0] if lines else "(no stderr)"
        print(
            f"llm extraction failed (exit {result.returncode}): {post_id} -- {detail}"
        )
        return True
    return False


def get_or_extract(post_id: str, text: str, stats: Counter) -> list | dict:
    """Return the cached extraction for post_id, or call the Haiku
    subprocess (original prompt, then one retry with "Return valid JSON
    only." appended) and cache the result. A cache file on disk --
    INCLUDING a stored {"error": "unparseable"} record -- means the LLM is
    never called again for this post; a human deletes the file to force a
    retry. stats["unparseable"] reflects every post whose final value is an
    error record, whether written just now or reloaded from a prior run --
    that keeps the run summary's "unparseable: N" honest across reruns.

    A subprocess that never succeeded (timeout, nonzero exit) is counted
    separately as stats["llm_failed"] and is NOT cached -- see below."""
    cache_path = EXTRACTED_CACHE / f"{post_id}.json"
    if cache_path.exists():
        cached = common.load_json(cache_path)
        if isinstance(cached, dict) and cached.get("error") == "unparseable":
            stats["unparseable"] += 1
        return cached

    stats["llm_calls"] += 1
    result = _run_claude(PROMPT, text)
    parsed = _parse_llm_output(result)
    if parsed is None:
        result = _run_claude(PROMPT + RETRY_SUFFIX, text)
        parsed = _parse_llm_output(result)

    # A permanent error record is right for a junk thread and wrong for a
    # systemic outage, so only a subprocess that RAN and produced unparseable
    # output earns one. A failed subprocess caches nothing: the post is
    # retried on the next run instead of becoming a permanent hole that every
    # rerun reproduces from cache at zero cost and zero noise.
    if parsed is None and _subprocess_failed(result, post_id):
        stats["llm_failed"] += 1
        return {"error": "llm_call_failed"}

    if parsed is None:
        parsed = {"error": "unparseable"}
        stats["unparseable"] += 1

    EXTRACTED_CACHE.mkdir(parents=True, exist_ok=True)
    common.save_json(cache_path, parsed)
    return parsed


def build_llm_text(title: str, selftext: str, comments: list[str]) -> str:
    """title + selftext + comment bodies joined, truncated to the brief's
    12000-char cap."""
    parts = [p for p in [title, selftext, *comments] if p]
    return "\n\n".join(parts)[:TEXT_CAP]


def validate_items(parsed, stats: Counter) -> list[dict]:
    """parsed is one post's cached/fresh extraction value -- either a list
    of {"artist", "album"} candidates or an {"error": "unparseable"} record
    (or, defensively, any other malformed shape). Keep only dict items with
    a non-empty string artist and album; drop and count anything else. The
    LLM is extraction only -- this is the plain-code validation gate."""
    if not isinstance(parsed, list):
        return []

    valid = []
    for item in parsed:
        if not isinstance(item, dict):
            stats["malformed_items"] += 1
            continue
        artist = item.get("artist")
        album = item.get("album")
        if (
            isinstance(artist, str)
            and artist.strip()
            and isinstance(album, str)
            and album.strip()
        ):
            valid.append({"artist": artist.strip(), "album": album.strip()})
        else:
            stats["malformed_items"] += 1
    return valid


# --- aggregation: within-post dedupe, distinct-post counting, sort ---


def _has_empty_norm_side(norm_key: str) -> bool:
    artist_part, _, title_part = norm_key.partition("::")
    return not artist_part or not title_part


def aggregate_mentions(
    posts_items: list[tuple[str, list[dict]]], stats: Counter
) -> list[dict]:
    """posts_items: [(post_id, validated items)], in sorted-post-id order.
    Within one post, dedupe by norm_key before counting (a post mentioning
    the same album 5x counts once). count = number of distinct posts;
    artist/title surface form = first-seen wording (sorted-post-id order);
    post_ids stored sorted; final list sorted by count desc, norm_key asc."""
    mentions: dict[str, dict] = {}
    for post_id, items in posts_items:
        seen_this_post: set[str] = set()
        for item in items:
            key = common.norm_key(item["artist"], item["album"])
            if _has_empty_norm_side(key):
                stats["empty_norm"] += 1
                continue
            if key in seen_this_post:
                continue
            seen_this_post.add(key)

            entry = mentions.setdefault(
                key,
                {
                    "norm_key": key,
                    "artist": item["artist"],
                    "title": item["album"],
                    "count": 0,
                    "post_ids": [],
                },
            )
            entry["count"] += 1
            entry["post_ids"].append(post_id)

    result = list(mentions.values())
    for entry in result:
        entry["post_ids"].sort()
    result.sort(key=lambda m: (-m["count"], m["norm_key"]))
    return result


# --- progress + summary ---


def _bump_progress(stats: Counter) -> None:
    stats["posts_processed"] += 1
    if stats["posts_processed"] % PROGRESS_EVERY == 0:
        print(f"... {stats['posts_processed']} posts processed")


def _abort_if_extraction_failing(processed: int, stats: Counter) -> None:
    """Hard stop once too large a share of processed posts yielded no
    extraction. A blip 100 posts into a ~380-post run otherwise thins the
    mention set, overwrites reddit.json and exits 0, with a one-line summary
    as the only signal. Below EXTRACTION_MIN_SAMPLE posts the share is too
    noisy to act on. Nothing is lost by stopping: every successful fetch and
    extraction stayed cached, so the rerun resumes."""
    failed = stats["unparseable"] + stats["llm_failed"]
    if processed < EXTRACTION_MIN_SAMPLE or failed <= processed * EXTRACTION_FAIL_SHARE:
        return
    print(
        f"extraction failing on {failed}/{processed} posts "
        f"(over {int(EXTRACTION_FAIL_SHARE * 100)}%), aborting -- "
        "fix the extractor and rerun (cached work is kept)"
    )
    sys.exit(1)


def _print_summary(post_count: int, mentions: list[dict], stats: Counter) -> None:
    unparseable_n = stats["unparseable"]
    llm_failed_n = stats["llm_failed"]
    extracted_n = post_count - unparseable_n - llm_failed_n
    print(
        f"posts: {post_count} | extracted: {extracted_n} | "
        f"unparseable: {unparseable_n} | distinct albums: {len(mentions)} | "
        f"llm_calls: {stats['llm_calls']} | "
        f"api_calls: {common.http_stats['api_calls']} | "
        f"cache_hits: {common.http_stats['cache_hits']}"
    )
    print(
        "skipped -- "
        f"comments_fetch_failed={stats['comments_fetch_failed']} "
        f"rate_limited={stats['rate_limited']} "
        f"llm_failed={stats['llm_failed']} "
        f"malformed_items={stats['malformed_items']} "
        f"empty_norm={stats['empty_norm']}"
    )
    if mentions:
        print("\ntop 10 mentions:")
        for m in mentions[:10]:
            print(f"  {m['count']:>3}  {m['artist']} / {m['title']}")


# --- main ---


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reddit jazz mentions fetcher")
    parser.add_argument(
        "--max-posts",
        type=int,
        default=None,
        help=(
            "After cross-feed dedup + sort, process only the first N posts "
            "(thread fetch + extraction + aggregation) -- verification / staged runs"
        ),
    )
    return parser.parse_args(argv)


def main() -> None:
    args = _parse_args()
    stats: Counter = Counter()

    posts = collect_posts()
    sorted_ids = sorted(posts.keys())
    if args.max_posts is not None:
        sorted_ids = sorted_ids[: args.max_posts]

    THREADS_CACHE.mkdir(parents=True, exist_ok=True)
    posts_items: list[tuple[str, list[dict]]] = []
    for post_id in sorted_ids:
        post = posts[post_id]
        comments = fetch_thread_comments_text(post_id, stats)

        common.save_json(
            THREADS_CACHE / f"{post_id}.json",
            {
                "id": post_id,
                "title": post["title"],
                "url": post["url"],
                "published": post["published"],
                "feeds": post["feeds"],
                "selftext": post["selftext"],
                "comments": comments,
            },
        )

        text = build_llm_text(post["title"], post["selftext"], comments)
        parsed = get_or_extract(post_id, text, stats)
        items = validate_items(parsed, stats)
        posts_items.append((post_id, items))

        _bump_progress(stats)
        _abort_if_extraction_failing(stats["posts_processed"], stats)

    mentions = aggregate_mentions(posts_items, stats)

    common.CACHE.mkdir(parents=True, exist_ok=True)
    common.save_json(OUTPUT_PATH, {"mentions": mentions})
    _print_summary(len(sorted_ids), mentions, stats)


if __name__ == "__main__":
    main()

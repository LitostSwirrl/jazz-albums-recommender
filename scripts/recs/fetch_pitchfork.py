"""Pitchfork fetcher: crawls the jazz genre review listing and extracts each
review's critic score, Best New Music flag, and publish year. Stage 3 of the
offline recs pipeline (parallel to Discogs/Last.fm) -- unlike them, this
fetcher scrapes HTML rather than a JSON API, and needs no taste_profile.json
input (Pitchfork's jazz coverage is swept wholesale, not per-artist).

Two plan deviations, both verified against the live site on 2026-07-23:
  - Listing URL: the original ?genre=jazz&page=N scheme now 301-loops into a
    soft 404. The working listing is /genre/jazz/review/?page=N.
  - Score source: the JSON-LD <script type="application/ld+json"> block's
    reviewRating is null on every page today. The real score/title/BNM data
    lives in the inline window.__PRELOADED_STATE__ JSON (its
    itemsReviewed[].musicRating.score). The plan's fallback regex for a bare
    score value still matches that embedded blob and is kept as the
    fallback for when a single item's musicRating key goes missing.

Every HTTP call goes through common.cached_get_json (disk-cached,
rate-limited) -- a rerun after the cache is warm costs zero API calls.

Run: python3 -m scripts.recs.fetch_pitchfork [--max-pages N]
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date, datetime

import requests

from scripts.recs import common

BASE_URL = "https://pitchfork.com"
LISTING_URL = f"{BASE_URL}/genre/jazz/review/"
BUCKET = "pitchfork"
MIN_INTERVAL = 3.0
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}

MAX_PAGES = 40
MIN_YEAR = 2018
MIN_REVIEWS = 50
PROGRESS_EVERY = 10

LISTING_DATE_FMT = "%B %d, %Y"
_HED_LINK_RE = re.compile(r'summary-item__hed-link[^>]*href="(/reviews/albums/[^"]+)"')
_PUBLISH_DATE_RE = re.compile(r'summary-item__publish-date">([^<]+)</time>')
_JSONLD_RE = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL
)
_MODIFIED_DATE_RE = re.compile(r'"modifiedDate":"(\d{4})-')
_SCORE_FALLBACK_RE = re.compile(r'"score":\s*"?(\d+\.\d)')
_TAG_RE = re.compile(r"<[^>]+>")

OUTPUT_PATH = common.CACHE / "pitchfork.json"
PARSE_FAIL_PATH = common.CACHE / "pitchfork_parse_fail.html"


# --- pure helpers: listing page ---


def parse_listing(html: str) -> list[tuple[str, date]] | None:
    """Extract (absolute review url, publish date) pairs from a genre/jazz
    listing page, in document order -- verified live: each item's hed-link
    href precedes its own summary-item__publish-date time tag, one pair per
    summary item, so the two regex passes zip together positionally.

    Returns None if the two passes disagree on count. Dates are load-bearing
    for the pre-2018 stop rule, so a mismatch means the listing markup
    changed -- zipping positionally anyway would silently mispair or
    silently truncate the crawl. The caller routes None to _fail_loud rather
    than guessing."""
    hrefs = [f"{BASE_URL}{m.group(1)}" for m in _HED_LINK_RE.finditer(html)]
    raw_dates = [m.group(1) for m in _PUBLISH_DATE_RE.finditer(html)]
    dates = [datetime.strptime(d.strip(), LISTING_DATE_FMT).date() for d in raw_dates]
    if len(hrefs) != len(dates):
        return None
    return list(zip(hrefs, dates))


def dedupe_new(pairs: list[tuple[str, date]], seen: set[str]) -> list[tuple[str, date]]:
    """Drop pairs whose url is already in `seen` (a sticky/featured listing
    item can repeat across pages) -- mutates `seen` with each newly-kept url."""
    new_pairs = []
    for url, pub_date in pairs:
        if url in seen:
            continue
        seen.add(url)
        new_pairs.append((url, pub_date))
    return new_pairs


# --- pure helpers: review page (embedded-state + JSON-LD parsing) ---


def _find_json_value(html: str, key: str):
    """Find `key` (e.g. '"itemsReviewed":') in the raw page text and parse
    the JSON value immediately following it, using json's own incremental
    decoder (raw_decode) rather than bracket-matching -- the value sits
    inside a much larger, non-JSON HTML document. Tolerant of incidental
    whitespace after the colon. Returns None if the key isn't found or its
    value fails to parse."""
    idx = html.find(key)
    if idx == -1:
        return None
    pos = idx + len(key)
    while pos < len(html) and html[pos].isspace():
        pos += 1
    try:
        value, _end = json.JSONDecoder().raw_decode(html, pos)
    except json.JSONDecodeError:
        return None
    return value


def extract_items_reviewed(html: str) -> list[dict] | None:
    """Locate and JSON-parse the itemsReviewed array embedded in
    window.__PRELOADED_STATE__ -- one entry per reviewed album on this page.
    Returns None if it can't be found/parsed, which the caller treats as a
    parse failure (every real Pitchfork review page carries this key)."""
    value = _find_json_value(html, '"itemsReviewed":')
    return value if isinstance(value, list) else None


def extract_artist_names(html: str) -> list[str] | None:
    """Locate and JSON-parse the top-level artists array embedded in
    window.__PRELOADED_STATE__ -- returns each artist's `name`, stripped of
    the leading space Pitchfork's markup adds, in document order.

    Returns None if the "artists" key is wholly ABSENT from the page: on
    every real Pitchfork review page it occurs exactly once, inside
    headerProps, so absence means the page structure changed -- same
    contract as extract_items_reviewed, and the caller routes None to
    _fail_loud rather than a silent skip. Returns [] if the key IS present
    but its value isn't a usable list (e.g. "artists":[] on a page with no
    credited artist) -- caller pairs against an empty list, yielding a
    counted empty-norm skip rather than a crash."""
    if '"artists":' not in html:
        return None
    value = _find_json_value(html, '"artists":')
    if not isinstance(value, list):
        return []
    return [str(a.get("name", "")).strip() for a in value if isinstance(a, dict)]


def extract_score(item: dict, html: str, total_items: int = 1) -> float | None:
    """Primary: item['musicRating']['score']. Fallback (musicRating missing
    or malformed on this item): regex-search the raw page text for the
    first "score": N.N occurrence -- verified to still match the embedded
    state today even when an item's own musicRating key is gone.

    The fallback scans the WHOLE page, so it only fires when `total_items`
    (the page's itemsReviewed count) is 1 -- on a multi-item roundup page it
    can't tell which item's score it found (reproduced: item 2 silently
    inheriting item 1's score). `total_items` defaults to 1 so single-item
    call sites/tests don't need to pass it explicitly. On a multi-item page
    a missing musicRating falls straight through to None, which the
    caller's completeness gate then routes to fail-loud -- a multi-item page
    missing musicRating is markup drift, not a case for the grace path."""
    rating = item.get("musicRating")
    if isinstance(rating, dict) and isinstance(rating.get("score"), (int, float)):
        return float(rating["score"])

    if total_items != 1:
        return None

    match = _SCORE_FALLBACK_RE.search(html)
    return float(match.group(1)) if match else None


def extract_bnm(item: dict) -> bool:
    """isBestNewMusic only -- isBestNewReissue is a separate flag the output
    schema doesn't carry."""
    rating = item.get("musicRating") or {}
    return bool(rating.get("isBestNewMusic", False))


def extract_publish_year(html: str) -> int | None:
    """Primary: the JSON-LD Review block's datePublished (ISO 8601 --
    verified reliable on the live site even though reviewRating went null).
    Fallback: the embedded state's own modifiedDate ISO field, for the rare
    page where the JSON-LD block itself is missing or fails to parse."""
    match = _JSONLD_RE.search(html)
    if match:
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            data = {}
        published = data.get("datePublished")
        if published and len(published) >= 4:
            return int(published[:4])

    fallback = _MODIFIED_DATE_RE.search(html)
    return int(fallback.group(1)) if fallback else None


def _strip_tags(s: str) -> str:
    """Defensively strip any residual HTML tags (e.g. <em>) from a title --
    dangerousHed is plain text in every sample seen, but the name says why
    this is worth guarding."""
    return _TAG_RE.sub("", s or "").strip()


def pair_artists_to_items(
    items: list[dict], artists: list[str], stats: Counter
) -> list[str]:
    """Primary-credit convention: artists[0] for every item -- this also
    covers a single item credited to several artists (a collab album), which
    is NOT ambiguous. The one exception is a multi-album roundup page
    (len(items) > 1): pair items to artists positionally when the counts
    match, otherwise fall back to artists[0] for every item and count each
    such record in multi_item_ambiguous."""
    if not artists:
        return ["" for _ in items]
    if len(items) > 1 and len(items) != len(artists):
        stats["multi_item_ambiguous"] += len(items)
        return [artists[0] for _ in items]
    if len(items) == len(artists):
        return list(artists)
    return [artists[0] for _ in items]


def _has_empty_norm_side(norm_key: str) -> bool:
    artist_part, _, title_part = norm_key.partition("::")
    return not artist_part or not title_part


def parse_review_page(html: str, url: str, stats: Counter) -> list[dict] | None:
    """Parse one fetched review page into zero or more review records (one
    per itemsReviewed entry -- a multi-album roundup shares one url across
    several records, each with its own score). Returns None if the
    itemsReviewed block itself can't be located/parsed, OR if the "artists"
    key is wholly absent from the page -- the caller treats either as an
    immediate fail-loud parse failure."""
    items = extract_items_reviewed(html)
    if items is None:
        return None

    year = extract_publish_year(html)
    artist_names = extract_artist_names(html)
    if artist_names is None:
        return None
    paired_artists = pair_artists_to_items(items, artist_names, stats)

    records = []
    for item, artist in zip(items, paired_artists):
        title = _strip_tags(item.get("dangerousHed", ""))
        key = common.norm_key(artist, title)
        if _has_empty_norm_side(key):
            stats["empty_norm"] += 1
            print(f"skip review (empty norm): {artist!r} / {title!r} -- {url}")
            continue

        records.append(
            {
                "norm_key": key,
                "artist": artist,
                "title": title,
                "score": extract_score(item, html, len(items)),
                "bnm": extract_bnm(item),
                "year": year,
                "url": url,
            }
        )

    return records


def _page_is_complete(records: list[dict]) -> bool:
    """Every emitted record must carry artist+title+score+year -- score=0.0
    is a plausible real value and must not read as missing, hence the
    explicit `is not None` rather than a truthiness check."""
    return all(
        r["artist"] and r["title"] and r["score"] is not None and r["year"]
        for r in records
    )


# --- HTTP ---


def _get(url: str, params: dict | None = None) -> str:
    return common.cached_get_json(
        BUCKET,
        url,
        params=params,
        headers=HEADERS,
        min_interval=MIN_INTERVAL,
        as_text=True,
    )


def _fetch_listing_page(page: int) -> str:
    return _get(LISTING_URL, {"page": page})


def _fetch_review_page(url: str) -> str:
    return _get(url)


def _slug(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


# --- listing crawl ---


def collect_review_urls(
    stats: Counter, max_pages: int
) -> tuple[list[tuple[str, date]], str]:
    """Paginate the jazz listing (page=1..max_pages) collecting (url, date)
    pairs for every review dated >= MIN_YEAR, deduped across pages. Stops
    early when a page yields no new links, or when a page's items are ALL
    dated before MIN_YEAR -- both cheaper than fetching every one of the
    capped pages. Returns the collected pairs plus page 1's raw HTML, kept
    only as the dump sample if the run-level review-count assertion in
    main() later fails.

    A listing page whose href/date counts don't match (parse_listing
    returns None) fails loud immediately -- dates decide the stop rule, so a
    silently mispaired or truncated page could stop the crawl early or
    misfile years."""
    seen: set[str] = set()
    collected: list[tuple[str, date]] = []
    first_html = ""

    for page in range(1, max_pages + 1):
        html = _fetch_listing_page(page)
        if page == 1:
            first_html = html

        pairs = parse_listing(html)
        if pairs is None:
            _fail_loud(
                html, f"{LISTING_URL}?page={page}", "listing href/date count mismatch"
            )
        if page == 1 and not pairs:
            # A real jazz listing page always carries links. Zero of them means
            # markup drift or a soft 404 (HTTP 200 with an error page -- the
            # previous URL scheme did exactly that), and parse_listing can't
            # tell: 0 hrefs == 0 dates, so it returns [] rather than None and
            # the crawl would record a tidy "stopped_no_new_links" instead.
            _fail_loud(
                html, f"{LISTING_URL}?page={page}", "listing page 1 yielded zero links"
            )

        new_pairs = dedupe_new(pairs, seen)
        if not new_pairs:
            stats["listing_stopped_no_new_links"] += 1
            break

        stats["listing_pages_fetched"] += 1
        collected.extend((u, d) for u, d in new_pairs if d.year >= MIN_YEAR)

        if all(d.year < MIN_YEAR for _, d in new_pairs):
            stats["listing_stopped_pre_2018"] += 1
            break

    return collected, first_html


# --- review fetch ---


def _fail_loud(html: str, url: str, reason: str) -> None:
    """Never return zeros silently: dump the offending page's raw HTML,
    print the dump path + url, exit 1 -- site markup changed, fix the
    parser, don't ship a run that quietly produced fewer/no reviews."""
    common.CACHE.mkdir(parents=True, exist_ok=True)
    with open(PARSE_FAIL_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"PARSE FAILURE: {reason}")
    print(f"url: {url}")
    print(f"dumped raw HTML: {PARSE_FAIL_PATH}")
    sys.exit(1)


def _bump_progress(stats: Counter) -> None:
    stats["reviews_processed"] += 1
    if stats["reviews_processed"] % PROGRESS_EVERY == 0:
        print(f"... {stats['reviews_processed']} review pages processed")


def fetch_reviews(pairs: list[tuple[str, date]], stats: Counter) -> list[dict]:
    """Fetch and parse every collected review url. A transport failure
    (requests.RequestException) is a skip, counted and logged by slug only.
    A page that fetches fine but can't be parsed -- itemsReviewed missing, or
    a record still incomplete after the score fallback -- is a DIFFERENT
    category: fail loud immediately rather than silently dropping it.

    The listing's per-item date already excludes pre-2018 urls before they
    reach here (cheaper: skips the fetch entirely) -- the per-record year
    check below is a defensive safety net for the rare case where a
    review's own publish year (the one actually emitted) disagrees with its
    listing date, e.g. a year-boundary timezone rollover."""
    reviews: list[dict] = []
    for url, _pub_date in pairs:
        try:
            html = _fetch_review_page(url)
        except requests.RequestException:
            stats["fetch_failed"] += 1
            print(f"skip review (fetch failed): {_slug(url)}")
            continue

        records = parse_review_page(html, url, stats)
        if records is None:
            _fail_loud(html, url, "itemsReviewed block or artists key not found")
        if not _page_is_complete(records):
            _fail_loud(
                html, url, "incomplete review record (missing artist/title/score/year)"
            )

        for record in records:
            if record["year"] < MIN_YEAR:
                stats["pre_2018_dropped"] += 1
                print(f"skip review (pre-2018 after parse): {_slug(url)}")
                continue
            reviews.append(record)

        _bump_progress(stats)

    return reviews


# --- progress + summary ---


def _print_summary(reviews: list[dict], stats: Counter) -> None:
    bnm_n = sum(1 for r in reviews if r["bnm"])
    years = [r["year"] for r in reviews if r["year"]]
    year_range = f"{min(years)}-{max(years)}" if years else "n/a"
    print(
        f"reviews: {len(reviews)} (bnm: {bnm_n}, years {year_range}) | "
        f"api_calls: {common.http_stats['api_calls']} | "
        f"cache_hits: {common.http_stats['cache_hits']}"
    )
    print(
        "skipped -- "
        f"fetch_failed={stats['fetch_failed']} "
        f"empty_norm={stats['empty_norm']} "
        f"pre_2018_dropped={stats['pre_2018_dropped']} "
        f"multi_item_ambiguous={stats['multi_item_ambiguous']}"
    )
    if reviews:
        print("\nsample reviews (spot-check against pitchfork.com):")
        for r in reviews[:3]:
            print(
                f"  {r['artist']} / {r['title']} | score={r['score']} "
                f"bnm={r['bnm']} year={r['year']} | {r['url']}"
            )


# --- main ---


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pitchfork jazz reviews fetcher")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Cap listing pages crawled (smoke runs / controller-staged full runs)",
    )
    return parser.parse_args(argv)


def _min_reviews_for(max_pages: int | None) -> int:
    """The zero-review floor SCALES with --max-pages rather than switching
    off. Gating it on `max_pages is None` disabled it on exactly the staged
    production runs the flag was built for -- so a markup change or soft 404
    could overwrite a good cache/pitchfork.json with {"reviews": []} at exit
    0. A capped run is held to the same per-page rate as a full crawl, and
    never to less than one review."""
    if max_pages is None or max_pages >= MAX_PAGES:
        return MIN_REVIEWS
    return max(1, MIN_REVIEWS * max_pages // MAX_PAGES)


def main() -> None:
    args = _parse_args()
    stats: Counter = Counter()

    max_pages = args.max_pages or MAX_PAGES
    pairs, first_listing_html = collect_review_urls(stats, max_pages)
    reviews = fetch_reviews(pairs, stats)

    min_reviews = _min_reviews_for(max_pages)
    if len(reviews) < min_reviews:
        _fail_loud(
            first_listing_html,
            LISTING_URL,
            f"only {len(reviews)} reviews found (expected >= {min_reviews})",
        )

    common.CACHE.mkdir(parents=True, exist_ok=True)
    common.save_json(OUTPUT_PATH, {"reviews": reviews})
    _print_summary(reviews, stats)


if __name__ == "__main__":
    main()

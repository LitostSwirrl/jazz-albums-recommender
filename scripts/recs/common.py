import hashlib
import json
import os
import re
import time
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import requests

# Connect / read timeout on every request. requests has no default: a server
# that accepts the connection and never answers would hang an unattended
# multi-hour run (Reddit's is ~380 posts spaced 90s apart) with no output and
# no exit. requests.Timeout is a RequestException, so it lands in the
# skip-and-count handlers the fetchers already have.
TIMEOUT = (10, 30)

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE = ROOT / "scripts" / "recs" / "cache"

# Per-bucket throttle tracking (bucket -> last_ts)
_bucket_last_ts = {}

# HTTP call/cache-hit counters, shared by every cached_get_json caller in the
# process. Fetchers read http_stats['api_calls'] / ['cache_hits'] to report
# cost in their own run summaries.
http_stats: Counter = Counter()


def load_env() -> None:
    """Parse ROOT/.env KEY=VALUE lines into os.environ (no override, skips comments/blanks)."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Parse KEY=VALUE
            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            # Don't override existing env vars
            if key and key not in os.environ:
                os.environ[key] = value


def norm(s: str) -> str:
    """Normalize: lowercase, NFKD accent-strip, drop punctuation, collapse whitespace, strip leading 'the '."""
    # Lowercase and NFKD unicode normalization to decompose accents
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    # Remove accents by encoding to ASCII and ignoring errors
    s = s.encode("ascii", "ignore").decode("ascii")

    # Drop punctuation (keep alphanumeric and spaces)
    s = re.sub(r"[^a-z0-9\s]", "", s)

    # Collapse multiple spaces into one
    s = re.sub(r"\s+", " ", s).strip()

    # Strip leading "the "
    s = re.sub(r"^the\s+", "", s)

    return s


def norm_title(s: str) -> str:
    """Normalize title after removing trailing edition markers in parentheses/brackets."""
    # Edition words to strip from trailing groups
    edition_pattern = r"(remaster|deluxe|edition|expanded|reissue|anniversary|bonus|mono|stereo|version|remix|rvg|ojc)"

    # Remove trailing parentheses/brackets if they contain only edition words
    # Pattern: (...) or [...] at the end where content matches edition words
    s = re.sub(
        rf"\s*[\(\[]([^)\]]*{edition_pattern}[^)\]]*)[)\]]$",
        "",
        s,
        flags=re.IGNORECASE,
    )

    return norm(s)


def norm_key(artist: str, title: str) -> str:
    """Combine normalized artist and title with '::'."""
    return f"{norm(artist)}::{norm_title(title)}"


def spotify_album_id(url: str) -> str | None:
    """Extract album ID from Spotify URL."""
    if not url:
        return None

    # Match the album ID in Spotify URL
    match = re.search(r"spotify\.com/album/([a-zA-Z0-9]+)", url)
    return match.group(1) if match else None


def slugify(s: str) -> str:
    """Normalize and convert to slug (hyphens instead of spaces)."""
    return norm(s).replace(" ", "-")


def cached_get_json(
    bucket: str,
    url: str,
    *,
    params=None,
    headers=None,
    min_interval=1.0,
    as_text=False,
):
    """
    GET with per-bucket disk cache and per-bucket monotonic throttle.

    Args:
        bucket: Cache bucket name
        url: URL to fetch
        params: Optional query parameters
        headers: Optional headers
        min_interval: Minimum seconds between requests to the same bucket
        as_text: If True, return text; if False, return parsed JSON

    Returns:
        Parsed JSON dict or text string

    Raises:
        requests.HTTPError for HTTP status >= 400 (after printing URL)
        Honors Retry-After on 429 (sleeps + retries once)
    """
    # Ensure cache directory exists
    cache_dir = CACHE / "http" / bucket
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Check cache first
    url_hash = hashlib.sha1(
        f"{url}?{json.dumps(params or {}, sort_keys=True)}".encode()
    ).hexdigest()
    cache_file = cache_dir / f"{url_hash}.json"

    if cache_file.exists():
        http_stats["cache_hits"] += 1
        with open(cache_file, "r", encoding="utf-8") as f:
            content = f.read()
            if as_text:
                return content
            return json.loads(content)

    # Cache miss -> exactly one API call, even if a 429 forces a retry below.
    http_stats["api_calls"] += 1

    # Throttle: honor min_interval per bucket
    if bucket in _bucket_last_ts:
        elapsed = time.time() - _bucket_last_ts[bucket]
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

    _bucket_last_ts[bucket] = time.time()

    # Make request
    response = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)

    # Handle 429 with Retry-After
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 1))
        time.sleep(retry_after)
        response = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)

    # Raise on error. Print scheme+host+path only, never the query string:
    # api keys ride in query params on some buckets and fetch_reddit builds
    # urls with inline query strings, so this line must be structurally
    # incapable of carrying a secret. (raise_for_status' own message DOES
    # include the full url -- callers must catch it, never let it print.)
    if response.status_code >= 400:
        parts = urlsplit(url)
        print(
            f"{bucket}: HTTP {response.status_code} {parts.scheme}://{parts.netloc}{parts.path}"
        )
        response.raise_for_status()

    # Cache only AFTER the body proves to be what the caller asked for.
    # Caching first put two kinds of junk in a permanent cache: a JSON error
    # body served as HTTP 200 (Last.fm answers rate limits and outages that
    # way), which would make the resulting skip permanent and unhealable by a
    # rerun; and a non-JSON page (proxy interstitial, captive portal), which
    # would make every later run raise on the same poisoned file.
    content = response.text
    if as_text:
        _atomic_write_text(cache_file, content)
        return content

    parsed = response.json()
    if isinstance(parsed, dict) and "error" in parsed:
        return parsed

    _atomic_write_text(cache_file, content)
    return parsed


def _atomic_write_text(path, text: str) -> None:
    """Write via a .tmp sibling + os.replace (atomic within a filesystem).
    Opening the destination with "w" truncates it immediately, so a Ctrl-C --
    the natural way to stop a multi-hour run -- could leave either a
    half-written cache file that the next run reads as a valid hit (a
    truncated HTML/RSS page parses as a short but perfectly good page and
    silently truncates the crawl) or a destroyed 868KB cache/discogs.json
    with no backup."""
    path = Path(path)
    tmp_path = path.with_name(path.name + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp_path, path)


def load_json(path):
    """Load JSON from file (UTF-8)."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    """Save JSON to file (UTF-8, ensure_ascii=False, indent=1), atomically."""
    _atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=1))

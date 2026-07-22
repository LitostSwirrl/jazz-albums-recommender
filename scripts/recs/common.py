import hashlib
import json
import os
import re
import time
import unicodedata
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE = ROOT / "scripts" / "recs" / "cache"

# Per-bucket throttle tracking (bucket -> last_ts)
_bucket_last_ts = {}


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
        with open(cache_file, "r", encoding="utf-8") as f:
            content = f.read()
            if as_text:
                return content
            return json.loads(content)

    # Throttle: honor min_interval per bucket
    if bucket in _bucket_last_ts:
        elapsed = time.time() - _bucket_last_ts[bucket]
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

    _bucket_last_ts[bucket] = time.time()

    # Make request
    response = requests.get(url, params=params, headers=headers)

    # Handle 429 with Retry-After
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 1))
        time.sleep(retry_after)
        response = requests.get(url, params=params, headers=headers)

    # Raise on error
    if response.status_code >= 400:
        print(url)
        response.raise_for_status()

    # Cache and return
    content = response.text
    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(content)

    if as_text:
        return content
    return response.json()


def load_json(path):
    """Load JSON from file (UTF-8)."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    """Save JSON to file (UTF-8, ensure_ascii=False, indent=1)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

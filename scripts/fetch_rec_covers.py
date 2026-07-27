#!/usr/bin/env python3
"""Resolve cover art for recommendation albums that have none.

Reads src/data/recommendations.json, queries the iTunes Search API for every
album with no coverUrl, and writes src/data/recCoverManifest.json mapping
album id -> cover URL.

A result is accepted ONLY when both the artist and the core title match. An
unmatched album gets no cover: attaching a plausible-looking wrong cover is a
false claim about a record, which is exactly what this project does not do.

Idempotent: per-album results are cached, so a rerun costs no API calls.

The manifest and the cache are both append-only -- a rerun merges into them and
never removes an entry. That means CHANGING THE MATCH RULE DOES NOT EVICT
ANYTHING IT PREVIOUSLY ACCEPTED: a cover accepted under the old rule survives
the tightening. After any change to is_match, wanted_title or core_title,
delete both src/data/recCoverManifest.json and scripts/cache/rec_covers.json
and run the full pass again, or the wrong cover stays live.

    python3 scripts/fetch_rec_covers.py
    python3 scripts/fetch_rec_covers.py --limit 10   # smoke test
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent.parent
RECS_PATH = ROOT / "src" / "data" / "recommendations.json"
MANIFEST_PATH = ROOT / "src" / "data" / "recCoverManifest.json"
CACHE_PATH = ROOT / "scripts" / "cache" / "rec_covers.json"
FAILURES_PATH = ROOT / "scripts" / "rec_covers_failures.json"

SEARCH_URL = "https://itunes.apple.com/search"
UA = "SmackCatsJazz/1.0 cover-resolve (+https://smack-cats-jazz.web.app)"
MIN_INTERVAL = 1.2
TIMEOUT = (10, 30)
LIMIT_PER_QUERY = 5

_PAREN = re.compile(r"[\(\[].*?[\)\]]")
_PAREN_INNER = re.compile(r"[\(\[](.*?)[\)\]]")
_NONWORD = re.compile(r"[^a-z0-9]+")


def normalize(s: str) -> str:
    return _NONWORD.sub("", (s or "").lower())


def core_title(s: str) -> str:
    """Title with parenthetical/bracketed edition suffixes removed."""
    return normalize(_PAREN.sub(" ", s or ""))


def wanted_title(want_artist: str, want_title: str) -> str:
    """The normalized title we are actually asking for.

    Normally that is the whole title, parentheticals included: ours is the side
    that says which record we mean. One exception -- a title that is just the
    artist name with the album in brackets ("Art Blakey and The Jazz Messengers
    [Moanin']"). Stripping the bracket there leaves nothing but the artist, so
    the bracket holds the album name and it is what we compare.
    """
    core = core_title(want_title)
    if core and core == normalize(want_artist):
        inner = normalize(" ".join(_PAREN_INNER.findall(want_title or "")))
        if inner:
            return inner
    return normalize(want_title)


def is_match(
    want_artist: str, want_title: str, got_artist: str, got_title: str
) -> bool:
    """Accept only when artist AND title agree.

    Artists compare by containment because the API returns ensemble forms
    ("Bill Evans Trio" for "Bill Evans").

    Titles never lose a token from OUR side. The API is the side that appends
    edition suffixes, so its title may equal ours either verbatim or once its
    own parentheticals are stripped -- but ours stays whole, because the
    parenthetical is often the token that names the record: "... Ocean Club
    (Volume 1)" is a different sleeve from "... Ocean Club", and stripping it
    from both sides made them identical. Containment is never used on titles;
    that is what let "Black Jazz Signature" wrongly match "First Floor".
    """
    wa, ga = normalize(want_artist), normalize(got_artist)
    if not wa or not ga:
        return False
    if wa not in ga and ga not in wa:
        return False
    wt = wanted_title(want_artist, want_title)
    if not wt:
        return False
    return wt in (normalize(got_title), core_title(got_title))


def artwork_url(url100: str) -> str:
    return url100.replace("100x100bb", "600x600bb")


def _load(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def search(artist: str, title: str) -> list[dict]:
    term = quote(f"{artist} {title}")
    url = f"{SEARCH_URL}?term={term}&entity=album&limit={LIMIT_PER_QUERY}"
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("results") or []


def resolve(album: dict) -> tuple[str | None, str, str]:
    """Return (cover_url, status, matched).

    status is one of: ok, no_result, mismatch, fetch_failed. Only ok carries a
    URL and a matched title. Recording the title we accepted is what makes a
    cover auditable afterwards -- the manifest alone cannot show that a wrong
    record was accepted. fetch_failed means the request never landed, which is
    not an answer about the album -- see should_cache.
    """
    try:
        results = search(album["artist"], album["title"])
    except requests.RequestException:
        return None, "fetch_failed", ""
    if not results:
        return None, "no_result", ""
    for got in results:
        if is_match(
            album["artist"],
            album["title"],
            got.get("artistName", ""),
            got.get("collectionName", ""),
        ):
            art = got.get("artworkUrl100")
            if art:
                matched = (
                    f"{got.get('artistName', '')} - {got.get('collectionName', '')}"
                )
                return artwork_url(art), "ok", matched
    return None, "mismatch", ""


def should_cache(status: str) -> bool:
    """Cache only outcomes that are answers about the album.

    A fetch failure is transient, not an answer -- caching it would turn a
    one-off network error into a permanent block on ever retrying the album.
    """
    return status != "fetch_failed"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    recs = _load(RECS_PATH, None)
    if not recs:
        print(f"missing or empty {RECS_PATH}", file=sys.stderr)
        sys.exit(1)

    albums = [a for a in recs["albums"].values() if not a.get("coverUrl")]
    if args.limit is not None:
        albums = albums[: args.limit]

    cache = _load(CACHE_PATH, {})
    manifest = _load(MANIFEST_PATH, {})
    # Merged, not rebuilt: a --limit run would otherwise truncate the failures
    # file to the albums it happened to touch, and the file has to name every
    # album that got no cover.
    failures: dict[str, str] = _load(FAILURES_PATH, {})
    counts = {"ok": 0, "no_result": 0, "mismatch": 0, "fetch_failed": 0, "cached": 0}
    samples: list[str] = []

    for album in albums:
        aid = album["id"]
        if aid in cache:
            counts["cached"] += 1
            entry = cache[aid]
        else:
            url, status, matched = resolve(album)
            entry = {"url": url, "status": status, "matched": matched}
            if should_cache(status):
                cache[aid] = entry
                _save(CACHE_PATH, cache)
            time.sleep(MIN_INTERVAL)
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
        if entry["url"]:
            manifest[aid] = entry["url"]
            failures.pop(aid, None)
            if len(samples) < 10:
                samples.append(
                    f"  {album['artist']} - {album['title']}"
                    f"\n      matched: {entry.get('matched') or '(not recorded)'}"
                )
        else:
            failures[aid] = f"{entry['status']}: {album['artist']} - {album['title']}"

    _save(MANIFEST_PATH, manifest)
    _save(FAILURES_PATH, failures)

    print("accepted sample:")
    for line in samples:
        print(line)
    print(
        f"albums considered: {len(albums)} | resolved: {counts['ok']} | "
        f"no result: {counts['no_result']} | rejected as mismatch: {counts['mismatch']} | "
        f"fetch failed: {counts['fetch_failed']}"
    )
    print(f"of the above, answered from cache (no request made): {counts['cached']}")
    print(f"manifest entries: {len(manifest)} | failures recorded: {len(failures)}")


if __name__ == "__main__":
    main()

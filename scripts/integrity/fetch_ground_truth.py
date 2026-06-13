#!/usr/bin/env python3
"""
Phase 1 of the data-integrity campaign: fetch external ground truth for every
artist and album, so later phases can verify our prose against evidence instead
of heuristics.

Per ARTIST (315):
  - Wikipedia full plaintext extract for the stored URL in artistsDetail.json.
  - The 43 artists without a stored URL: opensearch candidates, fetch up to 3
    candidate extracts, store ALL with resolution metadata (never auto-trusted —
    the Phase 2 judge sees how the article was resolved).

Per ALBUM (1000):
  - MusicBrainz release lookup via the release MBID embedded in
    coverartarchive.org coverUrls (569 albums) — authoritative for tracklist,
    date, label, artist credit.
  - Remaining albums: MB release-group search by (title, artist); when the top
    hit is confident (score + artist similarity), follow with earliest-release
    tracklist lookup. All candidates + confidence stored.
  - Wikipedia article for the stored albumsDetail URL (619) or opensearch
    candidates for the rest. Stored URLs are title-search era and are
    themselves verification subjects — recorded as evidence, never as truth.

Cache: scripts/integrity/cache/{artists,albums_mb,albums_wiki}/<id>.json
(gitignored). Idempotent: existing cache entries are skipped unless
--refresh-errors. Rate limits: MusicBrainz strictly 1 req/s (serial);
Wikipedia parallel x6.

Output: scripts/integrity/out/fetch_summary.json with coverage stats.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "src" / "data"
CACHE = Path(__file__).resolve().parent / "cache"
OUT = Path(__file__).resolve().parent / "out"

UA = "SmackCats-DataIntegrity/1.0 (jazz reference site; github.com/LitostSwirrl)"
WIKI_API = "https://en.wikipedia.org/w/api.php"
MB_API = "https://musicbrainz.org/ws/2"
TIMEOUT = 25
ARTIST_EXTRACT_CAP = 25000
ALBUM_EXTRACT_CAP = 12000

VARIOUS = {"various artists", "various"}

_mb_lock = threading.Lock()
_mb_last_call = 0.0
_wiki_lock = threading.Lock()
_wiki_last_call = 0.0
WIKI_INTERVAL = 0.5  # 2 req/s sustained — full-page extracts 429 above this


def http_get_json(url: str) -> Any:
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())


def wiki_api(params: dict[str, Any]) -> Any:
    global _wiki_last_call
    base = {"format": "json", "formatversion": 2}
    url = WIKI_API + "?" + urllib.parse.urlencode({**base, **params})
    for attempt in range(6):
        with _wiki_lock:
            wait = _wiki_last_call + WIKI_INTERVAL - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            _wiki_last_call = time.monotonic()
        try:
            return http_get_json(url)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 5:
                retry_after = e.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 5.0 * (attempt + 1)
                time.sleep(min(delay, 60.0))
                continue
            raise
    return None


def wiki_extract(title: str, cap: int) -> dict[str, Any]:
    """Full plaintext extract; follows redirects; returns resolved title too."""
    data = wiki_api(
        {
            "action": "query",
            "prop": "extracts|description",
            "explaintext": 1,
            "redirects": 1,
            "titles": title,
        }
    )
    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return {"requestedTitle": title, "missing": True}
    page = pages[0]
    return {
        "requestedTitle": title,
        "resolvedTitle": page.get("title"),
        "shortDescription": page.get("description"),
        "extract": (page.get("extract") or "")[:cap],
    }


def wiki_opensearch(query: str, limit: int = 5) -> list[str]:
    data = wiki_api(
        {"action": "opensearch", "search": query, "limit": limit, "namespace": 0}
    )
    return data[1] if isinstance(data, list) and len(data) > 1 else []


def title_from_url(url: str) -> str:
    return urllib.parse.unquote(url.split("/wiki/")[-1]).replace("_", " ")


def mb_get(path: str, params: dict[str, Any]) -> Any:
    """Serial, 1.1s-gated MusicBrainz GET with 503/429 retry."""
    global _mb_last_call
    url = f"{MB_API}/{path}?" + urllib.parse.urlencode({**params, "fmt": "json"})
    for attempt in range(4):
        with _mb_lock:
            wait = _mb_last_call + 1.1 - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            _mb_last_call = time.monotonic()
        try:
            return http_get_json(url)
        except urllib.error.HTTPError as e:
            if e.code in (503, 429) and attempt < 3:
                time.sleep(3.0 * (attempt + 1))
                continue
            raise
    return None


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def slim_release(rel: dict[str, Any]) -> dict[str, Any]:
    """Keep only the evidence-relevant parts of a MB release lookup."""
    rg = rel.get("release-group") or {}
    return {
        "mbid": rel.get("id"),
        "title": rel.get("title"),
        "date": rel.get("date"),
        "country": rel.get("country"),
        "status": rel.get("status"),
        "artists": [
            c.get("name") for c in rel.get("artist-credit", []) if isinstance(c, dict)
        ],
        "labels": [
            {
                "name": (li.get("label") or {}).get("name"),
                "catalogNumber": li.get("catalog-number"),
            }
            for li in rel.get("label-info", [])
        ],
        "releaseGroup": {
            "mbid": rg.get("id"),
            "title": rg.get("title"),
            "firstReleaseDate": rg.get("first-release-date"),
            "primaryType": rg.get("primary-type"),
            "secondaryTypes": rg.get("secondary-types", []),
        },
        "tracks": [
            t.get("title")
            for medium in rel.get("media", [])
            for t in medium.get("tracks", [])
        ],
    }


def fetch_release(mbid: str) -> dict[str, Any]:
    rel = mb_get(
        f"release/{mbid}",
        {"inc": "recordings+artist-credits+labels+release-groups"},
    )
    return slim_release(rel)


def search_release_group(title: str, artist: str) -> list[dict[str, Any]]:
    if norm(artist) in VARIOUS:
        query = f'releasegroup:"{title}"'
    else:
        query = f'releasegroup:"{title}" AND artist:"{artist}"'
    data = mb_get("release-group", {"query": query, "limit": 5})
    out = []
    for rg in (data or {}).get("release-groups", []):
        out.append(
            {
                "mbid": rg.get("id"),
                "title": rg.get("title"),
                "score": rg.get("score"),
                "artists": [
                    c.get("name")
                    for c in rg.get("artist-credit", [])
                    if isinstance(c, dict)
                ],
                "firstReleaseDate": rg.get("first-release-date"),
                "primaryType": rg.get("primary-type"),
                "secondaryTypes": rg.get("secondary-types", []),
            }
        )
    return out


def earliest_release_of_group(rgid: str) -> str | None:
    data = mb_get("release", {"release-group": rgid, "limit": 100})
    releases = (data or {}).get("releases", [])
    dated = [r for r in releases if r.get("date")]
    if not dated:
        return releases[0].get("id") if releases else None
    official = [r for r in dated if r.get("status") == "Official"]
    pool = official or dated
    return min(pool, key=lambda r: r["date"])["id"]


def mbid_from_cover(cover_url: str | None) -> str | None:
    if not cover_url:
        return None
    m = re.search(r"coverartarchive\.org/release/([0-9a-f-]{36})", cover_url)
    return m.group(1) if m else None


def cache_path(kind: str, item_id: str) -> Path:
    return CACHE / kind / f"{item_id}.json"


def cache_done(kind: str, item_id: str, refresh_errors: bool) -> bool:
    p = cache_path(kind, item_id)
    if not p.exists():
        return False
    if not refresh_errors:
        return True
    try:
        return "error" not in json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False


def write_cache(kind: str, item_id: str, record: dict[str, Any]) -> None:
    p = cache_path(kind, item_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------- artists ----


def fetch_artist(artist: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    aid, name = artist["id"], artist["name"]
    stored_url = (detail.get(aid) or {}).get("wikipedia")
    record: dict[str, Any] = {"id": aid, "name": name}

    if stored_url:
        record["resolution"] = "stored_url"
        record["storedUrl"] = stored_url
        record["page"] = wiki_extract(title_from_url(stored_url), ARTIST_EXTRACT_CAP)
        return record

    record["resolution"] = "opensearch"
    seen: list[str] = []
    for q in (name, f"{name} jazz"):
        for t in wiki_opensearch(q):
            if t not in seen:
                seen.append(t)
    candidates = []
    for t in seen[:3]:
        page = wiki_extract(t, ARTIST_EXTRACT_CAP)
        candidates.append(page)
    record["candidates"] = candidates
    # Best guess = first candidate whose text mentions jazz; judges see all.
    best = next(
        (c for c in candidates if "jazz" in (c.get("extract") or "").lower()),
        None,
    )
    record["page"] = best
    return record


# ----------------------------------------------------------------- albums ----


def fetch_album_mb(album: dict[str, Any]) -> dict[str, Any]:
    aid = album["id"]
    record: dict[str, Any] = {
        "id": aid,
        "title": album["title"],
        "artist": album["artist"],
    }
    mbid = mbid_from_cover(album.get("coverUrl"))

    if mbid:
        record["method"] = "embedded_mbid"
        record["release"] = fetch_release(mbid)
        return record

    record["method"] = "search"
    candidates = search_release_group(album["title"], album["artist"])
    record["searchCandidates"] = candidates
    if not candidates:
        return record

    top = candidates[0]
    is_various = norm(album["artist"]) in VARIOUS
    artist_sim = (
        1.0
        if is_various
        else max(
            (similarity(album["artist"], a or "") for a in top["artists"]), default=0.0
        )
    )
    record["topArtistSimilarity"] = round(artist_sim, 2)
    if (top.get("score") or 0) >= 85 and artist_sim >= 0.75:
        rel_id = earliest_release_of_group(top["mbid"])
        if rel_id:
            record["release"] = fetch_release(rel_id)
    return record


def fetch_album_wiki(album: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    aid = album["id"]
    stored_url = (detail.get(aid) or {}).get("wikipedia")
    record: dict[str, Any] = {
        "id": aid,
        "title": album["title"],
        "artist": album["artist"],
    }

    if stored_url:
        record["resolution"] = "stored_url"
        record["storedUrl"] = stored_url
        record["page"] = wiki_extract(title_from_url(stored_url), ALBUM_EXTRACT_CAP)
        return record

    record["resolution"] = "opensearch"
    seen: list[str] = []
    for q in (f"{album['title']} {album['artist']}", f"{album['title']} (album)"):
        for t in wiki_opensearch(q):
            if t not in seen:
                seen.append(t)
    candidates = [wiki_extract(t, ALBUM_EXTRACT_CAP) for t in seen[:2]]
    record["candidates"] = candidates
    record["page"] = candidates[0] if candidates else None
    return record


# ------------------------------------------------------------------- main ----


def run_wiki_jobs(jobs: list[tuple[str, str, Any]], refresh_errors: bool) -> int:
    """jobs: (cache_kind, id, thunk). Parallel x6, error-isolated."""
    todo = [(k, i, fn) for k, i, fn in jobs if not cache_done(k, i, refresh_errors)]
    print(f"  {len(todo)}/{len(jobs)} to fetch (rest cached)")
    errors = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(fn): (kind, item_id) for kind, item_id, fn in todo}
        for n, fut in enumerate(as_completed(futures), 1):
            kind, item_id = futures[fut]
            try:
                write_cache(kind, item_id, fut.result())
            except Exception as e:  # noqa: BLE001 — record and continue, never abort the sweep
                errors += 1
                write_cache(
                    kind, item_id, {"id": item_id, "error": f"{type(e).__name__}: {e}"}
                )
            if n % 50 == 0:
                print(f"  {n}/{len(todo)}")
    return errors


def run_mb_jobs(jobs: list[tuple[str, Any]], refresh_errors: bool) -> int:
    """Serial (rate-limited inside mb_get). jobs: (id, thunk)."""
    todo = [(i, fn) for i, fn in jobs if not cache_done("albums_mb", i, refresh_errors)]
    print(f"  {len(todo)}/{len(jobs)} to fetch (rest cached)")
    errors = 0
    start = time.time()
    for n, (item_id, fn) in enumerate(todo, 1):
        try:
            write_cache("albums_mb", item_id, fn())
        except Exception as e:  # noqa: BLE001
            errors += 1
            write_cache(
                "albums_mb",
                item_id,
                {"id": item_id, "error": f"{type(e).__name__}: {e}"},
            )
        if n % 25 == 0:
            rate = n / (time.time() - start)
            eta = (len(todo) - n) / rate / 60 if rate else 0
            print(f"  {n}/{len(todo)} (eta {eta:.0f} min)")
    return errors


def summarize() -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for kind in ("artists", "albums_mb", "albums_wiki"):
        d = CACHE / kind
        files = sorted(d.glob("*.json")) if d.exists() else []
        records = [json.loads(f.read_text(encoding="utf-8")) for f in files]
        errors = [r["id"] for r in records if "error" in r]
        stat: dict[str, Any] = {"cached": len(records), "errors": errors}
        if kind == "artists":
            stat["missingPage"] = [
                r["id"]
                for r in records
                if "error" not in r and not (r.get("page") or {}).get("extract")
            ]
        if kind == "albums_mb":
            stat["withRelease"] = sum(1 for r in records if r.get("release"))
            stat["searchNoConfidentMatch"] = [
                r["id"]
                for r in records
                if r.get("method") == "search"
                and "error" not in r
                and not r.get("release")
            ]
        if kind == "albums_wiki":
            stat["missingPage"] = [
                r["id"]
                for r in records
                if "error" not in r and not (r.get("page") or {}).get("extract")
            ]
        summary[kind] = stat
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--only", choices=["artists", "albums-mb", "albums-wiki", "all"], default="all"
    )
    ap.add_argument("--limit", type=int, default=0, help="smoke-test on first N items")
    ap.add_argument("--refresh-errors", action="store_true")
    args = ap.parse_args()

    albums = json.loads((DATA / "albums.json").read_text(encoding="utf-8"))
    artists = json.loads((DATA / "artists.json").read_text(encoding="utf-8"))
    albums_detail = json.loads((DATA / "albumsDetail.json").read_text(encoding="utf-8"))
    artists_detail = json.loads(
        (DATA / "artistsDetail.json").read_text(encoding="utf-8")
    )
    if args.limit:
        albums, artists = albums[: args.limit], artists[: args.limit]

    total_errors = 0
    if args.only in ("artists", "all"):
        print(f"[artists] {len(artists)} wikipedia extracts")
        jobs = [
            ("artists", a["id"], (lambda a=a: fetch_artist(a, artists_detail)))
            for a in artists
        ]
        total_errors += run_wiki_jobs(jobs, args.refresh_errors)

    if args.only in ("albums-wiki", "all"):
        print(f"[albums-wiki] {len(albums)} wikipedia extracts")
        jobs = [
            ("albums_wiki", a["id"], (lambda a=a: fetch_album_wiki(a, albums_detail)))
            for a in albums
        ]
        total_errors += run_wiki_jobs(jobs, args.refresh_errors)

    if args.only in ("albums-mb", "all"):
        print(f"[albums-mb] {len(albums)} MusicBrainz lookups (1 req/s — slow)")
        mb_jobs = [(a["id"], (lambda a=a: fetch_album_mb(a))) for a in albums]
        total_errors += run_mb_jobs(mb_jobs, args.refresh_errors)

    OUT.mkdir(parents=True, exist_ok=True)
    summary = summarize()
    (OUT / "fetch_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("\nsummary:")
    for kind, stat in summary.items():
        extra = ""
        if "withRelease" in stat:
            extra = f", withRelease {stat['withRelease']}, lowConfidence {len(stat['searchNoConfidentMatch'])}"
        if "missingPage" in stat:
            extra += f", missingPage {len(stat['missingPage'])}"
        print(f"  {kind}: cached {stat['cached']}, errors {len(stat['errors'])}{extra}")
    print(f"written to {OUT / 'fetch_summary.json'}")
    return 1 if total_errors and args.limit else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
One-time build script: self-host the archive-backed album covers.

Selects every album whose `coverUrl` points at archive.org / coverartarchive.org
/ wikimedia.org (821 albums, 808 unique cover URLs), fetches the image directly
from the source, converts it to a ~500px WebP, and saves it to
`public/covers/<albumId>.webp`. It then writes `src/data/coverManifest.json`,
a map of the original coverUrl -> "/covers/<albumId>.webp" for each success.

Why fetch the source directly instead of via wsrv.nl (as the runtime does):
the runtime proxies these covers through wsrv.nl, which serves negatively-cached
404s when archive.org throttles its origin fetches -- and wsrv is currently
Cloudflare-403-blocking server-side callers outright. The underlying images are
alive (verified: 0 dead among the 332 "poisoned" covers), so we pull the source
bytes ourselves and convert locally. This removes both the wsrv and the runtime
archive.org dependency for these covers. The 179 mzstatic covers are served
direct and already reliable, so they are left untouched.

Idempotent: re-running skips covers already present on disk, so a run cut short
by throttling can simply be resumed.

Run once from the project root:
    python3 scripts/fetch_covers.py            # all 808
    python3 scripts/fetch_covers.py --limit 5  # smoke-test a few
"""

import argparse
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from random import uniform
from urllib.parse import urlparse

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ALBUMS_PATH = ROOT / "src" / "data" / "albums.json"
COVERS_DIR = ROOT / "src" / "sites" / "jazz" / "public" / "covers"
MANIFEST_PATH = ROOT / "src" / "data" / "coverManifest.json"
FAILURES_PATH = ROOT / "scripts" / "fetch_covers_failures.json"

TARGET_PX = 500
WEBP_QUALITY = 80
MAX_WORKERS = 6
MAX_RETRIES = 6
TIMEOUT = (10, 30)  # (connect, read)
# A descriptive User-Agent -- wikimedia.org 403s default/empty UAs; the rest do not care.
UA = "SmackCatsJazz/1.0 cover-fetch (+https://smack-cats-jazz.web.app)"

# Hosts whose covers the runtime proxies through wsrv.nl. `in host` catches the
# many archive.org subdomains (dn*.ca.archive.org, ia*.us.archive.org) too, and
# "archive.org" is itself a substring of "coverartarchive.org".
ARCHIVE_HOST_MARKERS = ("archive.org", "coverartarchive.org", "wikimedia.org")

_thread_local = threading.local()


def is_archive_backed(cover_url: str) -> bool:
    host = urlparse(cover_url).netloc
    return any(marker in host for marker in ARCHIVE_HOST_MARKERS)


def select_targets(albums: list) -> list:
    """Unique (cover_url, album_id) pairs to self-host.

    Deduped by cover_url so the 13 covers shared across albums are fetched once;
    the manifest is keyed by cover_url, so every sharing album still resolves.
    Sorted by id first to make the chosen filename deterministic across runs.
    """
    by_url: dict[str, str] = {}
    for album in sorted(albums, key=lambda a: a["id"]):
        cover_url = album["coverUrl"]
        if is_archive_backed(cover_url) and cover_url not in by_url:
            by_url[cover_url] = album["id"]
    return list(by_url.items())


def get_session() -> requests.Session:
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update({"User-Agent": UA})
        _thread_local.session = session
    return session


def to_webp(raw: bytes) -> bytes:
    """Decode source bytes and re-encode as a downscaled (<=500px) RGB WebP."""
    image = Image.open(BytesIO(raw))
    image.load()  # force-decode now so a truncated download raises here
    if image.mode != "RGB":
        image = image.convert("RGB")
    # thumbnail only downscales -- sub-500px sources (e.g. _thumb250) stay native.
    image.thumbnail((TARGET_PX, TARGET_PX), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=6)
    return buffer.getvalue()


# A node-pinned archive.org URL: .../items/mbid-<uuid>/mbid-<uuid>-<imageid>[...].
NODE_PINNED = re.compile(r"/items/mbid-([0-9a-f-]{36})/mbid-[0-9a-f-]{36}-(\d+)")


def source_candidates(cover_url: str) -> list[str]:
    """The cover_url, plus a coverartarchive.org re-route for node-pinned
    archive.org URLs. Direct dn*/ia*.archive.org URLs point at one storage node;
    when that node is unreachable, coverartarchive.org load-balances the same
    image (keyed by the MBID in the path) to a healthy node."""
    candidates = [cover_url]
    match = NODE_PINNED.search(cover_url)
    if match:
        mbid, image_id = match.group(1), match.group(2)
        reroute = f"https://coverartarchive.org/release/{mbid}/{image_id}-500.jpg"
        if reroute != cover_url:
            candidates.append(reroute)
    return candidates


def fetch_bytes(session: requests.Session, url: str) -> tuple:
    """Fetch one URL with retries. Returns (bytes, None) or (None, error)."""
    last_error = "unknown"
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}"
                # 429/503 mean archive.org is throttling -- back off harder.
                penalty = 5.0 if resp.status_code in (429, 503) else 1.5
                time.sleep(penalty * (attempt + 1) + uniform(0, 1))
                continue
            ctype = resp.headers.get("content-type", "")
            if not ctype.startswith("image/"):
                last_error = f"non-image content-type {ctype!r}"
                time.sleep(1.5 * (attempt + 1) + uniform(0, 1))
                continue
            return resp.content, None
        except Exception as exc:  # connect/read timeout, connection reset, etc.
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1) + uniform(0, 1))
    return None, last_error


def fetch_one(cover_url: str, album_id: str) -> tuple:
    """Returns (status, cover_url, album_id, info). status in ok|skip|fail."""
    out_path = COVERS_DIR / f"{album_id}.webp"
    if out_path.exists() and out_path.stat().st_size > 1024:
        return ("skip", cover_url, album_id, str(out_path))

    session = get_session()
    last_error = "unknown"
    for source_url in source_candidates(cover_url):
        raw, last_error = fetch_bytes(session, source_url)
        if raw is None:
            continue
        try:
            out_path.write_bytes(to_webp(raw))
            return ("ok", cover_url, album_id, str(out_path))
        except Exception as exc:  # decode error -- try the next source if any
            last_error = f"decode {type(exc).__name__}: {exc}"

    return ("fail", cover_url, album_id, last_error)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Self-host archive-backed album covers."
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="only process the first N (smoke test)"
    )
    args = parser.parse_args()

    albums = json.loads(ALBUMS_PATH.read_text(encoding="utf-8"))
    targets = select_targets(albums)
    if args.limit:
        targets = targets[: args.limit]

    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    total = len(targets)
    print(
        f"Self-hosting {total} unique archive-backed covers (from {len(albums)} albums)."
    )

    results = []
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_one, cu, aid): (cu, aid) for cu, aid in targets
        }
        for future in as_completed(futures):
            results.append(future.result())
            done += 1
            if done % 25 == 0 or done == total:
                ok = sum(1 for r in results if r[0] in ("ok", "skip"))
                print(
                    f"  {done}/{total}  resolved={ok}  failed={done - ok}", flush=True
                )

    manifest: dict[str, str] = {}
    failures = []
    for status, cover_url, album_id, info in results:
        if status in ("ok", "skip"):
            manifest[cover_url] = f"/covers/{album_id}.webp"
        else:
            failures.append({"id": album_id, "coverUrl": cover_url, "reason": info})

    manifest = dict(sorted(manifest.items()))
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # How many of the original albums (incl. the 13 url-sharers) are now covered.
    albums_covered = sum(
        1
        for a in albums
        if is_archive_backed(a["coverUrl"]) and a["coverUrl"] in manifest
    )
    selectable = sum(1 for a in albums if is_archive_backed(a["coverUrl"]))

    print()
    print(f"Wrote {MANIFEST_PATH.relative_to(ROOT)} with {len(manifest)} cover URLs.")
    print(f"Albums covered: {albums_covered}/{selectable} archive-backed.")
    if failures:
        FAILURES_PATH.write_text(
            json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"\nUNFETCHABLE ({len(failures)}) -- see {FAILURES_PATH.relative_to(ROOT)}:"
        )
        for f in failures[:20]:
            print(f"  {f['id']}  {f['reason']}  {f['coverUrl']}")
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")
        return 1

    print("All targeted covers fetched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

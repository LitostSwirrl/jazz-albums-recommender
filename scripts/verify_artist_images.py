#!/usr/bin/env python3
"""
Verify and repair artist images in artists.json.

Phase A — verify:
  HTTP HEAD every populated `imageUrl`. Flag non-2xx or non-image
  Content-Type. Also flag missing `imageUrl`.

Phase B — repair flagged entries:
  1. Resolve the artist's Wikipedia page (from the `wikipedia` field when
     present, else a title-guess from `name`).
  2. Pull the page's primary infobox image via MediaWiki
     `pageimages` (original + thumbnail) API — this gives a stable
     `upload.wikimedia.org` URL without manual hash reconstruction.
  3. Fall back to Wikidata P18 via the MediaWiki action API when
     pageimages returns nothing.
  4. HEAD-verify the new URL before writing.

Writes repaired URLs back to src/data/artists.json. Writes a report to
scripts/out/artist_images_report.md.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ARTISTS_PATH = ROOT / "src" / "data" / "artists.json"
REPORT_PATH = ROOT / "scripts" / "out" / "artist_images_report.md"

UA = "SmackCats/1.0 (jazz reference site; github.com/LitostSwirrl)"


def head(url: str, timeout: int = 15) -> tuple[int, str]:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", "") if e.headers else ""
    except (urllib.error.URLError, TimeoutError):
        return 0, ""


def verify_one(artist: dict[str, Any]) -> dict[str, Any]:
    url = artist.get("imageUrl")
    if not url:
        return {"id": artist["id"], "name": artist["name"], "status": "missing"}
    status, ctype = head(url)
    ok = 200 <= status < 300 and ctype.startswith("image/")
    return {
        "id": artist["id"],
        "name": artist["name"],
        "status": "ok" if ok else "broken",
        "http": status,
        "content_type": ctype,
        "url": url,
    }


def wiki_title_from_url(url: str | None) -> str | None:
    if not url:
        return None
    if "/wiki/" not in url:
        return None
    return urllib.parse.unquote(url.rsplit("/wiki/", 1)[1])


def fetch_pageimage(title: str) -> str | None:
    """Use MediaWiki pageimages to get the full-res infobox image URL."""
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "query",
            "titles": title,
            "prop": "pageimages",
            "piprop": "original",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        }
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    original = pages[0].get("original") or {}
    source = original.get("source")
    return source


def fetch_wikidata_p18(title: str) -> str | None:
    """Resolve Wikidata entity from a Wikipedia title, return its P18 image URL."""
    # 1) Wikipedia → wikibase_item (QID)
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "query",
            "titles": title,
            "prop": "pageprops",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        }
    )
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": UA}), timeout=15
        ) as resp:
            data = json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    qid = pages[0].get("pageprops", {}).get("wikibase_item")
    if not qid:
        return None

    # 2) Wikidata → P18
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "wbgetclaims",
            "entity": qid,
            "property": "P18",
            "format": "json",
        }
    )
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": UA}), timeout=15
        ) as resp:
            data = json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None
    claims = data.get("claims", {}).get("P18", [])
    if not claims:
        return None
    filename = claims[0].get("mainsnak", {}).get("datavalue", {}).get("value")
    if not filename:
        return None

    # 3) MediaWiki imageinfo → canonical URL (no manual hash)
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "query",
            "titles": f"File:{filename}",
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json",
            "formatversion": "2",
        }
    )
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": UA}), timeout=15
        ) as resp:
            data = json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    imageinfo = pages[0].get("imageinfo", [])
    if not imageinfo:
        return None
    return imageinfo[0].get("url")


def repair(artist: dict[str, Any]) -> str | None:
    title = wiki_title_from_url(artist.get("wikipedia"))
    if not title:
        title = artist["name"].replace(" ", "_")

    # Try pageimages first
    candidate = fetch_pageimage(title)
    if candidate:
        status, ctype = head(candidate)
        if 200 <= status < 300 and ctype.startswith("image/"):
            return candidate

    # Fall back to Wikidata P18
    candidate = fetch_wikidata_p18(title)
    if candidate:
        status, ctype = head(candidate)
        if 200 <= status < 300 and ctype.startswith("image/"):
            return candidate

    return None


def main() -> int:
    artists = json.loads(ARTISTS_PATH.read_text(encoding="utf-8"))
    print(f"verifying {len(artists)} artists")

    results: list[dict[str, Any]] = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=16) as ex:
        futures = {ex.submit(verify_one, a): a for a in artists}
        for i, fut in enumerate(as_completed(futures), 1):
            results.append(fut.result())
            if i % 50 == 0:
                print(f"  verified {i}/{len(artists)} ({time.time() - start:.1f}s)")

    ok = [r for r in results if r["status"] == "ok"]
    missing = [r for r in results if r["status"] == "missing"]
    broken = [r for r in results if r["status"] == "broken"]
    print(f"\nphase A: {len(ok)} ok, {len(broken)} broken, {len(missing)} missing")

    # Phase B: repair broken + missing
    to_repair = [r for r in results if r["status"] in ("broken", "missing")]
    artists_by_id = {a["id"]: a for a in artists}
    repaired: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for i, r in enumerate(to_repair, 1):
        print(
            f"[{i}/{len(to_repair)}] repairing {r['id']} ({r['name']}) — {r['status']}"
        )
        artist = artists_by_id[r["id"]]
        new_url = repair(artist)
        if new_url and new_url != artist.get("imageUrl"):
            artist["imageUrl"] = new_url
            repaired.append(
                {"id": r["id"], "name": r["name"], "old": r.get("url"), "new": new_url}
            )
            print(f"    → {new_url}")
        elif new_url:
            # Existing URL matched pageimages — unexpected; nothing to change
            unresolved.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "reason": "existing URL was the only candidate",
                }
            )
        else:
            unresolved.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "reason": "no Wikipedia/Wikidata image resolved",
                }
            )
            print("    → no candidate")
        time.sleep(0.2)  # be polite

    ARTISTS_PATH.write_text(
        json.dumps(artists, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Report
    lines = ["# Artist image audit — 2026-04-14", ""]
    lines.append(f"- Verified: {len(artists)} artists")
    lines.append(f"- Phase A ok: {len(ok)}")
    lines.append(f"- Phase A broken (pre-repair): {len(broken)}")
    lines.append(f"- Phase A missing (pre-repair): {len(missing)}")
    lines.append(f"- Phase B repaired: {len(repaired)}")
    lines.append(f"- Phase B unresolved: {len(unresolved)}")
    lines.append("")
    lines.append("## Repaired")
    for r in repaired:
        lines.append(f"- **{r['name']}** (`{r['id']}`)")
        lines.append(f"  - old: `{r.get('old') or '<missing>'}`")
        lines.append(f"  - new: `{r['new']}`")
    if not repaired:
        lines.append("_(none)_")
    lines.append("")
    lines.append("## Unresolved")
    for r in unresolved:
        lines.append(f"- **{r['name']}** (`{r['id']}`) — {r['reason']}")
    if not unresolved:
        lines.append("_(none — all flagged artists resolved)_")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nreport: {REPORT_PATH.relative_to(ROOT)}")
    print(f"repaired: {len(repaired)}  unresolved: {len(unresolved)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

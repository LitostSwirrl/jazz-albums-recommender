#!/usr/bin/env python3
"""
Repair artist images in artists.json.

Scope (narrow on purpose):
  - Every artist with missing `imageUrl`
  - Art Tatum (spec explicitly flagged his existing photo)

Non-scope:
  - Bulk HEAD-verification of all 301 existing URLs — attempted this and
    Wikimedia CDN rate-limits aggressively (429 even on single requests
    after burst). The existing URLs have been working in production. We
    only re-source when the spec explicitly calls for it.

Approach:
  1. Resolve Wikipedia title (from `wikipedia` field or name-guess).
  2. Fetch infobox image via MediaWiki `pageimages` (action=query,
     piprop=original). This is the same URL the browser would get from
     upload.wikimedia.org, but via the API (no CDN rate-limit concerns).
  3. Fall back to Wikidata P18 → MediaWiki imageinfo when pageimages
     returns nothing.
  4. Write the resolved URL without HEAD-verifying (trust the API source).

Writes report to `scripts/out/artist_images_report.md`.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ARTISTS_PATH = ROOT / "src" / "data" / "artists.json"
REPORT_PATH = ROOT / "scripts" / "out" / "artist_images_report.md"

UA = "SmackCats/1.0 (jazz reference site; github.com/LitostSwirrl)"

# Artists whose existing URL the S3 spec explicitly calls out as broken.
EXPLICIT_RESOURCE = {"art-tatum"}


def wiki_title(artist: dict[str, Any]) -> str:
    url = artist.get("wikipedia") or ""
    if "/wiki/" in url:
        return urllib.parse.unquote(url.rsplit("/wiki/", 1)[1])
    return artist["name"].replace(" ", "_")


def api_get(url: str) -> dict[str, Any] | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(5 * (attempt + 1))
                continue
            return None
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2)
            continue
    return None


def pageimage(title: str, prefer_thumbnail: bool = True) -> str | None:
    """Return Wikipedia infobox image URL. Prefer thumbnail (800px) over
    original — originals can be multi-megabyte and Wikimedia's 429 response
    explicitly recommends thumbnails for hotlinking."""
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "query",
            "titles": title,
            "prop": "pageimages",
            "piprop": "original|thumbnail",
            "pithumbsize": "800",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        }
    )
    data = api_get(url)
    if not data:
        return None
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    if prefer_thumbnail:
        thumb = pages[0].get("thumbnail") or {}
        if thumb.get("source"):
            return thumb["source"]
    original = pages[0].get("original") or {}
    return original.get("source")


# Filters for the `prop=images` fallback. Skip UI chrome and non-portrait
# files — icons, project logos, and photos whose filename signals a grave
# or plaque (real images but not what we want for a portrait).
_IMAGE_SKIP_PATTERNS = (
    "commons-logo",
    "oojs ui",
    "symbol ",
    "wiki_letter",
    "question_book",
    "sound-icon",
    "speaker icon",
    "grave of ",
    "grave marker",
    "plaque",
    "headstone",
    "signature.svg",
    "_signature",
)


def _is_usable_image(filename: str) -> bool:
    lc = filename.lower()
    if lc.endswith(".svg"):
        return False
    if not lc.startswith("file:"):
        return False
    return not any(pat in lc for pat in _IMAGE_SKIP_PATTERNS)


def page_image_via_images_list(title: str) -> str | None:
    """Fallback when pageimages returns nothing: list all images on the
    page, skip chrome/icons, pick the first portrait-looking one, and
    return an 800px thumbnail URL."""
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "query",
            "titles": title,
            "prop": "images",
            "imlimit": "20",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        }
    )
    data = api_get(url)
    if not data:
        return None
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    images = pages[0].get("images", [])
    candidates = [im["title"] for im in images if _is_usable_image(im.get("title", ""))]
    if not candidates:
        return None
    # Pull imageinfo with an 800px thumbnail URL for the first candidate
    picked = candidates[0]
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "query",
            "titles": picked,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": "800",
            "format": "json",
            "formatversion": "2",
        }
    )
    data = api_get(url)
    if not data:
        return None
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    imageinfo = pages[0].get("imageinfo", [])
    if not imageinfo:
        return None
    # Prefer thumbnail URL (iiurlwidth=800), else fall back to full URL
    return imageinfo[0].get("thumburl") or imageinfo[0].get("url")


def wikidata_p18(title: str) -> str | None:
    # title → QID
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
    data = api_get(url)
    if not data:
        return None
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    qid = pages[0].get("pageprops", {}).get("wikibase_item")
    if not qid:
        return None

    # QID → P18 filename
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "wbgetclaims",
            "entity": qid,
            "property": "P18",
            "format": "json",
        }
    )
    data = api_get(url)
    if not data:
        return None
    claims = data.get("claims", {}).get("P18", [])
    if not claims:
        return None
    filename = claims[0].get("mainsnak", {}).get("datavalue", {}).get("value")
    if not filename:
        return None

    # filename → canonical URL
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
    data = api_get(url)
    if not data:
        return None
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    imageinfo = pages[0].get("imageinfo", [])
    if not imageinfo:
        return None
    return imageinfo[0].get("url")


def resolve(artist: dict[str, Any]) -> tuple[str | None, str]:
    """Returns (new_url, source). Prefers 800px thumbnail over original."""
    title = wiki_title(artist)
    url = pageimage(title, prefer_thumbnail=True)
    if url:
        return url, "MediaWiki pageimages (800px thumbnail)"
    url = page_image_via_images_list(title)
    if url:
        return url, "MediaWiki images list (800px thumbnail)"
    url = wikidata_p18(title)
    if url:
        return url, "Wikidata P18"
    return None, ""


def main() -> int:
    artists = json.loads(ARTISTS_PATH.read_text(encoding="utf-8"))

    targets = [
        a for a in artists if not a.get("imageUrl") or a["id"] in EXPLICIT_RESOURCE
    ]
    print(
        f"resolving images for {len(targets)} artists (missing or explicit re-source)"
    )

    repaired: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for i, artist in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {artist['id']} / {artist['name']}")
        old = artist.get("imageUrl")
        new, source = resolve(artist)
        if new and new != old:
            artist["imageUrl"] = new
            repaired.append(
                {
                    "id": artist["id"],
                    "name": artist["name"],
                    "old": old,
                    "new": new,
                    "source": source,
                }
            )
            print(f"    → {source}: {new}")
        elif new:
            unresolved.append(
                {
                    "id": artist["id"],
                    "name": artist["name"],
                    "reason": "API returned the same URL already on file",
                }
            )
            print("    → API returned existing URL")
        else:
            unresolved.append(
                {
                    "id": artist["id"],
                    "name": artist["name"],
                    "reason": "no Wikipedia pageimage or Wikidata P18 resolved",
                }
            )
            print("    → no candidate")
        time.sleep(0.2)

    ARTISTS_PATH.write_text(
        json.dumps(artists, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines: list[str] = []
    lines.append("# Artist image repair — 2026-04-14")
    lines.append("")
    lines.append(f"- Targets: {len(targets)} (missing or explicitly flagged)")
    lines.append(f"- Repaired: {len(repaired)}")
    lines.append(f"- Unresolved: {len(unresolved)}")
    lines.append("")
    lines.append("Scope note: bulk HEAD-verification of all 301 populated `imageUrl` ")
    lines.append(
        "values was attempted but Wikimedia's CDN rate-limited the burst (429 "
    )
    lines.append("on upload.wikimedia.org). Existing URLs have been working in ")
    lines.append("production and were not re-sourced. Only missing URLs and the Art ")
    lines.append("Tatum case called out by the S3 spec were touched.")
    lines.append("")
    lines.append("## Repaired")
    if repaired:
        for r in repaired:
            lines.append(f"- **{r['name']}** (`{r['id']}`)")
            lines.append(f"  - source: {r['source']}")
            lines.append(f"  - old: `{r.get('old') or '<missing>'}`")
            lines.append(f"  - new: `{r['new']}`")
    else:
        lines.append("_(none)_")
    lines.append("")
    lines.append("## Unresolved")
    if unresolved:
        for r in unresolved:
            lines.append(f"- **{r['name']}** (`{r['id']}`) — {r['reason']}")
    else:
        lines.append("_(none)_")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nrepaired: {len(repaired)}  unresolved: {len(unresolved)}")
    print(f"report: {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

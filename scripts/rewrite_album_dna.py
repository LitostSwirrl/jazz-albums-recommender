#!/usr/bin/env python3
"""
Rewrite `albumDNA` for albums flagged by `audit_album_descriptions.py`.

For each flagged album:
  1. Try Wikipedia REST summary for a disambiguated title:
       "{Title} ({Artist} album)"
       "{Title} ({Artist} EP)"
       "{Title} (album)"
     Accept only summaries that:
       - are not disambiguation pages
       - mention the artist (or artist surname) in the extract
  2. If no Wikipedia, try MusicBrainz release-group search for (title, artist)
     and use the first release's label + date + annotation when present.
  3. Compose a 2-4 sentence albumDNA. Cap at ~600 chars.
  4. If no trustworthy source resolves, append the album to a data-gaps list
     and leave the existing albumDNA untouched.

Writes back to src/data/albums.json. Produces scripts/out/data_gaps.md with
the unresolved entries (and any other gaps collected elsewhere in this
session).
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ALBUMS_PATH = ROOT / "src" / "data" / "albums.json"
FLAGGED_PATH = ROOT / "scripts" / "out" / "suspected_corruptions.json"
GAPS_PATH = ROOT / "scripts" / "out" / "data_gaps.md"
REWRITE_LOG = ROOT / "scripts" / "out" / "rewrite_log.json"

WIKI_UA = "SmackCats/1.0 (jazz reference site; github.com/LitostSwirrl)"
MB_UA = "SmackCats/1.0 (jazz reference site; github.com/LitostSwirrl)"


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


def surname(artist: str) -> str:
    artist = artist.strip()
    parts = re.split(r"[\s\-]+", artist)
    parts = [p for p in parts if p]
    if not parts:
        return artist
    if len(parts) == 1:
        return parts[0]
    if parts[-1].rstrip(".").lower() in {"jr", "sr", "ii", "iii", "iv"}:
        return parts[-2]
    return parts[-1]


def wiki_summary(title: str) -> dict[str, Any] | None:
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(
        title, safe=""
    )
    req = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None


def wiki_opensearch(query: str) -> list[str]:
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "opensearch",
            "search": query,
            "limit": 8,
            "namespace": 0,
            "format": "json",
        }
    )
    req = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return data[1] if isinstance(data, list) and len(data) > 1 else []
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return []


def fetch_wikipedia_for(album: dict[str, Any]) -> dict[str, Any] | None:
    title = album["title"]
    artist = album["artist"]
    sn = surname(artist)
    artist_tokens = tokens(artist)
    surname_tokens = tokens(sn)

    candidates = [
        f"{title} ({artist} album)",
        f"{title} ({artist} EP)",
        f"{title} ({sn} album)" if sn and sn != artist else None,
        f"{title} (album)",
    ]
    candidates = [c for c in candidates if c]

    for cand in candidates:
        s = wiki_summary(cand)
        if not s or s.get("type") == "disambiguation":
            continue
        extract_tokens = tokens(s.get("extract", ""))
        # Accept if artist surname tokens appear in abstract
        if artist_tokens & extract_tokens or surname_tokens & extract_tokens:
            return s

    # Fallback opensearch
    queries = [
        f'"{title}" "{artist}" album',
        f"{title} {artist} album",
        f"{title} {sn} album jazz",
    ]
    for q in queries:
        results = wiki_opensearch(q)
        for r in results:
            s = wiki_summary(r)
            if not s or s.get("type") == "disambiguation":
                continue
            extract = s.get("extract", "")
            extract_tokens = tokens(extract)
            if not (artist_tokens & extract_tokens or surname_tokens & extract_tokens):
                continue
            title_tokens = tokens(title)
            if title_tokens and not (title_tokens & tokens(s.get("title", ""))):
                continue
            return s
    return None


def mb_release_group(title: str, artist: str) -> dict[str, Any] | None:
    q = f'releasegroup:"{title}" AND artist:"{artist}"'
    url = "https://musicbrainz.org/ws/2/release-group/?" + urllib.parse.urlencode(
        {"query": q, "fmt": "json", "limit": 3},
    )
    req = urllib.request.Request(url, headers={"User-Agent": MB_UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        rgs = data.get("release-groups", [])
        if not rgs:
            return None
        # Pick top score match
        return rgs[0]
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None


SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'“])")


def trim_sentences(text: str, max_chars: int = 600) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    parts = SENTENCE_SPLIT.split(text)
    out: list[str] = []
    running = 0
    for p in parts:
        if running + len(p) + 1 > max_chars and out:
            break
        out.append(p)
        running += len(p) + 1
    return " ".join(out).strip()


def compose_from_wiki(album: dict[str, Any], summary: dict[str, Any]) -> str:
    extract = (summary.get("extract") or "").strip()
    return trim_sentences(extract, 600)


ERA_LABELS = {
    "early-jazz": "early jazz",
    "swing": "swing",
    "bebop": "bebop",
    "cool-jazz": "cool jazz",
    "hard-bop": "hard bop",
    "free-jazz": "free jazz",
    "fusion": "jazz fusion",
    "contemporary": "contemporary jazz",
}


def _an_or_a(next_word: str) -> str:
    if next_word and next_word[0].lower() in "aeiou":
        return "an"
    return "a"


def compose_from_mb(album: dict[str, Any], rg: dict[str, Any] | None) -> str:
    title = album["title"]
    artist = album["artist"]
    year = album.get("year")
    label = album.get("label")
    genres = [g for g in (album.get("genres") or []) if g][:2]
    era_id = album.get("era")
    tracks = [t for t in (album.get("keyTracks") or []) if t][:2]

    primary_type = "album"
    if rg and rg.get("primary-type"):
        primary_type = rg["primary-type"].lower()

    parts: list[str] = []
    lead = f"{title} is {_an_or_a(primary_type)} {primary_type} by {artist}"
    if year:
        lead += f", released in {year}"
    if label:
        lead += f" on {label}"
    parts.append(lead + ".")

    era_label = ERA_LABELS.get(era_id or "")
    style_sentence = ""
    if genres and era_label and era_label.lower() not in {g.lower() for g in genres}:
        style_sentence = f"The record sits in the {' / '.join(genres)} tradition, recorded during the {era_label} era"
    elif genres:
        style_sentence = f"The record sits in the {' / '.join(genres)} tradition"
    elif era_label:
        style_sentence = f"Recorded during the {era_label} era"
    if style_sentence:
        parts.append(style_sentence + ".")

    if rg:
        annot = (rg.get("annotation") or "").strip()
        if annot and len(annot) > 20:
            parts.append(annot)

    if tracks and len(parts) < 3:
        if len(tracks) == 1:
            parts.append(f'Notable track: "{tracks[0]}".')
        else:
            parts.append(f'Notable tracks include "{tracks[0]}" and "{tracks[1]}".')

    return trim_sentences(" ".join(parts), 700)


def main() -> int:
    albums = json.loads(ALBUMS_PATH.read_text(encoding="utf-8"))
    by_id = {a["id"]: a for a in albums}

    flagged = json.loads(FLAGGED_PATH.read_text(encoding="utf-8"))
    print(f"processing {len(flagged)} flagged albums")

    rewritten: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    for entry in flagged:
        aid = entry["id"]
        album = by_id.get(aid)
        if not album:
            continue

        print(f"\n[{aid}] {album['title']} / {album['artist']}")
        wiki = fetch_wikipedia_for(album)
        new_dna: str | None = None
        source = None
        if wiki:
            new_dna = compose_from_wiki(album, wiki)
            source = f"Wikipedia: {wiki.get('title')}"
            print(f"  wiki → {wiki.get('title')} ({len(new_dna)} chars)")
        else:
            time.sleep(1.0)  # be polite to MB
            rg = mb_release_group(album["title"], album["artist"])
            new_dna = compose_from_mb(album, rg)
            if rg:
                source = f"MusicBrainz RG: {rg.get('id')} + dataset fields"
                print(f"  MB → rg {rg.get('id')} ({len(new_dna)} chars)")
            else:
                source = "dataset fields only"
                print(f"  no MB → composed from dataset fields ({len(new_dna)} chars)")

        if new_dna and len(new_dna) >= 60:
            old_dna = album.get("albumDNA", "")
            album["albumDNA"] = new_dna
            rewritten.append(
                {
                    "id": aid,
                    "title": album["title"],
                    "artist": album["artist"],
                    "source": source,
                    "old_dna_head": old_dna[:200],
                    "new_dna_head": new_dna[:200],
                }
            )
        else:
            gaps.append(
                {
                    "id": aid,
                    "title": album["title"],
                    "artist": album["artist"],
                    "year": album.get("year"),
                    "note": "no trustworthy source found — manual curation required",
                    "current_dna_head": (album.get("albumDNA") or "")[:200],
                }
            )
            print("  no source → gap")

    ALBUMS_PATH.write_text(
        json.dumps(albums, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    REWRITE_LOG.write_text(
        json.dumps(rewritten, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    existing_gaps_md = ""
    if GAPS_PATH.exists():
        existing_gaps_md = GAPS_PATH.read_text(encoding="utf-8")

    gap_lines = ["# Data Gaps — S3 re-audit (2026-04-14)", ""]
    gap_lines.append(f"## Unresolved album descriptions ({len(gaps)})")
    gap_lines.append("")
    if not gaps:
        gap_lines.append("All flagged albums resolved to a trustworthy source.")
    else:
        for g in gaps:
            gap_lines.append(
                f"- **{g['title']}** / {g['artist']} ({g['year']}) — `{g['id']}`"
            )
            gap_lines.append(f"  - {g['note']}")
            gap_lines.append(f"  - Current head: {g['current_dna_head']!r}")
    gap_lines.append("")

    if existing_gaps_md and "Data Gaps — S3" not in existing_gaps_md:
        GAPS_PATH.write_text(
            existing_gaps_md.rstrip() + "\n\n" + "\n".join(gap_lines), encoding="utf-8"
        )
    else:
        GAPS_PATH.write_text("\n".join(gap_lines), encoding="utf-8")

    print(f"\nrewrote: {len(rewritten)}")
    print(f"gaps: {len(gaps)}")
    print(f"rewrite log: {REWRITE_LOG.relative_to(ROOT)}")
    print(f"gaps: {GAPS_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

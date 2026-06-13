#!/usr/bin/env python3
"""
Phase 2 prep: assemble evidence packs for judge agents.

Each pack = up to 25 items, each item pairing OUR content (the claims under
verification) with the cached external evidence from fetch_ground_truth.py.
Judges never see the raw cache; packs trim evidence to what a verdict needs.

Output: scripts/integrity/out/packs/{artists,albums}_NN.json
        scripts/integrity/out/packs/index.json  (pack -> item ids, for the
        dispatcher and for completeness checks during aggregation)

Items whose cache entry is missing or errored are still packed (with
evidence nulls) so the judge issues an explicit no_evidence verdict —
nothing silently drops out of the audit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "src" / "data"
CACHE = Path(__file__).resolve().parent / "cache"
PACKS = Path(__file__).resolve().parent / "out" / "packs"

PACK_SIZE = 25
ALBUM_WIKI_TRIM = 4500
ARTIST_WIKI_TRIM = 7000
CANDIDATE_HEAD = 500
TRACKS_CAP = 40


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def cached(kind: str, item_id: str) -> dict[str, Any] | None:
    p = CACHE / kind / f"{item_id}.json"
    if not p.exists():
        return None
    rec = load(p)
    return None if "error" in rec else rec


def trim_wiki(page: dict[str, Any] | None, cap: int) -> dict[str, Any] | None:
    if not page or not page.get("extract"):
        return None
    return {
        "requestedTitle": page.get("requestedTitle"),
        "resolvedTitle": page.get("resolvedTitle"),
        "shortDescription": page.get("shortDescription"),
        "extract": page["extract"][:cap],
    }


def trim_candidates(cands: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out = []
    for c in cands or []:
        if not c.get("extract"):
            continue
        out.append(
            {
                "resolvedTitle": c.get("resolvedTitle"),
                "shortDescription": c.get("shortDescription"),
                "extractHead": c["extract"][:CANDIDATE_HEAD],
            }
        )
    return out


def album_item(
    album: dict[str, Any],
    detail: dict[str, Any],
    mb: dict[str, Any] | None,
    wiki: dict[str, Any] | None,
) -> dict[str, Any]:
    det = detail.get(album["id"]) or {}
    release = (mb or {}).get("release")
    if release and release.get("tracks"):
        release = {**release, "tracks": release["tracks"][:TRACKS_CAP]}
    mb_evidence = None
    if mb:
        mb_evidence = {
            "method": mb.get("method"),
            "topArtistSimilarity": mb.get("topArtistSimilarity"),
            "release": release,
        }
        if not release:
            mb_evidence["searchCandidates"] = mb.get("searchCandidates")
    wiki_evidence = None
    if wiki:
        wiki_evidence = {
            "resolution": wiki.get("resolution"),
            "storedUrl": wiki.get("storedUrl"),
            "page": trim_wiki(wiki.get("page"), ALBUM_WIKI_TRIM),
        }
        if wiki.get("resolution") == "opensearch":
            wiki_evidence["candidates"] = trim_candidates(wiki.get("candidates"))
    return {
        "id": album["id"],
        "kind": "album",
        "ours": {
            "title": album["title"],
            "artist": album["artist"],
            "year": album.get("year"),
            "label": album.get("label"),
            "albumDNA": album.get("albumDNA"),
            "keyTracks": det.get("keyTracks"),
            "wikipediaUrl": det.get("wikipedia"),
        },
        "evidence": {"musicbrainz": mb_evidence, "wikipedia": wiki_evidence},
    }


def artist_item(
    artist: dict[str, Any],
    detail: dict[str, Any],
    cache_rec: dict[str, Any] | None,
) -> dict[str, Any]:
    det = detail.get(artist["id"]) or {}
    wiki_evidence = None
    if cache_rec:
        wiki_evidence = {
            "resolution": cache_rec.get("resolution"),
            "storedUrl": cache_rec.get("storedUrl"),
            "page": trim_wiki(cache_rec.get("page"), ARTIST_WIKI_TRIM),
        }
        if cache_rec.get("resolution") == "opensearch":
            wiki_evidence["candidates"] = trim_candidates(cache_rec.get("candidates"))
    return {
        "id": artist["id"],
        "kind": "artist",
        "ours": {
            "name": artist["name"],
            "birthYear": artist.get("birthYear"),
            "deathYear": artist.get("deathYear"),
            "instruments": artist.get("instruments"),
            "bio": det.get("bio"),
            "wikipediaUrl": det.get("wikipedia"),
        },
        "evidence": {"wikipedia": wiki_evidence},
    }


def write_packs(items: list[dict[str, Any]], prefix: str) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for n in range(0, len(items), PACK_SIZE):
        chunk = items[n : n + PACK_SIZE]
        name = f"{prefix}_{n // PACK_SIZE:02d}.json"
        (PACKS / name).write_text(
            json.dumps(chunk, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        index[name] = [c["id"] for c in chunk]
    return index


def main() -> int:
    albums = load(DATA / "albums.json")
    artists = load(DATA / "artists.json")
    albums_detail = load(DATA / "albumsDetail.json")
    artists_detail = load(DATA / "artistsDetail.json")
    PACKS.mkdir(parents=True, exist_ok=True)

    album_items = [
        album_item(
            a,
            albums_detail,
            cached("albums_mb", a["id"]),
            cached("albums_wiki", a["id"]),
        )
        for a in albums
    ]
    artist_items = [
        artist_item(a, artists_detail, cached("artists", a["id"])) for a in artists
    ]

    index = {}
    index.update(write_packs(artist_items, "artists"))
    index.update(write_packs(album_items, "albums"))
    (PACKS / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    no_mb = sum(1 for i in album_items if not i["evidence"]["musicbrainz"])
    no_mb_release = sum(
        1
        for i in album_items
        if i["evidence"]["musicbrainz"]
        and not i["evidence"]["musicbrainz"].get("release")
    )
    no_wiki_album = sum(
        1 for i in album_items if not (i["evidence"]["wikipedia"] or {}).get("page")
    )
    no_wiki_artist = sum(
        1 for i in artist_items if not (i["evidence"]["wikipedia"] or {}).get("page")
    )
    print(
        f"packs: {len(index)} files, {len(album_items)} albums + {len(artist_items)} artists"
    )
    print(
        f"albums without MB cache: {no_mb}; with MB but no confident release: {no_mb_release}"
    )
    print(f"albums without wiki page evidence: {no_wiki_album}")
    print(f"artists without wiki page evidence: {no_wiki_artist}")
    return 0


if __name__ == "__main__":
    main()

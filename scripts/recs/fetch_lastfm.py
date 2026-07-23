"""Last.fm fetcher: enriches the taste profile with similarity edges, curated
tag-album seeds, and per-artist genre tags. Stage 3 of the offline recs
pipeline (parallel to Discogs).

Consumes cache/taste_profile.json (stage 2). Produces cache/lastfm.json:
  - similar: top-30 affinity artists -> their Last.fm "similar artist" edges
  - tag_albums: 12 curated jazz tags -> top albums per tag
  - artist_tags: every artist appearing above -> their top-10 Last.fm tags
    (this is the contract _build_styles() in build_taste_profile.py reads --
    key = common.norm(artist name), value = list of lowercased tag strings)

Every HTTP call goes through common.cached_get_json (disk-cached,
rate-limited) -- a rerun after the cache is warm costs zero API calls.

Run: python3 -m scripts.recs.fetch_lastfm
"""

import os
import sys
from collections import Counter

import requests

from scripts.recs import common

API_BASE = "https://ws.audioscrobbler.com/2.0/"
BUCKET = "lastfm"
MIN_INTERVAL = 0.3

TOP_N_ARTISTS = 30
SIMILAR_LIMIT = 30
TOPALBUMS_LIMIT = 100
TOPTAGS_CAP = 10
PROGRESS_EVERY = 50

TAGS = [
    "spiritual jazz",
    "hard bop",
    "post-bop",
    "soul jazz",
    "jazz fusion",
    "avant-garde jazz",
    "free jazz",
    "modal jazz",
    "jazz guitar",
    "organ trio",
    "japanese jazz",
    "ecm",
]

OUTPUT_PATH = common.CACHE / "lastfm.json"


# --- pure helpers ---


def top_tags(tags: list[dict]) -> list[str]:
    """Lowercase every tag name, cap at the top TOPTAGS_CAP in API order --
    artist.gettoptags already returns them count-descending, so unbounded
    lists would drown the style profile in junk like 'seen live'."""
    return [t["name"].lower() for t in tags[:TOPTAGS_CAP]]


def coerce_match(value) -> float:
    """Last.fm returns similarity 'match' as a string ('0.87') -- store float."""
    return float(value)


def is_soft_error(parsed: dict) -> bool:
    """Last.fm often answers HTTP 200 with a JSON error body instead of an
    HTTP error status (e.g. artist not found)."""
    return "error" in parsed


def _build_tag_album_entry(album: dict) -> dict:
    artist_name = album.get("artist", {}).get("name", "")
    title = album.get("name", "")
    return {
        "artist": artist_name,
        "title": title,
        "norm_key": common.norm_key(artist_name, title),
    }


def _dedupe_target_names(name_lists: list[list[str]], stats: Counter) -> list[str]:
    """Deduped union of artist names across multiple lists, keyed by
    common.norm() (first-seen display name wins). common.norm() strips CJK
    entirely, and every downstream join is norm-keyed, so an empty-norm name
    is dropped here -- before any gettoptags call -- and counted."""
    seen: dict[str, str] = {}
    for names in name_lists:
        for name in names:
            key = common.norm(name)
            if not key:
                stats["artist_tags_skipped_empty_norm"] += 1
                continue
            seen.setdefault(key, name)
    return list(seen.values())


# --- Last.fm HTTP ---


def _get(params: dict) -> dict:
    query = {"format": "json", "api_key": os.environ["LASTFM_API_KEY"], **params}
    return common.cached_get_json(
        BUCKET, API_BASE, params=query, min_interval=MIN_INTERVAL
    )


# --- similar-artist sweep (top 30 affinity artists) ---


def sweep_similar(artists: list[dict], stats: Counter) -> dict[str, list[dict]]:
    similar: dict[str, list[dict]] = {}
    for entry in artists[:TOP_N_ARTISTS]:
        name = entry["name"]
        key = common.norm(name)
        if not key:
            stats["similar_skipped_empty_norm"] += 1
            print(f"skip similar (empty norm): {name}")
            continue

        try:
            data = _get(
                {"method": "artist.getsimilar", "artist": name, "limit": SIMILAR_LIMIT}
            )
        except requests.HTTPError:
            stats["similar_skipped_error"] += 1
            print(f"skip similar (HTTP error): {name}")
            continue

        if is_soft_error(data):
            stats["similar_skipped_not_found"] += 1
            print(f"skip similar (not found): {name}")
            continue

        raw = data.get("similarartists", {}).get("artist", [])
        similar[key] = [
            {"name": a["name"], "match": coerce_match(a["match"])} for a in raw
        ]
        stats["similar_swept"] += 1

    return similar


# --- tag-album sweep (12 curated jazz tags) ---


def sweep_tag_albums(stats: Counter) -> dict[str, list[dict]]:
    tag_albums: dict[str, list[dict]] = {}
    for tag in TAGS:
        try:
            data = _get(
                {"method": "tag.gettopalbums", "tag": tag, "limit": TOPALBUMS_LIMIT}
            )
        except requests.HTTPError:
            stats["tag_albums_skipped_error"] += 1
            print(f"skip tag_albums (HTTP error): {tag}")
            tag_albums[tag] = []
            continue

        if is_soft_error(data):
            stats["tag_albums_skipped_not_found"] += 1
            print(f"skip tag_albums (not found): {tag}")
            tag_albums[tag] = []
            continue

        raw = data.get("albums", {}).get("album", [])
        tag_albums[tag] = [_build_tag_album_entry(a) for a in raw]
        stats["tag_albums_swept"] += 1

    return tag_albums


# --- artist-tags sweep (deduped union of similar + tag_albums artists) ---


def _target_artist_names(
    similar: dict[str, list[dict]], tag_albums: dict[str, list[dict]], stats: Counter
) -> list[str]:
    similar_names = [edge["name"] for edges in similar.values() for edge in edges]
    tag_album_names = [
        entry["artist"] for entries in tag_albums.values() for entry in entries
    ]
    return _dedupe_target_names([similar_names, tag_album_names], stats)


def sweep_artist_tags(names: list[str], stats: Counter) -> dict[str, list[str]]:
    artist_tags: dict[str, list[str]] = {}
    for name in names:
        _bump_progress(stats)
        try:
            data = _get({"method": "artist.gettoptags", "artist": name})
        except requests.HTTPError:
            stats["artist_tags_skipped_error"] += 1
            print(f"skip artist_tags (HTTP error): {name}")
            continue

        if is_soft_error(data):
            stats["artist_tags_skipped_not_found"] += 1
            print(f"skip artist_tags (not found): {name}")
            continue

        raw = data.get("toptags", {}).get("tag", [])
        artist_tags[common.norm(name)] = top_tags(raw)
        stats["artist_tags_swept"] += 1

    return artist_tags


# --- progress + summary ---


def _bump_progress(stats: Counter) -> None:
    stats["artist_tags_processed"] += 1
    if stats["artist_tags_processed"] % PROGRESS_EVERY == 0:
        print(f"... {stats['artist_tags_processed']} artist_tags processed")


def _print_summary(
    similar: dict, tag_albums: dict, artist_tags: dict, stats: Counter
) -> None:
    total_albums = sum(len(v) for v in tag_albums.values())
    avg_per_tag = round(total_albums / len(TAGS))
    print(
        f"similar: {len(similar)} artists | "
        f"tag_albums: {len(TAGS)} tags × ~{avg_per_tag} | "
        f"artist_tags: {len(artist_tags)} | "
        f"api_calls: {common.http_stats['api_calls']} | "
        f"cache_hits: {common.http_stats['cache_hits']}"
    )
    print(
        "skipped -- similar: "
        f"empty_norm={stats['similar_skipped_empty_norm']} "
        f"not_found={stats['similar_skipped_not_found']} "
        f"error={stats['similar_skipped_error']} | "
        "tag_albums: "
        f"not_found={stats['tag_albums_skipped_not_found']} "
        f"error={stats['tag_albums_skipped_error']} | "
        "artist_tags: "
        f"empty_norm={stats['artist_tags_skipped_empty_norm']} "
        f"not_found={stats['artist_tags_skipped_not_found']} "
        f"error={stats['artist_tags_skipped_error']}"
    )
    sample = similar.get("grant green", [])
    if sample:
        names = ", ".join(s["name"] for s in sample[:5])
        print(f"\nsample similar (grant green): {names}")


# --- main ---


def main() -> None:
    common.load_env()
    if not os.environ.get("LASTFM_API_KEY"):
        print("LASTFM_API_KEY missing -- add it to .env", file=sys.stderr)
        sys.exit(1)

    profile_path = common.CACHE / "taste_profile.json"
    if not profile_path.exists():
        print(
            "cache/taste_profile.json not found -- run: "
            "python3 -m scripts.recs.build_taste_profile",
            file=sys.stderr,
        )
        sys.exit(1)

    profile = common.load_json(profile_path)
    stats: Counter = Counter()

    similar = sweep_similar(profile["artists"], stats)
    tag_albums = sweep_tag_albums(stats)
    target_names = _target_artist_names(similar, tag_albums, stats)
    artist_tags = sweep_artist_tags(target_names, stats)

    common.CACHE.mkdir(parents=True, exist_ok=True)
    common.save_json(
        OUTPUT_PATH,
        {"similar": similar, "tag_albums": tag_albums, "artist_tags": artist_tags},
    )

    _print_summary(similar, tag_albums, artist_tags, stats)


if __name__ == "__main__":
    main()

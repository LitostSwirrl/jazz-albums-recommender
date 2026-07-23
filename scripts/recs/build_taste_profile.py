"""Taste profile builder: reduces cache/spotify_library.json into a compact,
scored taste profile. Stage 2 of the offline recs pipeline.

Consumes cache/spotify_library.json (stage 1) + src/data/albums.json (catalog).
Produces cache/taste_profile.json: per-artist affinity scores, label counts,
style (genre) distribution, and which catalog/Spotify albums are already owned.

Run: python3 -m scripts.recs.build_taste_profile
"""

import difflib
import sys
from collections import Counter

from scripts.recs import common

CATALOG_PATH = common.ROOT / "src" / "data" / "albums.json"

W_SAVED_ALBUM = 5.0
W_SAVED_TRACK = 1.0
W_FOLLOWED = 2.0
RANGE_WEIGHT = {"short_term": 1.5, "medium_term": 1.25, "long_term": 1.0}
FUZZY_TITLE_THRESHOLD = 0.92


# --- affinity ---


def affinity_scores(lib: dict) -> dict[str, dict]:
    """Per-artist affinity, keyed by common.norm(artist name). Saved albums and
    saved tracks credit EVERY listed artist. Top-artist entries add rank points
    ((51-rank)/50*10*RANGE_WEIGHT[range]) per listening range they appear in.
    Followed artists get a flat bonus."""
    scores: dict[str, dict] = {}

    def entry(name: str) -> dict:
        key = common.norm(name)
        if key not in scores:
            scores[key] = {
                "name": name,
                "saved_albums": 0,
                "saved_tracks": 0,
                "followed": False,
                "score": 0.0,
            }
        return scores[key]

    for album in lib["saved_albums"]:
        for artist in album["artists"]:
            e = entry(artist)
            e["saved_albums"] += 1
            e["score"] += W_SAVED_ALBUM

    for track in lib["saved_tracks"]:
        for artist in track["artists"]:
            e = entry(artist)
            e["saved_tracks"] += 1
            e["score"] += W_SAVED_TRACK

    for term, weight in RANGE_WEIGHT.items():
        for item in lib["top_artists"][term]:
            e = entry(item["name"])
            e["score"] += (51 - item["rank"]) / 50 * 10 * weight

    for artist in lib["followed_artists"]:
        e = entry(artist["name"])
        e["followed"] = True
        e["score"] += W_FOLLOWED

    for e in scores.values():
        e["score"] = round(e["score"], 2)

    return scores


# --- ownership matching ---


def _catalog_spotify_index(catalog: list) -> dict[str, dict]:
    index = {}
    for album in catalog:
        spotify_id = common.spotify_album_id(album.get("spotifyUrl"))
        if spotify_id:
            index[spotify_id] = album
    return index


def _catalog_key_index(catalog: list) -> dict[str, dict]:
    return {common.norm_key(a["artist"], a["title"]): a for a in catalog}


def _catalog_by_artist(catalog: list) -> dict[str, list]:
    by_artist: dict[str, list] = {}
    for album in catalog:
        by_artist.setdefault(common.norm(album["artist"]), []).append(album)
    return by_artist


def _fuzzy_match(title: str, candidates: list) -> dict | None:
    norm_t = common.norm_title(title)
    best, best_ratio = None, 0.0
    for candidate in candidates:
        ratio = difflib.SequenceMatcher(
            None, norm_t, common.norm_title(candidate["title"])
        ).ratio()
        if ratio > best_ratio:
            best, best_ratio = candidate, ratio
    return best if best_ratio >= FUZZY_TITLE_THRESHOLD else None


def match_owned(saved_albums: list, catalog: list) -> tuple[dict, list]:
    """Match saved albums to catalog entries in order: spotify id (from
    spotifyUrl) -> exact norm_key (any listed artist) -> same norm(artist) +
    fuzzy title (ratio >= FUZZY_TITLE_THRESHOLD). Returns
    (owned: {spotify_album_ids, catalog_ids, norm_keys}, unmatched_saved_albums)."""
    spotify_index = _catalog_spotify_index(catalog)
    key_index = _catalog_key_index(catalog)
    artist_index = _catalog_by_artist(catalog)

    spotify_album_ids: list[str] = []
    catalog_ids: list[str] = []
    norm_keys: list[str] = []
    unmatched: list[dict] = []

    for album in saved_albums:
        matched = spotify_index.get(album["spotify_id"])

        if matched is None:
            for artist in album["artists"]:
                key = common.norm_key(artist, album["title"])
                if key in key_index:
                    matched = key_index[key]
                    break

        if matched is None:
            for artist in album["artists"]:
                candidates = artist_index.get(common.norm(artist), [])
                matched = _fuzzy_match(album["title"], candidates)
                if matched:
                    break

        if matched is None:
            unmatched.append({"title": album["title"], "artists": album["artists"]})
            continue

        spotify_album_ids.append(album["spotify_id"])
        catalog_ids.append(matched["id"])
        norm_keys.append(common.norm_key(matched["artist"], matched["title"]))

    owned = {
        "spotify_album_ids": spotify_album_ids,
        "catalog_ids": catalog_ids,
        "norm_keys": norm_keys,
    }
    return owned, unmatched


# --- profile assembly ---


def _build_artists_list(scores: dict) -> list:
    ranked = sorted(scores.items(), key=lambda kv: kv[1]["score"], reverse=True)
    return [
        {
            "name": data["name"],
            "norm": norm_name,
            "score": data["score"],
            "rank": rank,
            "saved_albums": data["saved_albums"],
            "saved_tracks": data["saved_tracks"],
            "followed": data["followed"],
        }
        for rank, (norm_name, data) in enumerate(ranked, start=1)
    ]


def _matched_catalog_entries(catalog_ids: list, catalog: list) -> list:
    by_id = {a["id"]: a for a in catalog}
    return [by_id[cid] for cid in catalog_ids]


def _build_labels(matched_albums: list) -> list:
    counts = Counter(a["label"] for a in matched_albums)
    return [
        {"name": name, "count": count}
        for name, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def _build_styles(matched_albums: list, scores: dict) -> tuple[list, str]:
    """Genre-tag distribution (weight = share) from owned catalog albums,
    enriched with Last.fm artist tags -- weighted by that artist's normalized
    affinity -- when cache/lastfm.json exists."""
    tag_weight: Counter = Counter()
    for album in matched_albums:
        for tag in album["genres"]:
            tag_weight[tag] += 1

    lastfm_path = common.CACHE / "lastfm.json"
    source = "catalog"

    if lastfm_path.exists():
        source = "catalog+lastfm"
        artist_tags = common.load_json(lastfm_path)["artist_tags"]
        max_score = max((data["score"] for data in scores.values()), default=0)
        if max_score:
            for artist_norm, tags in artist_tags.items():
                if artist_norm not in scores:
                    continue
                weight = scores[artist_norm]["score"] / max_score
                for tag in tags:
                    tag_weight[tag] += weight

    total = sum(tag_weight.values())
    if not total:
        return [], source

    styles = [
        {"tag": tag, "weight": round(count / total, 2)}
        for tag, count in tag_weight.most_common()
    ]
    return styles, source


def _print_report(
    artists: list, labels: list, unmatched: list, styles_source: str
) -> None:
    print(
        f"artists: {len(artists)} | labels: {len(labels)} | "
        f"unmatched saved albums: {len(unmatched)}"
    )
    print(f"styles source: {styles_source}")

    print("\ntop 15 artists:")
    for a in artists[:15]:
        followed = " [followed]" if a["followed"] else ""
        print(
            f"  #{a['rank']:<3} {a['name']:<28} score={a['score']:<7} "
            f"albums={a['saved_albums']} tracks={a['saved_tracks']}{followed}"
        )

    print("\nlabels:")
    for label in labels:
        print(f"  {label['name']}: {label['count']}")

    print(f"\nunmatched saved albums ({len(unmatched)}):")
    for u in unmatched:
        print(f"  {u['title']} -- {', '.join(u['artists'])}")


def main() -> None:
    lib_path = common.CACHE / "spotify_library.json"
    if not lib_path.exists():
        print(
            "cache/spotify_library.json not found -- run: "
            "python3 -m scripts.recs.sync_spotify",
            file=sys.stderr,
        )
        sys.exit(1)

    lib = common.load_json(lib_path)
    catalog = common.load_json(CATALOG_PATH)

    scores = affinity_scores(lib)
    owned, unmatched = match_owned(lib["saved_albums"], catalog)
    matched_albums = _matched_catalog_entries(owned["catalog_ids"], catalog)

    artists = _build_artists_list(scores)
    labels = _build_labels(matched_albums)
    styles, styles_source = _build_styles(matched_albums, scores)

    profile = {
        "artists": artists,
        "labels": labels,
        "styles": styles,
        "owned": owned,
        "unmatched_saved_albums": unmatched,
    }

    common.CACHE.mkdir(parents=True, exist_ok=True)
    common.save_json(common.CACHE / "taste_profile.json", profile)

    _print_report(artists, labels, unmatched, styles_source)


if __name__ == "__main__":
    main()

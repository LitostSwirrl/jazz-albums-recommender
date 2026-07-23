"""Discogs fetcher: sweeps the top affinity artists' and scene labels'
discographies for community rating/haves/wants and personnel credits. Stage 3
of the offline recs pipeline.

Consumes cache/taste_profile.json (stage 2). Produces cache/discogs.json:
a deduped, year-spread sample of each swept artist's/label's catalog, with
release detail fetched only for candidates not already owned. Every HTTP call
goes through common.cached_get_json (disk-cached, rate-limited) -- a rerun
after the cache is warm costs zero API calls.

Run: python3 -m scripts.recs.fetch_discogs
"""

import os
import re
import sys
from collections import Counter

import requests

from scripts.recs import common

API_BASE = "https://api.discogs.com"
BUCKET = "discogs"
MIN_INTERVAL = 1.1

TOP_N_ARTISTS = 40
MASTERS_PER_ARTIST = 12
MIN_LABEL_AFFINITY_COUNT = 3
RELEASES_PER_LABEL = 60
FIXED_SCENE_LABELS = [
    "Blue Note",
    "Impulse!",
    "ECM Records",
    "Strata-East",
    "CTI Records",
    "Black Jazz Records",
    "India Navigation",
    "Prestige",
    "Riverside",
    "SteepleChase",
    "Enja",
    "Three Blind Mice",
]

OUTPUT_PATH = common.CACHE / "discogs.json"
PROGRESS_EVERY = 10

# A profile/fixed-list label name can exact-norm-match an unrelated Discogs
# homonym instead of the intended canonical label -- verified for this one
# case: Discogs label 34094 "Riverside Records" is the real 1950s-60s
# American jazz label (its /releases sample includes Wes Montgomery, Bill
# Evans Trio, Thelonious Monk Quartet, Chet Baker); plain q="Riverside" has
# no cleanup-free exact match against "Riverside Records", so the homonym
# "Riverside (2)" -- a Polish progressive-rock band's own label imprint --
# won instead after clean_discogs_name's marker-stripping. Contamination was
# verified isolated to this one case (all other 17 labels + 37 matched
# artists resolved via a clean, unmarked exact match), so a single alias is
# the whole fix -- not a general homonym-preference heuristic.
LABEL_QUERY_ALIASES = {
    "Riverside": "Riverside Records",
}

# Discogs disambiguation markers on entity names (artists, labels, credits):
# a trailing homonym index "(2)" (this is the 2nd profile with this exact
# name) and/or a trailing name-variant marker "*" (this credit line is a
# variant spelling of a linked canonical entity). Only digit-only parens are
# the homonym marker -- a real descriptive parenthetical like "Tribe
# (Chicago)" must survive.
_HOMONYM_SUFFIX_RE = re.compile(r"\s*\(\d+\)\s*$")


def clean_discogs_name(name: str) -> str:
    """Strip trailing Discogs '(2)' homonym and '*' variant markers, in
    either order/combination. Applied to artist AND label search results,
    release/listing artist fields, release label names, and credit names --
    before display, norm(), or norm_key(). (Scoped to artists in the task's
    controller resolution, extended here to labels too: the same convention
    and the same norm() mismatch risk apply to both -- see _find_label.)"""
    cleaned = (name or "").strip()
    while True:
        next_cleaned = _HOMONYM_SUFFIX_RE.sub("", cleaned).strip()
        if next_cleaned.endswith("*"):
            next_cleaned = next_cleaned[:-1].strip()
        if next_cleaned == cleaned:
            return cleaned
        cleaned = next_cleaned


# --- pure helpers ---


def year_spread(entries: list[dict], n: int) -> list[dict]:
    """Pick up to n entries spread evenly across the year range covered by
    `entries` (by position in year-sorted order, not just earliest-first --
    first and last dated entries are always included). Entries with a
    missing/falsy `year` sort last and are used only to fill slots left over
    after the dated entries are exhausted -- they never crash the picker."""
    if n <= 0:
        return []

    dated = sorted((e for e in entries if e.get("year")), key=lambda e: e["year"])
    undated = [e for e in entries if not e.get("year")]

    if len(dated) <= n:
        picked = list(dated)
    elif n == 1:
        picked = dated[:1]
    else:
        indices = sorted({round(i * (len(dated) - 1) / (n - 1)) for i in range(n)})
        picked = [dated[i] for i in indices]

    remaining = n - len(picked)
    if remaining > 0:
        picked.extend(undated[:remaining])
    return picked


def _filter_main_role(entries: list[dict]) -> list[dict]:
    """Keep 'Main' role credits (leader/primary) plus entries with no role
    key at all -- label-release listings carry no role field whatsoever
    (verified against a live response), only artist-release listings do."""
    return [e for e in entries if e.get("role", "Main") == "Main"]


def dedupe_releases(releases: list[dict]) -> list[dict]:
    """Dedupe by discogs_release_id, keeping the first-encountered entry
    (and its `via`) -- the same release surfaces via multiple sweeps, e.g. a
    Blue Note label sweep overlapping an artist sweep."""
    seen: set[int] = set()
    deduped = []
    for r in releases:
        rid = r["discogs_release_id"]
        if rid in seen:
            continue
        seen.add(rid)
        deduped.append(r)
    return deduped


# --- Discogs HTTP ---


def _headers() -> dict:
    return {
        "Authorization": f"Discogs token={os.environ['DISCOGS_TOKEN']}",
        "User-Agent": "SmackCatsRecs/1.0",
    }


def _get(url: str, params: dict | None = None) -> dict:
    return common.cached_get_json(
        BUCKET, url, params=params, headers=_headers(), min_interval=MIN_INTERVAL
    )


def _find_artist(name: str) -> tuple[int, str] | None:
    """Search Discogs for `name`; return (id, clean matched name) for the
    first exact-norm match, or None. Never falls back to a fuzzy/first
    result -- a wrong artist poisons the candidate pool."""
    norm_target = common.norm(name)
    data = _get(f"{API_BASE}/database/search", {"q": name, "type": "artist"})
    for result in data.get("results", []):
        candidate = clean_discogs_name(result.get("title", ""))
        if common.norm(candidate) == norm_target:
            return result["id"], candidate
    return None


def _label_query(name: str) -> str:
    """Map a label name to its Discogs search query via LABEL_QUERY_ALIASES,
    passing through unchanged when no alias applies."""
    return LABEL_QUERY_ALIASES.get(name, name)


def _find_label(name: str) -> tuple[int, str] | None:
    """Same exact-norm-match contract as _find_artist, for labels. Discogs
    uses the identical '(2)'/'*' disambiguation convention on label names
    (e.g. a hypothetical 'ECM (2)') -- left uncleaned, common.norm() keeps
    the digit ('ecm 2') and a real match would be missed, so the same
    cleanup applies here too. Searches and matches against _label_query(name)
    (see LABEL_QUERY_ALIASES), not the raw name."""
    query_name = _label_query(name)
    norm_target = common.norm(query_name)
    data = _get(f"{API_BASE}/database/search", {"q": query_name, "type": "label"})
    for result in data.get("results", []):
        candidate = clean_discogs_name(result.get("title", ""))
        if common.norm(candidate) == norm_target:
            return result["id"], candidate
    return None


# --- release-detail extraction ---


def _extract_labels(release: dict) -> list[str]:
    seen: set[str] = set()
    names = []
    for entry in release.get("labels", []):
        name = clean_discogs_name(entry.get("name", ""))
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _extract_credits(release: dict) -> list[str]:
    """Union of release-level extraartists and every track's extraartists,
    cleaned + deduped, order = first appearance. Uses the canonical `name`
    field (not `anv`, the release-specific credited spelling) so the same
    person matches consistently across releases."""
    raw_names = [c.get("name", "") for c in release.get("extraartists", [])]
    for track in release.get("tracklist", []):
        raw_names.extend(c.get("name", "") for c in track.get("extraartists", []))

    seen: set[str] = set()
    credits = []
    for raw in raw_names:
        cleaned = clean_discogs_name(raw)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            credits.append(cleaned)
    return credits


def _release_primary_artist(release: dict) -> str:
    """Discogs primary credit order: artists[0].name, cleaned. norm_key is
    the cross-source join key downstream (Task 9 merges rym/discogs/lastfm
    candidates by it; ownership matching uses it), so the emitted artist
    must reflect the release's own real primary credit -- not whichever
    artist's/label's sweep happened to surface it (a co-credited album can
    be swept via a secondary artist's discography, e.g. Pharoah Sanders'
    sweep surfacing a release Discogs credits primarily to Alice Coltrane)."""
    artists = release.get("artists", [])
    if not artists:
        return ""
    return clean_discogs_name(artists[0].get("name", ""))


def _build_release_entry(release: dict, via: str) -> dict:
    community = release.get("community", {})
    rating = community.get("rating", {})
    artist_name = _release_primary_artist(release)
    return {
        "norm_key": common.norm_key(artist_name, release.get("title", "")),
        "artist": artist_name,
        "title": release.get("title", ""),
        "year": release.get("year"),
        "labels": _extract_labels(release),
        "rating": rating.get("average"),
        "rating_count": rating.get("count"),
        "haves": community.get("have"),
        "wants": community.get("want"),
        "credits": _extract_credits(release),
        "discogs_release_id": release["id"],
        "via": via,
    }


# --- artist sweep ---


def _fetch_artist_release(
    candidate: dict, artist_name: str, owned_keys: set[str], stats: Counter[str]
) -> dict | None:
    """Two owned gates, not one: the cheap pre-detail check below (swept
    artist's name + listing title) catches most owned releases without a
    fetch; it can miss when Discogs' real primary credit (only known once
    release detail is in hand) differs from the swept artist -- so the
    entry's actual norm_key is rechecked after _build_release_entry too."""
    title = candidate.get("title", "")
    if common.norm_key(artist_name, title) in owned_keys:
        stats["owned_skipped"] += 1
        return None

    try:
        master = _get(f"{API_BASE}/masters/{candidate['id']}")
        release_id = master.get("main_release")
        if release_id is None:
            stats["release_errors"] += 1
            print(f"skip release (no main_release): {artist_name} -- {title}")
            return None
        release = _get(f"{API_BASE}/releases/{release_id}")
    except requests.HTTPError:
        stats["release_errors"] += 1
        print(f"skip release (HTTP error): {artist_name} -- {title}")
        return None

    entry = _build_release_entry(release, f"artist:{artist_name}")
    if entry["norm_key"] in owned_keys:
        stats["owned_skipped"] += 1
        return None
    return entry


def sweep_artists(
    artists: list[dict], owned_keys: set[str], stats: Counter[str]
) -> list[dict]:
    releases: list[dict] = []
    for entry in artists[:TOP_N_ARTISTS]:
        name = entry["name"]
        if not common.norm(name):
            stats["artists_skipped_empty_norm"] += 1
            print(f"skip artist (empty norm): {name}")
            continue

        try:
            found = _find_artist(name)
            if found is None:
                stats["artists_skipped_no_match"] += 1
                print(f"skip artist (no exact match): {name}")
                continue
            artist_id, clean_name = found

            listing = _get(
                f"{API_BASE}/artists/{artist_id}/releases",
                {"sort": "year", "per_page": 100},
            )
        except requests.HTTPError:
            stats["artists_skipped_error"] += 1
            print(f"skip artist (HTTP error): {name}")
            continue

        masters = [r for r in listing.get("releases", []) if r.get("type") == "master"]
        picked = year_spread(_filter_main_role(masters), MASTERS_PER_ARTIST)
        stats["artists_swept"] += 1

        for candidate in picked:
            release_entry = _fetch_artist_release(
                candidate, clean_name, owned_keys, stats
            )
            if release_entry:
                releases.append(release_entry)
                _bump_progress(stats)

    return releases


# --- label sweep ---


def _resolve_labels(
    profile_labels: list[dict], stats: Counter[str]
) -> list[tuple[int, str]]:
    """Union of profile labels with affinity count >= MIN_LABEL_AFFINITY_COUNT
    and FIXED_SCENE_LABELS; each name resolved to a Discogs label id via
    exact-norm search (skip + count on no match/HTTP error); deduped by
    resolved id so e.g. profile 'ECM' and fixed-list 'ECM Records' -- if they
    resolve to the same label -- sweep once. Sorted iteration for a
    deterministic first-encountered winner."""
    names = {
        e["name"] for e in profile_labels if e["count"] >= MIN_LABEL_AFFINITY_COUNT
    }
    names |= set(FIXED_SCENE_LABELS)

    resolved: dict[int, str] = {}
    for name in sorted(names):
        try:
            found = _find_label(name)
        except requests.HTTPError:
            stats["labels_skipped_error"] += 1
            print(f"skip label (HTTP error): {name}")
            continue
        if found is None:
            stats["labels_skipped_no_match"] += 1
            print(f"skip label (no exact match): {name}")
            continue
        label_id, clean_name = found
        resolved.setdefault(label_id, clean_name)

    return list(resolved.items())


def _fetch_label_release(
    candidate: dict, label_name: str, owned_keys: set[str], stats: Counter[str]
) -> dict | None:
    """Same two-gate contract as _fetch_artist_release -- see its docstring."""
    artist_name = clean_discogs_name(candidate.get("artist", ""))
    title = candidate.get("title", "")
    if common.norm_key(artist_name, title) in owned_keys:
        stats["owned_skipped"] += 1
        return None

    try:
        release = _get(f"{API_BASE}/releases/{candidate['id']}")
    except requests.HTTPError:
        stats["release_errors"] += 1
        print(f"skip release (HTTP error): {artist_name} -- {title}")
        return None

    entry = _build_release_entry(release, f"label:{label_name}")
    if entry["norm_key"] in owned_keys:
        stats["owned_skipped"] += 1
        return None
    return entry


def sweep_labels(
    resolved_labels: list[tuple[int, str]], owned_keys: set[str], stats: Counter[str]
) -> list[dict]:
    releases: list[dict] = []
    for label_id, label_name in resolved_labels:
        try:
            listing = _get(f"{API_BASE}/labels/{label_id}/releases", {"per_page": 100})
        except requests.HTTPError:
            stats["labels_skipped_error"] += 1
            print(f"skip label (HTTP error): {label_name}")
            continue

        picked = year_spread(
            _filter_main_role(listing.get("releases", [])), RELEASES_PER_LABEL
        )
        stats["labels_swept"] += 1

        for candidate in picked:
            release_entry = _fetch_label_release(
                candidate, label_name, owned_keys, stats
            )
            if release_entry:
                releases.append(release_entry)
                _bump_progress(stats)

    return releases


# --- progress + summary ---


def _bump_progress(stats: Counter[str]) -> None:
    stats["releases_fetched"] += 1
    if stats["releases_fetched"] % PROGRESS_EVERY == 0:
        print(f"... {stats['releases_fetched']} releases fetched")


def _print_summary(releases: list[dict], stats: Counter[str]) -> None:
    artists_n = sum(1 for r in releases if r["via"].startswith("artist:"))
    labels_n = sum(1 for r in releases if r["via"].startswith("label:"))
    print(
        f"releases: {len(releases)} (artists: {artists_n}, labels: {labels_n}) | "
        f"api_calls: {common.http_stats['api_calls']} | "
        f"cache_hits: {common.http_stats['cache_hits']}"
    )
    print(
        f"bounds used: artists swept {stats['artists_swept']} x "
        f"{MASTERS_PER_ARTIST} masters cap | labels swept {stats['labels_swept']} x "
        f"{RELEASES_PER_LABEL} releases cap"
    )
    print(
        "skipped -- artists: "
        f"empty_norm={stats['artists_skipped_empty_norm']} "
        f"no_match={stats['artists_skipped_no_match']} "
        f"error={stats['artists_skipped_error']} | "
        "labels: "
        f"no_match={stats['labels_skipped_no_match']} "
        f"error={stats['labels_skipped_error']} | "
        "releases: "
        f"owned_skipped={stats['owned_skipped']} "
        f"error={stats['release_errors']}"
    )
    print("\nsample releases (spot-check against discogs.com):")
    for r in releases[:3]:
        print(
            f"  {r['artist']} / {r['title']} | rating={r['rating']} "
            f"(n={r['rating_count']}) | haves={r['haves']} wants={r['wants']} "
            f"| discogs_release_id={r['discogs_release_id']}"
        )


# --- main ---


def main() -> None:
    common.load_env()
    if not os.environ.get("DISCOGS_TOKEN"):
        print("DISCOGS_TOKEN missing -- add it to .env", file=sys.stderr)
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
    owned_keys = set(profile["owned"]["norm_keys"])
    stats: Counter[str] = Counter()

    artist_releases = sweep_artists(profile["artists"], owned_keys, stats)
    resolved_labels = _resolve_labels(profile["labels"], stats)
    label_releases = sweep_labels(resolved_labels, owned_keys, stats)

    all_releases = dedupe_releases(artist_releases + label_releases)

    common.CACHE.mkdir(parents=True, exist_ok=True)
    common.save_json(OUTPUT_PATH, {"releases": all_releases})

    _print_summary(all_releases, stats)


if __name__ == "__main__":
    main()

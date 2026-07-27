"""Deterministic recommendation scoring with cache-traceable reasons and a
zero-hallucination integrity gate (Stage 4 of the recs pipeline).

Consumes every source cache under scripts/recs/cache/ plus the site catalog
(src/data/albums.json, artists.json) and emits src/data/recommendations.json
and src/data/library.json (the Plan-2 UI contract).

There is NO model anywhere here (12-Factor: own your control flow). Scoring is
pure arithmetic over cached records; every emitted reason stores the cache
record it came from, and at the end of the build the integrity check reloads
each referenced record FRESH and re-renders it through the SAME render_reason
used to generate it -- any mismatch fails the whole build loud.

Run from repo root: python3 -m scripts.recs.build_recommendations
"""

import math
import random
import sys
import urllib.parse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime

from scripts.recs import common

# --- scoring constants (tuned at Task 11) ---
W_AFFINITY, W_QUALITY, W_NOVELTY = 0.45, 0.40, 0.15
AF = {"artist": 0.35, "sideman": 0.20, "label": 0.15, "similar": 0.20, "tags": 0.10}
CORROBORATION_BONUS = 0.05  # per quality source beyond the first, cap +0.15
MEGA_CANON_HAVES = 25000  # discogs haves above this -> novelty halved
NEW_TO_SITE_BONUS = 0.1
SHELF_SIZE = 12
TOP_PICKS = 8
EMIT_LIMIT = 300
SAMPLE_SEED = 1972  # fixed seed for the reproducible eyeball-sample print

# reason-ordering tie-break: fixed type priority after contribution
TYPE_PRIORITY = {
    "artist": 0,
    "chart": 1,
    "similar": 2,
    "label": 3,
    "sideman": 4,
    "pitchfork": 5,
    "reddit": 6,
}


# ======================================================================
# render_reason -- THE single renderer, shared by generation AND the checker
# ======================================================================


def render_reason(rtype: str, data: dict) -> str:
    """Render a reason to its exact display string. Pure. Used by both the
    build (to generate detail) and the integrity checker (to reconstruct it),
    so a faithful reason always re-renders identically."""
    if rtype == "artist":
        return f"{data['artist']} is your #{data['rank']} artist"
    if rtype == "sideman":
        return f"{data['name1']} and {data['name2']} appear on albums you saved"
    if rtype == "label":
        return f"On {data['label']} — you have {data['n']} albums from this label"
    if rtype == "similar":
        return f"Last.fm: similar to {data['top_artist']} (your #{data['rank']})"
    if rtype == "chart":
        return (
            f"#{data['rank']} in RYM {data['chart']} chart "
            f"({data['rating']} from {data['count']} ratings)"
        )
    if rtype == "pitchfork":
        suffix = ", Best New Music" if data["bnm"] else ""
        return f"Pitchfork {data['score']}{suffix} ({data['year']})"
    if rtype == "reddit":
        return f"Mentioned in {data['n']} r/jazz threads"
    raise ValueError(f"unknown reason type: {rtype}")


# ======================================================================
# shared derivation helpers (used by generation AND reconstruction so they
# cannot drift -- this is what makes the integrity gate meaningful)
# ======================================================================


def profile_by_norm(profile: dict) -> dict:
    """{artist norm -> profile entry}, skipping empty norms (CJK names that
    can never match a candidate). Last-wins on duplicate norm, deterministically."""
    return {a["norm"]: a for a in profile["artists"] if a["norm"]}


def label_count_map(profile: dict) -> dict:
    """{label name -> saved-album count}. Last-wins on duplicate name."""
    return {label["name"]: label["count"] for label in profile["labels"]}


def discogs_representative(releases: list[dict]) -> dict:
    """One representative release per norm_key: max haves, then rating_count,
    then lowest release id -- a single deterministic pick keeps refs clean."""
    return max(
        releases,
        key=lambda r: (r["haves"], r["rating_count"], -r["discogs_release_id"]),
    )


def pitchfork_pick(reviews: list[dict]) -> dict | None:
    """One review per norm_key: max score, then lexicographically smallest url."""
    if not reviews:
        return None
    return min(reviews, key=lambda r: (-r["score"], r["url"]))


def reddit_pick(mentions: list[dict]) -> dict | None:
    """One mention per norm_key: max count (first-seen on tie, file order)."""
    if not mentions:
        return None
    return max(mentions, key=lambda m: m["count"])


def best_chart_appearance(norm_key: str, rym: dict):
    """The candidate's best RYM chart appearance as (slug, entry): max rating,
    tie -> min rank, then slug ascending. Returns None if it charts nowhere."""
    best = None
    for slug in sorted(rym["charts"]):
        for entry in rym["charts"][slug]:
            if entry["norm_key"] != norm_key:
                continue
            key = (entry["rating"], -entry["rank"])
            if best is None or key > best[0]:
                best = (key, slug, entry)
    if best is None:
        return None
    return best[1], best[2]


def chart_data_for(norm_key: str, slug: str, rym: dict) -> dict | None:
    """The render-data dict for a candidate's appearance in one named chart.
    Both generation and reconstruction derive chart reason data from here."""
    for entry in rym["charts"].get(slug, []):
        if entry["norm_key"] == norm_key:
            return {
                "rank": entry["rank"],
                "chart": slug,
                "rating": entry["rating"],
                "count": entry["rating_count"],
            }
    return None


def shared_sidemen(release: dict | None, profile: dict) -> list[tuple[str, int]]:
    """Profile artists (rank <= 50) whose norm appears in the release credits,
    ordered by rank asc then norm asc. Names are the profile display names."""
    if not release:
        return []
    credit_norms = {common.norm(c) for c in release.get("credits", [])}
    out = [
        (a["name"], a["rank"])
        for a in profile["artists"]
        if a["norm"] and a["norm"] in credit_norms and a["rank"] <= 50
    ]
    out.sort(key=lambda t: (t[1], common.norm(t[0])))
    return out


def best_similar_seed(cand_artist: str, lastfm: dict, profile: dict):
    """Over top-30 affinity seeds, the strongest Last.fm similarity to the
    candidate artist as (match, seed_key, top_artist_name, seed_rank), or None.
    Tie -> min seed rank, then seed_key ascending."""
    cand_norm = common.norm(cand_artist)
    if not cand_norm:
        return None
    by_norm = profile_by_norm(profile)
    matches = []
    for seed_key, sims in lastfm["similar"].items():
        seed_entry = by_norm.get(seed_key)
        if not seed_entry or seed_entry["rank"] > 30:
            continue
        best_m = None
        for sim in sims:
            if common.norm(sim["name"]) == cand_norm:
                if best_m is None or sim["match"] > best_m:
                    best_m = sim["match"]
        if best_m is not None:
            matches.append((best_m, seed_entry["rank"], seed_key, seed_entry["name"]))
    if not matches:
        return None
    matches.sort(key=lambda t: (-t[0], t[1], t[2]))
    match, rank, seed_key, name = matches[0]
    return match, seed_key, name, rank


# ======================================================================
# component math
# ======================================================================


def corroboration_bonus(k: int) -> float:
    """+0.05 per quality source beyond the first, capped at +0.15."""
    if k < 1:
        return 0.0
    return min(0.15, CORROBORATION_BONUS * (k - 1))


def compute_quality(values: list[float]) -> float:
    """mean(present quality values) + corroboration_bonus(count). Not clamped
    -- Q may exceed 1.0 via the bonus (only novelty is clamped)."""
    if not values:
        return 0.0
    return sum(values) / len(values) + corroboration_bonus(len(values))


def compute_novelty(repr_release: dict | None, in_catalog: bool) -> float:
    """Owned candidates are already excluded upstream. Base 1.0; halved if the
    representative release is mega-canon; +NEW_TO_SITE_BONUS if not on the
    site; clamped to [0, 1]."""
    n = 1.0
    if repr_release and repr_release["haves"] > MEGA_CANON_HAVES:
        n *= 0.5
    if not in_catalog:
        n += NEW_TO_SITE_BONUS
    return min(1.0, max(0.0, n))


# ======================================================================
# candidate assembly
# ======================================================================


def assemble_candidates(
    discogs: dict,
    rym: dict,
    lastfm: dict,
    pitchfork: dict,
    reddit: dict,
    owned: set,
) -> dict:
    """Merge every source's records by norm_key into one candidate per distinct
    key, gathering a single representative record per source. Owned candidates
    (norm_key in owned) are dropped here -- never scored, never emitted."""
    rel_groups = defaultdict(list)
    for release in discogs["releases"]:
        rel_groups[release["norm_key"]].append(release)

    pf_groups = defaultdict(list)
    for review in pitchfork["reviews"]:
        pf_groups[review["norm_key"]].append(review)

    rd_groups = defaultdict(list)
    for mention in reddit["mentions"]:
        rd_groups[mention["norm_key"]].append(mention)

    tag_by_key = {}
    for items in lastfm["tag_albums"].values():
        for item in items:
            tag_by_key.setdefault(item["norm_key"], item)

    rym_keys = set()
    for entries in rym["charts"].values():
        for entry in entries:
            rym_keys.add(entry["norm_key"])

    all_keys = (
        set(rel_groups) | rym_keys | set(pf_groups) | set(rd_groups) | set(tag_by_key)
    )

    candidates = {}
    for norm_key in all_keys:
        if norm_key in owned:
            continue
        candidates[norm_key] = {
            "norm_key": norm_key,
            "discogs": (
                discogs_representative(rel_groups[norm_key])
                if norm_key in rel_groups
                else None
            ),
            "pitchfork": pitchfork_pick(pf_groups.get(norm_key, [])),
            "reddit": reddit_pick(rd_groups.get(norm_key, [])),
            "tag_album": tag_by_key.get(norm_key),
            "in_rym": norm_key in rym_keys,
        }
    return candidates


@dataclass
class Context:
    """Everything scoring needs, derived once from the loaded caches."""

    profile: dict
    lastfm: dict
    rym: dict
    catalog_index: dict
    by_norm: dict
    label_map: dict
    top50_norms: set
    top15_tags: set
    max_affinity: float


def build_context(
    profile: dict, lastfm: dict, catalog_index: dict, rym: dict
) -> Context:
    return Context(
        profile=profile,
        lastfm=lastfm,
        rym=rym,
        catalog_index=catalog_index,
        by_norm=profile_by_norm(profile),
        label_map=label_count_map(profile),
        top50_norms={
            a["norm"] for a in profile["artists"] if a["norm"] and a["rank"] <= 50
        },
        top15_tags={s["tag"] for s in profile["styles"][:15]},
        max_affinity=max((a["score"] for a in profile["artists"]), default=1.0),
    )


def _search_url(artist: str, title: str) -> str:
    return "https://open.spotify.com/search/" + urllib.parse.quote(f"{artist} {title}")


def display_fields(raw: dict, ctx: Context):
    """Resolve (artist, title, year, in_catalog, catalog, coverUrl, spotifyUrl).
    inCatalog -> canonical site data; else first present source in fixed
    precedence discogs -> rym(best) -> pitchfork -> reddit -> tag_albums."""
    norm_key = raw["norm_key"]
    catalog = ctx.catalog_index.get(norm_key)
    if catalog:
        artist, title = catalog["artist"], catalog["title"]
        spotify = catalog.get("spotifyUrl") or _search_url(artist, title)
        return (
            artist,
            title,
            catalog.get("year"),
            True,
            catalog,
            catalog.get("coverUrl"),
            spotify,
        )

    src = None
    if raw["discogs"]:
        src = raw["discogs"]
    elif raw["in_rym"]:
        appearance = best_chart_appearance(norm_key, ctx.rym)
        if appearance:
            src = appearance[1]
    if src is None and raw["pitchfork"]:
        src = raw["pitchfork"]
    if src is None and raw["reddit"]:
        src = raw["reddit"]
    if src is None and raw["tag_album"]:
        src = raw["tag_album"]

    artist, title = src["artist"], src["title"]
    return artist, title, src.get("year"), False, None, None, _search_url(artist, title)


def build_badges(raw: dict, rym: dict) -> dict:
    """Every present source's badge -- independent of the <=3 reason cap."""
    badges = {}
    appearance = best_chart_appearance(raw["norm_key"], rym)
    if appearance:
        slug, _entry = appearance
        cd = chart_data_for(raw["norm_key"], slug, rym)
        badges["rym"] = {"chart": slug, "rank": cd["rank"], "rating": cd["rating"]}
    if raw["discogs"]:
        badges["discogs"] = {
            "rating": raw["discogs"]["rating"],
            "haves": raw["discogs"]["haves"],
        }
    if raw["pitchfork"]:
        badges["pitchfork"] = {
            "score": raw["pitchfork"]["score"],
            "bnm": raw["pitchfork"]["bnm"],
        }
    if raw["reddit"]:
        badges["reddit"] = {"mentions": raw["reddit"]["count"]}
    return badges


def _mk_reason(rtype: str, data: dict, src: str, ref: str, contribution: float) -> dict:
    return {
        "type": rtype,
        "detail": render_reason(rtype, data),
        "src": src,
        "ref": ref,
        "_contribution": contribution,
    }


def score_candidate(raw: dict, ctx: Context) -> dict:
    """Score one candidate and build its reasons + badges. Pure over ctx."""
    norm_key = raw["norm_key"]
    artist, title, year, in_catalog, catalog, cover, spotify = display_fields(raw, ctx)
    art_norm = common.norm(artist)
    repr_release = raw["discogs"]

    # --- affinity components ---
    pa = ctx.by_norm.get(art_norm)
    artist_c = (pa["score"] / ctx.max_affinity) if pa else 0.0

    if repr_release:
        credit_norms = {common.norm(c) for c in repr_release["credits"]}
        sideman_c = min(1.0, len(credit_norms & ctx.top50_norms) / 5)
    else:
        sideman_c = 0.0
    shared_list = shared_sidemen(repr_release, ctx.profile)

    if repr_release:
        cand_labels = list(repr_release["labels"])
    elif in_catalog and catalog.get("label"):
        cand_labels = [catalog["label"]]
    else:
        cand_labels = []
    best_label, best_count = None, 0
    for label in cand_labels:
        count = ctx.label_map.get(label, 0)
        if count > best_count:
            best_count, best_label = count, label
    label_c = min(1.0, best_count / 8)

    sim = best_similar_seed(artist, ctx.lastfm, ctx.profile)
    similar_c = sim[0] if sim else 0.0

    cand_tags = set(ctx.lastfm["artist_tags"].get(art_norm, []))
    union = cand_tags | ctx.top15_tags
    tags_c = (len(cand_tags & ctx.top15_tags) / len(union)) if union else 0.0

    affinity = (
        AF["artist"] * artist_c
        + AF["sideman"] * sideman_c
        + AF["label"] * label_c
        + AF["similar"] * similar_c
        + AF["tags"] * tags_c
    )

    # --- quality components ---
    quality = {}
    appearance = best_chart_appearance(norm_key, ctx.rym)
    chart_slug = appearance[0] if appearance else None
    chart_cd = chart_data_for(norm_key, chart_slug, ctx.rym) if chart_slug else None
    if chart_cd:
        rc = chart_cd["count"]
        quality["rym"] = (
            (chart_cd["rating"] / 5) * min(1.0, math.log10(rc) / 4) if rc > 0 else 0.0
        )
    if repr_release:
        haves = max(repr_release["haves"], 1)
        quality["discogs"] = (repr_release["rating"] / 5) * min(
            1.0, math.log10(haves) / 4
        )
    if raw["pitchfork"]:
        review = raw["pitchfork"]
        quality["pitchfork"] = review["score"] / 10 + (0.05 if review["bnm"] else 0.0)
    if raw["reddit"]:
        quality["reddit"] = min(1.0, raw["reddit"]["count"] / 8)
    quality_score = compute_quality(list(quality.values()))

    novelty = compute_novelty(repr_release, in_catalog)

    score = round(
        100 * (W_AFFINITY * affinity + W_QUALITY * quality_score + W_NOVELTY * novelty),
        1,
    )

    # --- reasons (built only when the threshold is met) ---
    reasons = []
    if pa and pa["rank"] <= 30:
        reasons.append(
            _mk_reason(
                "artist",
                {"artist": pa["name"], "rank": pa["rank"]},
                "taste_profile",
                pa["norm"],
                W_AFFINITY * AF["artist"] * artist_c,
            )
        )
    if len(shared_list) >= 2:
        reasons.append(
            _mk_reason(
                "sideman",
                {"name1": shared_list[0][0], "name2": shared_list[1][0]},
                "discogs",
                f"release:{repr_release['discogs_release_id']}",
                W_AFFINITY * AF["sideman"] * sideman_c,
            )
        )
    if best_count >= 3:
        reasons.append(
            _mk_reason(
                "label",
                {"label": best_label, "n": best_count},
                "taste_profile",
                best_label,
                W_AFFINITY * AF["label"] * label_c,
            )
        )
    if sim and sim[0] >= 0.4:
        reasons.append(
            _mk_reason(
                "similar",
                {"top_artist": sim[2], "rank": sim[3]},
                "lastfm",
                sim[1],
                W_AFFINITY * AF["similar"] * similar_c,
            )
        )
    if chart_cd:
        reasons.append(
            _mk_reason("chart", chart_cd, "rym", chart_slug, W_QUALITY * quality["rym"])
        )
    if raw["pitchfork"] and raw["pitchfork"]["score"] >= 7.5:
        review = raw["pitchfork"]
        reasons.append(
            _mk_reason(
                "pitchfork",
                {
                    "score": review["score"],
                    "bnm": review["bnm"],
                    "year": review["year"],
                },
                "pitchfork",
                norm_key,
                W_QUALITY * quality["pitchfork"],
            )
        )
    if raw["reddit"] and raw["reddit"]["count"] >= 3:
        reasons.append(
            _mk_reason(
                "reddit",
                {"n": raw["reddit"]["count"]},
                "reddit",
                norm_key,
                W_QUALITY * quality["reddit"],
            )
        )

    reasons.sort(
        key=lambda r: (-r["_contribution"], TYPE_PRIORITY[r["type"]], r["detail"])
    )
    reasons = reasons[:3]
    for reason in reasons:
        del reason["_contribution"]

    return {
        "norm_key": norm_key,
        "id": catalog["id"]
        if in_catalog
        else "ext-" + common.slugify(f"{artist} {title}"),
        "title": title,
        "artist": artist,
        "year": year,
        "coverUrl": cover,
        "inCatalog": in_catalog,
        "catalogId": catalog["id"] if in_catalog else None,
        "spotifyUrl": spotify,
        "score": score,
        "reasons": reasons,
        "badges": build_badges(raw, ctx.rym),
        "_labels": cand_labels,
        "_tags": cand_tags,
        "_credits": repr_release["credits"] if repr_release else [],
        "_source_count": sum(
            1 for k in ("discogs", "pitchfork", "reddit", "tag_album") if raw[k]
        )
        + (1 if raw["in_rym"] else 0),
    }


def select_top(scored: list[dict], limit: int) -> list[dict]:
    """Top `limit` by score desc, norm_key asc for a deterministic tie-break."""
    return sorted(scored, key=lambda c: (-c["score"], c["norm_key"]))[:limit]


# ======================================================================
# shelves
# ======================================================================


def _shelf_match(cand: dict, matcher: dict) -> bool:
    if "labels" in matcher and any(
        label in matcher["labels"] for label in cand["_labels"]
    ):
        return True
    if "tags" in matcher and (cand["_tags"] & set(matcher["tags"])):
        return True
    if "players" in matcher:
        players = set(matcher["players"])
        if cand["artist"] in players or (set(cand["_credits"]) & players):
            return True
    return False


def build_shelves(emitted: list[dict], shelf_defs: list[dict]) -> list[dict]:
    shelves = []
    for shelf in shelf_defs:
        matcher = shelf.get("matcher", {})
        matches = [c for c in emitted if _shelf_match(c, matcher)]
        matches.sort(key=lambda c: (-c["score"], c["norm_key"]))
        items = [c["id"] for c in matches[:SHELF_SIZE]]
        if len(items) < 5:
            print(
                f"WARNING: shelf '{shelf['id']}' has only {len(items)} items (<5)",
                file=sys.stderr,
            )
        shelves.append(
            {
                "id": shelf["id"],
                "title": shelf["title"],
                "blurb": shelf["blurb"],
                "type": shelf["type"],
                "items": items,
            }
        )
    return shelves


# ======================================================================
# integrity check -- the zero-hallucination gate (never soften)
# ======================================================================


def reconstruct_data(reason: dict, album: dict, norm_key: str, fresh) -> dict | None:
    """Rebuild a reason's render-data by reloading its referenced cache record
    FRESH (via `fresh`) and re-deriving through the SAME shared helpers used to
    generate it. Returns None if the record no longer supports the reason."""
    rtype, ref = reason["type"], reason["ref"]
    if rtype == "chart":
        rym = fresh("rym")
        if ref not in rym["charts"]:
            return None
        return chart_data_for(norm_key, ref, rym)
    if rtype == "pitchfork":
        pf = fresh("pitchfork")
        review = pitchfork_pick([r for r in pf["reviews"] if r["norm_key"] == ref])
        if not review:
            return None
        return {"score": review["score"], "bnm": review["bnm"], "year": review["year"]}
    if rtype == "reddit":
        rd = fresh("reddit")
        mention = reddit_pick([m for m in rd["mentions"] if m["norm_key"] == ref])
        return {"n": mention["count"]} if mention else None
    if rtype == "label":
        lm = label_count_map(fresh("taste_profile"))
        return {"label": ref, "n": lm[ref]} if ref in lm else None
    if rtype == "artist":
        entry = profile_by_norm(fresh("taste_profile")).get(ref)
        return {"artist": entry["name"], "rank": entry["rank"]} if entry else None
    if rtype == "sideman":
        dg = fresh("discogs")
        rid = int(ref.split(":", 1)[1])
        release = next(
            (r for r in dg["releases"] if r["discogs_release_id"] == rid), None
        )
        if not release:
            return None
        pairs = shared_sidemen(release, fresh("taste_profile"))
        return {"name1": pairs[0][0], "name2": pairs[1][0]} if len(pairs) >= 2 else None
    if rtype == "similar":
        res = best_similar_seed(
            album["artist"], fresh("lastfm"), fresh("taste_profile")
        )
        if not res:
            return None
        match, seed_key, top_artist, rank = res
        if seed_key != ref or match < 0.4:
            return None
        return {"top_artist": top_artist, "rank": rank}
    return None


def run_integrity_check(emitted: list[dict]) -> None:
    """For every emitted reason, reconstruct it from a FRESH reload of its cache
    record and assert it re-renders to the exact same string. Any mismatch ->
    print the offending album+reason and sys.exit(1). Caches are loaded from
    disk once per run (independent of the build's in-memory dicts)."""
    loaded = {}

    def fresh(name: str) -> dict:
        if name not in loaded:
            loaded[name] = common.load_json(common.CACHE / f"{name}.json")
        return loaded[name]

    for album in emitted:
        norm_key = common.norm_key(album["artist"], album["title"])
        for reason in album["reasons"]:
            data = reconstruct_data(reason, album, norm_key, fresh)
            if data is None or render_reason(reason["type"], data) != reason["detail"]:
                print(f"INTEGRITY FAIL: {album['id']} :: {reason}")
                sys.exit(1)


# ======================================================================
# output assembly
# ======================================================================


def _public(cand: dict) -> dict:
    return {
        k: cand[k]
        for k in (
            "id",
            "title",
            "artist",
            "year",
            "coverUrl",
            "inCatalog",
            "catalogId",
            "spotifyUrl",
            "score",
            "reasons",
            "badges",
        )
    }


def assemble_recommendations(
    emitted: list[dict], shelves: list[dict], generated: str
) -> dict:
    return {
        "generated": generated,
        "topPicks": [c["id"] for c in emitted[:TOP_PICKS]],
        "shelves": shelves,
        "albums": {c["id"]: _public(c) for c in emitted},
    }


def assemble_library(
    spotify: dict, profile: dict, artists: list[dict], generated: str
) -> dict:
    artist_id_map = {common.norm(a["name"]): a["id"] for a in artists}
    top_artists = []
    for entry in sorted(profile["artists"], key=lambda a: a["rank"]):
        if not entry["norm"]:
            continue
        top_artists.append(
            {
                "name": entry["name"],
                "artistId": artist_id_map.get(entry["norm"]),
                "score": entry["score"],
            }
        )
        if len(top_artists) >= 20:
            break
    owned = profile["owned"]
    return {
        "generated": generated,
        "counts": {
            "savedAlbums": len(spotify["saved_albums"]),
            "savedTracks": len(spotify["saved_tracks"]),
            "matchedCatalog": len(owned["catalog_ids"]),
        },
        "topArtists": top_artists,
        "ownedCatalogIds": owned["catalog_ids"],
    }


# ======================================================================
# summary + sample stdout
# ======================================================================


def _print_summary(
    scored: list[dict], emitted: list[dict], shelves: list[dict]
) -> None:
    total = len(scored)
    catalog = sum(1 for c in scored if c["inCatalog"])
    external = total - catalog
    hist = dict(sorted(Counter(c["_source_count"] for c in emitted).items()))
    shelf_counts = ", ".join(f"{s['id']}→{len(s['items'])}" for s in shelves)
    print(
        f"candidates: {total} (catalog: {catalog}, external: {external}) | "
        f"emitted: {len(emitted)} | sources per emitted: {hist} | "
        f"shelves: {shelf_counts} | integrity: PASS"
    )


def _print_samples(emitted: list[dict]) -> None:
    rng = random.Random(SAMPLE_SEED)
    print("\n--- 10 sample recs (eyeball review) ---")
    for cand in rng.sample(emitted, min(10, len(emitted))):
        print(f"[{cand['score']}] {cand['artist']} - {cand['title']}")
        for reason in cand["reasons"]:
            print(f"    - {reason['detail']}  ({reason['src']}:{reason['ref']})")


# ======================================================================
# main
# ======================================================================


def main() -> None:
    discogs = common.load_json(common.CACHE / "discogs.json")
    rym = common.load_json(common.CACHE / "rym.json")
    lastfm = common.load_json(common.CACHE / "lastfm.json")
    pitchfork = common.load_json(common.CACHE / "pitchfork.json")
    reddit = common.load_json(common.CACHE / "reddit.json")
    profile = common.load_json(common.CACHE / "taste_profile.json")
    spotify = common.load_json(common.CACHE / "spotify_library.json")
    albums = common.load_json(common.ROOT / "src" / "data" / "albums.json")
    artists = common.load_json(common.ROOT / "src" / "data" / "artists.json")
    shelf_defs = common.load_json(common.ROOT / "scripts" / "recs" / "shelves.json")

    catalog_index = {common.norm_key(a["artist"], a["title"]): a for a in albums}
    owned = set(profile["owned"]["norm_keys"])
    ctx = build_context(profile, lastfm, catalog_index, rym)

    raw = assemble_candidates(discogs, rym, lastfm, pitchfork, reddit, owned)
    scored = [score_candidate(raw[norm_key], ctx) for norm_key in sorted(raw)]
    emitted = select_top(scored, EMIT_LIMIT)
    shelves = build_shelves(emitted, shelf_defs)

    # integrity gate runs BEFORE anything is written -- a hallucinated reason
    # must never reach disk.
    run_integrity_check(emitted)

    generated = datetime.now().astimezone().isoformat()
    common.save_json(
        common.ROOT / "src" / "data" / "recommendations.json",
        assemble_recommendations(emitted, shelves, generated),
    )
    common.save_json(
        common.ROOT / "src" / "data" / "library.json",
        assemble_library(spotify, profile, artists, generated),
    )

    _print_summary(scored, emitted, shelves)
    _print_samples(emitted)


if __name__ == "__main__":
    main()

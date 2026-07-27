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
import re
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
SHELF_PER_ARTIST = 3  # max albums per artist within one shelf
TOP_PICKS = 8
TOP_PICKS_PER_ARTIST = 2  # max albums per artist among the 8 hero picks
EMIT_LIMIT = 300
EMIT_PER_ARTIST = 4  # max albums per artist in the emitted list
SAMPLE_SEED = 1972  # fixed seed for the reproducible eyeball-sample print

# compilations / box-sets / "various" are poor picks for a players' guide --
# dropped from the pool after scoring (never in topPicks, shelves, or albums).
COMP_ARTISTS = {"various", "various artists", "unknown", "unknown artist"}
COMP_TITLE_RE = re.compile(
    r"\b(complete|anthology|best of|greatest hits|collection|compilation|"
    r"outtakes|alternates|box set|bootleg series|the prestige recordings|"
    r"legendary .{0,40} albums|essential|retrospective|rarities)\b",
    re.IGNORECASE,
)
# real LPs whose titles trip COMP_TITLE_RE -- the allowlist always wins.
COMP_ALLOWLIST = {
    "don cherry::complete communion",
    "chet baker::plays the best of lerner loewe",
    "chet baker::chet baker plays the best of lerner and loewe",
    "george russell::ezzthetics keepnews collection",
    "rashied ali::duo exchange complete sessions",
}
# box sets no safe title pattern catches -- a denylist entry beats a broad
# pattern, because a pattern that also kills real LPs is worse than a missed box.
BOX_DENYLIST = {
    "miles davis::final tour the bootleg series vol 6",
    "charles mingus::jazz in detroit strata concert gallery 46 selden",
    "bill evans::treasures solo trio orchestra recordings from denmark 19651969",
    "eric dolphy::musical prophet the expanded 1963 new york studio sessions",
    "sonny rollins::go west the contemporary records albums",
    "ornette coleman::round trip ornette coleman on blue note",
}
SINGLE_MARKER = " / "  # 78-rpm A-side/B-side titles, not albums

# cap-key canonicalization: "Last, First" -> "First Last", then a trailing
# ensemble word goes, so spelling variants share one per-artist allowance.
LAST_FIRST_RE = re.compile(r"^([^,]+),\s*([^,]+)$")
ENSEMBLE_SUFFIX_RE = re.compile(
    r"\s+(group|trio|quartet|quintet|sextet|septet|octet|band|orchestra|ensemble)$"
)

# edition-duplicate merge: leading article, then artist-name prefix, then all
# spaces come off the title so punctuation variants land on one key.
ARTICLE_RE = re.compile(r"^(the |a |an )")

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
# chart reasons reconstruct against the album's OWN norm_key (every other type
# reconstructs from its stored ref), so they cannot ride an edition merge over
# to the kept record without breaking the integrity gate.
NORM_KEY_BOUND_REASONS = {"chart"}


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


def usable_artists(profile: dict) -> list[dict]:
    """Profile artists with a non-empty norm, re-ranked 1-based in their existing
    rank order (already score-desc). This is the SAME set assemble_library
    displays, so a reason's #N equals the artist's topArtists position and the
    affinity ceiling is a real (matchable) artist, not an empty-norm CJK name.
    Keeps name/norm/score plus the fresh rank; the stored rank is discarded."""
    ordered = sorted(
        (a for a in profile["artists"] if a["norm"]),
        key=lambda a: (a["rank"], a["norm"]),
    )
    return [
        {"name": a["name"], "norm": a["norm"], "score": a["score"], "rank": i}
        for i, a in enumerate(ordered, start=1)
    ]


def profile_by_norm(profile: dict) -> dict:
    """{artist norm -> re-ranked usable entry}, skipping empty norms (CJK names
    that can never match a candidate). Last-wins on duplicate norm, matching the
    rank order. Ranks are the fresh 1-based ranks from usable_artists."""
    return {a["norm"]: a for a in usable_artists(profile)}


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


def usable_reviews(pitchfork: dict) -> list[dict]:
    """Pitchfork reviews minus box reviews. A URL carrying more than one album
    record where every record shares one score is a single review of a box set:
    that score is evidence about the box, not about each album inside it, so it
    is neither a quality signal nor a year source. Differing scores mean the
    reviewer graded each album -- a genuine multi-album review, kept.
    Generation AND the integrity gate both read reviews through here."""
    by_url = defaultdict(list)
    for review in pitchfork["reviews"]:
        by_url[review["url"]].append(review)
    return [
        review
        for review in pitchfork["reviews"]
        if not (
            len(by_url[review["url"]]) > 1
            and len({r["score"] for r in by_url[review["url"]]}) == 1
        )
    ]


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
        for a in usable_artists(profile)
        if a["norm"] in credit_norms and a["rank"] <= 50
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
    for review in usable_reviews(pitchfork):
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
    usable = usable_artists(profile)
    return Context(
        profile=profile,
        lastfm=lastfm,
        rym=rym,
        catalog_index=catalog_index,
        by_norm=profile_by_norm(profile),
        label_map=label_count_map(profile),
        top50_norms={a["norm"] for a in usable if a["rank"] <= 50},
        top15_tags={s["tag"] for s in profile["styles"][:15]},
        max_affinity=max((a["score"] for a in usable), default=1.0),
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


def _reason_rank(reason: dict) -> tuple:
    """The reason ordering: contribution desc, then fixed type priority, then
    detail. Generation and the edition merge both sort by this, so a merged
    record's reasons rank exactly as an unmerged one's do."""
    return (-reason["_contribution"], TYPE_PRIORITY[reason["type"]], reason["detail"])


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

    # _contribution stays on the reason through the edition merge (which re-sorts
    # a union of two records' reasons by this SAME key); _public strips it.
    reasons.sort(key=_reason_rank)
    reasons = reasons[:3]

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


def cap_key(artist: str) -> str:
    """The per-artist cap key: one allowance per person, however the sources
    spell them. "Davis, Miles" -> "Miles Davis"; a trailing ensemble word comes
    off, so "Pat Metheny Group" and "Pat Metheny" share one. Cap key ONLY --
    displayed artist names are never rewritten."""
    name = " ".join(artist.split())
    match = LAST_FIRST_RE.match(name)
    if match:
        name = f"{match.group(2)} {match.group(1)}"
    return ENSEMBLE_SUFFIX_RE.sub("", common.norm(name))


def select_emitted(pool: list[dict], limit: int) -> list[dict]:
    """The emitted list: walk the pool in score order and take a candidate only
    while its artist is under EMIT_PER_ARTIST, until `limit` is reached. Without
    the cap one name can hold a sixth of the list."""
    emitted = []
    per_artist = Counter()
    for cand in select_top(pool, len(pool)):
        key = cap_key(cand["artist"])
        if per_artist[key] >= EMIT_PER_ARTIST:
            continue
        emitted.append(cand)
        per_artist[key] += 1
        if len(emitted) >= limit:
            break
    return emitted


# ======================================================================
# edition-duplicate merge
# ======================================================================


def merge_key(norm_key: str) -> str:
    """The key that unifies edition variants norm_key leaves apart: drop a
    leading article, drop a leading copy of the artist name, then drop every
    space in the title. Deliberately NOT substring containment -- that wrongly
    merges "Virtuoso" with "Virtuoso #3"."""
    artist, _, title = norm_key.partition("::")
    title = ARTICLE_RE.sub("", title)
    if title.startswith(artist + " "):
        title = title[len(artist) + 1 :]
    return f"{artist}::{title.replace(' ', '')}"


def merge_editions(pool: list[dict]) -> tuple[list[dict], list[dict]]:
    """Collapse edition duplicates. Each merge-key group keeps its highest-scored
    record (ties by norm_key) and absorbs the others' source badges and reasons;
    reasons re-sort by the same contribution ordering generation uses and keep
    the <=3 cap. Returns (pool, merge log) in the input's order."""
    groups = defaultdict(list)
    for cand in pool:
        groups[merge_key(cand["norm_key"])].append(cand)

    keepers, log = {}, []
    for key, group in groups.items():
        group = sorted(group, key=lambda c: (-c["score"], c["norm_key"]))
        keeper, absorbed = group[0], group[1:]
        if not absorbed:
            keepers[keeper["norm_key"]] = keeper
            continue

        badges = dict(keeper["badges"])
        for cand in absorbed:
            for name, badge in cand["badges"].items():
                badges.setdefault(name, badge)

        # one reason per type, strongest first: both spellings carry their own
        # reddit count, and generation never emits two reasons of one type.
        by_type = {}
        transferable = list(keeper["reasons"]) + [
            reason
            for cand in absorbed
            for reason in cand["reasons"]
            if reason["type"] not in NORM_KEY_BOUND_REASONS
        ]
        for reason in transferable:
            best = by_type.get(reason["type"])
            if best is None or _reason_rank(reason) < _reason_rank(best):
                by_type[reason["type"]] = reason
        reasons = sorted(by_type.values(), key=_reason_rank)[:3]

        keepers[keeper["norm_key"]] = {**keeper, "badges": badges, "reasons": reasons}
        log.append({"key": key, "keeper": keeper, "absorbed": absorbed})

    merged = [keepers[c["norm_key"]] for c in pool if c["norm_key"] in keepers]
    log.sort(key=lambda entry: entry["key"])
    return merged, log


def near_duplicate_pairs(albums: list[dict]) -> list[tuple[dict, dict]]:
    """Same-artist pairs where one title extends the other at a word boundary
    ("Relaxin'" / "Relaxin' with the Miles Davis Quintet"). merge_editions
    deliberately leaves these alone -- the shape is identical to genuinely
    distinct albums -- so they are reported for the human gate instead."""
    by_artist = defaultdict(list)
    for album in albums:
        artist_norm, _, title_norm = album["norm_key"].partition("::")
        by_artist[artist_norm].append((title_norm, album))

    pairs = []
    for artist_norm in sorted(by_artist):
        entries = sorted(by_artist[artist_norm], key=lambda e: e[0])
        for i, first in enumerate(entries):
            for second in entries[i + 1 :]:
                short, long = sorted([first, second], key=lambda e: len(e[0]))
                if short[0] == long[0]:
                    continue
                if merge_key(short[1]["norm_key"]) == merge_key(long[1]["norm_key"]):
                    continue
                if long[0].startswith(short[0] + " ") or long[0].endswith(
                    " " + short[0]
                ):
                    pairs.append((short[1], long[1]))
    return pairs


# ======================================================================
# exclusions
# ======================================================================


def exclusion_reason(cand: dict) -> str | None:
    """Which exclusion category drops this scored candidate, or None to keep it.
    Fixed order, so every drop lands in exactly one printed category and the
    counts add up. The allowlist outranks COMP_TITLE_RE; the denylist outranks
    everything, since it names boxes no safe pattern catches."""
    if cand["norm_key"] in BOX_DENYLIST:
        return "denylisted"
    if SINGLE_MARKER in cand["title"]:
        return "single"
    if cand["norm_key"] in COMP_ALLOWLIST:
        return None
    if cand["artist"].strip().lower() in COMP_ARTISTS:
        return "comp-artist"
    if COMP_TITLE_RE.search(cand["title"]):
        return "comp-title"
    return None


COMP_CATEGORIES = ("comp-artist", "comp-title", "denylisted")


def _is_comp(cand: dict) -> bool:
    """A scored candidate is a compilation / box-set / various-artists record.
    Singles are excluded too but counted separately (their own category)."""
    return exclusion_reason(cand) in COMP_CATEGORIES


def select_top_picks(emitted: list[dict]) -> list[str]:
    """The TOP_PICKS hero ids, greedily from emitted (already score-ordered)
    with at most TOP_PICKS_PER_ARTIST per artist so the hero row is not one name."""
    picks = []
    per_artist = Counter()
    for cand in emitted:
        key = cap_key(cand["artist"])
        if per_artist[key] >= TOP_PICKS_PER_ARTIST:
            continue
        picks.append(cand["id"])
        per_artist[key] += 1
        if len(picks) >= TOP_PICKS:
            break
    return picks


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
    if "leaders" in matcher and cand["artist"] in set(matcher["leaders"]):
        return True
    return False


def _is_leader_match(cand: dict, matcher: dict) -> bool:
    """The shelf's named players hit the candidate's OWN artist, not its credits.
    Sideman work belongs on a lineage shelf, it just should not lead it. Pure
    label/tag shelves name nobody, so every match scores the same and their
    order is untouched."""
    named = set(matcher.get("players", [])) | set(matcher.get("leaders", []))
    return cand["artist"] in named


def build_shelves(pool: list[dict], shelf_defs: list[dict]) -> list[dict]:
    """Match each shelf over the FULL scored+comp-filtered pool (not just the
    top-300 emitted), so niche scenes below the cut still fill. Greedily take up
    to SHELF_SIZE with at most SHELF_PER_ARTIST per artist so a popular shelf
    cannot collapse onto one name; leader-matches come before credit-matches,
    each group by score desc then norm_key."""
    shelves = []
    for shelf in shelf_defs:
        matcher = shelf.get("matcher", {})
        matches = [c for c in pool if _shelf_match(c, matcher)]
        matches.sort(
            key=lambda c: (
                0 if _is_leader_match(c, matcher) else 1,
                -c["score"],
                c["norm_key"],
            )
        )
        items = []
        per_artist = Counter()
        for cand in matches:
            key = cap_key(cand["artist"])
            if per_artist[key] >= SHELF_PER_ARTIST:
                continue
            items.append(cand["id"])
            per_artist[key] += 1
            if len(items) >= SHELF_SIZE:
                break
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
        review = pitchfork_pick([r for r in usable_reviews(pf) if r["norm_key"] == ref])
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


def run_integrity_check(albums: list[dict]) -> None:
    """For every reason on every album in the output set (emitted ∪ shelf items),
    reconstruct it from a FRESH reload of its cache record and assert it
    re-renders to the exact same string. Any mismatch -> print the offending
    album+reason and sys.exit(1). Caches are loaded from disk once per run
    (independent of the build's in-memory dicts)."""
    loaded = {}

    def fresh(name: str) -> dict:
        if name not in loaded:
            loaded[name] = common.load_json(common.CACHE / f"{name}.json")
        return loaded[name]

    for album in albums:
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
    out = {
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
    # _contribution is build-internal (it orders reasons through the merge)
    out["reasons"] = [
        {k: v for k, v in reason.items() if not k.startswith("_")}
        for reason in cand["reasons"]
    ]
    return out


def collect_output_albums(
    emitted: list[dict], shelves: list[dict], pool: list[dict]
) -> list[dict]:
    """The output album set: emitted ∪ every candidate referenced by a shelf,
    de-duped by id. Deterministic order: emitted (score order) first, then any
    shelf-only items in shelf-then-item order. Shelf items resolve against the
    full pool so sub-emit picks still land in the albums map."""
    by_id = {c["id"]: c for c in pool}
    seen = {c["id"] for c in emitted}
    out = list(emitted)
    for shelf in shelves:
        for item_id in shelf["items"]:
            if item_id not in seen:
                seen.add(item_id)
                out.append(by_id[item_id])
    return out


def assemble_recommendations(
    emitted: list[dict], shelves: list[dict], album_cands: list[dict], generated: str
) -> dict:
    return {
        "generated": generated,
        "topPicks": select_top_picks(emitted),
        "shelves": shelves,
        "albums": {c["id"]: _public(c) for c in album_cands},
    }


def assemble_library(
    spotify: dict, profile: dict, artists: list[dict], generated: str
) -> dict:
    artist_id_map = {common.norm(a["name"]): a["id"] for a in artists}
    top_artists = []
    # same re-ranked usable view scoring/reasons use, so a reason's #N matches
    # the artist's position here (they cannot drift).
    for entry in usable_artists(profile):
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


def _print_exclusions(dropped: dict, rescued: list[dict]) -> None:
    """List every dropped candidate to stderr grouped by category, plus the
    candidates the allowlist rescued -- both directions of the filter stay
    auditable (completeness over silent removal)."""
    for category in ("comp-artist", "comp-title", "denylisted", "single"):
        cands = dropped.get(category, [])
        print(f"--- excluded {len(cands)}: {category} ---", file=sys.stderr)
        for cand in sorted(
            cands, key=lambda c: (c["artist"].lower(), c["title"].lower())
        ):
            print(f"  {cand['artist']} - {cand['title']}", file=sys.stderr)
    print(f"--- allowlist rescued {len(rescued)} ---", file=sys.stderr)
    for cand in sorted(
        rescued, key=lambda c: (c["artist"].lower(), c["title"].lower())
    ):
        print(f"  {cand['artist']} - {cand['title']}", file=sys.stderr)


def _print_merges(log: list[dict]) -> None:
    """Every edition merge: what was kept and what folded into it."""
    print(f"--- merged {len(log)} edition-duplicate groups ---", file=sys.stderr)
    for entry in log:
        keeper = entry["keeper"]
        print(
            f"  {entry['key']}: kept '{keeper['title']}' ({keeper['score']})",
            file=sys.stderr,
        )
        for cand in entry["absorbed"]:
            print(f"      + '{cand['title']}' ({cand['score']})", file=sys.stderr)


def _print_near_duplicates(pairs: list[tuple[dict, dict]]) -> None:
    """Subtitle-extension pairs in the output that the merge rule leaves alone
    -- the human gate rules on these individually."""
    print(
        f"--- {len(pairs)} unmerged near-duplicate pairs in the output ---",
        file=sys.stderr,
    )
    for short, long in pairs:
        print(
            f"  {short['artist']}: '{short['title']}' ({short['score']}) vs "
            f"'{long['title']}' ({long['score']})",
            file=sys.stderr,
        )


def _print_summary(
    scored: list[dict],
    emitted: list[dict],
    shelves: list[dict],
    dropped: dict,
    album_cands: list[dict],
) -> None:
    total = len(scored)
    catalog = sum(1 for c in scored if c["inCatalog"])
    external = total - catalog
    hist = dict(sorted(Counter(c["_source_count"] for c in emitted).items()))
    shelf_counts = ", ".join(f"{s['id']}→{len(s['items'])}" for s in shelves)
    shelf_only = len(album_cands) - len(emitted)
    comps = sum(len(dropped.get(c, [])) for c in COMP_CATEGORIES)
    print(
        f"candidates: {total} (catalog: {catalog}, external: {external}) | "
        f"emitted: {len(emitted)} | excluded_comps: {comps} | "
        f"excluded_singles: {len(dropped.get('single', []))} | "
        f"sources per emitted: {hist} | shelves: {shelf_counts} | "
        f"albums: {len(album_cands)} ({shelf_only} shelf-only) | integrity: PASS"
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
    scored_all = [score_candidate(raw[norm_key], ctx) for norm_key in sorted(raw)]
    # drop compilations / box-sets / various / singles BEFORE emit and shelves,
    # so they never surface in topPicks, shelves, or the albums map.
    dropped = defaultdict(list)
    kept = []
    for cand in scored_all:
        category = exclusion_reason(cand)
        if category:
            dropped[category].append(cand)
        else:
            kept.append(cand)
    rescued = [c for c in kept if c["norm_key"] in COMP_ALLOWLIST]
    # then collapse edition duplicates, so one album cannot hold two slots.
    scored, merge_log = merge_editions(kept)

    emitted = select_emitted(scored, EMIT_LIMIT)
    shelves = build_shelves(scored, shelf_defs)
    album_cands = collect_output_albums(emitted, shelves, scored)

    # integrity gate runs BEFORE anything is written -- a hallucinated reason
    # must never reach disk. It covers the FULL output set (emitted ∪ shelves).
    run_integrity_check(album_cands)

    generated = datetime.now().astimezone().isoformat()
    common.save_json(
        common.ROOT / "src" / "data" / "recommendations.json",
        assemble_recommendations(emitted, shelves, album_cands, generated),
    )
    common.save_json(
        common.ROOT / "src" / "data" / "library.json",
        assemble_library(spotify, profile, artists, generated),
    )

    _print_exclusions(dropped, rescued)
    _print_merges(merge_log)
    _print_near_duplicates(near_duplicate_pairs(album_cands))
    _print_summary(scored, emitted, shelves, dropped, album_cands)
    _print_samples(emitted)


if __name__ == "__main__":
    main()

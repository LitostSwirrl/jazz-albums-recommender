"""Build the authoritative documented-gap id set for Phase 4 re-verify reconciliation.

Derived from the SAME structured sources gen_gaps.py renders into gaps.md, so the
gap set and the human-readable report can never drift. Output:
scripts/integrity/out/_gap_ids.json -- {id: {"categories": [...], "dims": [...]}}.

`dims` are the verdict dimensions in which a non-clean re-verify result is EXPECTED
(documented, not a regression):
  field:artist | field:year | field:label | field:instruments | keytracks |
  catalog_error | thin_prose | unverifiable_comp | weak_match
A non-clean verdict on a gap id is a regression ONLY if it flags a dimension NOT
listed here (e.g. the rewritten prose introduced a brand-new wrong claim).
"""

import json
import re

OUT = "scripts/integrity/out"

LEAD = re.compile(r"^([a-z0-9][a-z0-9-]*)")


def lead_id(s: str) -> str:
    m = LEAD.match(s.strip())
    if not m:
        raise ValueError(f"no leading id in {s!r}")
    return m.group(1)


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


gm = load(f"{OUT}/gaps_mechanical.json")
rr = load(f"{OUT}/research_results.json")
prose = load(f"{OUT}/repairs_prose.json")["repairs"]

gaps: dict[str, dict] = {}


def add(item_id: str, category: str, *dims: str) -> None:
    g = gaps.setdefault(item_id, {"categories": [], "dims": []})
    if category not in g["categories"]:
        g["categories"].append(category)
    for d in dims:
        if d not in g["dims"]:
            g["dims"].append(d)


# 1. catalog data errors (deletion / reattribution candidates) + the attribution conflict
CATALOG_ERRORS = [
    "blue-note-4000",
    "investigations",
    "new-orleans-joys-kid-ory",
    "the-art-of-the-trio-vol-4-nat-king-cole",
    "a-smooth-one-woody-herman",
]
for cid in CATALOG_ERRORS:
    add(cid, "catalog_error", "catalog_error")
add(
    "lullaby-of-birdland",
    "catalog_error",
    "catalog_error",
    "thin_prose",
    "field:artist",
)

# 2. field_artist -- attribution review (artist field intentionally left)
for it in gm["field_artist"]:
    add(it["id"], "field_artist", "field:artist")

# 3. year disputed (year field intentionally left)
for s in gm["year_disputed"]:
    add(lead_id(s), "year_disputed", "field:year")

# 4. label review (label field intentionally left)
for s in gm["label_review"]:
    add(lead_id(s), "label_review", "field:label")

# 5. weak MusicBrainz match -- the parenthetical names the not-fixed field
for s in gm["weak_mb_match"]:
    iid = lead_id(s)
    m = re.search(r"\((label|year|keytracks|keytrack)", s)
    field = m.group(1) if m else None
    dim = (
        {"label": "field:label", "year": "field:year"}.get(field, "keytracks")
        if field
        else "weak_match"
    )
    add(iid, "weak_mb_match", dim, "weak_match")

# 6. keyTracks not fixed
for iid in gm["keytracks_no_tracklist"]:
    add(iid, "keytracks_no_tracklist", "keytracks")
for s in gm["keytracks_uncertain"]:
    add(lead_id(s), "keytracks_uncertain", "keytracks")

# 7. instrument review (instruments field intentionally left)
for s in gm["instrument_review"]:
    add(lead_id(s), "instrument_review", "field:instruments")

# 8. thin-evidence prose stubs (prose is a minimal factual stub -> unverifiable expected)
for r in prose:
    if r.get("thinEvidence"):
        add(r["id"], "thin_prose", "thin_prose")

# 9. research: unverifiable compilations (defensible as-is)
UNVERIFIABLE_COMPS = [
    "his-eye-is-on-the-sparrow-ethel-waters",
    "johnny-dodds-vol-1-johnny-dodds",
    "ma-rainey-vol-1-ma-rainey",
    "the-empress-of-the-blues-bessie-smith",
]
unresolved_ids = {u["id"] for u in rr["unresolved"]}
for cid in UNVERIFIABLE_COMPS:
    if cid in unresolved_ids:
        add(cid, "unverifiable_comp", "unverifiable_comp")

# 10. Phase-4 re-verify documented gaps (surfaced by the fresh judges; intentionally
# NOT auto-fixed -- reissue-trap labels with no cached original, attribution/catalog
# questions, +/-1yr recorded-vs-released, or a suspect MB release).
PHASE4 = {
    # reissue-label traps: MB resolved a reissue/audiophile label, cache has no original
    "a-study-in-frustration-fletcher-henderson": ("p4_label_reissue", ["field:label"]),
    "ben-webster-meets-oscar-peterson-ben-webster": (
        "p4_label_reissue",
        ["field:label", "field:year"],
    ),
    "the-hawk-flies-high-coleman-hawkins": ("p4_label_reissue", ["field:label"]),
    "joe-pass-at-the-montreux-jazz-festival-joe-pass": (
        "p4_label_reissue",
        ["field:label"],
    ),
    "undercurrent-bill-evans": ("p4_label_reissue", ["field:label"]),
    "swing-de-paris-django-reinhardt": (
        "p4_label_reissue",
        ["field:label", "field:year"],
    ),
    "concert-by-the-sea-erroll-garner": (
        "p4_label_reissue",
        ["field:label", "field:year"],
    ),
    # attribution / catalog-identity questions (no auto-fix per the field_artist policy).
    # For blue-rondo*, the judge confirmed albumDNA prose is CORRECT; the wrongClaim
    # merely restates the wrong artist FIELD, so "prose" is an accepted gap dim here.
    "blue-rondo": ("p4_attribution", ["field:artist", "prose"]),
    "blue-rondo-brubeck": ("p4_attribution", ["field:artist", "prose"]),
    "is-that-so": ("p4_attribution", ["field:artist"]),
    "mystic-brew": ("p4_catalog_title", ["field:title", "prose"]),
    "savoy-sessions-charlie-parker": (
        "p4_catalog_title",
        ["field:title", "field:year"],
    ),
    # original-vs-region label: French Pathe original vs MB's US Nessa release
    "les-stances-a-sophie": ("p4_label_region", ["field:label"]),
    # +/-1-2yr recorded-vs-released (not flipped, per Phase-3 policy). The prose
    # wrongClaim restates the disputed year, not a separate prose error.
    "caravan": ("p4_year_recorded_released", ["field:year", "prose"]),
    "waltz-for-debby": ("p4_year_recorded_released", ["field:year", "prose"]),
    "inside-hi-fi-lee-konitz": ("p4_year_recorded_released", ["field:year"]),
    # MB embedded release is a suspect budget comp; our keyTracks are the correct famous sides
    "begin-the-beguine-artie-shaw": ("p4_suspect_mb_release", ["keytracks"]),
    # recorded 1967 / released May 1968 (Archie Shepp); year field = recording year, prose says 1968
    "the-magic-of-juju": ("p4_year_recorded_released", ["field:year"]),
    # minor title variant ("Jazz Epistles: Verse 1" vs wiki "Jazz Epistle, Verse 1"); wiki is the band page
    "township-jive": ("p4_catalog_title", ["field:title"]),
}
for cid, (cat, dims) in PHASE4.items():
    add(cid, cat, *dims)

with open(f"{OUT}/_gap_ids.json", "w", encoding="utf-8") as f:
    json.dump(gaps, f, ensure_ascii=False, indent=2)
    f.write("\n")

from collections import Counter

cats = Counter(c for g in gaps.values() for c in g["categories"])
print(f"_gap_ids.json: {len(gaps)} distinct gap ids")
for k, v in sorted(cats.items()):
    print(f"  {k}: {v}")

"""Compose scripts/integrity/out/gaps.md -- the honest "could not auto-fix / needs human
review" report, consolidated from every Phase-3 artifact."""

import json

OUT = "scripts/integrity/out"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


gm = load(f"{OUT}/gaps_mechanical.json")
rr = load(f"{OUT}/research_results.json")
prose = load(f"{OUT}/repairs_prose.json")["repairs"]
recheck = load(f"{OUT}/recheck_result.json")

unresolved = {u["id"]: u for u in rr["unresolved"]}
thin = [r["id"] for r in prose if r.get("thinEvidence")]
over600 = [
    r["id"] for r in prose if isinstance(r.get("after"), str) and len(r["after"]) > 600
]

# catalog data errors (deletion / reattribution candidates) -- a subset of research-unresolved
CATALOG_ERRORS = {
    "blue-note-4000": "Not a real album title -- it is the Blue Note 4000-series catalog range. "
    "The three 'keyTracks' (Open Sesame, Hub-Tones, Ready for Freddie) are three "
    "separate Freddie Hubbard albums. DELETION candidate.",
    "investigations": "No Brad Mehldau album by this title exists in his discography. Hallucinated "
    "catalog entry. DELETION candidate.",
    "new-orleans-joys-kid-ory": "No Kid Ory album by this title; 'New Orleans Joys' is a Jelly Roll "
    "Morton solo-piano composition (1923). Misattributed/mislabeled. "
    "DELETION or relabel candidate.",
    "the-art-of-the-trio-vol-4-nat-king-cole": "WRONG ENTITY: 'The Art of the Trio, Vol. 4: Back at "
    "the Vanguard' is a 1999 BRAD MEHLDAU album (Warner "
    "Bros.), not Nat King Cole. Reattribute or delete.",
    "a-smooth-one-woody-herman": "No Woody Herman album by this title; 'A Smooth One' is a Benny "
    "Goodman tune Herman's band played on a 1941 broadcast. Mislabeled "
    "track-as-album. DELETION candidate.",
}

L = [
    "# Data-Integrity Phase 3 -- Gaps & Human-Review Report",
    "",
    "Items Phase 3 did NOT auto-fix, with the reason. Nothing here was guessed; every "
    "unresolved item is named honestly. Phase 4 should treat the catalog data errors as the "
    "highest priority.",
    "",
]

L += [
    "## 1. Catalog data errors (deletion / reattribution candidates) -- HIGH PRIORITY",
    "",
    "Web research could not resolve these because the catalog entry itself appears wrong "
    "(fabricated, mislabeled, or wrong artist). No safe field repair exists:",
    "",
]
for cid, note in CATALOG_ERRORS.items():
    L.append(f"- **{cid}**: {note}")
L += [
    "",
    "Plus an artist/album attribution conflict surfaced during rewrite:",
    "- **lullaby-of-birdland**: catalog says artist *Duke Ellington* (label Intermedia) but ALL "
    "evidence (MusicBrainz + Wikipedia) says this is a *Lee Konitz / Barry Harris* date on Candid. "
    "Prose was reduced to a bare title+tracks stub. Needs a catalog-level artist decision.",
    "",
]

L += [
    "## 2. field_artist -- attribution review (13) -- NOT auto-fixed",
    "These album `artist` fields disagree with the MusicBrainz credit (sideman-vs-leader, or "
    "a wrong lead). Left for human decision; MB credit shown:",
    "",
]
for it in gm["field_artist"]:
    L.append(
        f"- **{it['id']}**: ours=`{it['ours_artist']}` | MB credit=`{it.get('mb_artists')}` "
        f"(MB title: {it.get('mb_title')!r}) -- {it.get('sourceUrl')}"
    )
L += [
    "",
    "Note: **screamin-the-blues** prose was corrected to leader *Oliver Nelson* (Eric Dolphy is a "
    "sideman) per entity-matched evidence, but its `artist` field still reads *Eric Dolphy*. "
    "Setting the field to Oliver Nelson would make prose and field consistent.",
    "",
]

L += [
    "## 3. year disputed (17) -- left as-is",
    "MusicBrainz first-release year conflicts with ours, but Wikipedia/recording-date evidence "
    "is split (often a recorded-one-year / released-another case, e.g. the-olatunji-concert "
    "recorded 1967 / released 2001). Not auto-flipped:",
    "",
]
for s in gm["year_disputed"]:
    L.append(f"- {s}")

L += [
    "",
    "## 4. label review (16) -- left as-is",
    "ours has a plausible real label that disagrees with the MB release's label (often "
    "original-vs-reissue or a parent conglomerate). Auto-fix would risk regressing a correct "
    "original; human picks:",
    "",
]
for s in gm["label_review"]:
    L.append(f"- {s}")

L += [
    "",
    "## 5. weak MusicBrainz match (10) -- not auto-fixed",
    "MB match was a search hit with low artist-similarity or a title mismatch -- not trusted for "
    "an auto fix:",
    "",
]
for s in gm["weak_mb_match"]:
    L.append(f"- {s}")

L += [
    "",
    "## 6. keyTracks not fixed (16)",
    f"- No MB tracklist available ({len(gm['keytracks_no_tracklist'])}): "
    + ", ".join(gm["keytracks_no_tracklist"]),
    f"- Uncertain MB release / title mismatch ({len(gm['keytracks_uncertain'])}): "
    + ", ".join(gm["keytracks_uncertain"]),
]

L += [
    "",
    "## 7. instrument review (5) -- ours kept, lead-derived differs",
    "ours instruments neither empty nor a clean subset of the lead-derived set; left for review:",
    "",
]
for s in gm["instrument_review"]:
    L.append(f"- {s}")

L += [
    "",
    "## 8. thin-evidence prose stubs (7)",
    "Confirmed-bad prose was replaced, but entity-matched evidence was too thin for a full DNA, so "
    "a minimal factual stub was written (no invention). Could be enriched later with research:",
    "",
]
for i in thin:
    L.append(f"- {i}")

L += [
    "",
    "## 9. research: unverifiable compilations (defensible as-is)",
    "Real artist, but the bare title maps to many reissue 'Volume 1' products with different "
    "year/label/tracklist; no single release could be confirmed, so no field was changed:",
    "",
]
for cid in (
    "his-eye-is-on-the-sparrow-ethel-waters",
    "johnny-dodds-vol-1-johnny-dodds",
    "ma-rainey-vol-1-ma-rainey",
    "the-empress-of-the-blues-bessie-smith",
):
    if cid in unresolved:
        L.append(f"- **{cid}**: {unresolved[cid]['note']}")

L += [
    "",
    "## 10. Notes / minor",
    "- **clarence-williams** birthYear set to 1898 (first value in the Wikipedia lead; sources "
    "give '1898 or 1893').",
    "- **blue-rondo** and **blue-rondo-brubeck** point to the same MusicBrainz MBID (a 1997 Tudor "
    "multi-composer clarinet recital). Both rewritten neutrally; they may be duplicate slots.",
    "- 5 factual_error prose repairs exceed the 600-char house style ("
    + ", ".join(over600)
    + "); each was already over 600 before the surgical fix, and the "
    "factual_error rule preserves correct sentences, so they were not trimmed.",
    "- 4 wrong-wiki-link artists (andrew-hill, dave-holland, sadao-watanabe, sam-rivers) and 3 "
    "disambiguation-page stub artists (tommy-flanagan, james-moody, clarence-williams) were "
    "RESOLVED by research (correct disambiguated Wikipedia URLs + dates/instruments).",
    "",
]

with open(f"{OUT}/gaps.md", "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
print(f"gaps.md written: {len(L)} lines")
print(
    f"  catalog errors: {len(CATALOG_ERRORS)} | field_artist: {len(gm['field_artist'])} | "
    f"year_disputed: {len(gm['year_disputed'])} | label_review: {len(gm['label_review'])} | "
    f"weak_mb: {len(gm['weak_mb_match'])} | thin: {len(thin)} | unresolved: {len(unresolved)}"
)

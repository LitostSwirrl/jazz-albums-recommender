"""Build Phase-2.5 web-research packs.

Targets (49): 42 no_evidence items (5 artists + 37 albums that had NO MB release and NO
wiki page in the Phase-1 cache) + 4 wrong-wiki-link artists (correct page collides with an
actor/etc.; bio is fine, link needs repointing) + 3 disambiguation-page stub artists
(cached page is a disambig page; need correct page -> dates + instruments).

Each item carries its current src/data values (so a researcher can fill `before`) and a
researchGoal. Researchers fetch authoritative sources and propose verifiable repairs.

Outputs: scripts/integrity/out/research_packs/research_NN.json (~7 each) + manifest.json
"""

import json
import os

OUT = "scripts/integrity/out"
DATA = "src/data"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(o, p):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
        f.write("\n")


albums = {a["id"]: a for a in load(f"{DATA}/albums.json")}
albumsDetail = load(f"{DATA}/albumsDetail.json")
artists = {a["id"]: a for a in load(f"{DATA}/artists.json")}
artistsDetail = load(f"{DATA}/artistsDetail.json")
worklist = load(f"{OUT}/repair_worklist.json")

WIKI_LINK_ARTISTS = ["andrew-hill", "dave-holland", "sadao-watanabe", "sam-rivers"]
DISAMBIG_STUB_ARTISTS = ["tommy-flanagan", "james-moody", "clarence-williams"]


def album_item(aid, goal):
    a = albums.get(aid, {})
    return {
        "id": aid,
        "kind": "album",
        "researchGoal": goal,
        "ours": {
            "title": a.get("title"),
            "artist": a.get("artist"),
            "year": a.get("year"),
            "label": a.get("label"),
            "albumDNA": a.get("albumDNA"),
            "keyTracks": albumsDetail.get(aid, {}).get("keyTracks"),
            "wikipedia": albumsDetail.get(aid, {}).get("wikipedia"),
        },
    }


def artist_item(aid, goal):
    a = artists.get(aid, {})
    d = artistsDetail.get(aid, {})
    return {
        "id": aid,
        "kind": "artist",
        "researchGoal": goal,
        "ours": {
            "name": a.get("name"),
            "birthYear": a.get("birthYear"),
            "deathYear": a.get("deathYear"),
            "instruments": a.get("instruments"),
            "bio": d.get("bio"),
            "wikipedia": d.get("wikipedia"),
        },
    }


items = []
for x in worklist["no_evidence"]:
    kind, aid = x.split(":", 1)
    if kind == "album":
        items.append(
            album_item(
                aid,
                "no_evidence: find an authoritative source (MusicBrainz/"
                "Discogs/AllMusic/Wikipedia). Verify or correct year + label, "
                "fill keyTracks if null, confirm or rewrite albumDNA from sources, "
                "set wikipedia URL if a correct page exists. Else mark unresolved.",
            )
        )
    else:
        items.append(
            artist_item(
                aid,
                "no_evidence: find the correct artist page. Verify/fill "
                "birthYear/deathYear/instruments and a 2-3 sentence bio basis; "
                "set wikipedia URL. Else mark unresolved.",
            )
        )
for aid in WIKI_LINK_ARTISTS:
    it = artist_item(
        aid,
        "wrong_wiki_link: the stored wikipedia link is a DISAMBIGUATION page. "
        "Find the correct disambiguated Wikipedia URL for THIS jazz musician "
        "(e.g. '..._(musician)'/'..._(bassist)'). Bio/dates already fine -- only "
        "set the wikipedia field. Confirm dates match to be sure it is the right person.",
    )
    items.append(it)
for aid in DISAMBIG_STUB_ARTISTS:
    it = artist_item(
        aid,
        "disambig_stub: cached page was a disambiguation page (name collides with "
        "an actor/judge/athlete). Find the correct jazz-musician Wikipedia page; "
        "set wikipedia URL and fill birthYear/deathYear/instruments from its lead.",
    )
    items.append(it)

os.makedirs(f"{OUT}/research_packs", exist_ok=True)
CHUNK = 7
manifest = {"total": len(items), "packs": []}
for i in range(0, len(items), CHUNK):
    chunk = items[i : i + CHUNK]
    name = f"research_{i // CHUNK:02d}.json"
    dump(chunk, f"{OUT}/research_packs/{name}")
    manifest["packs"].append(
        {
            "file": name,
            "count": len(chunk),
            "ids": [f"{c['kind'][:2]}:{c['id']}" for c in chunk],
        }
    )
dump(manifest, f"{OUT}/research_packs/manifest.json")
print(
    f"research items: {len(items)} ({sum(1 for i in items if i['kind'] == 'album')} albums, "
    f"{sum(1 for i in items if i['kind'] == 'artist')} artists)"
)
print(f"packs: {len(manifest['packs'])} of ~{CHUNK}")

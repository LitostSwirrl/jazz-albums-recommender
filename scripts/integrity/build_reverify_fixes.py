"""Phase 4: build repairs_reverify.json from the re-verify regressions.

Every after-value is grounded in cached evidence (MB release-group, entity-matched
Wikipedia lead, or Phase-2.5 websearch). sourceUrl is constructed from the cache.
Schema matches the other repairs_*.json so apply_repairs.py can consume it.

Scope (high-confidence, evidence-backed only). Ambiguous cases (reissue-trap labels
with no cached original, attribution questions, +/-1yr recorded-vs-released, suspect
MB releases) are intentionally EXCLUDED here and documented in gaps instead.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "src" / "data"
CACHE = Path(__file__).resolve().parent / "cache"
OUT = Path(__file__).resolve().parent / "out"

albums = {a["id"]: a for a in json.loads((DATA / "albums.json").read_text("utf-8"))}
artists = {a["id"]: a for a in json.loads((DATA / "artists.json").read_text("utf-8"))}
adet = json.loads((DATA / "albumsDetail.json").read_text("utf-8"))

# id -> (after_value, source) ; source in {"mb","wiki","ws"}
LABEL = {
    "a-garland-of-red-red-garland": ("Prestige", "mb"),
    "a-swingin-affair-dexter-gordon": ("Blue Note", "mb"),
    "art-pepper-meets-the-rhythm-section-art-pepper": ("Contemporary Records", "mb"),
    "at-the-stratford-shakespearean-festival-oscar-peterson": ("Verve", "mb"),
    "clifford-brown-memorial-album-clifford-brown": ("Blue Note", "mb"),
    "coltrane-jazz-john-coltrane": ("Atlantic", "mb"),
    "cornbread-lee-morgan": ("Blue Note", "mb"),
    "dance-mania-tito-puente": ("RCA Victor", "mb"),
    "desmond-blue-paul-desmond": ("RCA Victor", "mb"),
    "detroitnew-york-junction-thad-jones": ("Blue Note", "mb"),
    "ella-fitzgerald-sings-the-cole-porter-song-book-ella-fitzgerald": ("Verve", "mb"),
    "far-east-suite-duke-ellington": ("RCA Victor", "mb"),
    "fontainebleau-tadd-dameron": ("Prestige", "mb"),
    "full-house-wes-montgomery": ("Riverside", "mb"),
    "inside-hi-fi-lee-konitz": ("Atlantic", "mb"),
    "jazz-giant-benny-carter": ("Contemporary Records", "wiki"),
    "open-sesame-freddie-hubbard": ("Blue Note", "mb"),
    "plenty-plenty-soul-milt-jackson": ("Atlantic", "mb"),
    "spellbound-clifford-jordan": ("Riverside", "mb"),
    "stan-getz-and-the-oscar-peterson-trio-stan-getz": ("Verve", "mb"),
    "the-dual-role-of-bob-brookmeyer-bob-brookmeyer": ("Prestige", "mb"),
    "the-freedom-book-booker-ervin": ("Prestige", "mb"),
    "the-oscar-peterson-trio-at-newport": ("Verve", "mb"),
    "the-sermon-jimmy-smith": ("Blue Note", "mb"),
    "the-man-i-love": ("Dreyfus Jazz", "mb"),
    "chet-baker-and-crew-chet-baker": ("Pacific Jazz", "mb"),
    "night-train-oscar-peterson": ("Verve", "wiki"),
    "afro-dizzy-gillespie": ("Norgran Records", "wiki"),
}

YEAR = {
    "a-garland-of-red-red-garland": (1956, "mb"),
    "a-swingin-affair-dexter-gordon": (1962, "mb"),
    "clifford-brown-memorial-album-clifford-brown": (1956, "mb"),
    "cornbread-lee-morgan": (1967, "wiki"),
    "dance-mania-tito-puente": (1958, "mb"),
    "fontainebleau-tadd-dameron": (1956, "wiki"),
    "full-house-wes-montgomery": (1962, "wiki"),
    "jazz-giant-benny-carter": (1958, "wiki"),
    "open-sesame-freddie-hubbard": (1960, "wiki"),
    "spellbound-clifford-jordan": (1960, "mb"),
    "stan-getz-and-the-oscar-peterson-trio-stan-getz": (1957, "mb"),
    "the-dual-role-of-bob-brookmeyer-bob-brookmeyer": (1955, "mb"),
    "the-freedom-book-booker-ervin": (1963, "mb"),
    "the-hawk-flies-high-coleman-hawkins": (1957, "mb"),
    "the-sermon-jimmy-smith": (1959, "wiki"),
    "undercurrent-bill-evans": (1962, "wiki"),
    "chet-baker-and-crew-chet-baker": (1956, "mb"),
    "night-train-oscar-peterson": (1963, "wiki"),
    "afro-dizzy-gillespie": (1954, "wiki"),
    "get-together": (1979, "wiki"),
    "the-awakening-ahmad-jamal": (1970, "wiki"),
    "destination-out-jackie-mclean": (1964, "mb"),
    "pimp-master": (2005, "wiki"),
}

BIRTHYEAR = {  # artists
    "james-blood-ulmer": (1940, "wiki"),
    "revolutionary-ensemble": (1970, "wiki"),
    "world-saxophone-quartet": (1977, "wiki"),
}

KEYTRACKS = {  # albumsDetail
    "amaryllis-belladonna": (
        ["Amaryllis", "Night Shift", "Belladonna", "Moonburn"],
        "ws",
    ),
    "we-insist-freedom-now-suite-max-roach": (
        [
            "Driva' Man",
            "Freedom Day",
            "Triptych: Prayer / Protest / Peace",
            "All Africa",
            "Tears For Johannesburg",
        ],
        "ws",
    ),
}

PROSE = {  # albums albumDNA -- evidence-only rewrites (compilation/anachronism/wrong-track fixes)
    "moonlight-serenade-glenn-miller": (
        "A compilation of Glenn Miller's signature swing-era recordings, built around his "
        "1939 theme “Moonlight Serenade.” It gathers the band's best-known sides "
        "— “In the Mood,” “Chattanooga Choo Choo,” “Pennsylvania "
        "6-5000,” “Tuxedo Junction” and “American Patrol” — from "
        "the most popular American dance orchestra of its day.",
        ["mb", "wiki"],
    ),
    "nows-the-time-charlie-parker": (
        "A reissue gathering Charlie Parker bebop recordings, titled for his 1945 composition "
        "“Now's the Time.” The program runs through Parker originals and standards "
        "— “The Song Is You,” “Laird Baird,” “Kim,” "
        "“Chi Chi” and “Cosmic Rays” — core bebop sides from the alto "
        "saxophonist who, with Dizzy Gillespie, defined the style.",
        ["mb", "wiki"],
    ),
    "smack": (
        "“Smack” is a compilation of Fletcher Henderson's 1920s–30s orchestra "
        "recordings. Key sides include “Sugar Foot Stomp,” “The Stampede” "
        "and “Henderson Stomp.”",
        ["mb"],
    ),
    "the-man-i-love": (
        "The Man I Love (2002) collects Billie Holiday recordings on the Dreyfus Jazz label. "
        "Among the tracks are “God Bless the Child” and “Lover Man.” The "
        "album comes from the big band era when jazz was America's popular music, driven by "
        "dancing and radio. Her vocal style, strongly influenced by jazz instrumentalists, "
        "inspired a new way of manipulating phrasing and tempo.",
        ["mb"],
    ),
}


def mb_url(item_id):
    p = CACHE / "albums_mb" / f"{item_id}.json"
    if not p.exists():
        return None
    rel = (json.loads(p.read_text("utf-8")) or {}).get("release") or {}
    return f"https://musicbrainz.org/release/{rel['mbid']}" if rel.get("mbid") else None


def wiki_url(item_id, artist=False):
    sub = "artists" if artist else "albums_wiki"
    p = CACHE / sub / f"{item_id}.json"
    if not p.exists():
        return None
    rec = json.loads(p.read_text("utf-8"))
    if rec.get("storedUrl"):
        return rec["storedUrl"]
    page = rec.get("page") or {}
    title = page.get("resolvedTitle")
    return f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}" if title else None


def ws_url(item_id):
    p = CACHE / "websearch" / f"{item_id}.json"
    if not p.exists():
        return None
    srcs = (json.loads(p.read_text("utf-8")) or {}).get("sources") or []
    return srcs[0] if srcs else None


def src_url(item_id, source, artist=False):
    if isinstance(source, list):
        urls = []
        for s in source:
            u = src_url(item_id, s, artist)
            if u:
                urls.extend(u if isinstance(u, list) else [u])
        return urls
    if source == "mb":
        return mb_url(item_id)
    if source == "wiki":
        return wiki_url(item_id, artist)
    if source == "ws":
        return ws_url(item_id)
    return None


repairs = []
warnings = []


def add(action, file, item_id, field, before, after, source, artist=False):
    if before == after:
        warnings.append(f"NOOP {file}:{item_id}.{field} (before==after={after!r})")
        return
    url = src_url(item_id, source, artist)
    if not url:
        warnings.append(f"NO_SOURCE_URL {file}:{item_id}.{field} source={source}")
    repairs.append(
        {
            "action": action,
            "file": file,
            "id": item_id,
            "field": field,
            "before": before,
            "after": after,
            "sourceUrl": url,
        }
    )


for iid, (val, src) in LABEL.items():
    add("field_label", "albums", iid, "label", albums[iid].get("label"), val, src)
for iid, (val, src) in YEAR.items():
    add("field_year", "albums", iid, "year", albums[iid].get("year"), val, src)
for iid, (val, src) in BIRTHYEAR.items():
    add(
        "field_birthYear",
        "artists",
        iid,
        "birthYear",
        artists[iid].get("birthYear"),
        val,
        src,
        artist=True,
    )
for iid, (val, src) in KEYTRACKS.items():
    add(
        "keytracks",
        "albumsDetail",
        iid,
        "keyTracks",
        (adet.get(iid) or {}).get("keyTracks"),
        val,
        src,
    )
for iid, (val, src) in PROSE.items():
    add("prose", "albums", iid, "albumDNA", albums[iid].get("albumDNA"), val, src)

(OUT / "repairs_reverify.json").write_text(
    json.dumps(
        {"count": len(repairs), "repairs": repairs}, ensure_ascii=False, indent=2
    )
    + "\n",
    encoding="utf-8",
)
print(
    f"repairs_reverify.json: {len(repairs)} fixes "
    f"(label={len(LABEL)} year={len(YEAR)} birthYear={len(BIRTHYEAR)} "
    f"keytracks={len(KEYTRACKS)} prose={len(PROSE)})"
)
if warnings:
    print("WARNINGS:")
    for w in warnings:
        print("  ", w)

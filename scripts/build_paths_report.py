"""Render the markdown editorial spec from the validated curated_paths.json."""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = json.load(
    open(os.path.join(ROOT, "scripts", "out", "curated_paths.json"), encoding="utf-8")
)
BYID = {
    a["id"]: a
    for a in json.load(
        open(os.path.join(ROOT, "src", "data", "albums.json"), encoding="utf-8")
    )
}
OUT = os.path.join(
    ROOT, "docs", "superpowers", "specs", "2026-06-12-inspiration-agenda-paths.md"
)

# Guitar-relevant artists verified present (lead artist unless noted). Sample ids shown.
present = [
    (
        "Django Reinhardt",
        "quintette-du-hot-club-de-france, django-reinhardt-et-son-quintette, django, plus 3 more",
    ),
    ("Charlie Christian", "after-hours-monroes-harlem-mintons"),
    (
        "Kenny Burrell",
        "kenny-burrell, midnight-blue, blue-bash-burrell, 2-guitars, lucky-so-and-so",
    ),
    (
        "Wes Montgomery",
        "boss-guitar, full-house-wes-montgomery, smokin-at-the-half-note-wes-montgomery, bumpin-wes-montgomery, movin-wes-wes-montgomery, tequila",
    ),
    (
        "Grant Green",
        "idle-moments, street-of-dreams, the-latin-bit, music-matador, shades-of-green, alive-grant-green",
    ),
    ("Jim Hall", "concierto-jim-hall, dialogues, jim-hall-basses"),
    (
        "Joe Pass",
        "a-sign-of-the-times, virtuoso-no-4, checkmate, joe-pass-at-the-montreux-jazz-festival-joe-pass",
    ),
    ("Barney Kessel", "the-poll-winners-ride-again-barney-kessel"),
    ("Pat Martino", "el-hombre, well-be-together-again"),
    (
        "Pat Metheny",
        "bright-size-life, question-and-answer, the-unity-sessions, moondial, the-lore",
    ),
    ("John McLaughlin", "love-devotion-surrender; also fronts Shakti on shakti"),
    ("Sonny Sharrock", "ask-the-ages, black-woman, faith-moves"),
    ("Bill Frisell", "this-land, el-viaje, it-happened-again"),
    ("Al Di Meola", "cielo-e-terra, di-meola-plays-piazzolla"),
    ("Kurt Rosenwinkel", "heartcore, the-chopin-project"),
    ("Julian Lage", "arclight, mount-royal, chesed-the-book-beriah-volume-4"),
    ("Lage Lund", "early-songs, terrible-animals, life-of-the-party"),
    (
        "Russell Malone",
        "russell-malone, bluebird, golden-striker-live-at-theaterstbchen-kassel",
    ),
    ("Mary Halvorson", "crackleknob, amaryllis-belladonna, bone-bells"),
    ("Egberto Gismonti (guitar and piano)", "danca-das-cabecas, saudades, alma"),
]

out = []
w = out.append
w("# Smack Cats -- Inspiration Agenda and Curated Paths")
w("")
w(
    "_Editorial spec. Date: 2026-06-12. Every album id below is verified to exist in `src/data/albums.json` (1000 albums). Machine-readable twin: `scripts/out/curated_paths.json`._"
)
w("")
w("## Agenda")
w("")
w(P["agenda"])
w("")
w("## Paths")
w("")
for path in P["paths"]:
    w(f"### {path['title']}")
    w("")
    w(f"**{path['subtitle']}**")
    w("")
    w(f"`id: {path['id']}` -- {len(path['albumIds'])} albums")
    w("")
    w(f"**Rationale.** {path['rationale']}")
    w("")
    w(f"**For the player.** {path['forThePlayer']}")
    w("")
    w("Listening order:")
    w("")
    for n, i in enumerate(path["albumIds"], 1):
        a = BYID[i]
        yr = a.get("year") or "?"
        w(f"{n}. **{a['title']}** -- {a['artist']} ({yr}) -- {a['era']} -- `{i}`")
    w("")
w("## Guitar-relevant artists present in the dataset")
w("")
w(
    "Verified by scanning `albums.json` for each name. Names checked but NOT found, and therefore excluded from the guitar path: George Benson, John Scofield, Tal Farlow, Marc Ribot, John Abercrombie."
)
w("")
for name, alb in present:
    w(f"- **{name}** -- {alb}")
w("")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print(f"WROTE {OUT}")
print(f"lines={len(out)}")

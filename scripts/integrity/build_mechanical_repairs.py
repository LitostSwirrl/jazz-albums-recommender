"""Compute deterministic mechanical repairs from the cache (NO LLM judgment).

Every proposed value is traceable to a cached MusicBrainz/Wikipedia field and carries a
sourceUrl. Ambiguous cases are NOT auto-fixed -- they go to diagnostics/gaps for review.

Safety rules baked in (learned from a first dry run):
  - MB search matches are trusted for a field ONLY if topArtistSimilarity>=0.9 AND the MB
    release title matches ours (artist match alone let "The Eternal Ellington" pose as
    "The Popular Duke Ellington"). embedded_mbid is always authoritative (it is our coverUrl).
  - Group entities (ensemble/trio/quartet/orchestra...) use formation/disband-year logic,
    never the person birth-death parenthetical (which grabbed a member's tenure year).
  - Instruments: word-boundary matching (no "organ" inside "organization"); persons derive
    from shortDescription + first sentence only (no collaborator instruments); groups derive
    from member "(instrument)" parentheticals.
  - field_label: only auto-fix when ours is junk (Unknown/Various/mastering). Real-vs-real
    label disagreements go to review (avoid regressing an original label to a reissue imprint
    or a parent conglomerate).

Outputs (no data files touched here):
  scripts/integrity/out/repairs_mechanical.json
  scripts/integrity/out/mechanical_diagnostics.md
"""

import json
import re
import unicodedata

OUT = "scripts/integrity/out"
DATA = "src/data"
CACHE = "scripts/integrity/cache"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(o, p):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
        f.write("\n")


def try_load(p):
    try:
        return load(p)
    except FileNotFoundError:
        return None


def bare(x):
    return x.split(":", 1)[1] if ":" in x else x


albums = load(f"{DATA}/albums.json")
albums_by_id = {a["id"]: a for a in albums}
albumsDetail = load(f"{DATA}/albumsDetail.json")
artists = load(f"{DATA}/artists.json")
artists_by_id = {a["id"]: a for a in artists}
worklist = load(f"{OUT}/repair_worklist.json")

repairs = []
gaps = {
    "field_artist": [],
    "year_disputed": [],
    "weak_mb_match": [],
    "instrument_review": [],
    "missing_lead": [],
    "wiki_link_dropped_albums": [],
    "wiki_link_artists_to_research": [],
    "no_change": [],
    "keytracks_no_tracklist": [],
    "keytracks_uncertain": [],
    "label_review": [],
    "stub_unresolved": [],
}


def mb_url(rel, group=False):
    if not rel:
        return None
    if group and rel.get("releaseGroup", {}).get("mbid"):
        return f"https://musicbrainz.org/release-group/{rel['releaseGroup']['mbid']}"
    if rel.get("mbid"):
        return f"https://musicbrainz.org/release/{rel['mbid']}"
    return None


def year_of(datestr):
    if not datestr:
        return None
    m = re.match(r"(\d{4})", str(datestr))
    return int(m.group(1)) if m else None


def norm(t):
    t = unicodedata.normalize("NFKD", str(t))
    for a, b in [("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"')]:
        t = t.replace(a, b)
    t = t.lower()
    t = t.replace("&", " and ")
    t = re.sub(r"\(.*?\)", " ", t)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"^(?:the|a|an) ", "", t)  # ignore a leading article in title match


def mb_confident(mb, ours_title):
    """Is this MB release trustworthy as the SAME album as ours?"""
    rel = (mb or {}).get("release")
    if not rel:
        return False, "no release"
    method = mb.get("method")
    if method == "embedded_mbid":
        return True, "embedded_mbid"
    sim = mb.get("topArtistSimilarity")
    if (
        method == "search"
        and sim is not None
        and sim >= 0.9
        and norm(rel.get("title")) == norm(ours_title)
    ):
        return True, f"search sim={sim} title-match"
    return False, f"search sim={sim} title={rel.get('title')!r} vs {ours_title!r}"


# ================================================================ keytracks
for kid in worklist["keytracks_mismatch"]:
    aid = bare(kid)
    a = albums_by_id.get(aid, {})
    mb = try_load(f"{CACHE}/albums_mb/{aid}.json")
    rel = (mb or {}).get("release") or {}
    tracks = rel.get("tracks") or []
    ours_kt = albumsDetail.get(aid, {}).get("keyTracks") or []
    if not tracks:
        gaps["keytracks_no_tracklist"].append(aid)
        continue
    ok, why = mb_confident(mb, a.get("title", ""))
    if not ok:
        gaps["keytracks_uncertain"].append(f"{aid} ({why})")
        continue
    mb_norm = {norm(t): t for t in tracks}
    matched, used = [], set()
    for t in ours_kt:
        n = norm(t)
        if n in mb_norm and mb_norm[n] not in used:
            matched.append(mb_norm[n])
            used.add(mb_norm[n])
    target = len(ours_kt) if ours_kt else min(5, len(tracks))
    for t in tracks:
        if len(matched) >= target:
            break
        if t not in used:
            matched.append(t)
            used.add(t)
    if matched != ours_kt:
        repairs.append(
            {
                "action": "keytracks",
                "file": "albumsDetail",
                "id": aid,
                "field": "keyTracks",
                "before": ours_kt,
                "after": matched,
                "sourceUrl": mb_url(rel),
                "evidence": f"MB tracklist ({why})",
            }
        )
    else:
        gaps["no_change"].append(f"{aid} (keytracks already match)")

# ================================================================ field_label
JUNK_LABEL = re.compile(r"^(unknown|various|n/?a|)$|mastering|distribution", re.I)
BAD_TARGET = re.compile(
    r"reissue|polygram|universal music|sony music|\bbmg\b|holdings?|gmbh|\bllc\b|productions? inc",
    re.I,
)
for lid in worklist["field_label"]:
    aid = bare(lid)
    a = albums_by_id.get(aid)
    mb = try_load(f"{CACHE}/albums_mb/{aid}.json")
    rel = (mb or {}).get("release")
    if not a or not rel:
        gaps["weak_mb_match"].append(f"{aid} (label; no MB release)")
        continue
    labels = [lab.get("name") for lab in (rel.get("labels") or []) if lab.get("name")]
    if not labels:
        gaps["weak_mb_match"].append(f"{aid} (label; MB has no named label)")
        continue
    ours_label = a.get("label")
    if ours_label and any(norm(ours_label) == norm(lab) for lab in labels):
        gaps["no_change"].append(f"{aid} (label ok: {ours_label})")
        continue
    target = next((lab for lab in labels if not BAD_TARGET.search(lab)), None)
    is_junk = ours_label is None or JUNK_LABEL.search((ours_label or "").strip())
    if target and is_junk:
        repairs.append(
            {
                "action": "field_label",
                "file": "albums",
                "id": aid,
                "field": "label",
                "before": ours_label,
                "after": target,
                "sourceUrl": mb_url(rel),
                "evidence": f"ours junk; MB labels={labels}",
            }
        )
    else:
        gaps["label_review"].append(
            f"{aid}: ours={ours_label!r} MB labels={labels} url={mb_url(rel)}"
        )

# ================================================================ field_year
for yid in worklist["field_year"]:
    aid = bare(yid)
    a = albums_by_id.get(aid)
    mb = try_load(f"{CACHE}/albums_mb/{aid}.json")
    rel = (mb or {}).get("release") or {}
    if not a or not rel:
        gaps["weak_mb_match"].append(f"{aid} (year; no MB release)")
        continue
    ok, why = mb_confident(mb, a.get("title", ""))
    rg = rel.get("releaseGroup") or {}
    mb_year = year_of(rg.get("firstReleaseDate")) or year_of(rel.get("date"))
    ours_year = a.get("year")
    if mb_year is None:
        gaps["weak_mb_match"].append(f"{aid} (year; MB no date)")
        continue
    if not ok:
        gaps["weak_mb_match"].append(f"{aid} (year; {why})")
        continue
    wiki = try_load(f"{CACHE}/albums_wiki/{aid}.json")
    wiki_text = json.dumps(wiki, ensure_ascii=False) if wiki else ""
    wiki_supports_ours = bool(ours_year and re.search(rf"\b{ours_year}\b", wiki_text))
    if ours_year in (None, 0):
        repairs.append(
            {
                "action": "field_year",
                "file": "albums",
                "id": aid,
                "field": "year",
                "before": ours_year,
                "after": mb_year,
                "sourceUrl": mb_url(rel, group=True),
                "evidence": f"MB firstReleaseDate ({why})",
            }
        )
    elif ours_year == mb_year:
        gaps["no_change"].append(f"{aid} (year ok: {ours_year})")
    elif ours_year - mb_year >= 3 and not wiki_supports_ours:
        repairs.append(
            {
                "action": "field_year",
                "file": "albums",
                "id": aid,
                "field": "year",
                "before": ours_year,
                "after": mb_year,
                "sourceUrl": mb_url(rel, group=True),
                "evidence": f"ours later reissue/comp; MB original={mb_year} ({why})",
            }
        )
    else:
        gaps["year_disputed"].append(
            f"{aid}: ours={ours_year} MB={mb_year} wiki_mentions_ours={wiki_supports_ours} ({why})"
        )

# ================================================================ wrong_wiki_link
for wid in worklist["wrong_wiki_link"]:
    kind, aid = wid.split(":", 1)
    if kind == "artist":
        gaps["wiki_link_artists_to_research"].append(aid)
        continue
    cur = albumsDetail.get(aid, {}).get("wikipedia")
    if cur is None:
        gaps["no_change"].append(f"{aid} (wiki already null)")
        continue
    repairs.append(
        {
            "action": "wiki_link_drop",
            "file": "albumsDetail",
            "id": aid,
            "field": "wikipedia",
            "before": cur,
            "after": None,
            "sourceUrl": None,
            "evidence": "Phase-2 wikiLinkVerdict=wrong_entity; no correct page cached -> drop",
        }
    )
    gaps["wiki_link_dropped_albums"].append(aid)

# ================================================================ field_artist (NO auto-fix)
for fid in worklist["field_artist"]:
    aid = bare(fid)
    a = albums_by_id.get(aid, {})
    mb = try_load(f"{CACHE}/albums_mb/{aid}.json")
    rel = (mb or {}).get("release") or {}
    gaps["field_artist"].append(
        {
            "id": aid,
            "ours_artist": a.get("artist"),
            "mb_artists": rel.get("artists"),
            "mb_title": rel.get("title"),
            "sourceUrl": mb_url(rel),
        }
    )

# ================================================================ artist_stub_fields
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
INSTR_MAP = [
    (r"tenor saxophon", "tenor saxophone"),
    (r"alto saxophon", "alto saxophone"),
    (r"baritone saxophon", "baritone saxophone"),
    (r"soprano saxophon", "soprano saxophone"),
    (r"\bsaxophon", "saxophone"),
    (r"\btrumpet|trumpeter", "trumpet"),
    (r"\bcornet", "cornet"),
    (r"\btrombon", "trombone"),
    (r"\bclarinet", "clarinet"),
    (r"\bpiano|\bpianist", "piano"),
    (r"\borganist|\borgan\b", "organ"),
    (r"vibraphon|vibraharp", "vibraphone"),
    (r"timbal", "timbales"),
    (r"\bdrums?\b|drummer|percussion", "drums"),
    (r"\bbassist|double[- ]bass|upright bass|\bbass\b", "bass"),
    (r"\bguitar", "guitar"),
    (r"\bviolin", "violin"),
    (r"\bflaut|\bflutist|\bflute\b", "flute"),
    (r"\bvocal|\bsinger\b", "vocals"),
    (r"\baccordion", "accordion"),
]
GROUP_RE = re.compile(
    r"\b(?:is|was|are|were)\b[^.]{0,60}\b(group|ensemble|trio|quartet|quintet|sextet|"
    r"septet|octet|band|orchestra|collective|big band)\b",
    re.I,
)
JUNK_ROLE = {
    "composer",
    "bandleader",
    "musician",
    "arranger",
    "conductor",
    "producer",
    "leader",
    "songwriter",
    "multi-instrumentalist",
    "artist",
    "performer",
}


def first_sentence(text):
    m = re.search(r"\.\s", text)
    return text[: m.start() + 1] if m else text[:240]


def looks_like_person_dates(inner):
    """A birth-death parenthetical: has a month, 'born', or is a bare year(-range)."""
    if re.search(MONTHS, inner):
        return True
    if re.search(r"\bborn\b", inner, re.I):
        return True
    return bool(re.match(r"^\s*c?\.?\s*\d{4}\s*(?:[–-]\s*\d{4})?\s*$", inner.strip()))


DATE_RANGE = re.compile(
    rf"(?:{MONTHS})\s+\d{{1,2}},?\s+(\d{{4}})\s*[–-]\s*(?:(?:{MONTHS})\s+\d{{1,2}},?\s+)?(\d{{4}})",
    re.I,
)
BORN_DATE = re.compile(rf"born\s+(?:(?:{MONTHS})\s+\d{{1,2}},?\s+)?(\d{{4}})", re.I)


def extract_person_years(text):
    # 1) parenthetical birth-death (month / 'born' / bare year-range)
    for m in re.finditer(r"\(([^)]*\d{4}[^)]*)\)", text):
        inner = m.group(1)
        if not looks_like_person_dates(inner):
            continue  # skip e.g. "(from 1952 to 1955)" = a member's tenure, not birth-death
        mb = re.search(r"born[^)\d]*(\d{4})", inner, re.I)
        years = re.findall(r"\d{4}", inner)
        if mb:
            return int(mb.group(1)), None
        if len(years) >= 2:
            return int(years[0]), int(years[1])
        if len(years) == 1:
            return int(years[0]), None
    # 2) bare date range -- handles malformed leads with a dropped opening paren
    #    (e.g. jimmy-giuffre: "...; April 26, 1921 - April 24, 2008) was ...")
    m = DATE_RANGE.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = BORN_DATE.search(text)
    if m:
        return int(m.group(1)), None
    return None, None


def extract_group_years(text):
    b = re.search(
        r"(?:established|formed|founded)(?:\s+\w+){0,3}?\s+in\s+(\d{4})", text, re.I
    )
    d = re.search(r"disband(?:ed|ing)?(?:\s+\w+){0,3}?\s+in\s+(\d{4})", text, re.I)
    return (int(b.group(1)) if b else None), (int(d.group(1)) if d else None)


def derive_instruments(text):
    found, low = [], text.lower()
    for pat, name in INSTR_MAP:
        if re.search(pat, low):
            if name == "saxophone" and any(s.endswith("saxophone") for s in found):
                continue
            if name not in found:
                found.append(name)
    return found


def role_clause(extract):
    """The 'was an American jazz X, Y, Z' predicate -- the subject's own roles, stopping at
    the first period. Robust to 'Jr.'/'Sr.' in the name (which precede the verb) and avoids
    leaking a later sentence's collaborator instruments."""
    m = re.search(r"\b(?:was|is|were|are)\s+(?:a|an|the)?\s*([^.]*)", extract)
    return m.group(1) if m else extract[:200]


for sid in worklist["artist_stub_fields"]:
    aid = bare(sid)
    art = artists_by_id.get(aid)
    cache = try_load(f"{CACHE}/artists/{aid}.json")
    if not art or not cache:
        gaps["missing_lead"].append(f"{aid} (no artist row or cache)")
        continue
    page = cache.get("page") or {}
    extract = page.get("extract") or ""
    short = page.get("shortDescription") or ""
    resolved = page.get("resolvedTitle")
    src = cache.get("storedUrl") or (
        f"https://en.wikipedia.org/wiki/{resolved.replace(' ', '_')}"
        if resolved
        else None
    )
    is_disambig = "same term" in short.lower()
    # PERSON iff a birth-death parenthetical sits before the first copula verb.
    # (A group's date parentheticals belong to its members and come after the verb,
    #  e.g. "The Revolutionary Ensemble was a trio ... Leroy Jenkins (1932-2007)".)
    vm = re.search(r"\b(?:was|is|were|are)\b", extract)
    head = extract[: vm.start()] if vm else extract[:160]
    p_by, p_dy = extract_person_years(head)
    if p_by is None:
        p_by, p_dy = extract_person_years(short)
    is_person = p_by is not None
    is_group = (not is_person) and not is_disambig
    # --- dates ---
    if is_group:
        by, dy = extract_group_years(extract)
    elif is_person:
        by, dy = p_by, p_dy
    else:
        by, dy = None, None
    changed = []
    if (art.get("birthYear") in (None, 0)) and by and not is_disambig:
        repairs.append(
            {
                "action": "stub_birthYear",
                "file": "artists",
                "id": aid,
                "field": "birthYear",
                "before": art.get("birthYear"),
                "after": by,
                "sourceUrl": src,
                "evidence": ("group formation; " if is_group else "")
                + f"lead: {extract[:80]!r}",
            }
        )
        changed.append("birthYear")
    if (art.get("deathYear") in (None,)) and dy and not is_disambig:
        repairs.append(
            {
                "action": "stub_deathYear",
                "file": "artists",
                "id": aid,
                "field": "deathYear",
                "before": art.get("deathYear"),
                "after": dy,
                "sourceUrl": src,
                "evidence": ("group disband; " if is_group else "")
                + f"lead: {extract[:80]!r}",
            }
        )
        changed.append("deathYear")
    # --- instruments ---
    if is_disambig:
        derived = []
    elif is_group:
        derived = derive_instruments(short + ". " + extract[:600])
    else:
        derived = derive_instruments(short + ". " + role_clause(extract))
    ours_instr = art.get("instruments") or []
    ours_real = [i for i in ours_instr if i.lower() not in JUNK_ROLE]
    if derived:
        if not ours_instr:
            repairs.append(
                {
                    "action": "stub_instruments",
                    "file": "artists",
                    "id": aid,
                    "field": "instruments",
                    "before": ours_instr,
                    "after": derived,
                    "sourceUrl": src,
                    "evidence": f"fill from lead: {(short or extract)[:80]!r}",
                }
            )
            changed.append("instruments(fill)")
        elif set(ours_instr) < set(derived):
            repairs.append(
                {
                    "action": "stub_instruments",
                    "file": "artists",
                    "id": aid,
                    "field": "instruments",
                    "before": ours_instr,
                    "after": derived,
                    "sourceUrl": src,
                    "evidence": f"ours subset; expand from lead: {(short or extract)[:80]!r}",
                }
            )
            changed.append("instruments(expand)")
        elif not ours_real:  # ours is all role-junk, no real instrument
            repairs.append(
                {
                    "action": "stub_instruments",
                    "file": "artists",
                    "id": aid,
                    "field": "instruments",
                    "before": ours_instr,
                    "after": derived,
                    "sourceUrl": src,
                    "evidence": f"ours all role-junk; replace from lead: {(short or extract)[:80]!r}",
                }
            )
            changed.append("instruments(replace-junk)")
        elif set(ours_instr) != set(derived):
            gaps["instrument_review"].append(
                f"{aid}: ours={ours_instr} derived={derived}"
            )
    if is_disambig:
        # cached wiki page is a disambiguation page (name collides with an actor/judge/etc.)
        # -> cannot trust the lead; surface for Phase 2.5 research (correct page + dates)
        gaps["stub_unresolved"].append(
            f"{aid}: cached page is a disambiguation page (resolvedTitle={page.get('resolvedTitle')!r}); "
            f"current birthYear={art.get('birthYear')} -> research correct page"
        )
    elif by is None and (art.get("birthYear") in (None, 0)):
        gaps["missing_lead"].append(
            f"{aid} (no birth/formation year in lead; group={is_group})"
        )
    if not changed and not is_disambig:
        gaps["no_change"].append(f"{aid} (stub: nothing to fill)")

# ================================================================ write
dump({"count": len(repairs), "repairs": repairs}, f"{OUT}/repairs_mechanical.json")
dump(gaps, f"{OUT}/gaps_mechanical.json")
by_action = {}
for r in repairs:
    by_action[r["action"]] = by_action.get(r["action"], 0) + 1
lines = [
    "# Mechanical Repairs -- Proposals & Diagnostics",
    "",
    f"Total proposed mechanical fixes: {len(repairs)}",
    "",
    "## By action",
]
for k in sorted(by_action):
    lines.append(f"- {k}: {by_action[k]}")
lines += ["", "## Gaps / review queues (NOT auto-fixed)"]
for k, v in gaps.items():
    lines.append(f"- {k}: {len(v)}")
    if k == "no_change":
        continue
    for item in v:
        lines.append(
            f"    - {json.dumps(item, ensure_ascii=False) if isinstance(item, dict) else item}"
        )
with open(f"{OUT}/mechanical_diagnostics.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"proposed mechanical repairs: {len(repairs)}")
for k in sorted(by_action):
    print(f"  {k}: {by_action[k]}")
print("gaps:")
for k, v in gaps.items():
    print(f"  {k}: {len(v)}")

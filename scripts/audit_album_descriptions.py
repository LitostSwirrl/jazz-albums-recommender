#!/usr/bin/env python3
"""
Audit albums.json for corrupted `albumDNA` entries.

The corruption pattern: descriptions were originally pulled from Wikipedia
by title-search alone, so disambiguation collisions silently substituted
unrelated articles (a Dusty Springfield song page substituted for an Art
Tatum album, a Wings album page for a Pastorius album, a Charlie Parker
biography for a Sun Ra album).

The principled audit: for each album, decide whether the DNA's *topic* is
plausibly this album. Two strong signals, scaled to severity:

  H_topic — cross-artist contamination (the load-bearing check):
    Build a set of all known jazz-artist full names (and distinctive
    surnames) from artists.json. For each album, find which of those
    names appear in the DNA as word-bounded matches. If any *other*
    artist is mentioned and this album's artist is not, the DNA is
    almost certainly about a different album/artist. Score 1.0.

  H_present — own artist absent at all:
    Word-bounded check (substring would let "Ra" match inside "rapid").
    If the album's artist tokens don't appear AND no other known jazz
    artist appears either, score 0.4 — could be a generic filler
    description, worth a Wikipedia cross-check.

  H_nonjazz — non-jazz genre markers present + own artist absent:
    Catches the "X is a single by British singer Y" pattern even when
    Y isn't in artists.json. Score 0.6.

Phase B (network, only for borderline suspects 0.3-0.9): fetch the
Wikipedia REST summary for the disambiguated title and compare opening
overlap. Promotes high-confidence corruptions and demotes false positives.

Known limitation
----------------
The cross-artist + own-absent signal also fires for **editorial-style
descriptions** that legitimately name the album's personnel but omit the
leader (e.g., a Bitches Brew description that names Wayne Shorter, Chick
Corea, etc., as the actual lineup, but never names Miles Davis). The
strongest discriminator between corruption and editorial style would be a
personnel/collaborator graph, which the dataset doesn't currently carry.
Wikipedia jaccard underperforms because formal Wikipedia openings share
few tokens with editorial prose even when topic matches.

Practical conclusion: the audit produces a *candidate list*. Borderline
cases need human eyes. The 2026-04-14 run flagged 9 candidates; manual
triage classified 3 as true corruptions (rewritten) and 6 as editorial-
style false positives (left untouched, listed in
`scripts/out/data_gaps.md`).

Output: scripts/out/suspected_corruptions.json.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ALBUMS_PATH = ROOT / "src" / "data" / "albums.json"
ARTISTS_PATH = ROOT / "src" / "data" / "artists.json"
OUT_DIR = ROOT / "scripts" / "out"
OUT_PATH = OUT_DIR / "suspected_corruptions.json"

WIKI_USER_AGENT = "SmackCats/1.0 (jazz reference site; github.com/LitostSwirrl)"
WIKI_TIMEOUT = 15

# Surnames that are also extremely common English words. Skip the surname-only
# match for these — full-name match still applies.
SURNAME_STOPWORDS = {
    "king",
    "young",
    "brown",
    "green",
    "smith",
    "white",
    "black",
    "gray",
    "grey",
    "small",
    "long",
    "short",
    "best",
    "rich",
    "wise",
    "bird",
    "fish",
    "wood",
    "stone",
    "hill",
    "lake",
    "river",
    "moon",
    "sun",
    "star",
    "love",
    "may",
    "day",
    "rose",
    "snow",
    "rain",
    "free",
    "ross",
    "ford",
    "hayes",
    "hall",
    "cole",
    "lewis",
    "harris",
    "jones",
    "moore",
    "scott",
    "carter",
    "bell",
    "russell",
    "ellis",
    "clark",
    "wright",
    "blake",
    "kelly",
    "moody",
}

NON_JAZZ_GENRE_WORDS = re.compile(
    r"\b(?:British singer|pop star|pop singer|pop group|rapper|hip hop|rock band|"
    r"heavy metal|punk band|disco hit|country singer|K-pop|reggae|dance-pop|"
    r"folk punk|R&B singer|boy band|girl group)\b",
    re.IGNORECASE,
)


def surname(artist: str) -> str:
    """Best-effort surname for matching. For band names, just use full name."""
    artist = artist.strip()
    if not artist:
        return ""
    tokens = [t for t in re.split(r"[\s\-]+", artist) if t]
    if not tokens:
        return artist
    if len(tokens) == 1:
        return tokens[0]
    # Skip common suffixes like Jr., Sr.
    if (
        tokens[-1].rstrip(".").lower() in {"jr", "sr", "ii", "iii", "iv"}
        and len(tokens) > 1
    ):
        return tokens[-2]
    return tokens[-1]


def tokenize_lc(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def word_bounded_match(needle: str, haystack: str) -> bool:
    """True iff `needle` appears as a word-bounded match in `haystack`.
    Both inputs are matched case-insensitively. Handles unicode word chars."""
    if not needle:
        return False
    pat = r"(?<![A-Za-z0-9])" + re.escape(needle) + r"(?![A-Za-z0-9])"
    return re.search(pat, haystack, re.IGNORECASE) is not None


def name_variants(artist: str) -> list[str]:
    """Variants worth matching (case-insensitive). Excludes single-token
    surnames that are stopwords or shorter than 4 chars (would false-match
    inside common words like 'Ra' in 'rapid')."""
    artist = artist.strip()
    if not artist:
        return []
    out = [artist]
    parts = [p for p in re.split(r"[\s\-]+", artist) if p]
    if len(parts) > 1:
        sn = parts[-1]
        if sn.rstrip(".").lower() in {"jr", "sr", "ii", "iii", "iv"}:
            sn = parts[-2] if len(parts) > 1 else sn
        if len(sn) >= 4 and sn.lower() not in SURNAME_STOPWORDS:
            out.append(sn)
    return out


def build_artist_index(
    artists: list[dict[str, Any]],
) -> tuple[set[str], dict[str, str]]:
    """Returns (matchable_names, name_to_canonical) for cross-artist detection."""
    names: set[str] = set()
    canonical: dict[str, str] = {}
    for a in artists:
        full = a.get("name", "").strip()
        if not full:
            continue
        for v in name_variants(full):
            names.add(v)
            canonical[v.lower()] = full
    return names, canonical


def score_local(
    album: dict[str, Any],
    other_artist_names: list[str],
    canonical: dict[str, str],
) -> tuple[float, list[str]]:
    dna = (album.get("albumDNA") or "").strip()
    artist = (album.get("artist") or "").strip()
    own_canonical = artist  # the album's own artist canonical name

    signals: list[str] = []
    score = 0.0

    if not dna:
        return 1.0, ["empty albumDNA"]

    own_variants = name_variants(artist)
    own_present = any(word_bounded_match(v, dna) for v in own_variants)

    # H_topic — cross-artist contamination (load-bearing).
    # Find all OTHER artists mentioned in the DNA (word-bounded).
    other_mentions: set[str] = set()
    for name in other_artist_names:
        if name in own_variants:
            continue
        if canonical.get(name.lower()) == own_canonical:
            continue
        if word_bounded_match(name, dna):
            other_mentions.add(canonical.get(name.lower(), name))

    if other_mentions and not own_present:
        score += 1.0
        sample = sorted(other_mentions)[:3]
        signals.append(
            f"DNA mentions other known artist(s) {sample} but not own artist '{artist}'"
        )

    # H_nonjazz — non-jazz markers + own artist absent
    if not own_present and NON_JAZZ_GENRE_WORDS.search(dna):
        score += 0.6
        signals.append("non-jazz genre markers present + own artist absent")

    # H_present — own artist absent at all (catch generic/filler descriptions)
    if not own_present:
        score = max(score, 0.4)
        signals.append("own artist name absent from albumDNA (word-bounded)")

    return min(score, 1.0), signals


def wiki_summary(title: str) -> dict[str, Any] | None:
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title, safe='')}"
    req = urllib.request.Request(url, headers={"User-Agent": WIKI_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=WIKI_TIMEOUT) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None


def wiki_opensearch(query: str) -> list[str]:
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "opensearch",
            "search": query,
            "limit": 5,
            "namespace": 0,
            "format": "json",
        }
    )
    req = urllib.request.Request(url, headers={"User-Agent": WIKI_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=WIKI_TIMEOUT) as resp:
            data = json.loads(resp.read())
        return data[1] if isinstance(data, list) and len(data) > 1 else []
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return []


def resolve_wiki(album: dict[str, Any]) -> dict[str, Any] | None:
    """Try disambiguated title; fall back to opensearch."""
    title = album["title"]
    artist = album["artist"]

    candidates = [
        f"{title} ({artist} album)",
        f"{title} ({artist} EP)",
    ]
    sn = surname(artist)
    if sn and sn != artist:
        candidates.append(f"{title} ({sn} album)")
    candidates.append(f"{title} (album)")

    for cand in candidates:
        s = wiki_summary(cand)
        if s and s.get("type") != "disambiguation":
            return s

    # Opensearch fallback
    results = wiki_opensearch(f'"{title}" "{artist}" album')
    for r in results:
        if r in candidates:
            continue
        s = wiki_summary(r)
        if not s or s.get("type") == "disambiguation":
            continue
        extract = s.get("extract", "").lower()
        # Require some match to artist name tokens
        if any(tok for tok in tokenize_lc(artist) if tok in extract and len(tok) > 2):
            return s
    return None


def score_network(album: dict[str, Any]) -> tuple[float, list[str]]:
    dna = album.get("albumDNA") or ""
    s = resolve_wiki(album)
    signals: list[str] = []
    if not s:
        return 0.0, ["no canonical Wikipedia article resolved"]

    extract = s.get("extract", "")
    head_dna = dna[:220]
    head_wiki = extract[:220]
    j = jaccard(tokenize_lc(head_dna), tokenize_lc(head_wiki))
    signals.append(f"wikipedia match: {s.get('title')} (jaccard {j:.2f})")
    if j < 0.15:
        return 0.6, signals + ["very low overlap with Wikipedia abstract"]
    if j < 0.25:
        return 0.3, signals
    return -0.2, signals


def audit_one(
    album: dict[str, Any],
    artist_names: list[str],
    canonical: dict[str, str],
) -> dict[str, Any] | None:
    score, signals = score_local(album, artist_names, canonical)
    # Network check is only worth doing when score is borderline (0.3-0.9).
    # Decisive cross-artist hits (1.0) go straight through; very low scores
    # don't need the round-trip.
    if 0.3 <= score < 1.0:
        net_score, net_signals = score_network(album)
        if net_score > 0:
            score = min(1.0, score + net_score)
        else:
            score = max(score, 0) + net_score
        signals.extend(net_signals)

    if score >= 0.7:
        return {
            "id": album["id"],
            "title": album["title"],
            "artist": album["artist"],
            "year": album.get("year"),
            "albumDNA_head": (album.get("albumDNA") or "")[:260],
            "score": round(score, 2),
            "signals": signals,
        }
    return None


def main() -> int:
    albums = json.loads(ALBUMS_PATH.read_text(encoding="utf-8"))
    artists = json.loads(ARTISTS_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    name_set, canonical = build_artist_index(artists)
    # Sort longest first so multi-token names match before single-token surnames
    artist_names = sorted(name_set, key=lambda s: (-len(s), s))
    print(
        f"artist index: {len(artist_names)} matchable name variants from {len(artists)} artists"
    )

    # Phase A locally first to narrow the set that needs network calls
    local_flagged: list[dict[str, Any]] = []
    for a in albums:
        s, _ = score_local(a, artist_names, canonical)
        if s >= 0.4:
            local_flagged.append(a)

    print(
        f"phase A (local): {len(local_flagged)} / {len(albums)} flagged for network check"
    )

    flagged: list[dict[str, Any]] = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(audit_one, a, artist_names, canonical): a for a in local_flagged
        }
        for i, fut in enumerate(as_completed(futures), 1):
            result = fut.result()
            if result:
                flagged.append(result)
            if i % 20 == 0:
                elapsed = time.time() - start
                print(f"  processed {i}/{len(local_flagged)} ({elapsed:.1f}s)")

    flagged.sort(key=lambda r: (-r["score"], r["id"]))
    OUT_PATH.write_text(
        json.dumps(flagged, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nfinal flagged: {len(flagged)} albums")
    print(f"written to {OUT_PATH.relative_to(ROOT)}")
    if flagged:
        print("\ntop 10:")
        for r in flagged[:10]:
            print(f"  [{r['score']:.2f}] {r['id']} — {r['title']} / {r['artist']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

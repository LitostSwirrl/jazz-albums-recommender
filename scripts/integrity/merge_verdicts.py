#!/usr/bin/env python3
"""
Phase 2 aggregation: merge per-pack judge verdicts deterministically.

- Validates every verdict against the schema (id, verdict class, required
  quote fields for non-clean calls).
- Checks completeness against packs/index.json: every packed item must have
  exactly one verdict. Missing or malformed packs are listed for re-dispatch —
  the audit never silently drops an item.
- Output: out/verdicts.json (merged), out/verdict_summary.md (counts + the
  full non-clean list for the adversarial re-check pass).

Usage: python3 merge_verdicts.py [--verdict-dir out/verdicts]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PACKS = HERE / "out" / "packs"
OUT = HERE / "out"

CLASSES = {"clean", "entity_mismatch", "factual_error", "unverifiable", "no_evidence"}


def validate(v: dict[str, Any]) -> list[str]:
    problems = []
    if v.get("verdict") not in CLASSES:
        problems.append(f"bad verdict class: {v.get('verdict')!r}")
    if v.get("verdict") == "factual_error" and not (
        v.get("wrongClaims")
        or v.get("fieldIssues")
        or (v.get("keyTracksVerdict") == "mismatch" and v.get("keyTracksUnmatched"))
    ):
        problems.append(
            "factual_error without wrongClaims/fieldIssues/keyTracks evidence"
        )
    for wc in v.get("wrongClaims") or []:
        if not wc.get("evidenceQuote"):
            problems.append("wrongClaim missing evidenceQuote")
    return problems


def kind_of(pack_name: str) -> str:
    return "artist" if pack_name.startswith("artists_") else "album"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdict-dir", default=str(OUT / "verdicts"))
    args = ap.parse_args()
    vdir = Path(args.verdict_dir)

    index = json.loads((PACKS / "index.json").read_text(encoding="utf-8"))
    # Key by kind:id — album and artist namespaces overlap (9 self-titled albums
    # share a slug with their artist, e.g. the album "Weather Report" vs the band).
    expected: dict[str, str] = {
        f"{kind_of(pack)}:{item_id}": pack
        for pack, ids in index.items()
        for item_id in ids
    }

    merged: dict[str, dict[str, Any]] = {}
    malformed: list[str] = []
    for pack_name in index:
        vfile = vdir / pack_name
        if not vfile.exists():
            continue
        try:
            verdicts = json.loads(vfile.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            malformed.append(f"{pack_name}: {e}")
            continue
        kind = kind_of(pack_name)
        for v in verdicts:
            key = f"{kind}:{v.get('id')}"
            if key not in expected:
                malformed.append(f"{pack_name}: unknown id {v.get('id')!r}")
                continue
            problems = validate(v)
            if problems:
                malformed.append(f"{pack_name}/{v.get('id')}: " + "; ".join(problems))
                continue
            if key in merged:
                malformed.append(f"{pack_name}: duplicate verdict for {v.get('id')}")
                continue
            merged[key] = {**v, "kind": kind}

    missing = sorted(set(expected) - set(merged))
    missing_by_pack = Counter(expected[i] for i in missing)

    counts = Counter(v["verdict"] for v in merged.values())
    wiki_wrong = [
        i for i, v in merged.items() if v.get("wikiLinkVerdict") == "wrong_entity"
    ]
    tracks_bad = [
        i for i, v in merged.items() if v.get("keyTracksVerdict") == "mismatch"
    ]
    nonclean = {i: v for i, v in merged.items() if v["verdict"] != "clean"}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "verdicts.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    lines = [
        "# Verdict Summary",
        "",
        f"- items expected: {len(expected)}",
        f"- verdicts merged: {len(merged)}",
        f"- missing (re-dispatch these packs): {len(missing)}"
        + (f" -> {dict(missing_by_pack)}" if missing else ""),
        f"- malformed entries: {len(malformed)}",
        "",
        "## Counts",
        "",
    ]
    lines += [f"- {cls}: {counts.get(cls, 0)}" for cls in sorted(CLASSES)]
    lines += [
        "",
        f"## Wrong wikipedia links shipped ({len(wiki_wrong)})",
        "",
        *(f"- {i}" for i in sorted(wiki_wrong)),
        "",
        f"## keyTracks mismatches ({len(tracks_bad)})",
        "",
        *(f"- {i}" for i in sorted(tracks_bad)),
        "",
        f"## Non-clean items for adversarial re-check ({len(nonclean)})",
        "",
    ]
    for i in sorted(nonclean):
        v = nonclean[i]
        lines.append(
            f"- `{i}` [{v['verdict']}, conf {v.get('confidence')}] {v.get('notes', '')[:160]}"
        )
    if malformed:
        lines += ["", "## Malformed", "", *(f"- {m}" for m in malformed)]
    (OUT / "verdict_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        f"merged {len(merged)}/{len(expected)}; missing {len(missing)}; malformed {len(malformed)}"
    )
    print(f"counts: {dict(counts)}")
    print(
        f"wrong wiki links: {len(wiki_wrong)}; keyTracks mismatches: {len(tracks_bad)}"
    )
    return 0 if not missing and not malformed else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Migrate albums.json: combine `description` + `significance` into a single
`albumDNA` field. Remove the old fields.

Rationale: two prose fields drift. At least one album (Art Tatum's "In
Private") has a description contaminated with text about a Dusty Springfield
single. Collapsing to one field is half the fix; the audit/rewrite pass is
the other half.

Merge logic (mechanical):
1. Strip both fields.
2. If `significance` is a prefix/suffix of `description` (case-insensitive,
   whitespace-normalized), drop `significance`.
3. Otherwise: ensure `description` ends with a sentence terminator, then
   append `significance`. If `significance` already starts with a quote
   that's a fragment of `description`, skip it.

Preserves every other field untouched and keeps the list order stable.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALBUMS_PATH = ROOT / "src" / "data" / "albums.json"
BACKUP_PATH = ROOT / "scripts" / "out" / "albums_pre_dna_backup.json"
SENTENCE_TERMINATORS = ".!?"


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def ensure_terminator(s: str) -> str:
    s = s.rstrip()
    if not s:
        return s
    if s[-1] in SENTENCE_TERMINATORS or s.endswith('."') or s.endswith(".”"):
        return s
    return s + "."


def merge(description: str, significance: str) -> str:
    desc = description.strip()
    sig = significance.strip()

    if not desc and not sig:
        return ""
    if not desc:
        return sig
    if not sig:
        return desc

    norm_desc = normalize(desc)
    norm_sig = normalize(sig)

    if norm_sig in norm_desc:
        return desc
    if norm_desc in norm_sig:
        return sig

    desc = ensure_terminator(desc)
    return f"{desc} {sig}".strip()


def main() -> int:
    data = json.loads(ALBUMS_PATH.read_text(encoding="utf-8"))
    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    BACKUP_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    migrated = []
    missing_count = 0
    short_count = 0

    for album in data:
        desc = album.get("description", "") or ""
        sig = album.get("significance", "") or ""
        dna = merge(desc, sig)

        if not dna:
            missing_count += 1
        elif len(dna) < 60:
            short_count += 1

        new_album = {}
        for key, value in album.items():
            if key in ("description", "significance"):
                continue
            new_album[key] = value
            if key == "genres":
                new_album["albumDNA"] = dna
        if "albumDNA" not in new_album:
            new_album["albumDNA"] = dna
        migrated.append(new_album)

    ALBUMS_PATH.write_text(
        json.dumps(migrated, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    have_dna = sum(1 for a in migrated if a.get("albumDNA"))
    have_legacy = sum(1 for a in migrated if "description" in a or "significance" in a)

    print(f"migrated {len(migrated)} albums")
    print(f"  albumDNA populated: {have_dna}")
    print(f"  legacy fields remaining: {have_legacy}")
    print(f"  empty albumDNA: {missing_count}")
    print(f"  short (<60 chars): {short_count}")
    print(f"  backup written to {BACKUP_PATH.relative_to(ROOT)}")

    return 0 if have_legacy == 0 and have_dna == len(migrated) else 1


if __name__ == "__main__":
    raise SystemExit(main())

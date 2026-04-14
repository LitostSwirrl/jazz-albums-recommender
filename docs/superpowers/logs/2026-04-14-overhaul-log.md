# v2 Overhaul — Session Log

Append-only. Each session writes an entry at the end.

---

## S1 — Brainstorm & decomposition (2026-04-14)

**Shipped:**
- Master spec + S2/S3/S4 specs written to `docs/superpowers/specs/`.
- This log file seeded.
- App rename decided: "Jazz Guide" → **"Smack Cats"** (user overrode AI pushback on the "smack" substance-abuse association — trade-off accepted).
- Issue #7 (feature triage) deferred to a post-analytics session; replaced in S4 with analytics install.
- Album schema decision: full migration to single `albumDNA` field in S3 (chosen over display-only merge).
- Fonts decision: Inter + Space Grotesk + JetBrains Mono (replacing DM Serif Display + Source Serif 4).
- PWA icon source: existing `public/favicon.svg` (vinyl with red label). No redesign — just rasterize to PNG.

**Deferred / open:**
- Feature triage until analytics data accumulates (≥ 2–4 weeks after S4 ships).

**Memory updates:**
- None this session. Reversal of `feedback_serif_override.md` happens in S2 (don't invalidate preferences before the code matches).

---

## Next session

Paste this into a fresh chat to kick off S2:

```
I'm continuing the jazz site v2 overhaul. S1 (brainstorming + specs) is done.

Please read these files in order, then execute S2:
1. docs/superpowers/specs/2026-04-14-overhaul-master.md
2. docs/superpowers/specs/2026-04-14-s2-shell-and-brand-design.md

Follow the spec exactly. The scope is: PWA icon + manifest, font swap (serif → Inter + Space Grotesk), footer removal, rename "Jazz Guide" → "Smack Cats". At the end, update memory entries as listed in the S2 spec (including deleting feedback_serif_override.md and creating a no-serif feedback entry), append a log entry to docs/superpowers/logs/2026-04-14-overhaul-log.md, and write the S3 kickoff prompt at the bottom of that log.

Don't ask for clarifications unless truly stuck. Ship it end-to-end.
```

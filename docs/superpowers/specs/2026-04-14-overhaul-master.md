# v2 Overhaul — Master Spec

**Date:** 2026-04-14
**Owner:** Joseph Chang (張趙)
**Status:** In progress (S1 brainstorming complete; S2 next)

## Goal

Fix a batch of long-standing issues with the jazz site in a chain of isolated sessions, each run from a cleared chat and connected only through spec files, memory entries, and a shared log.

## App rename

"Jazz Guide" → **"Smack Cats"**. User accepted the trade-off (rockabilly/band-name SEO noise is tolerable; the name is a deliberate jazz-tragedy nod — Bird, Chet, Billie). No rollback planned.

## Session chain

| # | Spec | Scope (one line) |
|---|---|---|
| S1 | *(this session)* | Brainstorm + decompose + write specs |
| S2 | `2026-04-14-s2-shell-and-brand-design.md` | PWA wiring, fonts (serif → sans), footer removal, rename |
| S3 | `2026-04-14-s3-data-audit-design.md` | Album DNA schema + re-audit descriptions + fill Spotify + repair artist images |
| S4 | `2026-04-14-s4-analytics-install-design.md` | Install privacy-friendly analytics (Umami default, Plausible alt) + wire events; feature triage deferred to a future session after 2–4 weeks of real data |

Originally a 9-item bug list from the user. Issue #7 ("which features are barely used?") was **deferred** — no analytics exist in the project today, so any triage call today would be heuristic. S4 installs the instrument; triage runs later from real data.

## Handoff mechanism

Each session is a cleared chat. Handoffs happen through three channels:

1. **Spec file on disk** (authoritative scope). Next session reads only `docs/superpowers/specs/2026-04-14-s{N}-*.md` — not this master, not the previous session's spec. The master is the index for a human reader.
2. **Memory entries** in `~/.claude/projects/.../memory/` — decisions that persist across all sessions (new fonts, rename locked, serif ban reinstated, analytics installed). Each session updates relevant entries at completion.
3. **Shared log** at `docs/superpowers/logs/2026-04-14-overhaul-log.md` — appended at the END of every session with: what shipped, what deferred, any follow-up items.

**Chain rule:** each session's LAST step is to write the *next* session's kickoff prompt into a new code block in the log file, so the user can grab it and paste it into a cleared chat.

## Shared conventions

- **Commits:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `chore:`). One semantically coherent commit per session minimum; more OK if logical.
- **Deploy:** `npm run deploy` (GitHub Pages) after each session if it changed user-facing behavior. S3 may skip deploy until data is verified.
- **Memory reversal:** `feedback_serif_override.md` currently whitelists serif fonts. S2 must delete it and replace with a new feedback entry that reinstates the no-serif rule. Reason given at the time was "nostalgic aesthetic" — that's overridden by the user's 2026-04-14 feedback that serif "feels so old."
- **No emojis** anywhere (code, UI, commits, spec files). Global user rule.
- **Traditional Chinese** if any Chinese appears. None expected in this project.

## Non-goals

- Do NOT redesign layouts, add features, or refactor unrelated code.
- Do NOT touch the React Flow artist graph logic, the weather-mood engine, or the seeded random picker — all three are working.
- Do NOT add server-side anything. Stays static site on GitHub Pages.

## Files referenced across sessions

- `index.html` — title, meta, fonts, manifest link, loading screen
- `src/index.css` — font tokens (Tailwind v4 `@theme`)
- `src/components/layout/Footer.tsx` — deletion candidate in S2
- `src/components/SEO.tsx` — title/OG strings
- `src/pages/Album.tsx` — "Why It Matters" heading removal in S3
- `src/data/albums.json` — schema migration in S3
- `src/data/artists.json` — image URL audit in S3
- `src/types/*` — Album type update in S3
- `public/favicon.svg` — source for PWA icon rasterization (do NOT modify; generate PNGs from it)
- `public/manifest.webmanifest` — to be created in S2
- `scripts/*.py` — extensive prior data-pipeline work; reuse patterns, don't reinvent

## Open questions

None at start of S2. If blockers arise mid-session, log them and stop — don't improvise around ambiguity.

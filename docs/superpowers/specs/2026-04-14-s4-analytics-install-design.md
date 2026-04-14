# S4 — Analytics Install (Triage Deferred)

**Parent:** `2026-04-14-overhaul-master.md`
**Scope:** Install privacy-friendly web analytics (Umami by default; Plausible as opt-in alternative) + wire custom events for key features. **Do NOT prune features this session.** Feature triage was deferred by the user from S1 because no usage data currently exists — guessing would waste effort. This session installs the instrument. A future session (after 2–4 weeks of traffic) does the triage.

## Provider decision — to be confirmed at session kickoff

**Default recommendation: Umami Cloud (free tier) — 3 sites, 100k events/month. Supports custom events via `umami.track()`. No cookie banner, GDPR-friendly.**

Alternatives with honest trade-offs:

| Provider | Cost | Custom events | Cookie banner | Notes |
|---|---|---|---|---|
| **Umami Cloud** | Free (100k events/mo) | Yes, good API | No | Recommended default. |
| **Plausible Cloud** | $9/mo (30-day trial only — no free tier) | Yes | No | Polished UX, 1 kB script. Worth the $9 only if you enjoy the UI. |
| **GoatCounter** | Free (non-commercial) | Yes, via API | No | Lightest; custom-event UX is rougher. |
| **Cloudflare Web Analytics** | Free, unlimited | No (page views only) | No | Eliminated: we need custom events. |
| **Google Analytics 4** | Free | Yes | Required in EU | Eliminated: cookie banner and PII concerns. |
| **Self-host (Plausible CE / Umami self-hosted)** | Hosting cost | Yes | No | Eliminated: overhead not worth it for a personal site. |

**Rest of this spec assumes Umami Cloud.** If user picks Plausible at session start, substitute the script tag and rename `umami.track(...)` calls to `window.plausible(...)` — API shape is similar. Everything else in this spec is unchanged.

## 1. Install Umami (default) or Plausible

### Manual step (must happen before Claude can ship the code)
User signs up (Umami Cloud at `cloud.umami.is` OR Plausible at `plausible.io`) and registers the site `litostswirrl.github.io/jazz-albums-recommender`. User provides the resulting script tag (Umami gives a `data-website-id`, Plausible gives `data-domain`) and pastes it into the chat. **Claude cannot do this step — session must pause and ask.**

### Steps (Umami path — default)
1. Add the Umami script to `index.html` `<head>` with the user-provided `data-website-id`:
   ```html
   <script defer src="https://cloud.umami.is/script.js" data-website-id="USER_PROVIDED_ID"></script>
   ```
2. Expose `umami` on `window` for TypeScript. Create `src/types/analytics.d.ts`:
   ```ts
   declare global {
     interface Window {
       umami?: {
         track: (event: string, data?: Record<string, string | number | boolean>) => void;
       };
     }
   }
   export {};
   ```
3. Create `src/utils/analytics.ts`:
   ```ts
   export function track(event: string, props?: Record<string, string | number | boolean>) {
     if (typeof window === 'undefined' || !window.umami) return;
     window.umami.track(event, props);
   }
   ```
   This keeps call sites clean AND no-ops when the script is blocked (ad blockers, no-JS environments).

### Steps (Plausible path — if user chose it instead)
Same pattern, different names. Script tag:
```html
<script defer data-domain="litostswirrl.github.io/jazz-albums-recommender" src="https://plausible.io/js/script.tagged-events.js"></script>
```
`track()` helper calls `window.plausible(event, { props })`.

## 2. Wire custom events

Instrument the following events. Keep event names `snake_case`, keep prop values string/number/bool (both Umami and Plausible require this).

| Event name | Where it fires | Props |
|---|---|---|
| `album_click` | Any album card click (carousels, grid, related-albums, today's pick) | `{ album_id: string, source: 'home_carousel' \| 'album_grid' \| 'related' \| 'todays_pick' \| 'search' \| 'artist_page' \| 'random' }` |
| `artist_click` | Any artist link click | `{ artist_id: string, source: string }` |
| `era_click` | Era timeline tile or era chip | `{ era_id: string }` |
| `random_spin` | "Vinyl Reveal" random picker button | `{ era_filter: string \| 'none' }` |
| `search_submit` | Spotlight search (from the 2026-03-20 spec) | `{ query_length: number, had_results: boolean }` |
| `todays_pick_click` | A Today's Pick tile is clicked | `{ album_id: string }` |
| `graph_node_click` | React Flow artist node is clicked on the influence graph | `{ artist_id: string }` |
| `spotify_open` | "Open in Spotify" button | `{ album_id: string }` |
| `apple_music_open` | "Open in Apple Music" button | `{ album_id: string }` |
| `add_to_homescreen` | `beforeinstallprompt` accepted (if we can hook it) | `{}` |

### Implementation pattern
For each event, find the existing component/handler, import `track`, call it inside the click/submit handler. Example:
```ts
import { track } from '@/utils/analytics';
// inside onClick:
track('album_click', { album_id: album.id, source: 'home_carousel' });
```

### Out of scope
- Do NOT track user identity. No PII.
- Do NOT track geolocation coordinates (we already get rough weather via IP — don't log user lat/lng).
- Do NOT track the exact search query text (log only length + hit count).
- Do NOT add session replay, heatmaps, or any third-party tool beyond the chosen analytics provider.

## 3. Deferred: feature triage

This is NOT in S4 scope. It's captured here so the user remembers why.

Once 2–4 weeks of data accumulates, a future session should:
1. Pull the analytics dashboard numbers for every tracked event.
2. Identify features with ≤ some threshold (e.g., < 1% of sessions) of engagement.
3. Present the candidates for removal. User decides.

Candidate features worth scrutinizing once data exists (NOT to be pre-judged in S4):
- Today's Pick (weather-mood engine — complex, but is anyone clicking through?)
- Random Album Picker (fun but maybe one-use)
- Artist influence graph (expensive to render; is it getting opened?)
- Genre Collections vs Era Carousels vs Artist Spotlight (overlap?)
- Quick Links Grid (nav redundancy?)

Record this list in the S4 log entry for the future-triage session to pick up.

## 4. Completion checklist

- [ ] Analytics account set up (Umami Cloud or Plausible, per user choice at kickoff); site registered; user provided the tracking ID/domain
- [ ] Script tag added to `index.html`
- [ ] `src/types/analytics.d.ts` exists; `npm run typecheck` passes
- [ ] `src/utils/analytics.ts` exists with `track()` helper
- [ ] All events in the table above wired at the correct sites
- [ ] `npm run dev` — open DevTools network tab, trigger each event, verify the provider's collector endpoint (e.g. `cloud.umami.is/api/send` or `plausible.io/api/event`) receives the call with correct event name + props
- [ ] `npm run build` and `npm run typecheck` pass
- [ ] Commit + deploy
- [ ] Log entry appended; triage candidate list recorded for future session
- [ ] Memory: capture that analytics are now installed, with the date to revisit (~2026-05-12 for 4 weeks)

## Memory entries to create/update

1. **Create** a project memory: "Web analytics installed 2026-04-14 using [Umami Cloud | Plausible — whichever was chosen]. Tracked events: [list]. Feature triage session should run on/after 2026-05-12 using the analytics dashboard."
2. **Update** `MEMORY.md`.

## No S5 kickoff prompt

Unlike S2 and S3, S4 does NOT write a kickoff prompt for a "next session," because the next session is data-dependent and happens weeks later. Instead, the log entry should include a note: "Revisit triage on or after 2026-05-12. To start, paste this into a fresh chat: `Open the analytics dashboard for the jazz site. Pull all event counts over the last 4 weeks. Rank features by engagement. Recommend cuts to the user, with dashboard numbers as evidence for each.`"

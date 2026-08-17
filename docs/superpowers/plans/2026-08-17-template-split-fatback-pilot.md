# Template Split + Fatback Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert this repo into a multi-site template (per-site data packs + config, one codebase) and deploy the Fatback funk/soul scaffold as a second Firebase hosting site, with the jazz site (Smack Cats) behaviorally unchanged.

**Architecture:** A `@site` Vite alias resolves to `src/sites/${VITE_SITE}` (default `jazz`) at build time; each site folder holds `config.ts`, `data/`, and `public/`. Feature flags in config gate routes and nav. `index.html` gets per-site values via a `transformIndexHtml` plugin. Firebase hosting targets deploy each site separately from the same project.

**Tech Stack:** React 19, TypeScript strict, Vite 7, Tailwind 4, Firebase Hosting (project `smack-cats-jazz`), Node scripts for validation.

**Spec:** `docs/superpowers/specs/2026-08-17-template-split-fatback-pilot-design.md`

**Scope:** Spec Phases 1–2 only. Phases 3–4 (content production, paths, launch polish) are curation work managed via the checkpoints file, not this plan.

## Global Constraints

- Jazz site is regression-frozen: after every task, `npm run typecheck` and a jazz build must pass, and jazz behavior must be identical. Any jazz-visible change is a bug.
- No code comments (except pragmas or genuinely non-obvious workarounds). No `any`. `interface` over `type`. Surgical diffs.
- There is no test framework in this repo and this plan does not add one. The test cycle per task is: `npm run typecheck` + `VITE_SITE=jazz npx vite build` (+ task-specific checks stated in the task). The validation script (Task 8) is tested by running it against a passing and a deliberately broken pack.
- Data JSON schemas are untouched. Jazz data files move but their content never changes.
- "jazz" as a data value (era ids like `early-jazz`, `cool-jazz`, genre strings) is NOT copy and must not be touched. Only user-visible copy and site identity strings move to config.
- Deploys are verified by loading the live URL, never by exit code.
- Conventional Commits; commit at the end of every task.
- macOS-only scripts are acceptable (`VITE_SITE=x` inline env syntax).

## File Structure

```
src/
├── sites/
│   ├── jazz/
│   │   ├── config.ts          # SiteConfig for Smack Cats (Task 2, 3)
│   │   ├── data/              # moved from src/data/ verbatim (Task 1)
│   │   └── public/            # moved from public/ minus sw.js, 404.html (Task 5)
│   └── funk/
│       ├── config.ts          # SiteConfig for Fatback (Task 10)
│       ├── data/              # placeholder pack + empty stubs (Task 10)
│       └── public/            # Fatback manifest/icons/robots/sitemap (Task 11)
├── types/site.ts              # SiteFeatures, SiteConfig, SiteCopy (Task 2)
public-shared/                 # sw.js, 404.html — copied into dist post-build (Task 5)
scripts/validate_site_pack.mjs # pack schema validation, runs pre-build (Task 8)
vite.config.ts                 # alias, publicDir, html transform, shared-copy plugin
firebase.json / .firebaserc    # hosting targets jazz + funk (Task 7, 12)
```

---

### Task 1: `@site` alias and jazz data move

**Files:**
- Modify: `vite.config.ts`, `tsconfig.app.json` (add `paths`)
- Move: `src/data/*` → `src/sites/jazz/data/` (git mv)
- Modify: the 19 files importing from `data/` (list below)

**Interfaces:**
- Produces: import specifier `@site/data/<file>.json` used by all later tasks; `SITE` build switch `VITE_SITE` (default `jazz`).

- [ ] **Step 1: Move the data**

```bash
mkdir -p src/sites/jazz
git mv src/data src/sites/jazz/data
```

- [ ] **Step 2: Add the alias in `vite.config.ts`**

```ts
import path from 'node:path'

const site = process.env.VITE_SITE ?? 'jazz'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/',
  resolve: {
    alias: { '@site': path.resolve(__dirname, `src/sites/${site}`) },
  },
  ...
})
```

- [ ] **Step 3: Add TS paths in `tsconfig.app.json`** (typecheck resolves against jazz; funk data is validated by Task 8's script instead)

```jsonc
"compilerOptions": {
  ...,
  "baseUrl": ".",
  "paths": { "@site/*": ["src/sites/jazz/*"] }
}
```

- [ ] **Step 4: Rewrite the imports**

Files: `src/utils/historicalContext.ts`, `src/utils/coverUrl.ts`, `src/utils/eventAlbumMatcher.ts`, `src/utils/connections.ts`, `src/components/home/DiscoverSection.tsx`, `src/components/layout/SearchBar.tsx`, `src/components/context/HistoricalEventCard.tsx`, `src/pages/{Paths,Artists,Home,Album,Path,Artist,Era,Timeline,Eras,ParallelTimeline,InfluenceGraph,Albums}.tsx`.

Every `'../data/X.json'` or `'../../data/X.json'` becomes `'@site/data/X.json'`:

```bash
grep -rl "data/.*\.json" src --include="*.ts" --include="*.tsx" | xargs sed -i '' -E "s#'(\.\./)+data/([A-Za-z]+\.json)'#'@site/data/\2'#g"
```

Then verify nothing was missed: `grep -rn "\.\./data/" src` must return nothing.

- [ ] **Step 5: Verify**

Run: `npm run typecheck && VITE_SITE=jazz npx vite build`
Expected: both pass. Then `npx vite preview`, open `http://localhost:4173`, confirm Home renders with albums.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "refactor(template): move jazz data to src/sites/jazz, add @site alias"
```

---

### Task 2: Site config module

**Files:**
- Create: `src/types/site.ts`
- Create: `src/sites/jazz/config.ts`
- Modify: `src/components/SEO.tsx`, `src/utils/colors.ts`, `src/components/layout/Header.tsx` (brand name only)

**Interfaces:**
- Produces:

```ts
// src/types/site.ts
export interface SiteFeatures {
  connections: boolean;
  historicalEvents: boolean;
  discover: boolean;
}

export interface SiteCopy {
  homeTitle: string;
  homeDescription: string;
}
// SiteCopy grows named string fields in Task 3 — named fields only, no index signature.

export interface SiteConfig {
  id: string;
  name: string;
  tagline: string;
  url: string;
  seoDescription: string;
  fallbackColors: string[];
  features: SiteFeatures;
  analyticsWebsiteId: string;
  copy: SiteCopy;
}
```

- Consumers import it as `import { siteConfig } from '@site/config'`.

- [ ] **Step 1: Write `src/types/site.ts`** with the interfaces above.

- [ ] **Step 2: Write `src/sites/jazz/config.ts`**

```ts
import type { SiteConfig } from '../../types/site';

export const siteConfig: SiteConfig = {
  id: 'jazz',
  name: 'Smack Cats',
  tagline: 'A Personal Jazz Companion',
  url: 'https://smack-cats-jazz.web.app',
  seoDescription:
    'A curated guide to 1000 jazz albums from New Orleans to today. Explore jazz history, discover artists, and understand how they shaped each other.',
  fallbackColors: [
    '#6b6358', '#7a7168', '#897f75', '#988d83',
    '#a79b90', '#b6a99d', '#c5b8ab', '#d4c7b9',
  ],
  features: { connections: true, historicalEvents: true, discover: true },
  analyticsWebsiteId: '64877654-bcc7-40f4-a769-e8744a6c519a',
  copy: {
    homeTitle: 'Your Jazz Library',
    homeDescription: '1000 jazz albums, 275 artists, 8 eras.',
  },
};
```

- [ ] **Step 3: Consume it**

`SEO.tsx`: replace the hard-coded `'Smack Cats'` and `siteUrl` with `siteConfig.name` / `siteConfig.url`.
`colors.ts`: `export const FALLBACK_COLORS = siteConfig.fallbackColors;` (drop the literal array; keep `hashColor` unchanged).
`Header.tsx`: the brand `<Link to="/">` text becomes `{siteConfig.name}`.
`src/pages/Home.tsx`: the `title=`/`description=` SEO props become `siteConfig.copy.homeTitle` / `siteConfig.copy.homeDescription`.

- [ ] **Step 4: Verify**

Run: `npm run typecheck && VITE_SITE=jazz npx vite build`
Expected: pass. Preview: header still reads "Smack Cats", Home tab title unchanged.

- [ ] **Step 5: Commit** — `feat(template): site config module, jazz config`

---

### Task 3: Copy sweep — no jazz copy outside `src/sites/`

**Files:**
- Modify: `src/types/site.ts` (grow `SiteCopy`), `src/sites/jazz/config.ts`, and every component the audit surfaces (expected: `src/pages/*.tsx`, `src/components/home/*`, `src/components/layout/Header.tsx`, `src/components/context/*`).

**Interfaces:**
- Produces: extended `SiteCopy` with one named string field per moved string (e.g. `albumsPageTitle`, `erasIntro`, `timelineTitle`...). Funk config (Task 10) must fill every field, so keep fields generic-purpose, not jazz-worded names.

- [ ] **Step 1: Audit**

Run: `grep -rn -i "jazz\|smack" src --include="*.ts" --include="*.tsx" | grep -v "src/sites/" | grep -v "@site"`

Classify every hit: (a) user-visible copy or site identity → move to `siteConfig.copy` as a named field; (b) data-value logic (era ids like `early-jazz`, genre strings compared against data) → leave untouched; (c) file/component names (`JazzMilestoneCard.tsx`) → leave (renaming is not copy; note in progress.md for later cleanup).

- [ ] **Step 2: Move category (a) strings** — add named fields to `SiteCopy` + jazz values in config, replace literals with `siteConfig.copy.<field>`.

- [ ] **Step 3: Verify the exit criterion**

Run the Step 1 grep again. Expected: remaining hits are only categories (b) and (c). Record the final hit list in progress.md.

Run: `npm run typecheck && VITE_SITE=jazz npx vite build`; preview and click through Home, Albums, Eras, Timeline — copy reads exactly as before.

- [ ] **Step 4: Commit** — `refactor(template): move site copy into site config`

---

### Task 4: Per-site `index.html` values

**Files:**
- Modify: `index.html`, `vite.config.ts`

**Interfaces:**
- Consumes: `siteConfig` (Task 2). `vite.config.ts` imports it directly: `const { siteConfig } = await import(`./src/sites/${site}/config`)` — top-level await is fine in vite.config bundling; if it is not, use a static `import` of both configs and pick by `site`.
- Produces: tokens `%SITE_NAME%`, `%SITE_TAGLINE%`, `%SITE_DESCRIPTION%`, `%SITE_URL%`, `%SITE_ANALYTICS%` in `index.html`.

- [ ] **Step 1: Tokenize `index.html`**

Replace every "Smack Cats" with `%SITE_NAME%`, the "A Personal Jazz Companion" title suffix with `%SITE_TAGLINE%` (title becomes `%SITE_NAME% — %SITE_TAGLINE%`), both meta descriptions with `%SITE_DESCRIPTION%`, any og:url with `%SITE_URL%`, and the entire Umami `<script ...>` line with `%SITE_ANALYTICS%`. The loading text and noscript text also use `%SITE_NAME%`.

- [ ] **Step 2: Add the transform plugin in `vite.config.ts`**

```ts
function siteHtml(config: SiteConfig): Plugin {
  const analytics = config.analyticsWebsiteId
    ? `<script defer src="https://cloud.umami.is/script.js" data-website-id="${config.analyticsWebsiteId}"></script>`
    : '';
  const tokens: Record<string, string> = {
    '%SITE_NAME%': config.name,
    '%SITE_TAGLINE%': config.tagline,
    '%SITE_DESCRIPTION%': config.seoDescription,
    '%SITE_URL%': config.url,
    '%SITE_ANALYTICS%': analytics,
  };
  return {
    name: 'site-html',
    transformIndexHtml: html =>
      Object.entries(tokens).reduce((h, [k, v]) => h.replaceAll(k, v), html),
  };
}
```

Register it in `plugins`.

- [ ] **Step 3: Verify**

Run: `VITE_SITE=jazz npx vite build && grep -c "Smack Cats" dist/index.html && grep -c "64877654" dist/index.html && grep -c "%SITE_" dist/index.html`
Expected: Smack Cats count matches the pre-change count, Umami id present once, `%SITE_` count is 0.

- [ ] **Step 4: Commit** — `feat(template): per-site index.html via transformIndexHtml`

---

### Task 5: Per-site public assets

**Files:**
- Move: `public/{manifest.webmanifest,favicon.svg,icon-192.png,icon-512.png,apple-touch-icon.png,robots.txt,sitemap.xml,covers}` → `src/sites/jazz/public/`
- Move: `public/{sw.js,404.html}` → `public-shared/`
- Modify: `vite.config.ts`

- [ ] **Step 1: git mv as listed above** (then `rmdir public`).

- [ ] **Step 2: Wire vite**

In `defineConfig`: `publicDir: `src/sites/${site}/public``. Add a post-build copy plugin:

```ts
import { copyFileSync, mkdirSync, readdirSync } from 'node:fs'

function sharedPublic(): Plugin {
  return {
    name: 'shared-public',
    closeBundle() {
      mkdirSync('dist', { recursive: true });
      for (const f of readdirSync('public-shared'))
        copyFileSync(`public-shared/${f}`, `dist/${f}`);
    },
  };
}
```

- [ ] **Step 3: Verify**

Run: `VITE_SITE=jazz npx vite build && ls dist/sw.js dist/404.html dist/manifest.webmanifest && ls dist/covers | wc -l`
Expected: all present; covers count matches `ls src/sites/jazz/public/covers | wc -l`. Dev check: `VITE_SITE=jazz npx vite` serves `/favicon.svg`.

- [ ] **Step 4: Commit** — `refactor(template): split public assets per site + shared sw/404`

---

### Task 6: Feature flags gate routes and nav

**Files:**
- Modify: `src/App.tsx`, `src/components/layout/Header.tsx`, `src/pages/Home.tsx`

**Interfaces:**
- Consumes: `siteConfig.features` (Task 2).

- [ ] **Step 1: Gate routes in `App.tsx`**

```tsx
{siteConfig.features.connections && <Route path="/influence" element={<InfluenceGraph />} />}
{siteConfig.features.historicalEvents && <Route path="/context" element={<ParallelTimeline />} />}
```

Unregistered paths fall through to the existing `*` NotFound route. `/timeline`, `/paths`, `/discover`-redirect stay unconditional.

- [ ] **Step 2: Gate nav in `Header.tsx`** — wrap the `/influence` and `/context` links (desktop Explore dropdown around lines 75–91 and their mobile-menu counterparts) in the same flag conditions.

- [ ] **Step 3: Gate Discover on Home** — in `Home.tsx`, render the lazy `DiscoverSection` only when `siteConfig.features.discover` is true, so the recommendations chunk is never requested when off.

- [ ] **Step 4: Verify** — `npm run typecheck && VITE_SITE=jazz npx vite build`; preview: Explore menu unchanged, `#/influence` and `#/context` load, Discover section renders (jazz flags are all true, so this task must be behavior-neutral). Temporarily flip a flag in dev to see the route vanish, then revert before commit (`git diff` must show no config change).

- [ ] **Step 5: Commit** — `feat(template): feature flags gate connections/context/discover`

---

### Task 7: Build scripts and Firebase hosting targets (jazz side)

**Files:**
- Modify: `package.json`, `firebase.json`, `.firebaserc`

- [ ] **Step 1: Scripts in `package.json`** (drop `predeploy`; each deploy builds its own site)

```jsonc
"dev": "npm run dev:jazz",
"dev:jazz": "VITE_SITE=jazz vite",
"dev:funk": "VITE_SITE=funk vite",
"typecheck": "tsc -b",
"build": "npm run build:jazz",
"build:jazz": "node scripts/validate_site_pack.mjs jazz && VITE_SITE=jazz vite build",
"build:funk": "node scripts/validate_site_pack.mjs funk && VITE_SITE=funk vite build",
"preview": "vite preview",
"deploy": "npm run deploy:jazz",
"deploy:jazz": "npm run build:jazz && firebase deploy --only hosting:jazz --project smack-cats-jazz",
"deploy:funk": "npm run build:funk && firebase deploy --only hosting:funk --project smack-cats-jazz"
```

(Validation script lands in Task 8; until then `build:*` will fail on the missing script — Tasks 7 and 8 are committed together only if the executor wants green in between; otherwise accept one red step within the task pair and order Task 8 immediately after.)

- [ ] **Step 2: Convert `firebase.json` to target form** — hosting becomes an array with one entry, `"target": "jazz"`, all existing `public/ignore/rewrites/headers` values copied verbatim.

- [ ] **Step 3: Map the target**

```bash
firebase target:apply hosting jazz smack-cats-jazz --project smack-cats-jazz
```

`.firebaserc` gains the `targets` block; commit it.

- [ ] **Step 4: Verify** — after Task 8: `npm run build:jazz` passes; `firebase deploy --only hosting:jazz --project smack-cats-jazz` dry-check deferred to Task 9 (the phase gate deploys for real).

- [ ] **Step 5: Commit** — `build(template): per-site scripts + firebase hosting target jazz`

---

### Task 8: Site pack validation script

**Files:**
- Create: `scripts/validate_site_pack.mjs`

**Interfaces:**
- Produces: `node scripts/validate_site_pack.mjs <siteId>` — exit 0 on valid pack, exit 1 with per-file field errors. Consumed by `build:*` scripts (Task 7).

- [ ] **Step 1: Write the script**

```js
import { readFileSync } from 'node:fs';

const site = process.argv[2];
if (!site) { console.error('usage: validate_site_pack.mjs <siteId>'); process.exit(1); }
const dir = `src/sites/${site}/data`;

const REQUIRED = {
  'albums.json': ['id', 'title', 'artist', 'artistId', 'year', 'era', 'albumDNA'],
  'artists.json': ['id', 'name'],
  'eras.json': ['id', 'name', 'period', 'years', 'description', 'color'],
  'paths.json': [],
  'connections.json': [],
  'historicalEvents.json': [],
};

let failed = false;
for (const [file, fields] of Object.entries(REQUIRED)) {
  let json;
  try {
    json = JSON.parse(readFileSync(`${dir}/${file}`, 'utf8'));
  } catch (e) {
    console.error(`${file}: unreadable (${e.message})`);
    failed = true;
    continue;
  }
  const items = Array.isArray(json) ? json : [];
  items.forEach((item, i) => {
    for (const f of fields)
      if (item[f] === undefined || item[f] === '') {
        console.error(`${file}[${i}] (${item.id ?? '?'}): missing ${f}`);
        failed = true;
      }
  });
}
const albumEras = new Set(JSON.parse(readFileSync(`${dir}/eras.json`, 'utf8')).map(e => e.id));
for (const a of JSON.parse(readFileSync(`${dir}/albums.json`, 'utf8')))
  if (!albumEras.has(a.era)) {
    console.error(`albums.json (${a.id}): unknown era ${a.era}`);
    failed = true;
  }
process.exit(failed ? 1 : 0);
```

Also require presence (readable JSON, any shape) of: `albumsDetail.json`, `artistsDetail.json`, `coverManifest.json`, `recommendations.json`, `recCoverManifest.json` — add a simple parse-only loop over those names.

- [ ] **Step 2: Test pass case** — `node scripts/validate_site_pack.mjs jazz` → exit 0.

- [ ] **Step 3: Test fail case**

```bash
mkdir -p src/sites/tmpbroken/data
cp src/sites/jazz/data/*.json src/sites/tmpbroken/data/
python3 -c "
import json
p = 'src/sites/tmpbroken/data/albums.json'
a = json.load(open(p))
del a[0]['albumDNA']
a[1]['era'] = 'no-such-era'
json.dump(a, open(p, 'w'))
"
node scripts/validate_site_pack.mjs tmpbroken
```

Expected: exit 1, errors naming album 0's missing `albumDNA` and album 1's unknown era. Then `rm -rf src/sites/tmpbroken`.

- [ ] **Step 4: Verify build wiring** — `npm run build:jazz` runs validation then builds; both green.

- [ ] **Step 5: Commit** — `feat(template): site pack validation gate in build`

---

### Task 9: Phase 1 gate — jazz regression check and deploy

**Files:** none (verification only)

- [ ] **Step 1:** `npm run typecheck && npm run build:jazz` — green.
- [ ] **Step 2:** `npx vite preview`; click through every route: `/`, `/albums`, one `/album/:id`, `/artists`, one `/artist/:id`, `/eras`, one `/era/:id`, `/paths`, one `/path/:id`, `/timeline`, `/influence`, `/context`, a bad URL (NotFound). Confirm: copy identical, covers load, Discover section renders, search works.
- [ ] **Step 3:** `npm run deploy:jazz`; load https://smack-cats-jazz.web.app in the browser, repeat a spot-check (Home, one album, one artist). Check the PWA still updates (hard reload; sw.js served with no-cache).
- [ ] **Step 4:** Checkpoint per the checkpoints file contract: progress.md What/Why/Next + 狀態 update, commit `docs: phase 1 checkpoint`.

---

### Task 10: Fatback site config + placeholder data pack

**Files:**
- Create: `src/sites/funk/config.ts`, `src/sites/funk/data/*.json`

**Interfaces:**
- Consumes: `SiteConfig` and the full post-Task-3 `SiteCopy` field list from `src/types/site.ts`. Note: `tsc` typechecks against jazz only (tsconfig paths), so funk's config is verified by `npm run build:funk` (Vite resolves `@site` → funk; the config file's own type annotation surfaces missing fields) plus the validation script.

- [ ] **Step 1: `src/sites/funk/config.ts`**

```ts
import type { SiteConfig } from '../../types/site';

export const siteConfig: SiteConfig = {
  id: 'funk',
  name: 'Fatback',
  tagline: 'An Instrumental Funk & Soul Guide',
  url: 'https://fatback.web.app',
  seoDescription:
    'A curated guide to instrumental funk and soul — from soul-jazz roots to the new pocket. Built for the groove, safe for the party.',
  fallbackColors: [
    '#5c3a21', '#7a4a24', '#985a26', '#b56d28',
    '#c98634', '#d9a04a', '#c2762f', '#8a5527',
  ],
  features: { connections: false, historicalEvents: false, discover: false },
  analyticsWebsiteId: '',
  copy: {
    homeTitle: 'Your Funk Library',
    homeDescription: 'Instrumental funk and soul, from soul-jazz roots to the new pocket.',
  },
};
```

The `copy` object must fill every field `SiteCopy` has after Task 3's sweep — open `src/types/site.ts`, write a funk-worded value for each field beyond the two shown (the type annotation makes omissions a build error).

(`url` updated in Task 12 if the slug falls back to `fatback-funk`.)

- [ ] **Step 2: `eras.json`** — the 6 eras from spec §4, each with id/name/period/years/description/characteristics/keyArtists/color. Era ids: `soul-jazz-roots`, `classic-funk`, `jazz-funk`, `pfunk-boogie`, `rare-groove-revival`, `new-pocket`. Colors: 6 steps of the warm palette above. Descriptions: 2–3 factual sentences each, verifiable claims only.

- [ ] **Step 3: placeholder albums + artists** — 10 canonical, easily verifiable albums spanning the eras, e.g.: Booker T & the MG's *Green Onions* (1962), Jimmy Smith *Back at the Chicken Shack* (1963), The Meters *The Meters* (1969), James Brown *Sex Machine* (1970), Herbie Hancock *Head Hunters* (1973), Sly & the Family Stone *There's a Riot Goin' On* (1971), Parliament *Mothership Connection* (1975), The J.B.'s *Doing It to Death* (1973), El Michels Affair *Sounding Out the City* (2005), Vulfpeck *Thrill of the Arts* (2015). Each album: id, title, artist, artistId, year, label, era, genres, albumDNA (2–3 sentences, facts verified against Wikipedia before writing — zero-hallucination applies to placeholders too). `artists.json`: one entry per artist referenced (id, name, plus whatever fields the jazz artist schema marks required — copy field shape from a jazz entry).

- [ ] **Step 4: stubs** — `connections.json`: `[]`; `historicalEvents.json`: `[]`; `paths.json`: same top-level shape as jazz's (copy its structure, empty routes list or one placeholder path over the 10 albums); `albumsDetail.json` / `artistsDetail.json` / `coverManifest.json` / `recCoverManifest.json`: `{}`; `recommendations.json`: same top-level shape as jazz's with empty arrays (open jazz's to copy the shape).

- [ ] **Step 5: Verify** — `node scripts/validate_site_pack.mjs funk` exit 0; `npm run build:funk` green; `npm run dev:funk` → header reads "Fatback", 10 albums listed, no Explore entries for influence/context, no Discover section, `#/influence` shows NotFound.

- [ ] **Step 6: Commit** — `feat(fatback): site config + placeholder data pack`

---

### Task 11: Fatback public assets

**Files:**
- Create: `src/sites/funk/public/{favicon.svg,icon-192.png,icon-512.png,apple-touch-icon.png,manifest.webmanifest,robots.txt,sitemap.xml}`

- [ ] **Step 1: favicon.svg** — hand-written: dark-brown rounded square, mustard "F" in a bold sans, e.g. `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#5c3a21"/><text x="32" y="44" font-family="Arial Black, sans-serif" font-size="36" font-weight="900" fill="#d9a04a" text-anchor="middle">F</text></svg>`

- [ ] **Step 2: PNG icons** — render the SVG at 192/512/180 via Pillow (`python3 -c "import PIL"` to check; if missing, `python3 -m pip install --user pillow cairosvg` — if cairosvg is troublesome, draw the rect+text directly in Pillow, no SVG rasterization needed).

- [ ] **Step 3: manifest.webmanifest** — copy jazz's, change name/short_name to "Fatback", theme/background colors to `#5c3a21`, icon paths unchanged.

- [ ] **Step 4: robots.txt** (copy jazz's) and `sitemap.xml` (root URL only for the scaffold).

- [ ] **Step 5: Verify** — `npm run build:funk`; `ls dist/manifest.webmanifest dist/icon-512.png dist/sw.js`; `grep Fatback dist/manifest.webmanifest`; confirm `dist/covers` does NOT exist and dist total size is small (`du -sh dist`).

- [ ] **Step 6: Commit** — `feat(fatback): PWA assets`

---

### Task 12: Fatback hosting site + first deploy (Phase 2 gate)

**Files:**
- Modify: `firebase.json` (add funk target entry), `.firebaserc` (target mapping), possibly `src/sites/funk/config.ts` (url, on slug fallback)

- [ ] **Step 1: Create the site**

```bash
firebase hosting:sites:create fatback --project smack-cats-jazz
```

If the slug is taken, retry with `fatback-funk` and update `url` in `src/sites/funk/config.ts` and `sitemap.xml`.

- [ ] **Step 2: Wire the target** — add second entry to the `firebase.json` hosting array (`"target": "funk"`, same public/ignore/rewrites/headers verbatim); `firebase target:apply hosting funk <site-id> --project smack-cats-jazz`.

- [ ] **Step 3: Deploy** — `npm run deploy:funk`.

- [ ] **Step 4: Verify live** — load the live URL in the browser: header "Fatback", tab title "Fatback — An Instrumental Funk & Soul Guide", 10 albums render, era pages work, `#/influence` → NotFound, no Umami script in page source, manifest served. Then load https://smack-cats-jazz.web.app and spot-check it is untouched.

- [ ] **Step 5: Commit + checkpoint** — `feat(fatback): hosting target + first deploy`; progress.md What/Why/Next; 狀態 update in the checkpoints file; this is the Phase 2 gate, so generate the Phase 3 resume prompt per the checkpointing contract if the window warrants.

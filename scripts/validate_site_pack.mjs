import { readFileSync } from 'node:fs';

const site = process.argv[2];
if (!site) {
  console.error('usage: validate_site_pack.mjs <siteId>');
  process.exit(1);
}
const dir = `src/sites/${site}/data`;

const REQUIRED = {
  'albums.json': ['id', 'title', 'artist', 'artistId', 'year', 'era', 'albumDNA'],
  'artists.json': ['id', 'name'],
  'eras.json': ['id', 'name', 'period', 'years', 'description', 'color'],
  'paths.json': [],
  'connections.json': [],
  'historicalEvents.json': [],
};

const PRESENCE_ONLY = [
  'albumsDetail.json',
  'artistsDetail.json',
  'coverManifest.json',
  'recommendations.json',
  'recCoverManifest.json',
];

let failed = false;
const parsed = {};

function load(file) {
  try {
    return JSON.parse(readFileSync(`${dir}/${file}`, 'utf8'));
  } catch (e) {
    console.error(`${file}: unreadable (${e.message})`);
    failed = true;
    return undefined;
  }
}

for (const [file, fields] of Object.entries(REQUIRED)) {
  const json = load(file);
  if (json === undefined) continue;
  parsed[file] = json;
  const items = Array.isArray(json) ? json : [];
  items.forEach((item, i) => {
    for (const f of fields)
      if (item[f] === undefined || item[f] === '') {
        console.error(`${file}[${i}] (${item.id ?? '?'}): missing ${f}`);
        failed = true;
      }
  });
}

for (const file of PRESENCE_ONLY) load(file);

const eras = parsed['eras.json'];
const albums = parsed['albums.json'];
if (Array.isArray(eras) && Array.isArray(albums)) {
  const eraIds = new Set(eras.map(e => e.id));
  for (const a of albums)
    if (!eraIds.has(a.era)) {
      console.error(`albums.json (${a.id}): unknown era ${a.era}`);
      failed = true;
    }
}

process.exit(failed ? 1 : 0);

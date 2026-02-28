const https = require('https');
const fs = require('fs');

const albums = require('../src/data/albums.json');
const artists = require('../src/data/artists.json');

const artistMap = new Map(artists.map(a => [a.id, a.name]));

const fakeUuidPattern = /-39f8-4c5e-9e5c-1f9c2d8b8d8d/;
const textIdPattern = /coverartarchive\.org\/release\/[a-z][a-z0-9-]+\/front$/;

const needsCovers = albums.filter(a => {
  if (!a.coverUrl) return true;
  if (fakeUuidPattern.test(a.coverUrl)) return true;
  if (textIdPattern.test(a.coverUrl)) return true;
  return false;
}).map(a => ({
  id: a.id,
  title: a.title,
  artist: artistMap.get(a.artistId) || a.artistId,
  year: a.year
}));

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function fetchJSON(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, {
      headers: { 'User-Agent': 'JazzAlbumsRecommender/1.0 (contact@example.com)' }
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(data) });
        } catch (e) {
          resolve({ status: res.statusCode, data: null });
        }
      });
    });
    req.on('error', reject);
  });
}

async function searchMusicBrainz(title, artist) {
  const query = encodeURIComponent(`release:"${title}" AND artist:"${artist}"`);
  const url = `https://musicbrainz.org/ws/2/release/?query=${query}&fmt=json&limit=5`;

  try {
    const result = await fetchJSON(url);
    if (result.status === 200 && result.data && result.data.releases) {
      return result.data.releases;
    }
  } catch (e) {
    console.error(`Error searching for ${title}: ${e.message}`);
  }
  return [];
}

async function checkCoverArt(mbid) {
  const url = `https://coverartarchive.org/release/${mbid}`;
  return new Promise((resolve) => {
    const req = https.get(url, {
      headers: { 'User-Agent': 'JazzAlbumsRecommender/1.0' }
    }, (res) => {
      resolve(res.statusCode === 200 || res.statusCode === 307);
    });
    req.on('error', () => resolve(false));
  });
}

async function findCoverUrl(album) {
  console.log(`Searching: ${album.title} - ${album.artist}`);

  const releases = await searchMusicBrainz(album.title, album.artist);

  for (const release of releases) {
    // Check if this release has cover art
    const hasCover = await checkCoverArt(release.id);
    await sleep(500); // Rate limit

    if (hasCover) {
      return {
        id: album.id,
        mbid: release.id,
        coverUrl: `https://coverartarchive.org/release/${release.id}/front`
      };
    }
  }

  return { id: album.id, mbid: null, coverUrl: null };
}

async function main() {
  const startIdx = parseInt(process.argv[2]) || 0;
  const endIdx = parseInt(process.argv[3]) || needsCovers.length;
  const batch = needsCovers.slice(startIdx, endIdx);

  console.log(`Processing albums ${startIdx + 1} to ${Math.min(endIdx, needsCovers.length)} of ${needsCovers.length}`);

  const results = [];

  for (let i = 0; i < batch.length; i++) {
    const album = batch[i];
    const result = await findCoverUrl(album);
    results.push(result);

    if (result.coverUrl) {
      console.log(`  ✓ Found: ${result.coverUrl}`);
    } else {
      console.log(`  ✗ No cover found`);
    }

    await sleep(1100); // MusicBrainz rate limit: 1 req/sec
  }

  // Output results
  const found = results.filter(r => r.coverUrl);
  console.log(`\nFound ${found.length}/${batch.length} covers`);
  console.log('\nResults JSON:');
  console.log(JSON.stringify(found, null, 2));
}

main().catch(console.error);

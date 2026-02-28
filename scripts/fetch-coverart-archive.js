// Script to fetch album covers from Cover Art Archive (CORS-friendly)
// Run with: node scripts/fetch-coverart-archive.js
// API: https://coverartarchive.org/

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const albumsPath = path.join(__dirname, '../src/data/albums.json');

const USER_AGENT = 'JazzAlbumsRecommender/1.0 (https://github.com/litostswirrl/jazz-albums-recommender)';

// Search MusicBrainz for album and get release MBID
async function searchMusicBrainz(title, artist) {
  try {
    const query = encodeURIComponent(`release:"${title}" AND artist:"${artist}"`);
    const searchUrl = `https://musicbrainz.org/ws/2/release/?query=${query}&fmt=json&limit=5`;

    const response = await fetch(searchUrl, {
      headers: {
        'User-Agent': USER_AGENT,
        'Accept': 'application/json',
      }
    });

    if (response.status === 503) {
      console.log('    Rate limited, waiting 5s...');
      await new Promise(resolve => setTimeout(resolve, 5000));
      return searchMusicBrainz(title, artist);
    }

    if (!response.ok) {
      return null;
    }

    const data = await response.json();

    if (data.releases && data.releases.length > 0) {
      // Return top matches for cover art checking
      return data.releases.slice(0, 3).map(r => r.id);
    }

    return null;
  } catch (error) {
    return null;
  }
}

// Check if Cover Art Archive has cover for a release
async function getCoverArtUrl(mbid) {
  try {
    // Use the Internet Archive's direct URL pattern which has CORS
    // Format: https://coverartarchive.org/release/{mbid}/front
    const checkUrl = `https://coverartarchive.org/release/${mbid}`;

    const response = await fetch(checkUrl, {
      headers: {
        'User-Agent': USER_AGENT,
        'Accept': 'application/json',
      }
    });

    if (!response.ok) {
      return null;
    }

    const data = await response.json();

    // Find front cover
    if (data.images && data.images.length > 0) {
      const front = data.images.find(img => img.front) || data.images[0];
      // Use the Archive.org thumbnail URL which has CORS support
      if (front.thumbnails && front.thumbnails['500']) {
        return front.thumbnails['500'];
      }
      if (front.thumbnails && front.thumbnails['large']) {
        return front.thumbnails['large'];
      }
      if (front.thumbnails && front.thumbnails['small']) {
        return front.thumbnails['small'];
      }
      // Fall back to image URL
      return front.image;
    }

    return null;
  } catch (error) {
    return null;
  }
}

async function main() {
  const albums = JSON.parse(fs.readFileSync(albumsPath, 'utf-8'));

  console.log(`Processing ${albums.length} albums...`);
  console.log('Using MusicBrainz + Cover Art Archive (CORS-friendly)\n');

  let updated = 0;
  let skipped = 0;
  let failed = 0;

  for (let i = 0; i < albums.length; i++) {
    const album = albums[i];

    // Skip if already has an archive.org cover (known to work with CORS)
    if (album.coverUrl && album.coverUrl.includes('archive.org')) {
      console.log(`✓ ${album.title} - already has Archive.org cover`);
      skipped++;
      continue;
    }

    console.log(`[${i + 1}/${albums.length}] "${album.title}" by ${album.artist}...`);

    // Search MusicBrainz for release MBIDs
    const mbids = await searchMusicBrainz(album.title, album.artist);

    if (!mbids || mbids.length === 0) {
      console.log(`  ✗ Not found in MusicBrainz`);
      failed++;
      // Rate limit for MusicBrainz: 1 request per second
      await new Promise(resolve => setTimeout(resolve, 1100));
      continue;
    }

    // Try each MBID to find one with cover art
    let foundCover = null;
    for (const mbid of mbids) {
      const coverUrl = await getCoverArtUrl(mbid);
      if (coverUrl) {
        foundCover = coverUrl;
        break;
      }
      // Small delay between cover art checks
      await new Promise(resolve => setTimeout(resolve, 300));
    }

    if (foundCover) {
      album.coverUrl = foundCover;
      updated++;
      console.log(`  ✓ Found cover`);
    } else {
      console.log(`  ✗ No cover art available`);
      failed++;
    }

    // Rate limit: 1 second between MusicBrainz requests
    await new Promise(resolve => setTimeout(resolve, 1100));
  }

  // Write updated data
  fs.writeFileSync(albumsPath, JSON.stringify(albums, null, 2));

  console.log(`\n========================================`);
  console.log(`Done!`);
  console.log(`  Updated: ${updated}`);
  console.log(`  Skipped (had cover): ${skipped}`);
  console.log(`  Failed: ${failed}`);
  console.log(`========================================`);
}

main().catch(console.error);

// Script to fetch album cover images from Discogs
// Run with: node scripts/fetch-discogs-covers.js
// Discogs API: https://www.discogs.com/developers

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const albumsPath = path.join(__dirname, '../src/data/albums.json');

const USER_AGENT = 'JazzAlbumsRecommender/1.0 +https://github.com/litostswirrl/jazz-albums-recommender';

// Search Discogs for an album and get cover image
async function searchDiscogs(title, artist) {
  try {
    // Clean up search terms
    const cleanTitle = title.replace(/['"]/g, '').trim();
    const cleanArtist = artist.replace(/['"]/g, '').trim();

    const query = encodeURIComponent(`${cleanTitle} ${cleanArtist}`);
    const searchUrl = `https://api.discogs.com/database/search?q=${query}&type=release&per_page=5`;

    const response = await fetch(searchUrl, {
      headers: {
        'User-Agent': USER_AGENT,
        'Accept': 'application/json',
      }
    });

    if (response.status === 429) {
      console.log('    Rate limited, waiting 60s...');
      await new Promise(resolve => setTimeout(resolve, 60000));
      return searchDiscogs(title, artist); // Retry
    }

    if (!response.ok) {
      console.log(`    Discogs search failed: ${response.status}`);
      return null;
    }

    const data = await response.json();

    if (data.results && data.results.length > 0) {
      // Find best match - prefer results with cover_image
      for (const result of data.results) {
        if (result.cover_image && !result.cover_image.includes('spacer.gif')) {
          return result.cover_image;
        }
      }
      // Fall back to thumb if no cover_image
      for (const result of data.results) {
        if (result.thumb && !result.thumb.includes('spacer.gif')) {
          return result.thumb;
        }
      }
    }

    return null;
  } catch (error) {
    console.log(`    Error: ${error.message}`);
    return null;
  }
}

async function main() {
  const albums = JSON.parse(fs.readFileSync(albumsPath, 'utf-8'));

  console.log(`Processing ${albums.length} albums...`);
  console.log('Note: Discogs rate limit is ~25 req/min for unauthenticated requests\n');

  let updated = 0;
  let skipped = 0;
  let failed = 0;

  for (let i = 0; i < albums.length; i++) {
    const album = albums[i];

    // Skip if already has a working cover (not Wikipedia/en or fake coverartarchive)
    const hasWorkingCover = album.coverUrl &&
      !album.coverUrl.includes('/wikipedia/en/') &&
      !album.coverUrl.match(/coverartarchive\.org\/release\/[a-z-]+\/front$/);

    if (hasWorkingCover) {
      console.log(`✓ ${album.title} - already has cover`);
      skipped++;
      continue;
    }

    console.log(`[${i + 1}/${albums.length}] Searching: "${album.title}" by ${album.artist}...`);

    const coverUrl = await searchDiscogs(album.title, album.artist);

    if (coverUrl) {
      album.coverUrl = coverUrl;
      updated++;
      console.log(`  ✓ Found cover`);
    } else {
      failed++;
      console.log(`  ✗ No cover found`);
    }

    // Rate limit: ~2.5 seconds between requests to stay under 25/min
    await new Promise(resolve => setTimeout(resolve, 2500));
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

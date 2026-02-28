// Script to fetch album cover images
// Run with: node scripts/fetch-album-covers.js

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const albumsPath = path.join(__dirname, '../src/data/albums.json');

// Search MusicBrainz for album and get cover art
async function searchMusicBrainz(title, artist) {
  try {
    // URL encode the query
    const query = encodeURIComponent(`release:"${title}" AND artist:"${artist}"`);
    const searchUrl = `https://musicbrainz.org/ws/2/release/?query=${query}&fmt=json&limit=1`;

    const response = await fetch(searchUrl, {
      headers: {
        'User-Agent': 'JazzAlbumsRecommender/1.0 (contact@example.com)'
      }
    });

    if (!response.ok) {
      console.log(`    MusicBrainz search failed: ${response.status}`);
      return null;
    }

    const data = await response.json();

    if (data.releases && data.releases.length > 0) {
      const mbid = data.releases[0].id;
      // Check if cover art exists
      const coverUrl = `https://coverartarchive.org/release/${mbid}/front-250`;

      // Test if the cover exists (don't follow redirect, just check status)
      const coverResponse = await fetch(coverUrl, {
        method: 'HEAD',
        redirect: 'manual'
      });

      // 307 redirect means cover exists
      if (coverResponse.status === 307 || coverResponse.status === 302) {
        return coverUrl;
      }
    }

    return null;
  } catch (error) {
    console.log(`    Error: ${error.message}`);
    return null;
  }
}

// Try to get album image from Wikipedia
async function getWikipediaAlbumImage(title, artist) {
  try {
    // Try common Wikipedia article title formats for albums
    const queries = [
      `${title} (album)`,
      `${title} (${artist} album)`,
      title
    ];

    for (const query of queries) {
      const apiUrl = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(query)}`;
      const response = await fetch(apiUrl);

      if (response.ok) {
        const data = await response.json();
        if (data.originalimage?.source || data.thumbnail?.source) {
          return data.originalimage?.source || data.thumbnail?.source;
        }
      }

      await new Promise(resolve => setTimeout(resolve, 100));
    }

    return null;
  } catch (error) {
    return null;
  }
}

async function main() {
  const albums = JSON.parse(fs.readFileSync(albumsPath, 'utf-8'));

  console.log(`Processing ${albums.length} albums...`);

  let updated = 0;
  let failed = 0;

  // Only process first 50 albums to avoid rate limiting
  const albumsToProcess = albums.slice(0, 60);

  for (const album of albumsToProcess) {
    // Skip if has valid coverUrl (not coverartarchive.org with fake MBID)
    if (album.coverUrl && !album.coverUrl.includes('coverartarchive.org/release/')) {
      console.log(`✓ ${album.title} already has cover`);
      continue;
    }

    console.log(`Fetching cover for "${album.title}" by ${album.artist}...`);

    // Try MusicBrainz/Cover Art Archive first
    let coverUrl = await searchMusicBrainz(album.title, album.artist);

    if (!coverUrl) {
      // Fallback to Wikipedia
      console.log(`    Trying Wikipedia...`);
      coverUrl = await getWikipediaAlbumImage(album.title, album.artist);
    }

    if (coverUrl) {
      album.coverUrl = coverUrl;
      updated++;
      console.log(`  ✓ Found cover`);
    } else {
      // Keep existing or set to empty
      failed++;
      console.log(`  ✗ No cover found`);
    }

    // Rate limit: 1 second between requests (MusicBrainz requirement)
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  // Write updated data
  fs.writeFileSync(albumsPath, JSON.stringify(albums, null, 2));

  console.log(`\nDone! Updated: ${updated}, Failed: ${failed}`);
}

main().catch(console.error);

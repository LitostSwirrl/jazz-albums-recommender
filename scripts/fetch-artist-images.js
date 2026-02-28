// Script to fetch Wikipedia images for artists
// Run with: node scripts/fetch-artist-images.js

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const artistsPath = path.join(__dirname, '../src/data/artists.json');

async function getWikipediaImage(wikipediaUrl) {
  if (!wikipediaUrl) return null;

  // Extract article title from Wikipedia URL
  const match = wikipediaUrl.match(/wikipedia\.org\/wiki\/(.+)$/);
  if (!match) return null;

  const title = match[1];

  try {
    const apiUrl = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}`;
    const response = await fetch(apiUrl);

    if (!response.ok) {
      console.log(`  Failed to fetch ${title}: ${response.status}`);
      return null;
    }

    const data = await response.json();

    // Get the original image URL (higher quality than thumbnail)
    if (data.originalimage?.source) {
      return data.originalimage.source;
    }
    if (data.thumbnail?.source) {
      return data.thumbnail.source;
    }

    return null;
  } catch (error) {
    console.log(`  Error fetching ${title}: ${error.message}`);
    return null;
  }
}

async function main() {
  const artists = JSON.parse(fs.readFileSync(artistsPath, 'utf-8'));

  console.log(`Processing ${artists.length} artists...`);

  let updated = 0;
  let failed = 0;

  for (const artist of artists) {
    // Skip if already has imageUrl
    if (artist.imageUrl) {
      console.log(`✓ ${artist.name} already has image`);
      continue;
    }

    console.log(`Fetching image for ${artist.name}...`);
    const imageUrl = await getWikipediaImage(artist.wikipedia);

    if (imageUrl) {
      artist.imageUrl = imageUrl;
      updated++;
      console.log(`  ✓ Found image`);
    } else {
      failed++;
      console.log(`  ✗ No image found`);
    }

    // Rate limit: 200ms between requests
    await new Promise(resolve => setTimeout(resolve, 200));
  }

  // Write updated data
  fs.writeFileSync(artistsPath, JSON.stringify(artists, null, 2));

  console.log(`\nDone! Updated: ${updated}, Failed: ${failed}`);
}

main().catch(console.error);

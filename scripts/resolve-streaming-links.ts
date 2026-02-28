/**
 * Resolve Apple Music and YouTube Music URLs from existing Spotify URLs
 * using the Odesli/Songlink API (https://odesli.co/).
 *
 * Usage: npx tsx scripts/resolve-streaming-links.ts
 *
 * The script will:
 * 1. Read albums.json
 * 2. For each album with a spotifyUrl, query Odesli to find matching platform links
 * 3. Write back appleMusicUrl and youtubeMusicUrl where found
 * 4. Rate-limit requests to respect Odesli's free tier (1 req/sec)
 */

import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';

interface Album {
  id: string;
  title: string;
  artist: string;
  spotifyUrl?: string;
  appleMusicUrl?: string;
  youtubeMusicUrl?: string;
  [key: string]: unknown;
}

interface OdesliResponse {
  entityUniqueId: string;
  userCountry: string;
  pageUrl: string;
  linksByPlatform: Record<
    string,
    {
      url: string;
      entityUniqueId: string;
    }
  >;
}

const ALBUMS_PATH = join(__dirname, '..', 'src', 'data', 'albums.json');
const RATE_LIMIT_MS = 1100; // slightly over 1s to be safe

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function resolveLinks(
  spotifyUrl: string,
  retries = 0
): Promise<{
  appleMusicUrl?: string;
  youtubeMusicUrl?: string;
}> {
  const apiUrl = `https://api.song.link/v1-alpha.1/links?url=${encodeURIComponent(spotifyUrl)}&userCountry=US`;

  const response = await fetch(apiUrl);

  if (!response.ok) {
    if (response.status === 429) {
      if (retries >= 3) {
        throw new Error('Rate limited after 3 retries');
      }
      console.warn(`  Rate limited, waiting 5s... (retry ${retries + 1}/3)`);
      await sleep(5000);
      return resolveLinks(spotifyUrl, retries + 1);
    }
    throw new Error(`Odesli API error: ${response.status} ${response.statusText}`);
  }

  const data = (await response.json()) as OdesliResponse;
  const links = data.linksByPlatform;

  return {
    appleMusicUrl: links.appleMusic?.url,
    youtubeMusicUrl: links.youtubeMusic?.url,
  };
}

async function main() {
  const albums: Album[] = JSON.parse(readFileSync(ALBUMS_PATH, 'utf8'));

  const withSpotify = albums.filter(
    (a) => a.spotifyUrl && (!a.appleMusicUrl || !a.youtubeMusicUrl)
  );

  console.log(`Found ${withSpotify.length} albums with Spotify URLs needing resolution`);
  console.log(`Total albums: ${albums.length}`);

  let resolved = 0;
  let failed = 0;

  for (const album of withSpotify) {
    if (!album.spotifyUrl) continue;
    console.log(`[${resolved + failed + 1}/${withSpotify.length}] ${album.title} - ${album.artist}`);

    try {
      const links = await resolveLinks(album.spotifyUrl);

      if (links.appleMusicUrl && !album.appleMusicUrl) {
        album.appleMusicUrl = links.appleMusicUrl;
        console.log(`  ✓ Apple Music: ${links.appleMusicUrl}`);
      }
      if (links.youtubeMusicUrl && !album.youtubeMusicUrl) {
        album.youtubeMusicUrl = links.youtubeMusicUrl;
        console.log(`  ✓ YouTube Music: ${links.youtubeMusicUrl}`);
      }

      resolved++;
    } catch (err) {
      console.error(`  ✗ Failed: ${(err as Error).message}`);
      failed++;
    }

    await sleep(RATE_LIMIT_MS);
  }

  writeFileSync(ALBUMS_PATH, JSON.stringify(albums, null, 2) + '\n');

  console.log(`\nDone! Resolved: ${resolved}, Failed: ${failed}`);
  console.log(`Updated ${ALBUMS_PATH}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

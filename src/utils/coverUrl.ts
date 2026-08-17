import { getProxiedUrl } from './imageProxy';
import coverManifest from '@site/data/coverManifest.json';

// Original coverUrl -> self-hosted "/covers/<id>.webp", for the 808 unique
// archive-backed covers fetched by scripts/fetch_covers.py. Built offline so the
// app serves them same-origin instead of through the flaky wsrv.nl path.
const manifest: Record<string, string> = coverManifest;

/**
 * Ordered, best-first list of URLs to try for an album cover.
 *
 * Primary is the self-hosted local copy when one exists (same-origin WebP, no
 * external dependency). Next is the wsrv.nl proxy (fast WebP, resized,
 * CDN-cached); it occasionally returns a negatively-cached 404 when its origin
 * fetch from archive.org was throttled — the underlying image is still fine. So
 * on proxy failure we fall back to the direct source URL (the same image,
 * un-proxied; archive.org / coverartarchive send `Access-Control-Allow-Origin: *`).
 *
 * The caller (AlbumCover) walks this list on each <img> onError and shows the
 * initials placeholder only after every candidate has failed.
 */
export function getCoverCandidates(coverUrl: string, width: number): string[] {
  const proxied = getProxiedUrl(coverUrl, width);
  // mzstatic and other pass-through hosts are returned unchanged by the proxy
  // helper — no separate fallback to add in that case.
  const remote = proxied === coverUrl ? [coverUrl] : [proxied, coverUrl];
  const local = manifest[coverUrl];
  return local ? [local, ...remote] : remote;
}

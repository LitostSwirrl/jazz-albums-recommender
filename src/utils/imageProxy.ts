/**
 * Proxy external images through wsrv.nl for WebP conversion, resizing, and CDN caching.
 */
export function getProxiedUrl(url: string, width: number): string {
  if (!url) return url;

  // Already proxied — pass through as-is to avoid double-wrapping
  if (url.startsWith('https://wsrv.nl')) return url;

  const needsProxy =
    url.includes('archive.org') ||
    url.includes('coverartarchive.org') ||
    url.includes('wikimedia.org') ||
    url.includes('staticflickr.com') ||
    url.includes('dzcdn.net');

  if (needsProxy) {
    return `https://wsrv.nl/?url=${encodeURIComponent(url)}&w=${width}&output=webp&maxage=7d`;
  }

  return url;
}

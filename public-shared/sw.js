/*
 * Smack Cats service worker.
 * Runtime caching for Spotify-smooth repeat visits and offline support.
 * No precache manifest (keeps it dependency-free); everything is cached on first use.
 * Bump VERSION to invalidate all caches on a release if a stale-asset issue ever appears.
 */
const VERSION = 'sc-v1';
const STATIC_CACHE = `${VERSION}-static`;
const IMAGE_CACHE = `${VERSION}-img`;
const FONT_CACHE = `${VERSION}-font`;
const MAX_IMAGES = 400;

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k))
      );
      await self.clients.claim();
    })()
  );
});

// Trim a cache to a maximum number of entries (oldest first).
async function trim(cacheName, max) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  if (keys.length <= max) return;
  for (const req of keys.slice(0, keys.length - max)) {
    await cache.delete(req);
  }
}

async function cacheFirst(request, cacheName, max) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;
  try {
    const res = await fetch(request);
    // Cache successful or opaque (cross-origin no-cors) responses.
    if (res && (res.ok || res.type === 'opaque')) {
      cache.put(request, res.clone());
      if (max) trim(cacheName, max);
    }
    return res;
  } catch {
    return cached || Response.error();
  }
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const res = await fetch(request);
    if (res && res.ok) cache.put(request, res.clone());
    return res;
  } catch {
    // Offline: serve the cached app shell so hash-routed navigation still works.
    const cached = await cache.match(request);
    return cached || (await cache.match(self.registration.scope)) || Response.error();
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Album covers / artist photos (proxied via wsrv.nl, or any image): cache-first, capped.
  if (request.destination === 'image' || url.hostname === 'wsrv.nl') {
    event.respondWith(cacheFirst(request, IMAGE_CACHE, MAX_IMAGES));
    return;
  }

  // Google Fonts stylesheet + font files: cache-first.
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
    event.respondWith(cacheFirst(request, FONT_CACHE, 40));
    return;
  }

  // Same-origin app assets.
  if (url.origin === self.location.origin) {
    if (request.mode === 'navigate') {
      // Fresh HTML when online, cached shell when offline.
      event.respondWith(networkFirst(request, STATIC_CACHE));
      return;
    }
    // Hashed JS/CSS/JSON are immutable — cache-first, uncapped (cleared on VERSION bump).
    event.respondWith(cacheFirst(request, STATIC_CACHE, 0));
    return;
  }

  // Everything else (analytics, Open-Meteo, Spotify embed): straight to network.
});

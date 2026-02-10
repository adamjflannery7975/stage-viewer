/* ChordPro Stage Viewer - simple offline shell cache (PWA)
   Notes:
   - This caches the app shell (HTML + icons + manifest) so the Viewer opens offline.
   - Local File inputs (gig/songs) must still be selected by the user; browsers don't allow us
     to fetch arbitrary local files via service worker.
*/
const CACHE_NAME = 'chordpro-stage-viewer-v1';
const APP_SHELL = [
  './Stage_Viewer_Styled_v5_songcards_singer_PWA.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  './serviceWorker.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.map(k => (k === CACHE_NAME ? null : caches.delete(k))));
      await self.clients.claim();
    })()
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // Only handle same-origin requests
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    (async () => {
      const cache = await caches.open(CACHE_NAME);

      // Cache-first for app shell + static assets
      const cached = await cache.match(req);
      if (cached) return cached;

      try {
        const fresh = await fetch(req);
        // Opportunistically cache same-origin static files
        const isStatic = /\.(html|js|css|png|json|svg)$/.test(url.pathname);
        if (fresh.ok && isStatic) cache.put(req, fresh.clone());
        return fresh;
      } catch (e) {
        // Offline fallback: try cached HTML
        if (req.mode === 'navigate') {
          const fallback = await cache.match('./Stage_Viewer_Styled_v5_songcards_singer_PWA.html');
          if (fallback) return fallback;
        }
        throw e;
      }
    })()
  );
});

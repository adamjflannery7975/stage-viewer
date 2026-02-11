/* ChordPro Studio – Apps Service Worker
   Offline-first shell + offline fallback for library index + .cho files
*/

const CACHE_VERSION = "v5"; // bump to force updates
const SHELL_CACHE = `cps-shell-${CACHE_VERSION}`;
const DATA_CACHE  = `cps-data-${CACHE_VERSION}`;

// These are all relative to /stage-viewer/apps/ because the SW lives in /apps
const APP_SHELL_ASSETS = [
  "./index.html",
  "./stage_viewer.html",
  "./setlist_builder.html",
  "./chordpro_edit.html",
  "./manifest.json",
  "./serviceWorker.js",
  "./icon-192.png",
  "./icon-512.png",
  "../shared/theme.js"
];

// Install: pre-cache the app shell so it loads offline once visited at least once
self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(SHELL_CACHE);
    await cache.addAll(APP_SHELL_ASSETS);
    await self.skipWaiting();
  })());
});

// Activate: clean old caches + take control immediately
self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(
      keys.map((k) => {
        if (![SHELL_CACHE, DATA_CACHE].includes(k)) return caches.delete(k);
      })
    );
    await self.clients.claim();
  })());
});

function isSameOriginRequest(request) {
  try {
    const url = new URL(request.url);
    return url.origin === self.location.origin;
  } catch (e) {
    return false;
  }
}

function isAppShell(url) {
  return url.pathname.includes("/apps/") && (
    url.pathname.endsWith("/apps/") ||
    url.pathname.endsWith("/apps/index.html") ||
    url.pathname.endsWith("/apps/stage_viewer.html") ||
    url.pathname.endsWith("/apps/setlist_builder.html") ||
    url.pathname.endsWith("/apps/chordpro_edit.html") ||
    url.pathname.endsWith("/apps/manifest.json") ||
    url.pathname.endsWith("/apps/serviceWorker.js") ||
    url.pathname.endsWith("/apps/icon-192.png") ||
    url.pathname.endsWith("/apps/icon-512.png") ||
    url.pathname.endsWith("/shared/theme.js")
  );
}

function isLibraryOrSongData(url) {
  const p = url.pathname;
  return (
    (p.includes("/library/") && p.endsWith(".json")) ||
    (p.includes("/songs/") && p.endsWith(".cho"))
  );
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;

  const fresh = await fetch(request);
  if (fresh && fresh.ok) cache.put(request, fresh.clone());
  return fresh;
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const fresh = await fetch(request);
    if (fresh && fresh.ok) cache.put(request, fresh.clone());
    return fresh;
  } catch (e) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw e;
  }
}

self.addEventListener("fetch", (event) => {
  const req = event.request;

  if (req.method !== "GET") return;
  if (!isSameOriginRequest(req)) return;

  const url = new URL(req.url);

  // Navigations: cache-first for the *requested page* (fixes loading other apps offline)
  if (req.mode === "navigate") {
    event.respondWith((async () => {
      try {
        return await cacheFirst(req, SHELL_CACHE);
      } catch (e) {
        // fallback to apps index if available
        const cache = await caches.open(SHELL_CACHE);
        const fallback = await cache.match("./index.html");
        return fallback || Response.error();
      }
    })());
    return;
  }

  // Shell assets
  if (isAppShell(url)) {
    event.respondWith(cacheFirst(req, SHELL_CACHE));
    return;
  }

  // Library index + .cho song files
  if (isLibraryOrSongData(url)) {
    event.respondWith(networkFirst(req, DATA_CACHE));
    return;
  }

  // Default: network
});

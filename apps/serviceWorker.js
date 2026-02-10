/* ChordPro Studio – Stage Viewer Service Worker
   Goals:
   - stage_viewer.html updates reliably (network-first)
   - app shell assets available offline (cache-first)
   - library + .cho sync when online (network-first with cache fallback)
*/

const CACHE_VERSION = "v5"; // bump when you publish changes
const SHELL_CACHE = `cps-shell-${CACHE_VERSION}`;
const DATA_CACHE  = `cps-data-${CACHE_VERSION}`;

// SW lives in /apps, so these are relative to /apps/
const APP_SHELL_ASSETS = [
  "./stage_viewer.html",
  "./manifest.json",
  "./serviceWorker.js",
  "./icon-192.png",
  "./icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(SHELL_CACHE);
    await cache.addAll(APP_SHELL_ASSETS);
    await self.skipWaiting();
  })());
});

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
  } catch {
    return false;
  }
}

function isLibraryOrSongData(url) {
  const p = url.pathname;
  return (
    (p.includes("/library/") && p.endsWith(".json")) ||
    (p.includes("/songs/") && p.endsWith(".cho"))
  );
}

function isStageViewerHtml(url) {
  return url.pathname.endsWith("/apps/stage_viewer.html");
}

function isShellAsset(url) {
  return (
    url.pathname.endsWith("/apps/manifest.json") ||
    url.pathname.endsWith("/apps/serviceWorker.js") ||
    url.pathname.endsWith("/apps/icon-192.png") ||
    url.pathname.endsWith("/apps/icon-512.png")
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
    const fresh = await fetch(request, { cache: "no-store" });
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

  // Always try to update HTML (prevents "old UI" after deploy)
  if (req.mode === "navigate" || isStageViewerHtml(url)) {
    event.respondWith(networkFirst(req, SHELL_CACHE));
    return;
  }

  // Shell assets: icons/manifest/sw = cache-first
  if (isShellAsset(url)) {
    event.respondWith(cacheFirst(req, SHELL_CACHE));
    return;
  }

  // Library + songs: network-first so it syncs when online
  if (isLibraryOrSongData(url)) {
    event.respondWith(networkFirst(req, DATA_CACHE));
    return;
  }

  // Default: network
});

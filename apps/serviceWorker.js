/* ChordPro Studio – Service Worker
   Scope: /stage-viewer/apps/
   - App shell: cache-first (instant + offline once visited)
   - Data: network-first (refresh when online, fallback when offline)
*/

const CACHE_VERSION = "v5"; // bump when you change this file or caching behaviour
const SHELL_CACHE = `cps-shell-${CACHE_VERSION}`;
const DATA_CACHE  = `cps-data-${CACHE_VERSION}`;

// NOTE: These paths are relative to /apps/ because this SW lives in /apps/
const APP_SHELL_ASSETS = [
  "./stage_viewer.html",
  "./setlist_builder.html",
  "./chordpro_edit.html",
  "./manifest.json",
  "./icon-192.png",
  "./icon-512.png",
  "../shared/theme.js"
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
  } catch (e) {
    return false;
  }
}

function isAppShell(url) {
  // Anything in /apps/ that is part of the shell (plus shared theme)
  const p = url.pathname;

  // /apps/ html + key assets
  const inApps =
    p.includes("/apps/") &&
    (
      p.endsWith("/apps/") ||
      p.endsWith("/apps/stage_viewer.html") ||
      p.endsWith("/apps/setlist_builder.html") ||
      p.endsWith("/apps/chordpro_edit.html") ||
      p.endsWith("/apps/manifest.json") ||
      p.endsWith("/apps/serviceWorker.js") ||
      p.endsWith("/apps/icon-192.png") ||
      p.endsWith("/apps/icon-512.png")
    );

  // shared theme
  const sharedTheme = p.endsWith("/shared/theme.js");

  return inApps || sharedTheme;
}

function isLibraryOrSongData(url) {
  // Data to be available offline:
  // - /library/*.json (library.index.json, songs.index.json, setlists.json, consolidate.log.json)
  // - /songs/*.cho
  const p = url.pathname;
  return (
    (p.includes("/library/") && p.endsWith(".json")) ||
    (p.includes("/songs/") && p.endsWith(".cho"))
  );
}

// Normalize cache keys so querystrings like ?rev=1 don't create duplicates
function cacheKeyForRequest(request) {
  const url = new URL(request.url);
  const normalized = url.origin + url.pathname; // strip ?query + #hash
  return new Request(normalized, { method: "GET" });
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const key = cacheKeyForRequest(request);

  const cached = await cache.match(key, { ignoreSearch: true });
  if (cached) return cached;

  const fresh = await fetch(request);
  if (fresh && fresh.ok) cache.put(key, fresh.clone());
  return fresh;
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const key = cacheKeyForRequest(request);

  try {
    const fresh = await fetch(request);
    if (fresh && fresh.ok) cache.put(key, fresh.clone());
    return fresh;
  } catch (e) {
    const cached = await cache.match(key, { ignoreSearch: true });
    if (cached) return cached;
    throw e;
  }
}

self.addEventListener("fetch", (event) => {
  const req = event.request;

  // Only handle GET and same-origin; leave everything else alone
  if (req.method !== "GET") return;
  if (!isSameOriginRequest(req)) return;

  const url = new URL(req.url);

  // Navigations inside /apps/ (e.g. stage_viewer.html?rev=1)
  if (req.mode === "navigate" && url.pathname.includes("/apps/")) {
    event.respondWith(cacheFirst(req, SHELL_CACHE));
    return;
  }

  // App shell assets (+ shared theme)
  if (isAppShell(url)) {
    event.respondWith(cacheFirst(req, SHELL_CACHE));
    return;
  }

  // Library JSON + .cho song files
  if (isLibraryOrSongData(url)) {
    event.respondWith(networkFirst(req, DATA_CACHE));
    return;
  }

  // Default: go to network (predictable)
});

// Bright Solar Ops service worker
// Simple strategy: pass through network, let the IndexedDB queue handle offline writes.
// Caches the app shell so opening the homescreen app while offline at least shows the UI.

const SHELL_CACHE = "bsp-shell-v2";
const SHELL_PATHS = ["/", "/log", "/login", "/manifest.webmanifest", "/brand/logo.png"];
const IS_LOCAL_DEV = ["localhost", "127.0.0.1"].includes(self.location.hostname);

self.addEventListener("install", (event) => {
  if (IS_LOCAL_DEV) {
    self.skipWaiting();
    return;
  }
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_PATHS).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  if (IS_LOCAL_DEV) {
    event.waitUntil(
      caches.keys()
        .then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
        .then(() => self.registration.unregister())
    );
    return;
  }
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== SHELL_CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (IS_LOCAL_DEV) return;
  const req = event.request;
  // Only intercept same-origin GETs for HTML & assets — leave API calls alone
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    fetch(req)
      .then((res) => {
        // Cache fresh shell documents
        if (res.ok && (req.destination === "document" || SHELL_PATHS.includes(url.pathname))) {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() => {
        if (req.destination === "document") {
          return caches.match(req).then((hit) => hit || caches.match("/"));
        }
        return caches.match(req);
      })
  );
});

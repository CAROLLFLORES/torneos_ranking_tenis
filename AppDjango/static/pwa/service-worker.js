const CACHE = "tenis-v2";
const OFFLINE_URLS = [
  "/",
  "/static/css/styles.css",
  "/static/css/styles_index.css"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(OFFLINE_URLS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    fetch(event.request)
      .then(res => { caches.open(CACHE).then(c => c.put(event.request, res.clone())); return res; })
      .catch(() => caches.match(event.request).then(m => m || caches.match("/")))
  );
});

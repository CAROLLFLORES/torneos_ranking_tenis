# torneo/views_pwa.py
from django.http import HttpResponse
import json

def manifest(request):
    data = {
        "name": "Liga de Tenis",
        "short_name": "Tenis",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#0d1b2a",
        "theme_color": "#90be6d",
        "icons": [
            {"src": "/static/pwa/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/pwa/icons/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    }
    return HttpResponse(json.dumps(data), content_type="application/manifest+json")


def service_worker(request):
    js = r"""
const CACHE = "tenis-v2";
const OFFLINE_URLS = [
  "/",
  "/static/css/styles.css",
  "/static/css/styles_index.css"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(OFFLINE_URLS))
  );
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
    (async () => {
      try {
        const response = await fetch(event.request);

        // ⚡ Solo cachear HTTP/HTTPS
        if (event.request.url.startsWith("http")) {
          const cache = await caches.open(CACHE);
          cache.put(event.request, response.clone());
        }

        return response;
      } catch (err) {
        // fallback offline
        const cached = await caches.match(event.request);
        return cached || caches.match("/");
      }
    })()
  );
});
"""
    return HttpResponse(js, content_type="application/javascript")

// BrainDump service worker.
//
// Purpose: make the app installable and show a friendly page when it is
// opened without a connection. It deliberately does NOT cache app pages or
// API responses: they belong to a signed-in user and must never be served
// stale or to someone else. Only the offline page and the few static files
// it needs are stored.

const CACHE = 'braindump-offline-v1';
const OFFLINE_URL = '/offline';
const PRECACHE = [
    OFFLINE_URL,
    '/static/css/core/variables.css',
    '/static/css/core/fonts.css',
    '/static/css/core/base.css',
    '/static/css/offline.css',
    '/static/fonts/Inter-Variable.woff2',
    '/static/favicon/android-chrome-192x192.png',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then((names) => Promise.all(names.filter((name) => name !== CACHE).map((name) => caches.delete(name))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const request = event.request;
    if (request.method !== 'GET') return;            // never touch form posts or API writes

    const url = new URL(request.url);
    if (url.origin !== self.location.origin) return; // third-party requests pass straight through

    if (request.mode === 'navigate') {
        // Pages always come from the network; the offline page is only a fallback
        event.respondWith(
            fetch(request).catch(() => caches.match(OFFLINE_URL, { ignoreSearch: true }))
        );
        return;
    }

    if (PRECACHE.includes(url.pathname)) {
        // Network first so a deploy is picked up; the stored copy is for offline only
        event.respondWith(
            fetch(request).catch(() => caches.match(url.pathname))
        );
    }
    // Everything else: default browser behaviour, no caching
});

/* ============================================================
   NutriAI Service Worker — v3
   Strategies:
     • Static assets (CSS/JS/images) → Cache-First
     • HTML pages                    → Network-First with cache fallback
     • API endpoints                 → Network-Only (never cache)
     • Admin routes                  → Network-Only
   ============================================================ */

const CACHE_VERSION = 'nutriai-v6';
const STATIC_CACHE  = `${CACHE_VERSION}-static`;
const PAGES_CACHE   = `${CACHE_VERSION}-pages`;
const OLD_CACHES    = ['nutriai-v1', 'nutriai-v2', 'nutriai-v3', 'nutriai-v4', 'nutriai-v5', 'nutriai-v1-static', 'nutriai-v2-static', 'nutriai-v3-static', 'nutriai-v4-static', 'nutriai-v5-static', 'nutriai-v3-pages', 'nutriai-v4-pages', 'nutriai-v5-pages'];

// Assets to pre-cache on install
const PRECACHE_ASSETS = [
  '/',
  '/offline',
  '/manifest.json',
  '/static/css/style.css',
  '/static/js/script.js',
  '/static/js/pwa.js?v=2',
  '/static/icon-192.png',
  '/static/icon-512.png',
];

// ── Install: pre-cache essential assets ──────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(PRECACHE_ASSETS).catch(err => {
        console.warn('[SW] Some precache items failed (probably CDN):', err);
      }))
      .then(() => self.skipWaiting())
  );
});

// ── Activate: clean up old caches ────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.map(key => {
          if (key !== STATIC_CACHE && key !== PAGES_CACHE) {
            console.log('[SW] Deleting old cache:', key);
            return caches.delete(key);
          }
        })
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch: routing strategy ───────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // 1. Only handle GET requests
  if (request.method !== 'GET') return;

  // 2. Skip API, admin, auth-sensitive routes (network only)
  const skipPatterns = ['/api/', '/admin', '/logout', '/login', '/register',
                        '/analyze', '/forgot-password', '/reset-password', '/ping'];
  if (skipPatterns.some(p => url.pathname.startsWith(p))) return;

  // 3. Static assets → Cache-First
  if (
    url.pathname.startsWith('/static/') ||
    url.hostname.includes('fonts.googleapis') ||
    url.hostname.includes('fonts.gstatic') ||
    url.hostname.includes('cdn.jsdelivr')
  ) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // 4. HTML pages → Network-First with offline fallback
  if (request.headers.get('Accept')?.includes('text/html') || url.hostname === self.location.hostname) {
    event.respondWith(networkFirstWithFallback(request));
    return;
  }
});

// ── Strategy: Cache-First ────────────────────────────────────
async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Asset unavailable offline', { status: 503 });
  }
}

// ── Strategy: Network-First with offline fallback ────────────
async function networkFirstWithFallback(request) {
  const cache = await caches.open(PAGES_CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;
    // Serve the offline page
    const offline = await caches.match('/offline');
    return offline || new Response(
      `<!DOCTYPE html><html><head><title>Offline — NutriAI</title></head>
       <body style="font-family:sans-serif;text-align:center;padding:60px">
       <h1>🥗 NutriAI</h1><p>You're offline. Please check your connection.</p>
       <a href="/">Try again</a></body></html>`,
      { headers: { 'Content-Type': 'text/html' } }
    );
  }
}

// ── Push Notifications ────────────────────────────────────────
self.addEventListener('push', event => {
  const data = event.data?.json() ?? {};
  const title   = data.title   || 'NutriAI 🥗';
  const options = {
    body:    data.body    || 'Your personalized nutrition update is ready!',
    icon:    '/static/icon-192.png',
    badge:   '/static/icon-192.png',
    tag:     data.tag    || 'nutriai-notification',
    data:    { url: data.url || '/' },
    actions: [
      { action: 'view',    title: 'View Plan',  icon: '/static/icon-192.png' },
      { action: 'dismiss', title: 'Dismiss' }
    ],
    vibrate: [100, 50, 100],
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

// ── Notification Click ────────────────────────────────────────
self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'dismiss') return;

  const urlToOpen = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      const existing = clientList.find(c => c.url.includes(urlToOpen) && 'focus' in c);
      if (existing) return existing.focus();
      return clients.openWindow(urlToOpen);
    })
  );
});

// ── Background Sync (for offline form submissions) ────────────
self.addEventListener('sync', event => {
  if (event.tag === 'sync-diary') {
    event.waitUntil(syncOfflineDiary());
  }
});

async function syncOfflineDiary() {
  // Placeholder: real implementation would read from IndexedDB and POST
  console.log('[SW] Background sync: diary entries');
}

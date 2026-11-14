/* ScamDojo service worker: offline app shell with stale-while-revalidate.
   The server injects the real file list and a content-based version into the two marked lines below (see server.py),
   so a new release automatically replaces the old cache. Served as-is, it still works with the fallback list. */
const VERSION = /*VERSION*/ 'dev' /*END*/;
const PRECACHE = /*PRECACHE*/ ['/', '/index.html', '/css/style.css', '/manifest.json', '/js/app.js', '/api/cards', '/api/samples', '/api/config'] /*END*/;
const SHELL = 'scamdojo-shell-' + VERSION;
const RUNTIME = 'scamdojo-runtime-' + VERSION;
const SWR_API = ['/api/cards', '/api/samples', '/api/config', '/api/metrics'];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(SHELL);
    // one missing file must not stop the install, so add them individually
    await Promise.all(PRECACHE.map((u) => cache.add(new Request(u, { cache: 'reload' })).catch(() => null)));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.startsWith('scamdojo-') && k !== SHELL && k !== RUNTIME) await caches.delete(k);
    await self.clients.claim();
  })());
});

async function staleWhileRevalidate(request, cacheName, fallbackUrl) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request, { ignoreSearch: false }) || (fallbackUrl && await cache.match(fallbackUrl));
  const network = fetch(request).then((res) => { if (res && res.ok) cache.put(request, res.clone()); return res; }).catch(() => null);
  if (cached) { network.catch(() => null); return cached; }          // answer instantly from cache, refresh in the background
  return (await network) || new Response('Offline', { status: 503, statusText: 'Offline', headers: { 'Content-Type': 'text/plain' } });
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;                                   // scans, logins and saves always go to the network
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    if (url.pathname === '/sw.js') return;
    if (req.mode === 'navigate') { event.respondWith(staleWhileRevalidate(new Request('/index.html'), SHELL, '/')); return; }
    if (url.pathname.startsWith('/api/')) {
      if (SWR_API.includes(url.pathname)) event.respondWith(staleWhileRevalidate(req, SHELL));
      return;                                                         // account and user data are never cached
    }
    event.respondWith(staleWhileRevalidate(req, SHELL));
    return;
  }
  if (/fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) event.respondWith(staleWhileRevalidate(req, RUNTIME));
});

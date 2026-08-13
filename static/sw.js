const CACHE_NAME = 'comercio-v2';
const URLS_A_CACHEAR = [
  '/',
  '/static/css/app.css',
  '/static/js/app.js',
  '/static/manifest.json',
  '/static/img/icon-192.png',
  '/static/img/icon-512.png'
];

// Instalar: guardar archivos en caché
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Cache abierta');
        return cache.addAll(URLS_A_CACHEAR);
      })
      .then(() => self.skipWaiting())
  );
});

// Activar: limpiar cachés viejas
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// Fetch: estrategia "Stale-While-Revalidate"
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  
  // Solo cachear peticiones GET y dentro del mismo origen
  if (event.request.method !== 'GET' || url.origin !== location.origin) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then(cached => {
      // Si está en caché, devolverlo y actualizar en segundo plano
      const fetchPromise = fetch(event.request).then(response => {
        if (response.ok && event.request.url.includes('/static/')) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => {
        // Si falla la red y no hay caché, devolver página offline
        if (event.request.destination === 'document') {
          return caches.match('/offline.html');
        }
      });

      return cached || fetchPromise;
    })
  );
});

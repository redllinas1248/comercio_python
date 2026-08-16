const CACHE_NAME = 'comercio-v1';
const URLS_A_CACHEAR = [
  '/',
  '/static/css/app.css',
  '/static/js/app.js',
  '/static/manifest.json'
];

// Instalar: guardar archivos en caché
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(URLS_A_CACHEAR))
  );
  self.skipWaiting();
});

// Activar: limpiar cachés viejas
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: responder con caché si hay, si no ir a la red
self.addEventListener('fetch', event => {
  // Solo cachear peticiones GET
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        // Cachear respuestas válidas de recursos estáticos
        if (response.ok && event.request.url.includes('/static/')) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => {
        // Sin conexión y sin caché: devolver página offline básica
        if (event.request.destination === 'document') {
          return new Response(
            '<h1>Sin conexión</h1><p>Revisa tu internet e intenta de nuevo.</p>',
            { headers: { 'Content-Type': 'text/html' } }
          );
        }
      });
    })
  );
});

const CACHE_NAME = 'comercio-v2';
const STATIC_CACHE = 'comercio-static-v2';
const DYNAMIC_CACHE = 'comercio-dynamic-v2';

// Recursos estáticos a cachear al instalar
const STATIC_ASSETS = [
  '/',
  '/static/css/app.css',
  '/static/js/app.js',
  '/static/manifest.json',
  '/static/img/icon-192.png',
  '/static/img/icon-512.png',
  '/static/img/banner.svg'
    '/',
  '/offline', // Si agregas una ruta en Flask
  // ...
];

// Instalar: cachear recursos estáticos
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('Cacheando recursos estáticos...');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activar: limpiar cachés viejos
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== STATIC_CACHE && key !== DYNAMIC_CACHE)
          .map(key => caches.delete(key))
      );
    })
    .then(() => self.clients.claim())
  );
});

// Fetch: estrategia "stale-while-revalidate"
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  
  // Ignorar peticiones a otras APIs o recursos externos
  if (url.origin !== location.origin) return;
  
  // Para peticiones de API, usar network-first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Cachear respuesta exitosa para offline
          const clone = response.clone();
          caches.open(DYNAMIC_CACHE).then(cache => {
            cache.put(event.request, clone);
          });
          return response;
        })
        .catch(() => {
          // Offline: devolver respuesta en caché o error
          return caches.match(event.request);
        })
    );
    return;
  }
  
  // Para recursos estáticos, usar stale-while-revalidate
  event.respondWith(
    caches.match(event.request)
      .then(cachedResponse => {
        // Devolver caché inmediatamente y actualizar en segundo plano
        const fetchPromise = fetch(event.request)
          .then(networkResponse => {
            if (networkResponse && networkResponse.status === 200) {
              caches.open(STATIC_CACHE).then(cache => {
                cache.put(event.request, networkResponse.clone());
              });
            }
            return networkResponse;
          })
          .catch(() => {
            // Si falla la red, devolver la caché (si existe)
            return cachedResponse;
          });
        
        // Si hay caché, devolverla y actualizar en segundo plano
        if (cachedResponse) {
          // Actualizar en segundo plano (no esperar)
          fetchPromise.catch(() => {});
          return cachedResponse;
        }
        
        // Si no hay caché, esperar la red
        return fetchPromise;
      })
  );
});

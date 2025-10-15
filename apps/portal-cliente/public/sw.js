self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('telecable-portal-cliente').then((cache) => cache.addAll(['/', '/index.html']))
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        const clone = response.clone();
        caches.open('telecable-portal-cliente').then((cache) => cache.put(event.request, clone));
        return response;
      });
    })
  );
});

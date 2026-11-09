// Cidadania: funciona offline guardando o app no aparelho.
const VERSAO = "cidadania-d8300cc8e2";
const ESSENCIAIS = ["./", "index.html", "manifest.webmanifest", "vendor/nostr.bundle.js", "icons/icon-192.png", "icons/icon-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(VERSAO).then(c => c.addAll(ESSENCIAIS)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSAO).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const req = e.request; if (req.method !== "GET") return;
  const url = new URL(req.url);
  const proprio = url.origin === self.location.origin;
  const fonte = /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname);
  if (!proprio && !fonte) return;
  // páginas: sempre tenta a versão nova primeiro; sem internet, usa a guardada
  if (proprio && (req.mode === "navigate" || url.pathname.endsWith("/") || url.pathname.endsWith(".html"))) {
    e.respondWith(fetch(req, { cache: "no-cache" }).then(r => { const c = r.clone(); caches.open(VERSAO).then(k => k.put(req, c)); return r; })
      .catch(() => caches.match(req, { ignoreSearch: true }).then(r => r || caches.match("index.html"))));
    return;
  }
  e.respondWith(caches.open(VERSAO).then(async cache => {
    const salvo = await cache.match(req, { ignoreSearch: proprio });
    const rede = fetch(req).then(r => { if (r && (r.ok || r.type === "opaque")) cache.put(req, r.clone()); return r; }).catch(() => salvo);
    return salvo || rede;
  }));
});

# Reverse Proxy (nginx) Setup

Production runs behind **your own nginx**, which terminates TLS and forwards plain
HTTP to Traefik. Traefik then path-routes to every service. You expose **one
upstream** — `127.0.0.1:8080` — and nginx needs **one `location /`** block.

```
browser ──HTTPS:443──► nginx (your TLS cert) ──HTTP──► 127.0.0.1:8080 ──► Traefik ──► services
                                                                           ├─ /api      → backend
                                                                           ├─ /auth     → Keycloak
                                                                           ├─ /forgejo  → Forgejo (if enabled)
                                                                           ├─ /docs     → static docs
                                                                           └─ /          → web frontend
```

Traefik does all sub-path routing internally — **nginx must not strip or rewrite
paths**. A single catch-all `location /` is correct.

## Prerequisites

- nginx is on the **same host** as the stack (it proxies to `127.0.0.1:8080`).
  Traefik binds to loopback by default. If nginx is on a **different** host, set
  `TRAEFIK_BIND_ADDRESS=0.0.0.0` in `.env` and firewall port 8080 to the nginx host.
- A valid TLS certificate for your domain.
- `PUBLIC_DOMAIN=https://your-domain` is set in `.env` (the stack derives all public
  URLs from it). The domain in nginx's `server_name` must match `PUBLIC_DOMAIN`.

## nginx configuration

Replace `code.tugraz.at` with your domain and point the cert paths at your files.

```nginx
# Redirect all HTTP to HTTPS
server {
    listen 80;
    server_name code.tugraz.at;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name code.tugraz.at;

    ssl_certificate     /etc/letsencrypt/live/code.tugraz.at/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/code.tugraz.at/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    # Allow large git pushes over HTTP (Forgejo). Default is 1m → "413" on push.
    client_max_body_size 512M;

    location / {
        proxy_pass http://127.0.0.1:8080;

        # Tell Traefik/Keycloak/the backend the original request was HTTPS.
        # Without X-Forwarded-Proto=https, OAuth callbacks and Keycloak cookies
        # break (login "session not found" loops).
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host  $host;
        proxy_set_header X-Forwarded-Port  443;

        # Keycloak's login redirect sets several large Set-Cookie headers; the
        # default 4k/8k proxy buffers overflow → 502 (looks like "nothing happens").
        proxy_buffer_size       128k;
        proxy_buffers           4 256k;
        proxy_busy_buffers_size 256k;
    }
}
```

Apply with:

```bash
nginx -t && systemctl reload nginx
```

## Why each non-obvious directive

| Directive | Reason |
|---|---|
| `X-Forwarded-Proto https` | TLS ends at nginx; downstream must know it was HTTPS or it builds `http://` callback URLs and drops Secure cookies. |
| `X-Forwarded-Host` / `-Port` | Keycloak/Traefik reconstruct public URLs from these. |
| `proxy_buffer_size 128k` (+ buffers) | Keycloak login responses carry large `Set-Cookie` headers; small buffers → 502. |
| `client_max_body_size 512M` | `git push` over HTTPS to Forgejo; the 1 MB default rejects real pushes. |
| single `location /`, no path rewrite | Traefik owns `/api`, `/auth`, `/forgejo`, `/docs`; stripping paths breaks routing. |

## Checklist

- [ ] `server_name` matches `PUBLIC_DOMAIN` in `.env`.
- [ ] TLS cert valid for the domain.
- [ ] `X-Forwarded-Proto https` (+ Host/Port) headers set.
- [ ] Keycloak proxy buffers raised.
- [ ] `client_max_body_size` ≥ your largest expected git push (only if Forgejo is enabled).
- [ ] Port 8080 not reachable from outside the host (loopback bind, or firewalled).
- [ ] `nginx -t` passes; reload done.

> The stack itself needs no nginx-specific config beyond `PUBLIC_DOMAIN`. Keycloak
> (`KC_PROXY_HEADERS=xforwarded`) and Traefik (`forwardedHeaders.trustedIPs`) are
> already configured to trust these forwarded headers in production.

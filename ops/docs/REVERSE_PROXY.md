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

Replace `code.example.com` with your domain and point the cert paths at your files.

```nginx
# WebSocket upgrade passthrough: Coder workspaces (code-server, the MATLAB
# browser desktop) live or die by this. nginx drops the hop-by-hop Upgrade
# header unless it is forwarded explicitly.
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

# Redirect all HTTP to HTTPS
server {
    listen 80;
    server_name code.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name code.example.com;

    # HTTP/2 lets the browser multiplex the hundreds of small assets the
    # MATLAB browser desktop loads at startup. Without it, HTTP/1.1 caps the
    # browser at ~6 connections and the desktop takes minutes to come up.
    # (nginx < 1.25.1: use `listen 443 ssl http2;` instead.)
    http2 on;

    ssl_certificate     /etc/letsencrypt/live/code.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/code.example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    # Allow large request bodies. EVERY upload passes through this vhost: git
    # pushes to Forgejo AND all API uploads (example upload, student submissions).
    # nginx's default is 1m — without this line, anything bigger dies at nginx
    # with its stock HTML 413 page and never reaches the stack.
    client_max_body_size 512M;

    location / {
        proxy_pass http://127.0.0.1:8080;

        # WebSockets (Coder workspaces, matlab-proxy's connector) need
        # HTTP/1.1 to the upstream plus the forwarded Upgrade handshake.
        proxy_http_version 1.1;
        proxy_set_header Upgrade    $http_upgrade;
        proxy_set_header Connection $connection_upgrade;

        # Workspace sessions hold long-lived idle connections; the 60s default
        # read timeout severs them and forces constant reconnects.
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;

        # Tell Traefik/Keycloak/the backend the original request was HTTPS.
        # Without X-Forwarded-Proto=https, OAuth callbacks and Keycloak cookies
        # break (login "session not found" loops).
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host  $host;
        proxy_set_header X-Forwarded-Port  443;

        # Don't buffer response bodies: the MATLAB connector streams events,
        # and buffering delays them into bursts (sluggish, half-initialized
        # desktop). proxy_buffer_size still applies to response HEADERS, which
        # is what the Keycloak sizing below is for. Request buffering off lets
        # large git pushes stream through instead of spooling to disk first.
        proxy_buffering off;
        proxy_request_buffering off;

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
| `proxy_http_version 1.1` + `Upgrade`/`Connection` headers | WebSocket handshakes are hop-by-hop; nginx silently drops them by default. Code-server terminals and the MATLAB browser desktop (matlab-proxy connector) require WebSockets — without this they fail or fall back to slow polling. |
| `http2 on` | The MATLAB desktop fetches hundreds of small assets at load; HTTP/1.1 serializes them over ~6 connections (minutes-long startup). HTTP/2 multiplexes them over one. |
| `proxy_read_timeout`/`send_timeout 3600s` | Idle workspace WebSockets outlive the 60s default; severing them causes reconnect stalls mid-session. |
| `proxy_buffering off` | The MATLAB connector streams incremental events; body buffering delays them into bursts. Header buffers (below) still apply. |
| `X-Forwarded-Proto https` | TLS ends at nginx; downstream must know it was HTTPS or it builds `http://` callback URLs and drops Secure cookies. |
| `X-Forwarded-Host` / `-Port` | Keycloak/Traefik reconstruct public URLs from these. |
| `proxy_buffer_size 128k` (+ buffers) | Keycloak login responses carry large `Set-Cookie` headers; small buffers → 502. |
| `client_max_body_size 512M` | Every upload crosses this vhost: `git push` to Forgejo **and** API uploads (examples, submissions). The 1 MB default rejects them all with nginx's HTML 413 page. |
| single `location /`, no path rewrite | Traefik owns `/api`, `/auth`, `/forgejo`, `/docs`; stripping paths breaks routing. |

## Telling the two 413s apart

Uploads cross two independent size limits; the response body tells you which one fired:

- **nginx's stock HTML page** (`<h1>413 Request Entity Too Large</h1>` … `<center>nginx</center>`)
  → this vhost is missing `client_max_body_size` (or it is too small). The request
  never reached the stack. Fix in nginx, reload.
- **JSON** `{"detail": {"error": "Request body too large. Maximum allowed size is …"}}`
  → the request passed nginx and hit the backend's own limiter, capped by
  `MINIO_MAX_UPLOAD_SIZE` in `.env` (bytes; 20 MiB in prod). Raise the env var and
  restart the backend. Note: the example-upload JSON base64-encodes binary files
  (~+33%), so a 20 MiB body cap fits roughly 15 MiB of actual example content.

A quick unauthenticated probe distinguishes the layers without touching real data —
any body that clears both limits earns a backend `400 VAL_001` (request validation),
proving it traversed the full chain:

```bash
dd if=/dev/zero of=/tmp/probe bs=2M count=1
curl -s -X POST https://<domain>/api/examples/upload \
  -H "Content-Type: application/json" --data-binary @/tmp/probe -w "\n%{http_code}\n"
```

## Checklist

- [ ] `server_name` matches `PUBLIC_DOMAIN` in `.env`.
- [ ] TLS cert valid for the domain.
- [ ] WebSocket upgrade forwarded (`map` block + `proxy_http_version 1.1` + `Upgrade`/`Connection` headers). Verify in the browser: DevTools → Network → WS filter shows a `wss://` connection with status 101 inside a workspace.
- [ ] HTTP/2 enabled (DevTools Protocol column shows `h2`, not `http/1.1`).
- [ ] `proxy_read_timeout` raised above the 60s default.
- [ ] `X-Forwarded-Proto https` (+ Host/Port) headers set.
- [ ] Keycloak proxy buffers raised.
- [ ] `client_max_body_size 512M` present in every `server` block that serves the
      stack (also the ones for alternate hostnames). NOT Forgejo-only: example and
      submission uploads need it too — without it they 413 at nginx.
- [ ] Port 8080 not reachable from outside the host (loopback bind, or firewalled).
- [ ] `nginx -t` passes; reload done.

> The stack itself needs no nginx-specific config beyond `PUBLIC_DOMAIN`. Keycloak
> (`KC_PROXY_HEADERS=xforwarded`) and Traefik (`forwardedHeaders.trustedIPs`) are
> already configured to trust these forwarded headers in production.

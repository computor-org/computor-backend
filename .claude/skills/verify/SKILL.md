---
name: verify
description: How to drive the running computor dev stack (backend API + web UI) to verify changes end-to-end — headless auth included.
---

# Verifying against the running dev stack

## Handles

- Backend: `http://localhost:8000` (`python3 server.py` from `computor-backend/src`, uvicorn with reload — code edits are live immediately). `GET /docs` = liveness; `GET /openapi.json` to confirm route changes landed.
- Web: `http://localhost:3000` (Next.js dev server, hot reload).
- If either is down: start via `./computor.sh` + `api.sh` / `web.sh` (never raw docker compose).

## Headless API auth (no browser)

Bearer/cookie auth = Redis session lookup, so mint one directly:

```python
# source .env first (REDIS_PASSWORD); redis on localhost:6379
import hashlib, json, secrets, redis
token = secrets.token_urlsafe(32)
r = redis.Redis(host="localhost", port=6379, password=REDIS_PASSWORD)
key = "sso_session:" + hashlib.sha256(token.encode()).hexdigest()
r.setex(key, 600, json.dumps({"user_id": ADMIN_UUID, "provider": "keycloak"}))
```

- Admin user id: `docker exec computor-postgres-1 psql -U postgres -d computor -tAc "SELECT u.id FROM \"user\" u JOIN user_role ur ON ur.user_id=u.id WHERE ur.role_id='_admin' LIMIT 1"` (dev bootstrap: admin@computor.local).
- Use as `Authorization: Bearer <token>` OR cookie `ct_access_token=<token>`.
- Cleanup: delete `sso_session:{sha256}` and `sso_permissions:{sha256}` (TTL refreshes on every request, so don't rely on expiry).

## Driving the web UI (Playwright)

Playwright + chromium are already installed (`computor-web/node_modules`, `~/.cache/ms-playwright`). Run scripts with `NODE_PATH=computor-web/node_modules node script.js`.

The UI shows the login page unless BOTH are present:
1. Cookie `ct_access_token` (domain `localhost`, the minted token above) — backend auth.
2. sessionStorage seeded via `context.addInitScript` — the frontend treats the session as dead without a cached user:
   - `auth_user`: `{"id": <uuid>, "username": <email>, "email": <email>, "givenName": ..., "familyName": ..., "role": "admin", "systemRoles": ["_admin"]}`
   - `auth_views`: `[]`, `auth_provider`: `"sso"`

## Gotchas

- `body.innerText` does NOT include `<input>` values — read `inputValue()` on inputs when checking form state.
- DB writes during verification: check `workspace_template_settings` (etc.) state before, delete created rows after (main postgres = `computor-postgres-1`, port 5437; NEVER touch coder postgres 5439).
- Backend unit tests need `.env` sourced in the same shell command (`set -a; source .env; set +a; pytest ...`).

# GDPR Consent Gate

Blocks API access for authenticated users who have not consented to
(acknowledged) the current privacy-policy version. Implements informed,
versioned, auditable, withdrawable consent (GDPR Art. 7).

## Legal-basis note — read before changing UI copy

- **Strictly necessary authentication cookies** (Keycloak SSO session,
  `ct_access_token`/`ct_refresh_token`) do **not** require consent under
  ePrivacy/GDPR. The consent page presents them as **information only** —
  never as an opt-in checkbox.
- Whether this gate records *consent as a legal basis* (Art. 6(1)(a)) or an
  *informed acknowledgment* of processing based on contract / public task /
  legitimate interest depends on what the privacy-policy text declares. The
  mechanism is identical; **the UI wording must match the policy text**.
  Confirm the exact legal basis and wording with whoever owns the privacy
  policy before the first production policy version is published.

## Data model

Migration: `computor-backend/.../alembic/versions/dd2e3f4a5b6c_add_consent_tables.py`

- **`policy_versions`** — append-only, immutable. One row per version;
  `languages text[]` lists the available language variants, `content_hashes`
  stores a sha256 per language for tamper-evidence. The **current** version is
  the latest row with `effective_from <= now()` — set `effective_from` in the
  future to schedule a policy. Never UPDATE/DELETE rows; a change = a new row.
- **`user_consents`** — audit trail (who, when, which version, ip, user-agent,
  optional granular `purposes`). Valid consent = row with the current
  `policy_version` and `withdrawn_at IS NULL`. Partial unique index
  `(user_id, policy_version) WHERE withdrawn_at IS NULL` makes concurrent
  first-consent idempotent. Withdrawal sets `withdrawn_at` (row is kept).
  `policy_version` is a FK to `policy_versions.version`.

**Deviation from the original task spec:** `user_consents.user_id` is the
internal `user.id` UUID (FK, `ON DELETE CASCADE`), not the Keycloak `sub`.
This backend resolves Keycloak identities to local users at login and only the
internal id is available everywhere (Principal, Redis caches, triggers);
storing `sub` would have broken referential integrity and local-account users.

## Policy texts (MinIO)

Markdown notices live in the default MinIO bucket under
`policies/{version}/{lang}.md` (e.g. `policies/2026-07-04/de.md`).
**Write-once is enforced by the DB row**: a version that exists in
`policy_versions` can never be published again, so its objects are never
rewritten. Orphaned objects from a *failed* publish (uploads succeeded, DB
insert didn't) may be overwritten by a retry — otherwise a failed publish
would burn the version name forever. Consider additionally enabling bucket
versioning on MinIO in production. The DB row (`version`, `languages`,
`content_hashes` — a sha256 per language for tamper-evidence) is the index;
MinIO holds the content.

## Endpoints (`/consent`, all authenticated, all whitelisted from the gate)

Note: this app has no global `/api` prefix (routers mount at root, e.g.
`/users`, `/auth`), so the consent routes live at `/consent`, not
`/api/consent`.

| Endpoint | Purpose |
|---|---|
| `GET /consent/status` | `{required_version, has_consented, granted_at}` |
| `POST /consent` | body `{policy_version, purposes?}`; records consent + ip/user-agent; 201 |
| `POST /consent/withdraw` | sets `withdrawn_at`; user is gated again |
| `GET /consent/policy?lang=de` | current version + Markdown text; falls back to `en`, then the first available language |
| `GET /consent/policy-versions` | admin: list versions |
| `POST /consent/policy-versions` | admin: publish `{version, effective_from?, texts: {lang: md}}` |

## Middleware (`middleware/consent.py`)

**Ordering:** auth in this codebase is a per-route dependency, not middleware,
so no middleware ever sees a resolved Principal. The gate resolves the user
itself via the shared `middleware/principal_lookup.py`. Registration order in
`server.py` (outermost first):
`CORS → Maintenance → ConsentGate → UploadSizeLimiter`. The gate must stay
inside CORS so its 403 responses carry CORS headers. The downstream app is
invoked outside the gate's try block, so endpoint exceptions propagate
normally (they are never swallowed by the fail-open handler).

**Identity resolution** (`middleware/principal_lookup.py`, shared logic that
`MaintenanceMiddleware` can migrate to later): credential precedence mirrors
`parse_authorization_header` exactly — `X-API-Token`, then `GLP-CREDS`, then
`Authorization`, then the `ct_access_token` cookie only when no Authorization
header is present — so the gate always judges the same identity the route
authenticates. Sources: SSO tokens → principal cache, falling back to the
`sso_session:{hash}` store; API tokens → principal cache, falling back to one
indexed DB lookup (`api_token.token_hash` is a deterministic sha256), so
infrequent API-token clients are still gated; GLP-CREDS → principal cache
only.

Flow: whitelisted path or OPTIONS → pass; unresolvable credentials → pass (the
route's auth dependency 401s); service principals (`is_service`) → pass; no
effective policy version → gate inactive; otherwise Redis-cached consent check
(`consent:{user_id}:{version}`, TTL 300 s, DB fallback in a threadpool) and

```json
403 {"error": "consent_required", "required_version": "2026-07-04"}
```

**Whitelist:** exact `/`, `/consent`, `/docs`, `/redoc`, `/openapi.json`,
`/extensions-public`, `/extensions-getting-started`; prefixes `/consent/`,
`/auth/`, `/password/`, `/invites/` (public registration), `/docs/`; plus
GET-only `/user` and `/user/views` (the web UI needs the signed-in identity to
render the consent page). Prefixes end with `/` deliberately so they cannot
cover sibling routes (`/docs` must not exempt `/documents`; a bare `/ws`
prefix would have exempted `/workspaces/*` — WebSockets need no entry because
non-HTTP scopes are skipped). The documents API (`/documents`) **is** gated.

**Caching / invalidation:** the current version is resolved by
`business_logic.consent.resolve_current_policy_version` — the same
Redis-cached helper the consent endpoints use, so the gate and the API can
never disagree about the required version (relevant around scheduled
`effective_from` boundaries). Cached at `consent:current_version` (TTL 300 s,
invalidated on publish). The per-user key includes the version, so a version
bump auto-invalidates stale entries; `POST /consent` refreshes the key,
withdraw deletes it. Policy Markdown is additionally cached at
`consent:policytext:{version}:{lang}` (immutable content, TTL 1 h). On
Redis/DB failure the gate **fails open** (logged) — an infra outage must not
take down the API.

**Kill switch:** `CONSENT_GATE_ENABLED=false` disables the middleware. The
gate is also inactive as long as no `policy_versions` row is effective — a
fresh deployment is not gated until the first policy is published.

**Known limitation:** HTTP Basic credentials (dev `admin/admin`, some test
suites) cannot be resolved without password verification and pass the gate;
GLP-CREDS users are only gated while their principal cache entry (15 min TTL)
is warm. All real clients (web, VS Code extension) use SSO tokens/cookies or
API tokens and are fully gated.

## Frontend (computor-web)

- Interceptors in `src/utils/apiClient.ts` (`apiFetch`) and
  `src/api/client.ts` (generated clients): any 403 with
  `error === "consent_required"` stores the current route in
  `sessionStorage['consent_redirect']` and navigates to `/consent`.
- Bootstrap check once per page load in `AuthenticatedLayout` via
  `GET /consent/status`.
- `/consent` page: standalone (no sidebar/topbar — those fire gated calls),
  renders processing info + cookie info (info-only), the Markdown notice with
  language switcher, the version, and an **unchecked-by-default** checkbox.
  On submit → `POST /consent` → returns to the originally requested route.
  `/consent?review=1` shows the notice read-only after consent.
- Withdraw: Settings → "Privacy & Consent" (status, view notice, withdraw with
  confirmation; after withdrawal the user lands back on `/consent`).

## ⚠️ Cross-client impact — VS Code extension (decide before merging)

The VS Code extension hits the same API and will receive
`403 {"error": "consent_required", "required_version": ...}` for unconsented
users on every non-whitelisted call. **No extension-side handling exists yet.**
Recommended minimal flow: detect the stable error body, show a notification
("WISCode needs your consent — open the web UI"), deep-link to
`{web}/consent`, and retry after the user returns. A headless consent path was
deliberately not built — consent should be given on a page that shows the full
notice. Track this as a follow-up issue for the extension before enabling the
gate in production (i.e. before publishing the first policy version).

## Ops: publishing a policy version

```bash
curl -X POST "$API/consent/policy-versions" \
  -H 'Content-Type: application/json' -H "X-API-Token: $ADMIN_TOKEN" \
  -d '{
    "version": "2026-07-04",
    "effective_from": null,
    "texts": {"de": "# Datenschutzhinweis\n...", "en": "# Privacy notice\n..."}
  }'
```

Publishing with `effective_from <= now()` re-gates **all** users who have not
consented to the new version on their next request (within the ≤300 s cache
TTL). Users must re-consent after every version bump — bump only for material
changes.

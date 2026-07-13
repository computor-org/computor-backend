# 02 — Target Architecture (integration harness)

The harness keeps its proven shape — pytest + httpx, black-box over HTTP, session-scoped
idempotent fixtures, accumulating state, markdown reporting — and swaps the broken parts:
GitLab CE out, **Keycloak + Forgejo in**, auth fixtures rebuilt around the real SSO path.

## 1. Docker stack (`integration-tests/docker-compose.integration.yaml`)

| Service | Source / image | Host port (proposal) | Notes |
|---|---|---|---|
| `api` | `../docker/api/Dockerfile` | 18000 | keep; env additions below; `CODER_ENABLED=false` stays |
| `postgres` | postgres:16 | 15432 | keep |
| `redis` | redis:alpine | 16379 | keep |
| `minio` | minio:latest | 19000/19001 | keep |
| `temporal` + `temporal-ui` | temporalio/auto-setup:1.27.0 / ui | 17233 / 18088 | keep |
| `temporal-worker` | `../docker/temporal-worker/` | — | keep (core worker: hierarchy/template workflows) |
| `temporal-worker-testing` | `../docker/temporal-worker-testing/` | — | keep (`--queues=testing`, `TESTING_EXECUTABLE=computor-test`, python 3.13) |
| **`keycloak` + `keycloak-db`** | quay.io/keycloak/keycloak:25.0.6 + postgres:16 | 18180 (http) | NEW — blueprint: `ops/docker/docker-compose.keycloak.yaml`; `start-dev --import-realm`; health on mgmt port 9000, `start_period: 60s` |
| **`forgejo` + `forgejo-db` + `forgejo-bootstrap`** | codeberg.org/forgejo/forgejo:9 + postgres:16 + one-shot | 13030 (http) | NEW — blueprint: `ops/docker/docker-compose.forgejo.yaml`; bootstrap via `computor-forgejo/scripts/bootstrap.sh` creates the admin |
| ~~`gitlab`~~ | — | — | REMOVED (with ports 8085/8444/2224, `GITLAB_*` env, bootstrap script) |

Forgejo must keep the self-migration settings from the ops blueprint — student repos are
**self-migrated template copies**, so without these, `provision-repository` fails:

```yaml
FORGEJO__migrations__ALLOW_LOCALNETWORKS: "true"
FORGEJO__migrations__ALLOWED_DOMAINS: "forgejo"   # pinned to the container's own hostname
```

## 2. API/worker environment additions

| Variable | Value (integration) | Why |
|---|---|---|
| `KEYCLOAK_ENABLED` | true (default) | SSO is the only auth path |
| `KEYCLOAK_SERVER_URL` | `http://keycloak:8080` | backend↔Keycloak in-network (code exchange, admin API) |
| `KEYCLOAK_REALM` / `KEYCLOAK_CLIENT_ID` | `computor` / `computor-backend` | realm import below |
| `KEYCLOAK_CLIENT_SECRET` | fixed IT value in `.env.integration.template` | substituted into the realm JSON at `make env` |
| `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD` | IT values | backend admin-API ops (`auth/keycloak_admin.py`), invite provisioning |
| `API_ADMIN_EMAIL` / `API_ADMIN_PASSWORD` | `admin@integration.test` / IT value | `ensure_keycloak_admin` (`server.py:163-179`) → Keycloak group `administrators`; **first login grants `_admin`** |
| `GIT_SERVER` | `forgejo` | triggers `ensure_managed_forgejo_registered` (`server.py:238-244`) — auto-registers the managed GitServer + mints its service token |
| `GIT_SERVER_URL` | `http://forgejo:3030` | backend↔Forgejo in-network |
| `GIT_SERVER_URL_PUBLIC` | `http://localhost:13030` | what `to_public_git_url` hands to clients — host-side `git clone` in tests must work |
| `GIT_SERVER_ADMIN_USERNAME` / `GIT_SERVER_ADMIN_PASSWORD` | IT values (match `forgejo-bootstrap`) | managed-server admin ops |
| `DEPLOYMENTS_DIR` | `/deployments` (bind-mount `integration-tests/deployments/`) | see §3 |
| `TESTING_WORKER_TOKEN` | **real `ctp_` format, ≥32 chars** | shared by api (YAML expansion) and worker (`API_TOKEN`); the old fallback `it-worker-token-change-me` fails `validate_token_format` (`permissions/auth.py:229`) |

Realm import: `make env` stages `data/keycloak/computor-realm.json` into the Keycloak
import volume with the IT client secret substituted (same mechanism `startup.sh` uses via
`SYSTEM_DEPLOYMENT_PATH`). Import happens **on first boot only** — `make clean` (volume
wipe) is the reset. The realm ships clients `computor-backend` (confidential),
`computor-vscode`, `forgejo`; only `computor-backend` matters here.

## 3. Bootstrap deployments (`integration-tests/deployments/`)

`ensure_bootstrap_services` (`business_logic/bootstrap.py`) applies `services:` and
`example_repositories:` from every YAML in `DEPLOYMENTS_DIR` at each API start,
idempotently. The integration stack currently stages **nothing**, so no Service row
exists and no test run can execute. Add two committed files:

- `testing-worker.yaml` — the Service the examples' `executionBackend.slug` resolves to:
  `slug: itpcp.exec.py`, `service_type_path: testing.temporal`,
  `config.temporal.task_queue: testing` (must equal the worker's `--queues`),
  `api_token.token: ${TESTING_WORKER_TOKEN}`.
- `example-repository.yaml` — the default MinIO-backed `example_repositories:` entry
  (`source_url: computor-storage` bucket) that `POST /examples/upload` targets.

## 4. Auth fixture design (`fixtures/keycloak_auth.py`, new)

Constraints discovered in code: the backend only honors (a) `ctp_` API tokens and
(b) Bearer tokens that map to a Redis session minted by `GET /auth/keycloak/callback`.
There is no ROPC endpoint. Therefore the fixture performs the **headless authorization-
code dance** with plain httpx (no browser):

1. `GET {api}/auth/keycloak/login` with `follow_redirects=False` → 302 to the Keycloak
   authorize URL (`api/auth.py:75-134`).
2. **Rewrite the authorize URL host** `keycloak:8080 → localhost:18180` (the backend
   emits its in-network URL; Keycloak `start-dev` doesn't enforce hostname). Keep the
   query string (contains the backend-minted `state`) intact.
3. GET the authorize URL with a cookie jar; parse the login form `action` from the HTML.
4. POST `username` + `password` to the form action (Keycloak cookies attached).
5. Keycloak 302s to `{api}/auth/keycloak/callback?code=…&state=…`; GET it with
   `follow_redirects=False` and read `token` / `refresh_token` from the final redirect's
   `Location` query params (`api/auth.py:143-243`).

Invite-created users are immediately form-login-capable: `provision_keycloak_login`
creates them `enabled`, `emailVerified: true`, non-temporary password, no required
actions (`business_logic/auth.py:735-783`).

Fixture rules:
- **One login per persona per pytest session** (session-scoped bearer `httpx.Client`s in
  `fixtures/clients.py`, as today) — cheap, and avoids Keycloak brute-force heuristics.
- The admin persona **must log in once before any admin API call**: the `_admin`
  UserRole is granted during the first SSO callback (group `administrators`), not at
  user creation.
- Escape hatch (documented, not default): mint `sso_session:{sha256(token)}` directly in
  Redis for pathological cases — the harness already has DB and Redis fixtures.
- If the login dance ever breaks (Keycloak theme/form change), it is the *first* thing
  `02_auth` smoke-asserts, so failures localize.

## 5. Persona seeding (`fixtures/users.py`, rewritten)

Personas (see [03-personas-and-scenario.md](03-personas-and-scenario.md)) are seeded
through the **real onboarding flow**, session-scoped and idempotent:

1. Admin (env-bootstrapped) logs in.
2. Admin `POST /admin/invites` with `roles=[…]` for the key-role personas; `uma`
   creates the plain invites for course personas.
3. Each persona `POST /invites/{token}/accept` (public), then logs in via §4.
4. Idempotency: "find-or-create" — if the user already exists (accept returns the
   already-used error on re-run), skip straight to login. Fixed emails/passwords from
   `.env.integration.template`.

This *is* the golden path's phase 0 — the seeding fixture and scenario steps 1–2 are the
same code, asserted once in `02_auth`.

## 6. State model

Unchanged by design: the stack boots once per session, state accumulates, fixtures are
find-or-create, `make clean` wipes volumes. Two additions:

- **Namespacing**: scenario objects carry a fixed slug prefix (`it-…`) so re-runs against
  a dirty stack remain idempotent (org path `it.org`, course `it.course.python`, …).
- **Ordering**: suites are numbered by dependency (01 stack → 02 identity → 03/04
  read-mostly → 05–08 lifecycle). `pytest-xdist` parallelism only *within* suites that
  are read-only (03/04); lifecycle suites run serially (`-p no:randomly`, no xdist).

## 7. Reporting

Keep `reporting.py` (`reports/latest.md`) and extend:
- the existing endpoint×role **matrix cross-tab** (from `record_property` observations);
- a new **grading-outcome table** for the lifecycle run: per student × assignment —
  submitted?, test result, grade, grading status. This satisfies "the grading in the end
  should show what happened".

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Keycloak first-boot realm import is slow (~30–60s) and only runs on a fresh volume | healthcheck on mgmt `:9000/health/ready`, `start_period: 60s`; `wait_for_services.sh` polls it; realm changes require `make clean` (document loudly) |
| Forgejo bootstrap one-shot ordering (admin must exist before API starts registering) | `depends_on: condition: service_completed_successfully` on `forgejo-bootstrap`; API healthcheck retries |
| Test runs execute real Python via Temporal — polling can flake | poll `GET /tests/status/{result_id}` with generous timeout (≥120s per example) and fail with the workflow status in the message |
| `/tests` rate limit 1/s/user (`RATE_003`) | serialize per-student test submissions in the fixture helper (sleep ≥1s between `POST /tests`) |
| 10 MB upload cap (`MINIO_MAX_UPLOAD_SIZE`) | solution ZIPs are tiny; assert the cap explicitly in 04_contracts instead of tripping it accidentally |
| Authorize-URL host rewrite is a heuristic | isolate in one helper; assert early in 02_auth; fallback documented (`/etc/hosts` alias or running pytest inside the compose network) |
| Sibling-package imports (`computor-types` DTOs) via `sys.path` hack in `conftest.py` | keep but declare intent: typed payload assertions **should** import `computor_types`; promote to editable installs in the Makefile `env` target if the hack breaks |

# Service accounts

Everything that talks to Computor without a human behind it — testing systems,
integrations, AI agents — is a **service account**. This page explains the model,
how to add one, and the two contracts that trip people up.

## The model

```
User (is_service = true)  ──1:1──  Service  ──N:1──  ServiceType
      │                               │
      │                               └── config  (JSONB: language, temporal.task_queue, …)
      └── ApiToken(s)                      slug    (the meta.yaml binding — see below)
```

| Table | What it is |
|---|---|
| `user` with `is_service = true` | The **identity**. Has no password (the column was dropped when Keycloak SSO became the only human login) and holds **no roles**. |
| `service` | The **metadata**: `slug`, `config`, `enabled`, `last_seen_at`. One row per service, 1:1 with its user. |
| `service_type` | The **taxonomy**: an ltree `path` (`testing.temporal`, `agent`) plus a `category` that decides default token scopes. |
| `api_token` | The **credential**, hung off the *user*, not the service. `ctp_<32 chars>`, stored SHA-256 hashed; only the 12-char prefix is kept in the clear. |

A service account authenticates by sending `X-API-Token: ctp_…`. That header takes
precedence over `Authorization` (`permissions/auth.py:parse_authorization_header`).

## Two contracts worth getting right

### 1. An example declares what it needs; the slug is an optional pin

An example's `meta.yaml` declares how it must be executed. Prefer **language** —
it says what the example actually is, and resolves on any installation that has
a runner for it:

```yaml
properties:
  executionBackend:
    language: python        # ← what this example needs (portable)
    version: "3.13"         # ← optional; matched against Service.config.language_version
    settings: { timeout: 60 }
```

Use **slug** only when you genuinely need one specific registered service:

```yaml
properties:
  executionBackend:
    slug: acme.exec.py      # ← must equal Service.slug (a pin)
```

Exactly one of the two is required. A pin is honoured **strictly**: if that
service is missing or disabled, resolution returns nothing rather than
substituting a different runner — silently running a student's code on a
backend the author didn't choose is not a favour. Language binding is what makes
examples transferable; a slug hardcodes one deployment's service naming into the
content, so sharing those examples between installations requires editing every
`meta.yaml`.

Resolution (one rule, shared by upload, assignment and test time —
`business_logic/testing_service.py:resolve_service_for_execution_backend`):

1. a pinned `slug` → that enabled service, or nothing;
2. else `language` → a runner whose `config.language` matches, preferring an
   exact `config.language_version` match, then a runner that declares no version.

That last step is how you run e.g. python 3.11 and 3.13 as separate workers:
give each service a `config.language_version`, and examples that don't care
still land on whichever runner declares no version.

The binding is resolved at upload (`api/examples.py:_resolve_testing_service_id`),
at assignment (`lecturer_deployment:_link_testing_service`) and again at test time
(`business_logic/testing_service.py:resolve_testing_service`) — all three now
delegate to the single rule above.

`CourseContent.testing_service_id`, `ExampleVersion.testing_service_id` and
`Result.testing_service_id` are **caches** of that resolution, self-healing. So an
example can be uploaded and assigned before its service exists — testing starts
working the moment a matching runner appears.

The slug is an **identifier you choose**. It does not select the test runner and
carries no meaning to the code — `config.language` does that. Any name works,
which is exactly why binding content to it is a liability: the name is arbitrary
and local to one deployment.

### 2. `config.language` selects the runner

```yaml
config:
  language: python                  # selects the runner
  temporal:
    task_queue: testing             # must equal the worker's --queues= value
```

Valid languages: `python`, `octave`, `r`, `julia`, `c`, `cpp`, `fortran`,
`document`, `matlab`. The first eight run through the `computor-test <language> run`
CLI; `matlab` talks to a MATLAB engine over Pyro5.

Creating a `testing.*` service without a language is rejected at creation. If one
somehow reaches dispatch without it, the run fails loudly naming the service and
the valid values — it never guesses.

> **Historical note.** Until 2026-07, `TestingBackendFactory` looked the *slug* up
> in a hardcoded table of eight `itpcp.exec.*` names (and `ComputorTestingBackend`
> kept a second copy of the same table). A service registered under any other slug
> bound to examples correctly and then died at execution with "Unknown testing
> backend", so adding a testing system meant a code change and a redeploy. Both
> tables are gone. Adding a testing system is now a data change.

## Adding a service account

Two routes to the same rows. Pick by how reproducible it needs to be.

### Web UI — `/admin/services`

Admin or `_service_manager`. Create the service, then mint its token on the detail
page; the value is shown **once**. Best for ad-hoc and delegated work.

### Bootstrap YAML — the reproducible one

Any `services:` block under `data/deployments/*.yaml` is applied idempotently on
**every API start** (`business_logic/bootstrap.py:ensure_bootstrap_services`):
created once, then a no-op.

```yaml
services:
  - slug: itpcp.exec.py
    service_type_path: testing.temporal
    language: python                    # folded into config.language at apply time
    user:
      email: testing-worker@computor.local
      given_name: Testing
      family_name: Worker
    api_token:
      token: ${TESTING_WORKER_TOKEN}    # expanded from the environment
      name: Testing Worker Token
      expires_days: 365
    config:
      temporal:
        task_queue: testing
```

This is the only route that can pin a **predefined** token value, which is what
keeps the API and the worker container from drifting: `api_token.token` and the
container's `API_TOKEN` read the same environment variable.

Tokens are deliberately **never auto-rotated** here. Changing `TESTING_WORKER_TOKEN`
does not re-issue anything — that would silently break a running worker. Rotate on
purpose: mint the new token, update the container's `API_TOKEN`, restart it, then
revoke the old one.

The token value is also validated with the same checker authentication uses
(`ctp_` + exactly 32 url-safe base64 characters). A near-miss used to be stored
happily and then rejected on every request as "Invalid API token format".

**Expiry is a cutoff, not a nudge.** `expires_days: 365` means that a year after
first boot the worker stops authenticating and every test fails — and because
the seeding check only asked "is there an unrevoked token", it kept reporting
*already present* while the pipeline was dead. Startup now warns for the last 30
days, and if the token has already lapsed while the deployment file still pins
that same value, it extends the expiry (same secret, so nothing needs
reconfiguring). Omit `expires_days` for a token that never expires.

## Wiring a testing worker

```
docker-compose        Service (DB)                 worker container
  API_TOKEN=ctp_…  →  api_token.token_hash    →    GET /service-accounts/me
  --queues=testing    config.temporal.task_queue    → config.language → runtime setup
```

Three things must agree — and two of them are now checked for you:

1. The container's `API_TOKEN` must be an active token on the service's user.
2. `config.temporal.task_queue` must equal the container's `--queues=` value.
   **Checked:** `POST /tests` refuses a service whose queue has no listening
   worker, naming the queue, instead of leaving the run stuck. You can also just
   omit `task_queue` — see below.
3. `config.language` must name a runtime the image actually has. **Checked:** the
   worker refuses to start if its image cannot provide the language its service
   advertises, rather than claiming tests it will certainly fail.

### One worker per language

The intended topology is one worker image per language, so the queue is derived
from the language: a service with `language: octave` and no `temporal.task_queue`
routes to **`testing-octave`**, and you start that worker with
`--queues=testing-octave`. An explicit `task_queue` always wins, so existing
deployments (and bespoke topologies like `testing-python-gpu`) are unaffected.

To add a language:

```bash
scripts/add-testing-language.sh octave
```

That mints a conforming token into `.env`, writes
`data/deployments/testing-worker-octave.yaml` (bootstrap globs that directory,
so no existing file is edited), and prints the compose block to paste. Restart
the API to seed the service, then `./computor.sh up`.

Scaling *one* language across several containers does not need any of this —
use `replicas` on the same queue.

`last_seen_at` on the service is a heartbeat (`PUT /service-accounts/{id}/heartbeat`).
The unified testing worker does not currently call it, so "never" there is not yet
evidence of a problem.

## Token scopes are additive — they never restrict

This is the single most misread part of the system.

`PrincipalBuilder.build` (`permissions/auth.py`) appends every scope on a token to
the principal as a `("permissions", scope)` claim. Scopes **grant**. There is no
mechanism by which a scope removes anything.

Consequences:

- A **service** user holds no roles at all, so its token's scopes are its entire
  authority. That is what makes scopes meaningful — and why leaving the scope list
  empty at creation is normal: the backend fills in the defaults for the service
  type's category (`DEFAULT_SERVICE_SCOPES` in `business_logic/api_tokens.py`;
  `testing` gets 15, including `result:create` and `example:download`).
- A token on a **human** account carries that person's full role set regardless of
  what scopes are listed. A "read-only" personal token does not exist. Every
  `workspace-auto-login:*` token in the system has `scopes: []` and full user power.

That asymmetry is why only admins may mint a token for another human, and why a
`_service_manager` is confined to service accounts (below).

### …but there is a ceiling on what you may grant

Because scopes only ever add authority, "who may mint" is not by itself enough:
a `_service_manager` holds nothing but `service:*` and `api_token:*`, yet could
once mint a service token carrying `result:update` or `user:create` and then
authenticate as that service — forging grades in any course.

`assert_may_grant_scopes` (`business_logic/api_tokens.py`) closes that:

| Caller | May grant |
|---|---|
| `_admin` | any scope |
| anyone else (e.g. `_service_manager`) | only the scopes in `DEFAULT_SERVICE_SCOPES` for the target service type's **category** |

So provisioning a testing worker still works — `testing` category ⇒ its 15
scopes — while a service manager cannot invent authority the type was never
meant to have. The ceiling applies at every write: `POST /api-tokens`,
`POST /api-tokens/admin/create`, and `PATCH /api-tokens/admin/{id}` (re-scoping
is minting by another name). Because the same table is now also the allow-list,
keep the defaults tight — `worker` deliberately no longer includes
`course:create`/`course:update`.

## Governance

| | `_admin` | `_service_manager` |
|---|---|---|
| Create / edit / archive services | ✅ | ✅ |
| See service-owned tokens | ✅ | ✅ |
| Mint / revoke tokens on **service** accounts | ✅ | ✅ |
| See or revoke another **human's** tokens | ✅ | ❌ (404) |
| Mint a token for another human | ✅ | ❌ (403) |
| Create service **types** | ✅ | ❌ |
| Enrol a service in a course | ✅ | only where they also hold a course role |

`_service_manager` exists so machine identities can be delegated without handing
out admin. `ApiTokenPermissionHandler` narrows its token queries to service-owned
rows; `assert_may_mint_token_for` blocks the mint path. Both are needed: without
the narrowing a service manager could revoke an admin's tokens (denial of
service), and without the mint guard they could issue themselves admin authority.

## AI agents

The `agent` ServiceType is seeded and usable today as **plumbing**: create an agent
service, mint it a token, and enrol it in a course from the service detail page.
Enrolment gives it that course role's permissions through normal course-membership
claims, independent of its token scopes. Because the `agent` type has
`requires_workspace = false`, `_should_skip_service_account` skips the post-create
hooks — no git repository is provisioned.

There is **no agent runtime**: no LLM calls, no `@mention` activation, no websocket
consumer. `DEFAULT_SERVICE_SCOPES` has no `agent` entry either, so agent tokens
default to `[]` and an agent's authority comes from its course membership.

## Fields that look meaningful but are not

- **`ServiceType.schema`** — a JSON Schema for `Service.config`, shipped to workers
  but **never validated against**. Treat it as documentation.
- **`ServiceType.plugin_module`** — a filter column only; nothing imports it.
- **`ApiToken.last_used_at` / `usage_count`** — written only on a Redis cache *miss*
  (`permissions/auth.py`, 120 s TTL), so they undercount badly. A liveness hint, not
  an audit log.
- **Archiving a service** is a soft delete and `service.user_id` is `RESTRICT`, so
  the user survives and **the slug stays taken**. Archiving is not a way to free a
  slug for reuse.

## Where things live

| Concern | File |
|---|---|
| Models | `computor-backend/…/model/service.py` |
| Business logic | `…/business_logic/service_accounts.py`, `…/business_logic/api_tokens.py` |
| Boot seeding | `…/business_logic/bootstrap.py`, `data/deployments/*.yaml` |
| Endpoints | `…/api/services.py` (`/service-accounts`), `…/api/api_tokens.py` (`/api-tokens`), `…/api/service_type.py` (`/service-types`) |
| Authorization | `…/permissions/handlers_service.py`, `…/permissions/role_setup.py` |
| Runner dispatch | `…/testing/backends.py` |
| Slug resolution | `…/business_logic/testing_service.py` |
| Web UI | `computor-web/app/admin/services/` |

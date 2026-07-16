# Architecture

Computor is a **monorepo of independent packages** with a single source of truth for data
contracts. The Python packages depend on each other in one direction; the web frontend
consumes generated TypeScript.

## Packages

| Package | Purpose | Depends on |
|---------|---------|-----------|
| **computor-types** | Pure Pydantic DTOs — the single source of truth for API contracts, `meta.yaml`/`test.yaml` formats, and deployment configs. Zero backend deps. | — |
| **computor-testing** | Test-execution framework (`computor-tester`). One backend per language (Python, Octave/MATLAB, R, Julia, C, Fortran, Document). Re-exports its models from `computor-types`. | types |
| **computor-client** | Auto-generated async HTTP client (`httpx`). One endpoint client per entity. | types |
| **computor-cli** | `computor` command — auth, CRUD (`rest`), `deployment`, tokens, docs sync, workers, codegen. | client, types |
| **computor-backend** | FastAPI server + business logic + Temporal workflows. | types, client |
| **computor-web** | Next.js frontend (yarn). Consumes generated TS types/clients. | (generated) |
| **computor-coder** | Terraform templates + scripts for provisioning Coder workspaces (not a Python package). | — |

The dependency rule: **types has no dependencies; everything else flows from it.** Never
import SQLAlchemy or backend modules into `computor-types`.

## Layered backend

Each HTTP request flows top-to-bottom; async work is handed off sideways to Temporal.

```
HTTP request
   │
   ▼  api/          🔵 Thin endpoints — routing, DI, response_model. No business logic.
   ▼  permissions/  🟣 RBAC — Principal/Claims, role checks, permission handlers.
   ▼  business_logic/ 🟢 Fat layer — rules, validation, orchestration. Reusable, testable.
   ▼  repositories/ 🟡 Complex/reused queries beyond basic CRUD.
   ▼  model/        🔴 SQLAlchemy ORM — the DB schema (Alembic migrations derive from it).
   ▼  PostgreSQL

   tasks/     ⚡ Temporal workflows/activities — long-running & external work (git, testing).
   services/  🔧 Infra clients — MinIO storage, GitLab/Forgejo helpers, Redis.
```

**The core rule: thin endpoints, fat business logic.** An endpoint injects `Principal` and
`Session` and delegates to a `business_logic/` function that takes explicit parameters,
checks permissions early, and returns a DTO (never an ORM model).

```python
# api/submissions.py — thin
@router.get("/artifacts/{artifact_id}", response_model=SubmissionArtifactGet)
async def get_artifact_endpoint(
    artifact_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    return get_artifact_with_details(artifact_id, permissions, db)  # all logic lives here
```

Other backend modules: `auth/` (external admin clients, e.g. Keycloak), `plugins/`
(pluggable auth providers), `coder/` (workspace API), `generator/` (code generation),
`exceptions/`, `middleware/`. Startup lives in `server.py`; config in `settings.py`;
sessions in `database.py`.

## Data flow

**Synchronous request**: `endpoint → get_current_principal → business_logic → permission
check → query/repository → return DTO`.

**Asynchronous work**: `endpoint/business_logic → start Temporal workflow (task_queue
"computor-tasks") → worker runs activities → external services (git, MinIO, DB) → workflow
completes`. The endpoint returns a workflow handle immediately; it does not block.
See [backend-patterns.md](backend-patterns.md#temporal-workflows).

## Infrastructure services

| Service | Role | Notes |
|---------|------|-------|
| **PostgreSQL** | Primary DB | Audit fields (`created_by/at`, `updated_by/at`) + soft delete (`archived_at`) on every model. Main DB is isolated from the Coder DB. |
| **Redis** | Caching | Tag-based view cache; expanding over time. |
| **MinIO** | S3-compatible object storage | File uploads/downloads, presigned URLs, example repositories. |
| **Temporal** | Workflow orchestration | Reliable async execution with retries; UI at `:8088`. |
| **Traefik** | Reverse proxy | Routing + ForwardAuth (workspace access). |
| **Forgejo** _(optional)_ | In-system git server | Managed per-course git hosting; auto-registers into the GitServer registry at startup. See [git-integration.md](git-integration.md). |
| **Keycloak** _(optional)_ | SSO / IdP brokering | External institute logins brokered via Keycloak. |
| **Coder** _(optional, `CODER_ENABLED=true`)_ | Browser IDE workspaces | Separate Postgres + registry + a dedicated Temporal worker. |
| **Updater** _(optional, `UPDATE_ENABLED=true`, prod)_ | Self-update sidecar | Executes admin-triggered updates (maintenance page → rebuild → restart, auto-rollback). See [ops/docs/SELF_UPDATE.md](../ops/docs/SELF_UPDATE.md). |

## Key design patterns

- **EntityInterface** — one class per entity in `computor-types` defines its Create/Get/
  List/Update/Query DTOs; drives client + TypeScript + OpenAPI generation.
- **Business-logic separation** — thin API, fat `business_logic/` (see above).
- **Repository pattern** — reusable/complex queries in `repositories/`.
- **Auto code generation** — `bash generate.sh {types|clients|python-client|schemas|all}`.
- **Dependency injection** — FastAPI `Depends` for `db`, `permissions`, services.

The first three, plus permissions and Temporal, are detailed in
[backend-patterns.md](backend-patterns.md).

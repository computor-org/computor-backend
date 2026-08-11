---
name: computor-backend-api
description: Computor backend HTTP surface — FastAPI endpoints, CrudRouter registration, business_logic, and the DTOs behind them. Use when adding or changing an API endpoint, a request/response shape, or the business logic under one, in computor-fullstack/computor-backend.
---

# Computor backend — API layer

You own `computor-backend/src/computor_backend/api/` and `business_logic/`, plus
the DTOs in `computor-types` that define their shapes.

**Read first:** `docs/backend-patterns.md` (repo root) — EntityInterface, the
permission pattern, and Temporal, in about 150 lines. Do not restate it back to
the user; act on it.

## The rule that gets broken most

**Every API-facing pydantic model lives in `computor-types`, never in a backend
module.** TypeScript types, the TS API clients, the Python client and the JSON
schemas are all generated from those models.

Know exactly what you lose by putting one elsewhere, because the failure is
partial and therefore easy to miss:

- A model in `business_logic/` is **invisible** to every generator. The frontend
  loses the type and someone hand-writes it.
- A model in `api/` **does** get a TypeScript interface emitted (the interface
  generator scans `api/` and `tasks/` too) — but it gets **no** Python-client
  type and **no** client method, because those come from `EntityInterface`
  discovery. And it is outside the `computor-types` package that the VS Code
  extension and `computor-agent` install. So it looks generated and is only half
  generated, which is worse than plainly missing.

There is exactly one such model left in `api/` today (`api/course_contents.py`).
Keep it at one, or move it.

Placement:

| Kind | Home |
|---|---|
| Request/response DTOs, query filters, enums crossing the wire | `computor-types/src/computor_types/<entity>.py` |
| `EntityInterface` subclass naming the CRUD five | same file as its DTOs |
| SQLAlchemy models | `computor_backend/model/` |
| Internal-only structs never serialized to a client | backend module is fine |

`computor-types` must stay framework-free: no `fastapi`, `starlette`,
`sqlalchemy` or `computor_backend` imports. `scripts/check_forbidden_imports.py`
enforces this in the pre-commit hook. `scripts/check_dto_location.py` catches the
other direction (an API-facing model declared in the backend).

After changing any DTO, regenerate — see the `computor-regenerate-types` skill.
Never hand-edit anything under a `generated/` directory.

## DTO families

One `EntityInterface` per entity naming five DTOs — `Create`, `Get`, `List`,
`Update`, `Query`. `Update` is all-`Optional`; `Query` is all-`Optional` plus
pagination; `List` stays lean because it is what list endpoints serialize per
row. Keep field names identical across the family. Generic `CrudRouter` /
`LookUpRouter` in `api/api_builder.py` turn an interface into
`POST/GET/PUT/DELETE` automatically — reach for a hand-written route only when
the operation is genuinely not CRUD.

## Where logic goes

Endpoints in `api/` stay thin: dependency injection, call `business_logic/`,
return. **Permission checks belong in `business_logic/`, not the endpoint**, and
run early — before expensive work. Admin bypass (`if principal.is_admin: return`)
always exists. For anything beyond a plain check, hand off to
`computor-backend-auth`.

## Footguns

- **`ComputorException` takes `error_code` as the first positional argument.**
  `NotFoundException("Course not found")` sets the *error code* to that sentence
  and produces a garbage response. Always write
  `NotFoundException(detail="Course not found")`.
- **UUID columns want strings in query filters.** Passing a `uuid.UUID` object
  into a filter raises `StatementError` and surfaces as a 500. Convert with
  `str(...)` at the boundary.
- A permission handler that *narrows* a query instead of raising means a
  successful `check_permissions` call says "here is what you may see", not "you
  are authorized" — the caller must then fetch **through the returned query**, not
  re-fetch by id. See `permissions/handlers_service.py` and its call sites.
- Endpoints that render or redirect for the browser use
  `get_current_principal_optional` and return `RedirectResponse(login_url)`
  directly. Raising `HTTPException(302)` breaks — the exception handler turns it
  into a 500.

## Verifying

Use the `verify` skill (project skill in computor-fullstack) to drive the running
dev stack: mint a session token against Redis, hit `localhost:8000`, confirm the
route shape in `GET /openapi.json`. Backend unit tests need `.env` sourced in the
same shell: `set -a; source .env; set +a; pytest …`.

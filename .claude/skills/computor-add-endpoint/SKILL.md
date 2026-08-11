---
name: computor-add-endpoint
description: Add or change a Computor backend API endpoint end to end — DTOs in computor-types, EntityInterface, router registration, business logic with permission checks, code generation and verification. Use when adding a new API route or reshaping an existing one.
---

# Adding a Computor API endpoint

Order matters: the type comes first, everything else is generated from or checked
against it.

## 1. DTOs — in `computor-types`, always

`computor-types/src/computor_types/<entity>.py`. Five DTOs per entity:

| DTO | Shape |
|---|---|
| `Create` | required fields only, no `id`/audit fields |
| `Get` | extends `BaseEntityGet`; full fields + audit; may nest relations |
| `List` | extends `BaseEntityList`; lean — this is what list endpoints serialize per row |
| `Update` | every field `Optional`; only provided ones change |
| `Query` | every field `Optional`, plus `skip`/`limit` |

Field names identical across the family. Pure data — no business logic, no
SQLAlchemy. The package must not import `fastapi`, `starlette`, `sqlalchemy`,
`flask`, `django` or `computor_backend`.

## 2. EntityInterface

```python
class ThingInterface(EntityInterface):
    create = "ThingCreate"
    get    = "ThingGet"
    list   = "ThingList"
    update = "ThingUpdate"
    query  = "ThingQuery"
```

Without this, the TS and Python client generators emit no methods for the entity
— you get types and nothing to call them with. The backend extends the interface
with its own concerns (SQLAlchemy `model`, `endpoint`, `cacheable`, `searchable`).

## 3. Route

Plain CRUD: register with `CrudRouter` / `LookUpRouter` (`api/api_builder.py`) —
you get `POST/GET/PUT/DELETE` for free. Hand-write a route only when the
operation genuinely is not CRUD (`enroll`, `bulk_import`, an export).

Keep the endpoint thin: dependencies in, call `business_logic/`, return.

## 4. Business logic + permissions

In `business_logic/<entity>.py`. **The permission check lives here, not in the
endpoint**, and runs before any expensive work:

```python
def get_thing(thing_id: str, permissions: Principal, db: Session) -> ThingGet:
    thing = db.query(Thing).filter_by(id=thing_id).first()
    if not thing:
        raise NotFoundException(detail="Thing not found")
    check_course_permissions(permissions, thing.course, "read", required_role="_student")
    return ThingGet.model_validate(thing)
```

- `ComputorException` takes **`error_code` first positionally** — always pass
  `detail=` by keyword, or your message becomes the error code.
- UUIDs in query filters must be **strings**; a `uuid.UUID` object raises
  `StatementError` and surfaces as a 500.
- Admin bypass always exists (`if principal.is_admin: return`).
- If a permission handler narrows a query rather than raising, fetch **through**
  the returned query — do not re-fetch by id afterwards.

## 5. Regenerate

```bash
bash generate.sh                       # from the monorepo root
cd computor-web && npx tsc --noEmit
```

Use the `computor-regenerate-types` skill for the extension and `computor-agent`
legs, which `generate.sh` does not reach.

## 6. Verify

```bash
python scripts/check_forbidden_imports.py
python scripts/check_dto_location.py
curl -s localhost:8000/openapi.json | jq '.paths | keys' | grep <your-path>
set -a; source .env; set +a; pytest computor-backend/src/computor_backend/tests/...
```

The `verify` skill mints a session token so you can exercise the route
headlessly. Test the **negative** case too: the role one step below the required
one must be refused. A permission-gated endpoint with only a happy-path test is
not verified.

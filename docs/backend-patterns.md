# Backend Patterns

Three patterns carry most of the backend: **EntityInterface** (data contracts + code
generation), **the permission system** (RBAC), and **Temporal workflows** (async work).

---

## EntityInterface & DTOs

`EntityInterface` (in `computor-types/…/base.py`) is the single source of truth for an
entity's DTOs. One interface per entity references its five CRUD DTOs by name:

```python
class UserInterface(EntityInterface):
    create = "UserCreate"
    get    = "UserGet"
    list   = "UserList"
    update = "UserUpdate"
    query  = "UserQuery"
```

| DTO | Used for | Shape |
|-----|----------|-------|
| `Create` | POST | Required fields only; no `id`/audit fields. |
| `Get` | GET one | Extends `BaseEntityGet`; full fields + audit; may nest relations. |
| `List` | GET many | Extends `BaseEntityList`; lean fields for performance. |
| `Update` | PUT/PATCH | All fields `Optional`; only provided ones change. |
| `Query` | filters | All `Optional`, plus pagination (`skip`, `limit`). |

`BaseEntityList` carries `created_at`/`updated_at`; `BaseEntityGet` adds
`created_by`/`updated_by`. Keep DTOs as pure data — no business logic, no SQLAlchemy
imports. Keep field names identical across a family (`email`, not `email_address` in one).

**Why it matters — code generation.** From these definitions, `bash generate.sh` produces
the Python HTTP client (`computor-client`), TypeScript interfaces, TypeScript clients, and
OpenAPI schema — end-to-end type safety from DB to frontend with no hand-written clients.
`get_all_dtos()` discovers every interface for registration.

On the backend, an interface is extended with backend concerns (SQLAlchemy `model`,
`endpoint`, `cacheable`, `searchable`), and generic CRUD routers (`CrudRouter`,
`LookUpRouter`) turn it into `POST/GET/PUT/DELETE` endpoints automatically. Add custom DTOs
(e.g. `enroll`, `bulk_import`) and Pydantic validators for anything beyond plain CRUD.

---

## Permission system (RBAC)

Access control is a **hierarchical RBAC** system checked in the business-logic layer.

- **Principal** — the authenticated user, injected via `Depends(get_current_principal)`.
  Carries `user_id`, `is_admin`, and `Claims`.
- **Claims** — the user's system roles plus their per-course and per-organization roles
  (`{course_id: role}`), built from `CourseMember` rows at auth time.
- **Course role hierarchy** — higher roles inherit lower ones:

  ```
  _owner > _maintainer > _lecturer > _tutor > _student
  ```

- **Admins bypass every check** (`if principal.is_admin: return`).

The common check:

```python
def get_course(course_id: str, permissions: Principal, db: Session) -> CourseGet:
    course = db.query(Course).filter_by(id=course_id).first()
    if not course:
        raise NotFoundException("Course not found")
    check_course_permissions(permissions, course, "read", required_role="_student")
    return CourseGet.model_validate(course)
```

Recurring shapes:

- **Course-level** — `check_course_permissions(principal, course, action, required_role)`.
- **Resource-owner** — staff (`_tutor`+) see everything; a student only their own rows
  (membership check on the submission group).
- **Admin-only** — `if not permissions.is_admin: raise ForbiddenException(...)`.
- **Assignment ceiling** — when granting course roles, a member cannot grant a role above
  their own (admins/org-managers are uncapped).

Entity-specific rules live in **permission handlers** registered at startup
(`permission_registry.register(Model, Handler(Model))`). System roles like `_admin`,
`_user_manager`, and `_workspace_user` are seeded into the `role` table.

**Rules of thumb**: check permissions in `business_logic/` (not the endpoint), check them
**early** (before expensive work), always allow the admin bypass, and raise descriptive
`ForbiddenException` messages.

---

## Temporal workflows

Temporal runs long-running and external-service work reliably (automatic retries, durable
state, visibility in the UI at `:8088`). Used for git provisioning, student-template/
reference generation, submission testing, and example deployment.

Four pieces:

- **Workflow** (`@workflow.defn`) — orchestration only; deterministic; calls activities.
- **Activity** (`@activity.defn`) — the actual work (DB, git, MinIO). Make it **idempotent**
  (check-if-exists before create) so retries are safe.
- **Worker** — runs workflows+activities off a task queue (`computor-tasks`, `testing`,
  `testing-matlab`, and — with Coder — `coder`).
- **Client** — starts workflows from the API/business logic.

```python
@workflow.defn
class GenerateStudentTemplateWorkflow:
    @workflow.run
    async def run(self, course_content_id: str) -> dict:
        content = await workflow.execute_activity(
            fetch_course_content_activity, course_content_id,
            start_to_close_timeout=timedelta(minutes=2),
        )
        repo = await workflow.execute_activity(
            create_template_repository_activity, content,
            start_to_close_timeout=timedelta(minutes=10),
        )
        return {"repository_url": repo["repository_url"]}
```

Starting one from the backend returns immediately with a handle:

```python
client = await get_temporal_client()
handle = await client.start_workflow(
    SomeWorkflow.run, arg,
    id=f"some-{arg}", task_queue="computor-tasks",
)
return {"workflow_id": handle.id, "status": "started"}
```

Patterns you'll see: **sequential** (activity output → next input), **parallel**
(`asyncio.gather` over activities), **retry/fallback** (`RetryPolicy` + compensation on
`ActivityError`), and **poll-until-done** for long external operations.

**Workers run in Docker** as part of the stack (`temporal-worker`, `-testing`, `-matlab`,
and `-coder` when enabled); replica counts are env-tunable. Because source is baked into the
image, rebuild after editing `tasks/`: `./computor.sh up dev --build -d`.

The course-git workflows (`temporal_hierarchy_management`, `temporal_student_template_v2`)
are the backbone of [git-integration.md](git-integration.md).

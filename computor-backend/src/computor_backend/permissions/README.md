# Permissions

Authorization for the Computor backend: a **handler-registry** system that
authenticates each request into a `Principal`, then answers "may this principal
perform `<action>` on `<entity>`?" and builds permission-filtered queries.

This is the live, integrated system used by the whole API — there is no separate
"old" permission module (the former `api/permissions.py` and the
`migration.py` / `integration.py` toggle layer were removed).

## Request flow

```
Request
  → auth.get_current_principal   # build/validate Principal (Redis-cached per token hash)
  → core.check_permissions(principal, Entity, action, db)
  → entity PermissionHandler     # allow/deny + return a permission-filtered query
```

Admins bypass every handler (`core.check_admin`). Every other decision goes
through the registered handler for the entity.

## Files

- `principal.py` — `Principal`, `Claims`, and the role hierarchies
  (`CourseRoleHierarchy`, `ScopedRoleHierarchy`). Source of truth for role
  inheritance.
- `roles.py` — canonical role identifiers as `str` enums (`CourseRole`,
  `ScopeRole`, `SystemRole`) plus derived role-list constants
  (`LECTURER_AND_ABOVE`, `SCOPE_MANAGER_AND_ABOVE`, …). Prefer these over raw
  `"_lecturer"` strings; the enums compare equal to their string value and work
  directly in SQLAlchemy `==`/`.in_(...)` filters.
- `handlers.py` — the `PermissionHandler` ABC (`can_perform_action` /
  `build_query`) and the `PermissionRegistry` singleton.
- `handlers_user.py` / `handlers_course.py` / `handlers_scoped.py` /
  `handlers_misc.py` — concrete per-entity handlers (users/profiles, course &
  content & members & results, org/course-family scopes, read-only lookups &
  examples). `handlers_impl.py` is a thin re-export shim kept so pre-split
  imports keep working.
- `core.py` — `initialize_permission_handlers()` (registers every entity),
  `check_permissions()` / `check_course_permissions()` /
  `check_course_family_permissions()`, `get_permitted_course_ids()`, the admin
  bypass, and the `db_get_*_claims` loaders.
- `course_access.py` — shared course/submission-group access ladders
  (`get_course_member_or_403`, `require_submission_group_access`).
- `auth.py` — `AuthenticationService`, `PrincipalBuilder`, the FastAPI
  dependencies `get_current_principal[_optional]`, principal cache keys, and the
  user-ban cache.
- `cache.py` — course-membership caching (`get_user_course_memberships`,
  `get_user_courses_with_role`, `invalidate_*`), backed by Redis.
- `query_builders.py` — reusable membership/visibility query fragments.
- `role_setup.py` — claim sets for the built-in system roles.
- `api_token_cache.py` — API-token → principal cache.

## Role hierarchy

Course roles rank `_owner > _maintainer > _lecturer > _tutor > _student`;
organization / course-family scope roles rank `_owner > _manager > _developer`;
the system role is `_admin`. A check for role *R* is satisfied by *R or higher*
(`course_role_hierarchy.get_allowed_roles(R)`).

## Claim structure

```python
Claims:
  general:              # global permissions granted by system roles
    user:   ["list", "get"]
    course: ["create"]
  dependent:            # resource-scoped role grants
    course:
      "course-id-1": ["_lecturer"]
      "course-id-2": ["_student"]
```

## Adding an entity handler

1. Subclass `PermissionHandler` in the matching `handlers_*.py` — usually just
   set `ACTION_ROLE_MAP` and reuse a base `can_perform_action` / `build_query`.

   ```python
   class MyEntityPermissionHandler(PermissionHandler):
       ACTION_ROLE_MAP = {
           "get": CourseRole.STUDENT,
           "list": CourseRole.STUDENT,
           "update": CourseRole.LECTURER,
           "create": CourseRole.MAINTAINER,
           "delete": CourseRole.OWNER,
       }
   ```

2. Register it in `core.initialize_permission_handlers()`:

   ```python
   permission_registry.register(MyEntity, MyEntityPermissionHandler(MyEntity))
   ```

---
name: computor-backend-auth
description: Computor authentication and authorization — the RBAC permission system, permission handlers, Principal/Claims, API tokens, service accounts, Keycloak SSO and the consent gate. Use when changing who may do what, adding a permission handler, touching roles or scopes, or debugging a 401/403 in computor-fullstack/computor-backend.
---

# Computor backend — auth & permissions

You own `computor_backend/permissions/`, `auth/`, and the auth-adjacent business
logic (`api_tokens.py`, `service_accounts.py`, `role_claims.py`, `consent.py`).

**Read first:** `permissions/README.md`, and the RBAC section of
`docs/backend-patterns.md`. For service accounts, `docs/service-accounts.md`;
for the consent gate, `docs/consent-gate.md`.

## The model

- **Principal** — injected via `Depends(get_current_principal)`; carries
  `user_id`, `is_admin`, `Claims`.
- **Claims** — system roles plus per-course and per-organization roles
  (`{course_id: role}`), built from `CourseMember` rows at auth time.
- **Course role hierarchy**, higher inherits lower:
  `_owner > _maintainer > _lecturer > _tutor > _student`.
- **Admins bypass every check.** `if principal.is_admin: return` is always present.
- Builtin system roles (`_admin`, `_user_manager`, `_organization_manager`,
  `_example_manager`, `_git_manager`, `_service_manager`, `_workspace_user`,
  `_workspace_maintainer`) are seeded by migrations and re-applied idempotently
  on every start from `permissions/role_setup.py`. Adding a role means a
  migration **and** a `role_setup.py` entry — one without the other silently
  half-works.

Checks live in `business_logic/`, never in the endpoint, and run before expensive
work. The common shape is
`check_course_permissions(principal, course, action, required_role="_student")`.

## The trap in permission handlers

`check_permissions` calls **only** `build_query`. A handler that *narrows* the
query instead of raising turns a successful check into "here is what you may
see", not "you are authorized". Callers must then fetch **through the returned
query** — re-fetching by id from a repository afterwards bypasses the narrowing
entirely and hands the caller a row they may not see. See
`permissions/handlers_service.py` and its call sites in
`business_logic/api_tokens.py`.

## Rules that have already been violated once

- **Scope ceilings.** A member cannot grant a role above their own; admins and
  organization managers are uncapped. `_service_manager` previously escalated
  past its own ceiling — when you touch scope assignment, re-check the ceiling
  applies to the *granter's* effective role, not the target's.
- **Token scopes are additive by design.** Do not "fix" that by making a later
  grant replace an earlier one.
- **Token revocation is cached.** Revoking leaves a window where the old token
  still authenticates until the permission cache entry expires
  (`permissions/api_token_cache.py`, `cache.py`). Any revocation path must
  invalidate the cache explicitly, not wait for TTL.
- **Never a long default token lifetime.** A 365-day default shipped once. New
  token paths take an explicit, short expiry.
- Ingestion endpoints that a runner or tutor posts to still need
  authentication — an unauthenticated tutor ingestion endpoint shipped once.

## Errors

`ComputorException` takes **`error_code` as the first positional argument** —
always pass `detail=` by keyword. Forbidden responses carry an error code the
frontend keys on (the consent gate uses `AUTHZ_006`); do not change a code
without checking the web and extension for consumers.

Browser-facing endpoints use `get_current_principal_optional` and return
`RedirectResponse(login_url)` **directly** — raising `HTTPException(302)` becomes
a 500 in the handler.

## Verifying

The `verify` skill mints a Redis session token so you can exercise a 401/403 path
headlessly. Test both directions: that the permitted role succeeds *and* that the
role one step below is refused. A permission change with only a positive test is
not verified.

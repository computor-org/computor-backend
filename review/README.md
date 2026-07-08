# Codebase Refactoring Plans

**Created:** 2026-07-07 · **Reviewed branch:** `release/2026.10` · **Reviewed by:** Claude (5 parallel deep-review agents over the whole monorepo)

This directory contains precise, self-contained refactoring plans intended to be picked up **one task at a time** by a coding agent (Claude Opus) or an engineer. Every task lists exact files with line numbers (valid as of the review commit), a concrete step-by-step plan, and risks/verification — no re-analysis of the codebase should be needed, but **line numbers will drift as tasks land; re-locate by symbol name if a range no longer matches.**

## Plan files

| File | Scope | Tasks |
|---|---|---|
| [01-backend-core.md](01-backend-core.md) | `computor-backend`: model, repositories, database, permissions, auth, middleware, config | TASK-101 … 115 |
| [02-backend-api.md](02-backend-api.md) | `computor-backend`: api routers, business_logic, services, interfaces, entrypoints | TASK-201 … 214 |
| [03-backend-tasks-integrations.md](03-backend-tasks-integrations.md) | `computor-backend`: Temporal tasks, coder, git_provider, generator, plugins, testing | TASK-301 … 313 |
| [04-web.md](04-web.md) | `computor-web`: Next.js app, HTTP layers, auth services, components | TASK-401 … 413 |
| [05-shared-packages.md](05-shared-packages.md) | `computor-types`, `computor-client`, `computor-cli`, `computor-utils`, `computor-coder`, packaging | TASK-501 … 511 |

## How to work these tasks

1. **One task per branch/PR.** Task IDs are stable — reference them in branch names and commit subjects (e.g. `refactor: dedupe permission ladder (TASK-202)`). Commit messages: single-line `<type>: <subject>`.
2. **Read the "Architecture context" section** at the top of the plan file before starting any task in it.
3. **Safety nets are prerequisites, not suggestions.** Tasks marked SECURITY-SENSITIVE or touching authorization/transactions (103, 108, 109, 110, 202, 204, 206, 209, 401, 403) explicitly require characterization/permission-matrix tests BEFORE the refactor. Write them first.
4. **Do not silently normalize divergent behavior.** Several duplications hide intentional per-site differences (token-resolution fallback order in TASK-301, role floors in TASK-202, tree sort order in TASK-407). The plans call these out — preserve behavior unless the task says the difference is a bug.
5. **Track status here:** update the Status column below when a task is started/done/skipped.

## Suggested order

**Quick wins first (P1/P2 · S effort · low risk):**
101 (class-name collision) → 105 (delete dead permission cache) → 108 (permitted() cache bug) → 203 (duplicate routes) → 205 (dead router) → 309 (dead task code) → 312 (prints) → 112 (Keycloak prints/secret logs) → 411 (dead web components) → 506 (dead computor-coder shell) → 313.

**High-value structural work (needs safety nets):**
- Backend: 202 → 201 → 204 (submissions/testing dedup chain, shares tests) · 102 → 106 (repository fixes) · 301 → 303 → 302 (git-layer unification chain)
- Web: smoke tests → 403 → 401 → 402 (auth/HTTP chain)
- Packages: 502 (codegen offline) → 501 (sync facade) → 503

**Defer / decide-first (L effort or needs an owner decision):**
103 (unit-of-work — highest-risk backend change), 110 (repository-layer direction), 311 (async activity model), 209 (404-vs-403 policy — breaking for clients), 507 (packaging strategy).

## Cross-file coordination

- **TASK-208 (GitLab sync out of users.py) ↔ TASK-301 (git-provider unification):** same target area; do 301's token/client factories first, then 208 moves onto them.
- **TASK-103 (unit-of-work) ↔ TASK-213 (`set_db_user` dependency):** both change session/audit handling; land together or 213 first.
- **TASK-104 (grading enum) spans computor-types and backend** — single PR across both packages.
- **TASK-504 (crypto out of computor-types) ↔ TASK-508 (computor-utils purpose):** one decision, two tasks; pick the destination before starting either.
- **TASK-401/402 (web HTTP consolidation) ↔ TASK-502 (codegen):** if the TS generator emit changes (TASK-413 step 1), regenerate once, not per-task.

## Status

| Task | Title | Prio | Effort | Status |
|---|---|---|---|---|
| 101 | Class-name collision: two CourseMemberRepository | P1 | S | done (merged) |
| 102 | Broken overrides + silent filter drops in BaseRepository | P1 | M | done (merged; found 6 broken find_active_* methods, all deleted) |
| 103 | Single unit-of-work (repo commits vs get_db commit) | P1 | L | done (merged; BaseRepository create/update/update_entity/delete flush+refresh instead of commit; cache invalidation + post-write hooks deferred to the session's after_commit event via database.register_post_commit, dropped on rollback; +4 characterization tests. Audited: Temporal-submission sites use explicit db.commit(); gitlab_builder org-create is idempotent + already flush-based. Full suite: 0 new failures vs release/2026.10.) |
| 104 | Grading-status vocabulary ×5 → one enum | P1 | M | done (merged) |
| 105 | Delete dead/broken permission-caching layer | P1 | S | done (merged) |
| 106 | Remove asyncio.run() from sync cache invalidation | P1 | M | done (merged) |
| 107 | Dedupe Principal-cache logic (3 modules) | P2 | M | todo |
| 108 | permitted() cache key ignores course_role | P1 | S | done (merged) |
| 109 | Split handlers_impl.py; merge scoped-handler clones | P2 | M | todo |
| 110 | Decide repository-layer direction (bypassed by codebase) | P2 | L | todo |
| 111 | Model mixins for 19× audit-column boilerplate | P2 | M | todo |
| 112 | Keycloak: remove prints + secret-bearing logs | P2 | S | todo |
| 113 | Consolidate config (8 modules, import-time side effects) | P3 | M | todo |
| 114 | course_member_gradings: dedupe/delete parallel stats | P3 | M | todo |
| 115 | Fix stale permission docs; role-string literals → enums | P3 | S | todo |
| 201 | api/submissions duplicates business_logic verbatim | P1 | M | done (merged) |
| 202 | Extract ~10× copy-pasted permission ladder | P1 | M | done (merged; helpers in permissions/course_access.py + matrix tests) |
| 203 | examples.py duplicate route registrations | P1 | S | done (merged) |
| 204 | Consolidate triplicated testing orchestration | P1 | L | done (merged; helpers in business_logic/testing_orchestration.py + ResultStatus enum; tutor endpoint body kept in api/tutor.py) |
| 205 | Dead router api/deployment.py | P2 | S | todo |
| 206 | Merge profiles vs student_profiles CRUD stacks | P2 | M | todo |
| 207 | Clean generic CRUD core (prints, special-cases, UnboundLocalError) | P2 | M | todo |
| 208 | GitLab provisioning engine out of users.py | P2 | M | todo |
| 209 | Unify 404-vs-403 semantics | P2 | M | todo |
| 210 | Split business_logic/messages.py | P3 | M | todo |
| 211 | Pagination on the other half of list endpoints | P3 | S | todo |
| 212 | Normalize response conventions (delete shapes, raw dicts) | P3 | S | todo |
| 213 | Hoist mid-function imports; systematic set_db_user | P3 | S | todo |
| 214 | Decompose api/examples.py upload god-endpoint | P3 | M | todo |
| 301 | Unify three GitLab integration layers | P1 | L | done (merged; git_provider/{gitlab,gitlab_members,token_resolution}.py; users.py/organizations.py client sites left for 208) |
| 302 | Split 890-line generate_student_template_activity_v2 | P1 | L | done (merged; tasks/student_template/ package; activity 890→346 lines; unit tests for selection/status helpers) |
| 303 | Extract shared git plumbing (clone/identity/push-retry) | P1 | M | done (merged; tasks/git_ops.py + functional tests; assignments repo gained rebase-retry) |
| 304 | Dedupe legacy temporal_student_repository clones | P2 | M | todo |
| 305 | CoderClient boilerplate + bypassing caller | P2 | M | todo |
| 306 | gitlab_builder copy-pasted group/config trios | P2 | M | todo |
| 307 | Dedupe student/tutor testing activities | P2 | S | todo |
| 308 | Reduce workflow-module boilerplate (registration ×4) | P2 | M | todo |
| 309 | Delete dead task code (analytics, demo workflows) | P2 | S | todo |
| 310 | Centralize task-layer config into pydantic settings | P2 | M | todo |
| 311 | Fix blocking I/O in async Temporal activities | P2 | M | todo |
| 312 | print() → logging; list_tasks error contract | P3 | S | todo |
| 313 | task_tracker duplicate accessible-ID logic | P3 | S | todo |
| 401 | Consolidate four HTTP layers into one transport | P1 | M | done (merged; apiFetch is the single transport, APIClient delegates to it, one pluggable refresh strategy in tokenRefresh; tsc+build clean) |
| 402 | Adopt generated clients over hand-typed endpoints | P1 | M | done (merged; ~55 call sites → generated clients, incl. /consent/* after the codegen regen added ConsentClient. api.ts now retained only for genuine codegen gaps: /user + /user/* (TS UserClient name collision with /user-roles), the two ambiguous dual-route org/family deletes, /examples/{id} (no single-id backend delete). Full api.ts deletion + ESLint ban blocked only on fixing the UserClient name collision in the TS generator — TASK-510/511.) |
| 403 | Retire dead password-login path / dual auth providers | P1 | M | done (merged; deleted authService + IAuthProviderWithLogin + login(); tsc+build clean) |
| 404 | Split 641-line members/add page | P2 | M | todo |
| 405 | Decompose Sidebar.tsx | P2 | S | todo |
| 406 | Finish useResource migration (~20 pages) | P2 | M | todo |
| 407 | Shared ltree tree-building (3 implementations) | P2 | S | todo |
| 408 | Adopt or delete UI primitives (Button, useNotify, tables) | P2 | M | todo |
| 409 | Dedupe workspace tables | P2 | S | todo |
| 410 | Unify loading/error presentation | P3 | S | todo |
| 411 | Delete dead components; config redirects for stubs | P3 | S | todo |
| 412 | Stop hand-mirroring backend schemas (workspaces.ts) | P3 | M | todo |
| 413 | Normalize import-alias schemes | P3 | S | todo |
| 501 | CLI sync-shim sprawl → sync facade in computor-client | P1 | L | done (merged; SyncComputorClient facade + shared raise_for_response; both SyncHTTPWrapper classes, _verify_token, delete.py raw _http calls, and 2 inline httpx blocks removed; ComputorClient.timeout/auth_headers accessors; +10 tests. Sweeping get_computor_client→sync + run_async removal left as a follow-up — run_async is still the legit async bridge.) |
| 502 | Offline codegen; stop hand-editing generated client | P1 | M | done (merged; generate_python_clients.py builds spec via app.openapi() offline by default, --url fallback, DO NOT EDIT header; verified end-to-end to a temp dir, 53 clients. Full regen (`bash generate.sh`) run + committed as chore(codegen): the drift was small/clean — just the DO-NOT-EDIT headers, the TASK-201/203/204 backend changes, and the previously-missing ConsentClient/InstanceClient.) |
| 503 | Split computor-cli/deployment.py (2,149 LOC) | P2 | M | todo |
| 504 | Move crypto out of computor-types | P2 | M | todo |
| 505 | Rename deployments_refactored.py; decouple CLI config | P2 | M | todo |
| 506 | Remove computor-coder dead package shell | P2 | S | todo |
| 507 | Packaging hygiene (local deps, pins, py.typed) | P2 | M | todo |
| 508 | Give computor-utils a purpose (or fold it away) | P3 | S | todo |
| 509 | Dedupe per-command CLI boilerplate | P3 | S | todo |
| 510 | Harden computor_types get_all_dtos (silent failures) | P3 | M | todo |
| 511 | Rename colliding test-spec modules | P3 | S | todo |

## Global verification commands

- Backend: `python -c "import computor_backend.server"` (import smoke), backend test suite under `computor-backend/src/computor_backend/tests/`, OpenAPI diff: capture `GET /openapi.json` before/after API-touching tasks.
- Web: `cd computor-web && npx tsc --noEmit && yarn build`; Playwright: `npx playwright test`.
- Alembic no-op check (model refactors): `alembic revision --autogenerate` must produce an empty migration.
- Integration tests: see `integration-tests/` (suite scaffolding per issue #106; MATLAB and Coder are excluded from the integration compose stack).

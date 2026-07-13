# 01 — Current State

Inventory of the existing test landscape (verified against the working tree on
`release/2026.10`, 2026-07-13). This is the baseline every backlog item starts from.

## 1. `integration-tests/` — pytest black-box harness

**What it is.** A pytest 8 + httpx harness (`pytest-asyncio` auto mode, `pytest-xdist`)
driving a self-contained Docker stack (`docker-compose.integration.yaml`) over HTTP.
Launched via `Makefile` (`env → up → wait → bootstrap → test → down/clean`). Deliberate
design: **no per-test rollback** — the stack comes up once, state accumulates, seed
fixtures are session-scoped and idempotent (find-or-create), teardown is a volume wipe.
That design is sound and is kept (see [02-architecture.md](02-architecture.md)).

**Layout.**

```
integration-tests/
├── Makefile, pyproject.toml, conftest.py, reporting.py
├── docker-compose.integration.yaml     # api, postgres, redis, minio, temporal(+ui),
│                                       # temporal-worker, temporal-worker-testing, GitLab CE
├── .env.integration.template           # committed defaults
├── fixtures/  api.py clients.py course.py users.py db.py permission_matrix.py gitlab.py
├── helpers/                            # EMPTY (README claims "reusable assertions")
├── scripts/   bootstrap_gitlab.py wait_for_services.sh
├── reports/   latest.md                # last run: 0 tests collected (2026-06-28)
└── suites/
    ├── 01_smoke/          test_stack_reachable.py        # incl. GitLab health checks
    ├── 02_auth/           login/logout/refresh/whoami/api-tokens
    ├── 03_permissions/    7 per-role files over fixtures/permission_matrix.py
    ├── 04_deployment/     test_gitlab_provider.py, test_gitlab_course_group_only.py
    └── 05_examples … 08_full_lifecycle   # EMPTY __init__.py stubs
```

**Broken: authentication.** The whole harness assumes local password auth:
`POST /auth/login`, `POST /password/admin/set`, Basic auth. The backend has since removed
all of it — migration `d3e4f5a6b7c8_drop_user_username_password_columns.py` dropped the
columns; `get_current_principal` (`permissions/auth.py:386-466`) accepts only `ctp_` API
tokens and Bearer tokens that resolve to a **Redis session** (`sso_session:{sha256}`,
`permissions/auth.py:154-197`) minted exclusively by the Keycloak SSO callback
(`business_logic/auth.py:369+`). Raw Keycloak JWTs are not verified either. Consequence:
**suites 02_auth and 03_permissions cannot authenticate at all** — consistent with
`reports/latest.md` showing 0 tests collected. There is no Keycloak service in the
integration compose.

**Obsolete: the GitLab layer — REMOVED (P1.1 executed 2026-07-13).** Everything
git-related targeted GitLab, which the project replaced with Forgejo. The sweep deleted:
compose service `gitlab`, `fixtures/gitlab.py`, both `04_deployment` suites,
`scripts/bootstrap_gitlab.py`, GitLab checks in `01_smoke`, the `python-gitlab`
dependency, all `GITLAB_*` env keys, the dead top-level `run_gitlab_test.sh`, and the
local `.env.gitlab-local`. The `glpat-` tokens found in local env files pointed at
**local throwaway GitLab containers** (`localhost:8085`/`8086`), not an institutional
instance — no revocation was needed.

**Worth keeping (the good bones).**
- `fixtures/permission_matrix.py` — a real matrix design: `MatrixRow(method, path,
  expected={role→status}, body)` parametrized across per-role clients, with observations
  rendered as an endpoint×role cross-tab by `reporting.py`. It already documents the
  backend's status conventions (403 for org/family denials, **404 for course-and-below**
  to hide existence). Small (~18 rows) but the right shape — extend, don't replace.
- `reporting.py` — markdown report generator (`reports/latest.md`).
- API-token tests in `02_auth` (`ctp_` mint/list/revoke) — that auth path still exists.
- The Makefile lifecycle, `conftest.py` env/sys.path wiring (sibling `computor-types`,
  `computor-client`, `computor-utils`), and the compose skeleton (Postgres 15432,
  Redis 16379, MinIO 19000/19001, Temporal 17233/18088, API 18000,
  `temporal-worker-testing` already built with `--queues=testing` and python runtimes;
  `CODER_ENABLED=false` hard-wired — keep).

**Stale details to purge.** README references a `data/` directory that doesn't exist and
"reusable assertions" in the empty `helpers/`; macOS absolute paths
(`/Users/theta/…`) in a Linux repo; `.pytest_cache` referencing renamed tests
(422→400 validation-status change).

## 2. `computor-backend/src/computor_backend/testing/` — NOT tests

Runtime grading-engine code: the `TestingBackend` dispatch layer
(`PythonTestingBackend`, `MatlabTestingBackend`, `ComputorTestingBackend`,
`JavaTestingBackend` stub, `TestingBackendFactory`, `execute_tests_with_backend`) that
Temporal workers use to execute **student submissions**. Decision: **leave untouched**.
It is out of scope for this strategy except as the machinery the golden-path scenario
exercises indirectly.

## 3. `computor-backend/src/computor_backend/tests/` — the real backend unit suite

~68 `test_*.py` files, entry point `computor-backend/src/pytest.ini`
(`testpaths = computor_backend/tests`, markers `unit/integration/slow/asyncio/docker`),
runnable via top-level `test.sh`. Fixtures: SQLite in-memory `test_db`, `mock_db`,
`Principal` fixtures per role, `test_client_factory` overriding
`get_current_principal`/`get_db` on the FastAPI app.

Problems:

| Problem | Files (representative) |
|---|---|
| Five overlapping mocked permission suites | `test_permissions_comprehensive.py`, `test_permissions_comprehensive_fixed.py`, `test_permissions_mocked.py`, `test_permissions_practical.py`, `test_permissions_simple.py` |
| Script-style "tests" needing live services with hardcoded endpoints | `test_keycloak.py` (Keycloak on `localhost:8180`, `__main__` style), Postgres fixture defaulting to db `codeability` on `:5432` (stack uses `:5437`/`:15432`) |
| GitLab-era tests overlapping the abandoned integration path | `test_gitlab_managed.py`, parts of `test_git_service.py`, `test_git_ops.py`, `test_course_creation.py` |
| Coder tests (feature excluded from testing) | `test_coder_forwardauth.py`, `test_coder_provision_errors.py`, `test_workspace_token_ttl.py` |
| Possibly stale after local-password removal | `test_password_hashing.py` (verify: hashing may still serve API/git tokens), `test_auth.py` local-login paths |

Assets to keep as-is: the Forgejo naming/descriptor layer is already unit-tested
(`test_forgejo_naming.py`, `test_course_git_descriptor.py`, `test_student_repo_name.py`,
`test_submission_group_repository_mapper.py`, `test_token_resolution.py`), plus DTO,
storage/MinIO, Temporal, messages, and the live `test_course_access_matrix.py`
(transaction-rollback Postgres matrix). Details in
[07-backend-unit-suite.md](07-backend-unit-suite.md).

## 4. `computor-web/e2e/` — Playwright, one spec

- Exactly one file: `e2e/admin-users.spec.ts` (admin users list: paging, search,
  forbidden state). Framework `@playwright/test` 1.60, config `playwright.config.ts`
  (chromium only, boots `next dev -p 3100`, `NEXT_PUBLIC_API_URL=http://localhost:8000`).
- **Fully network-mocked**: `page.route('http://localhost:8000/**')` + sessionStorage
  injection of `auth_user`/`auth_provider` (matches `src/services/authStorage.ts`). No
  backend or DB required. The pattern works and is the template for expansion.
- **Broken promise**: `playwright.config.ts` and `README.md` both reference a shared
  `e2e/fixtures.ts` that does not exist — the one spec inlines its mocks.
- No `test`/`typecheck` npm scripts; lint is bare `eslint`.
- Untested but existing UI (route inventory in [08-web-e2e.md](08-web-e2e.md)): login
  redirect, invites admin + public `/invite/[token]` (the app's **only** registration
  path), courses/members/groups management, examples, git-servers admin, role dashboards
  (student/tutor/lecturer), org hierarchy pages.

## 5. Other suites and entry points (context, mostly out of scope)

- `computor-client/tests/`, `computor-testing/testers/tests/` — healthy per-package
  pytest suites; not part of this refactor.
- `run_gitlab_test.sh` — stale GitLab script runner; delete in the sweep.
- `tmp/test_*.py` — throwaway scripts, ignore.
- **CI: none.** No `.github/workflows`, no `.gitlab-ci.yml`, nothing. All testing is
  manual today.

## 6. Gap summary

| Requirement (user) | Today |
|---|---|
| Permission matrix for the API | Exists in miniature (~18 rows), cannot run (auth broken) |
| Payload & exception testing | Scattered assertions in 02_auth only |
| Invite-link onboarding under test | Backend + web UI fully implemented, zero tests |
| Org-manager → org/family/course → lecturer scenario | Nothing (suite stubs empty) |
| Lecturer authors course from `computor-testing` examples | Nothing |
| Students submit correct/empty/mixed solutions, tests execute | Nothing (worker exists in compose but the Service row is never seeded — see [02-architecture.md](02-architecture.md)) |
| Tutor grades, results visible | Nothing |
| Forgejo-only git | Integration layer is 100% GitLab; only backend unit tests cover Forgejo naming |

# BACKLOG — step-by-step

Master checklist. Phases are ordered by dependency; items within a phase are ordered for
execution. Every item names the files it touches and its acceptance criterion (AC).
Detail lives in the referenced doc.

Sequencing: **P1 → P2 unblock everything.** P3 and P4 parallelize after P2. P5 needs
only P1–P2. P6 and P7 are independent and can run anytime. P8 is last.

Branch convention: work branches off `release/2026.10` (e.g. `feat/testing-strategy-p1`),
same branch name across sibling repos when applicable. Never push to `main`.

---

## P1 — Harness rebuild: stack & config (`integration-tests/`) → [02](02-architecture.md)

- [x] **P1.1 GitLab sweep.** ✅ Done 2026-07-13. Deleted the `gitlab` compose service,
  `fixtures/gitlab.py`, `suites/04_deployment/`, `scripts/bootstrap_gitlab.py`, GitLab
  checks in `suites/01_smoke/`, `python-gitlab` from `pyproject.toml`, all `GITLAB_*`
  keys from `.env.integration.template` and the local `.env.integration`,
  `.env.gitlab-local`, and the dead top-level `run_gitlab_test.sh`. Markers updated
  (`gitlab`/`deployment` dropped; `contracts`/`invites`/`forgejo` added). Both READMEs
  rewritten. Token check: the `glpat-` values pointed at local throwaway GitLab
  containers — nothing to revoke.
  AC met: `grep -ri gitlab integration-tests/ --include='*.py' --include='*.yaml' --include='*.toml'` → empty.
- [ ] **P1.2 Add Keycloak.** `keycloak` + `keycloak-db` services (blueprint
  `ops/docker/docker-compose.keycloak.yaml`; host port 18180; health on mgmt `:9000`,
  `start_period: 60s`). `make env` stages `data/keycloak/computor-realm.json` with the
  IT client secret substituted into the import volume.
  AC: fresh `make up` → realm `computor` answers `/.well-known/openid-configuration`.
- [ ] **P1.3 Add Forgejo.** `forgejo` + `forgejo-db` + one-shot `forgejo-bootstrap`
  (blueprint `ops/docker/docker-compose.forgejo.yaml`; host port 13030;
  `ALLOW_LOCALNETWORKS=true` + `ALLOWED_DOMAINS` pinned; bootstrap admin creds from
  env; `depends_on: service_completed_successfully`).
  AC: `GET :13030/api/healthz` OK; admin token works.
- [ ] **P1.4 Wire API/worker env.** On `api` (and workers where relevant):
  `KEYCLOAK_*`, `API_ADMIN_EMAIL/_PASSWORD`, `GIT_SERVER=forgejo`,
  `GIT_SERVER_URL=http://forgejo:3030`, `GIT_SERVER_URL_PUBLIC=http://localhost:13030`,
  `GIT_SERVER_ADMIN_*`, `DEPLOYMENTS_DIR=/deployments` (bind-mount), ctp_-format
  `TESTING_WORKER_TOKEN` in the template (≥32 chars).
  AC: API boots; startup logs show managed-Forgejo registration and role seeding.
- [ ] **P1.5 Stage bootstrap deployments.** New committed
  `integration-tests/deployments/testing-worker.yaml` (`slug: itpcp.exec.py`,
  `service_type_path: testing.temporal`, `task_queue: testing`,
  `api_token.token: ${TESTING_WORKER_TOKEN}`) and `example-repository.yaml` (MinIO
  default repo). → [02](02-architecture.md) §3.
  AC: after boot, the Service and ExampleRepository rows exist (asserted by P1.6 smoke).
- [ ] **P1.6 Rewrite smoke + wait script.** `suites/01_smoke/test_stack_reachable.py` and
  `scripts/wait_for_services.sh` per [06](06-integration-suites.md) §01 (Keycloak,
  Forgejo, managed-git-server row, `itpcp.exec.py` Service row).
  AC: `make up && pytest suites/01_smoke` green from cold.
- [ ] **P1.7 Docs & hygiene.** Rewrite `integration-tests/README.md` (new stack, `make
  clean` = realm reset); fix `Makefile` targets; delete phantom `data/`/`helpers/`
  claims, macOS paths, stale `.pytest_cache`; update markers in `pyproject.toml`
  (drop `gitlab`/`deployment`, add `contracts`/`invites`/`forgejo`).
  AC: README matches reality; `pytest --collect-only` clean.

## P2 — Identity & personas (`integration-tests/fixtures/`) → [02](02-architecture.md) §4–5, [03](03-personas-and-scenario.md)

- [ ] **P2.1 Headless login helper.** New `fixtures/keycloak_auth.py`: authorization-code
  form dance (login 302 → host-rewrite → form POST → callback → tokens from redirect
  query). → [02](02-architecture.md) §4.
  AC: admin (env-bootstrapped) gets a working Bearer; `GET /user` returns the admin.
- [ ] **P2.2 Persona seeding.** Rewrite `fixtures/users.py`: admin login (grants
  `_admin` on first callback) → role invites for `uma`/`orga`/`exma` → `uma` invites
  `lena`/`tobi`/students → all accept + login. Idempotent (find-or-create on re-run).
  AC: `make test` twice in a row both green on the seeding fixture.
- [ ] **P2.3 Persona clients.** Rewrite `fixtures/clients.py`: session-scoped bearer
  `httpx.Client` per persona (9) + `anon`; one login per session.
  AC: all suites import clients from here; no other file logs in.
- [ ] **P2.4 Rebuild 02_auth.** SSO dance cases, refresh/logout, API tokens (kept),
  invite lifecycle happy paths. → [06](06-integration-suites.md) §02.
  AC: suite green; invite-created user's roles visible via `GET /user-roles`.

## P3 — Permission matrix (`suites/03_permissions/`) → [04](04-permission-matrix.md)

- [ ] **P3.1 OpenAPI inventory + coverage guard.** Fixture pulling `GET /openapi.json`;
  `test_coverage_guard.py` failing on endpoints in neither `MATRIX` nor `EXCLUDED`;
  `EXCLUDED` staleness check.
  AC: guard fails when a new endpoint is added without a matrix decision (verified by
  temporarily removing a row).
- [ ] **P3.2 Expand the matrix.** Grow `fixtures/permission_matrix.py` to the router
  groups in [04](04-permission-matrix.md) §5, on the new persona axis; placeholders
  resolved from scenario objects.
  AC: guard passes with zero undeclared endpoints.
- [ ] **P3.3 Ceiling & relationship rows.** The named cases from
  [04](04-permission-matrix.md) §6 (lecturer→tutor 403, org-manager 201, cross-student
  isolation, tutor-authoring denial, lecturer-upload denial, import ceiling).
  AC: all cases asserted; cross-tab in `reports/latest.md` renders them.
- [ ] **P3.4 Per-persona spec files.** One file per persona + anonymous, parametrized
  over `MATRIX`; read-only rows xdist-parallel.
  AC: suite green; runtime acceptable (< a few minutes).

## P4 — Payload & exception contracts (new `suites/04_contracts/`) → [05](05-payload-validation.md)

- [ ] **P4.1 Assertion helpers.** New `helpers/assertions.py` (`assert_error`,
  `assert_shape` against `computor_types` DTOs).
  AC: helpers imported by 04+ suites; `helpers/` no longer empty.
- [ ] **P4.2 Validation shapes.** VAL_001=400 cases per representative DTO
  ([05](05-payload-validation.md) §2).
  AC: green; any 422 observed = backend regression caught.
- [ ] **P4.3 Domain exceptions.** Invite edge cases (expired/revoked/used/email-
  restricted/double-accept), member-without-group, git-binding lock, hierarchy delete
  409, example re-upload, submission caps, RATE_003, auth 401 shapes
  ([05](05-payload-validation.md) §3). Registry gaps noted as backend follow-ups.
  AC: every case asserts `(status, error_code)` or documents the registry gap inline.
- [ ] **P4.4 Happy-path shapes.** `assert_shape` round-trips for the scenario endpoints,
  incl. the no-internal-host URL guard on git payloads ([05](05-payload-validation.md) §4).
  AC: green.

## P5 — Golden-path lifecycle (`suites/05…08`) → [03](03-personas-and-scenario.md), [06](06-integration-suites.md)

- [ ] **P5.1 Examples fixtures + suite.** New `fixtures/examples.py` (locate the 6
  examples, build upload ZIPs, expose identifiers); `suites/05_examples/` upload +
  list/versions/download + permission side-cases.
  AC: 6 examples in `GET /examples`; re-run idempotent.
- [ ] **P5.2 Hierarchy & binding.** `suites/06_release/`: org → family → course with
  Forgejo binding at creation (canonical: sync `POST /courses` + `PUT /courses/{id}/git`;
  the async deploy path gets one contract test); seat `lena`/`tobi` (`orga`).
  New `fixtures/forgejo.py` (admin client, replaces deleted gitlab fixture); rewrite
  `fixtures/course.py`.
  AC: `GET /courses/{id}/git` shows configured+locked binding on the managed server.
- [ ] **P5.3 Authoring & release.** Groups, student enrolment, unit + 6 assignment
  contents, `assign-example`, `generate-student-template`, workflow polling, Forgejo-side
  template assertion (stubs present, `*_master.py`/`test.yaml` absent).
  AC: template repo verified via Forgejo API.
- [ ] **P5.4 Student workflow.** `suites/07_student_workflow/` + `fixtures/submissions.py`:
  provision-repository + real `git clone` (public URL), ZIP per case
  (correct/empty/mixed split per [03](03-personas-and-scenario.md)), submit
  (`submit:true`), `POST /tests` with ≥1s spacing, poll to terminal, assert scores per
  case.
  AC: 3 students × 6 assignments all reach terminal results matching their case.
- [ ] **P5.5 Grading & final state.** `suites/08_full_lifecycle/`: tutor grades all 18
  (CORRECTED / CORRECTION_NECESSARY), aggregate + per-student + lecturer-view
  assertions, grading-outcome table in `reporting.py`.
  AC: `reports/latest.md` shows the outcome table with s-correct ≈ 100%, s-empty ≈ 0%,
  s-mixed ≈ 50%.

## P6 — Backend unit cleanup (`computor_backend/tests/`) → [07](07-backend-unit-suite.md)

- [ ] **P6.1 Marker discipline.** `pytest.ini`: markers `integration/keycloak/docker/coder`,
  hermetic default via `addopts`; env-driven Postgres DSN in `fixtures.py`.
  AC: `./test.sh` green with no services running.
- [ ] **P6.2 Permission-suite consolidation.** Merge the five `test_permissions_*` into
  one `test_permissions.py`; keep `test_course_access_matrix.py` behind `integration`.
  AC: no duplicate case survives (diff the merged assertions); default run green.
- [ ] **P6.3 Stale-behavior removal.** Delete local-login tests; resolve
  `test_password_hashing.py` (verify token-hashing relevance first); **delete all
  GitLab-era tests** (`test_gitlab_managed.py` + GitLab cases in `test_git_service.py`,
  `test_git_ops.py`, `test_course_creation.py` — GitLab is omitted entirely); rewrite
  `test_keycloak.py` as marked pytest.
  AC: `grep -rl "auth/login\|password/admin/set" computor_backend/tests/` → empty;
  `grep -ril gitlab computor_backend/tests/` → empty.
- [ ] **P6.4 Coder quarantine.** Marker `coder` on `test_coder_forwardauth.py`,
  `test_coder_provision_errors.py`, `test_workspace_token_ttl.py`.
  AC: default run collects none of them; `-m coder` collects all.

## P7 — Web e2e expansion (`computor-web/e2e/`) → [08](08-web-e2e.md)

- [ ] **P7.1 `e2e/fixtures.ts`.** `injectAuth` + `PERSONAS`, `mockApi` router with
  default handlers, typed data builders; refactor `admin-users.spec.ts` onto it.
  AC: README/config references are finally true; existing spec still green.
- [ ] **P7.2 Tooling.** Add `"typecheck": "tsc --noEmit"` script (yarn, never npm).
  AC: `yarn typecheck` passes.
- [ ] **P7.3 Invite specs.** `invites-admin.spec.ts` + `invite-accept.spec.ts`
  ([08](08-web-e2e.md) §3 rows 1–2).
  AC: green headless, no backend.
- [ ] **P7.4 Management specs.** `courses.spec.ts`, `members-groups.spec.ts`,
  `examples.spec.ts`, `git-servers.spec.ts` (forgejo default asserted).
  AC: green.
- [ ] **P7.5 Role-view + login specs.** `role-dashboards.spec.ts`,
  `login-redirect.spec.ts`.
  AC: green; full suite runtime stays in seconds-to-low-minutes.

## P8 — Live smoke & CI (last) → [08](08-web-e2e.md) §4, [09](09-ci-and-tooling.md)

- [ ] **P8.1 Playwright `live` project.** Second project in `playwright.config.ts`,
  excluded by default; real Keycloak browser login + one golden-path slice against the
  integration stack.
  AC: `yarn test:e2e --project=live` green with `make up` + seeded state.
- [ ] **P8.2 Make targets & report polish.** `make report`, gitignore
  `reports/latest.md` + committed `reports/example.md`.
  AC: targets documented in README.
- [ ] **P8.3 Optional CI.** `backend-unit.yml` + `web.yml` PR gates, `integration.yml`
  nightly with report artifact ([09](09-ci-and-tooling.md) §3). Promote integration to
  PR gate only after a stable streak.
  AC: workflows green on `release/2026.10`.

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
- [x] **P1.2 Add Keycloak.** ✅ Done + validated 2026-07-13. `keycloak` + `keycloak-db`
  added (host port 18180, mgmt-`:9000` health, `start_period 60s`). `make env` gained a
  `stage-realm` step: substitutes `KEYCLOAK_CLIENT_SECRET`/`FORGEJO_CLIENT_SECRET` into
  the `PLACEHOLDER_*` slots of `data/keycloak/computor-realm.json` → `keycloak-import/`
  (gitignored), bind-mounted to `/opt/keycloak/data/import`.
  AC met: realm `computor` answers `/.well-known/openid-configuration` (smoke green).
- [x] **P1.3 Add Forgejo.** ✅ Done + validated 2026-07-13. `forgejo` + `forgejo-db` +
  one-shot `forgejo-bootstrap` (host port 13030; `ALLOW_LOCALNETWORKS=true`;
  `ALLOWED_DOMAINS=forgejo,localhost,127.0.0.1`; `api depends_on … service_completed_successfully`).
  AC met: `GET :13030/api/healthz` 200; admin created; backend minted its managed-server token.
- [x] **P1.4 Wire API/worker env.** ✅ Done + validated 2026-07-13. api + temporal-worker
  got `KEYCLOAK_*`, `API_ADMIN_EMAIL`, `GIT_SERVER=forgejo`, `GIT_SERVER_URL(_INTERNAL)=http://forgejo:3030`,
  `GIT_SERVER_URL_PUBLIC/FORGEJO_ROOT_URL=http://localhost:13030`, `GIT_SERVER_ADMIN_*`,
  `DEPLOYMENTS_DIR=/deployments`, ctp_ `TESTING_WORKER_TOKEN`.
  **Gotcha found + fixed:** `TOKEN_SECRET` symmetrically encrypts the git-server token
  via keycove/Fernet, so it MUST be a valid Fernet key (32 url-safe base64 bytes / 44
  chars) — the old `it-token-secret-change-me` made managed-Forgejo registration fail
  (non-fatally: `Fernet key must be 32 url-safe base64-encoded bytes`). Template now
  ships a valid key. **Also fixed a pre-existing bug:** the `temporal-worker` build
  pointed at the renamed-away `docker/temporal-worker-dev/` → `docker/temporal-worker/`.
  AC met: managed Forgejo GitServer row exists with `managed=t, has_token=t`.
- [x] **P1.5 Stage bootstrap deployments.** ✅ Done + validated 2026-07-13. Committed
  `integration-tests/deployments/{testing-worker,example-repository}.yaml` (python-only
  worker; MinIO repo), bind-mounted at `/deployments`.
  AC met: startup logged `Bootstrap service 'itpcp.exec.py': created + token set` and
  `Bootstrap example repository 'Default Examples': created`.
- [x] **P1.6 Rewrite smoke + wait script.** ✅ Done + validated 2026-07-13. Smoke drops
  the GitLab checks, adds `test_keycloak_realm_reachable` + `test_forgejo_health`;
  `wait_for_services.sh` waits on keycloak(+db)/forgejo(+db).
  AC met: `make up && pytest suites/01_smoke` → 6 passed from cold. (The authenticated
  canaries — managed-server row + Service row via `GET /git-servers` — move to P2 once
  the login fixture exists; both were verified here directly against the DB.)
- [x] **P1.7 Docs & hygiene.** ✅ Done 2026-07-13 (with P1.1). READMEs rewritten,
  Makefile targets fixed (+`stage-realm`), phantom `data/`/`helpers/` claims and macOS
  paths gone, markers updated. `pytest --collect-only` clean (147 tests).

## P2 — Identity & personas (`integration-tests/fixtures/`) → [02](02-architecture.md) §4–5, [03](03-personas-and-scenario.md)

- [x] **P2.1 Headless login helper.** ✅ Done + validated 2026-07-13.
  `fixtures/keycloak_auth.py` — `authenticate(email, password)` drives the SSO dance
  (initiate 302 → fetch form → POST creds → backend callback → token from redirect query
  / `ct_access_token` cookie); also a `bearer_client_factory` fixture. Validated: admin
  logs in, `GET /user` → `admin@integration.test`, `/user/scopes` → `is_admin: True`.
  **Two realm-staging fixes were required** (now in `scripts/stage_realm.py`, replacing
  the sed substitution): (1) the canonical realm's `computor-backend` client only allows
  the dev/prod redirect ports, so the integration callback `http://localhost:18000/*` is
  appended to `redirectUris`/`webOrigins`; (2) the bootstrap admin is created without
  firstName/lastName, so `VERIFY_PROFILE` is disabled to stop Keycloak interrupting the
  dance with a profile-completion form. Also note: the backend emits the browser-facing
  Keycloak host already (`localhost:18180`), so the internal→public rewrite is defensive.
  Coupling to remember: wiping `keycloak-db` alone needs an `api` restart (the admin is
  created by `ensure_keycloak_admin` at API startup); `make clean && make up` handles it.
- [x] **P2.2 Persona seeding.** ✅ Done + validated 2026-07-13. `fixtures/users.py`
  replaced by `fixtures/personas.py`: `personas` session fixture runs the invite chain
  (admin → role invites for `uma`/`orga`/`exma` → `uma` invites `lena`/`tobi`/3 students
  → all accept + SSO-login), returning a `Persona` registry. Idempotent (skips creation
  when the user already exists, via `GET /users?search=`). `fixtures/api.py` now logs the
  admin in via the SSO dance (no local login).
  AC met: seeding is idempotent; `test_key_role_personas_carry_their_system_role` confirms
  roles via `GET /user-roles/users/{id}/roles/{role}`.
- [x] **P2.3 Persona clients.** ✅ Done 2026-07-13. `fixtures/clients.py` exposes a
  session bearer `httpx.Client` per persona (`uma_client`, `orga_client`, `exma_client`,
  `lena_client`, `tobi_client`, `student_{correct,empty,mixed}_client`), surfaced from the
  registry; `admin_client`/`anonymous_client` stay in `fixtures/api.py`. One login each.
- [x] **P2.4 Rebuild 02_auth.** ✅ Done + validated 2026-07-13. Removed the local-login
  tests; new `test_sso_login.py` (dance + whoami + bad/absent token → 401) and
  `test_invites.py` (persona seeding assertion, who-may-invite 201/403, public metadata,
  accept→loginable, single-use + revoked guards); `test_api_tokens.py` kept (email fix).
  **Whole suite green from cold: 25 passed** (6 smoke + 19 auth), legacy `03_permissions`
  visibly skipped (126, reworked in P3). Two fixes landed here: an api HTTP healthcheck
  (uvicorn accepts connections before lifespan finishes and resets them → `make wait` now
  gates on `/docs` returning 200), and `keycloak_auth` demoted to a pure helper module.

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

- [x] **P5.1 Examples fixtures + suite.** ✅ Done + validated 2026-07-13.
  `fixtures/examples.py` discovers the 6 `itpcp.pgph.py.*` examples, reads their text
  files (skips binary content assets), resolves the seeded MinIO repo, and uploads via
  `POST /examples/upload` (`{repository_id, directory, files}`); idempotent (VERSION_001
  → fetch existing). Also exposes `correct_solution_files()` for P5.4. `suites/05_examples`
  (5 passed): all 6 upload + list + version; lecturer/org-manager upload → 403.
  AC met: 6 examples in `GET /examples`; re-run idempotent.
- [x] **P5.2 Hierarchy & binding.** ✅ Done + validated 2026-07-13. `fixtures/course.py`
  rewritten (orga-driven, idempotent): org → family → course via `POST`, then
  `PUT /courses/{id}/git` `{delivery:'git', git_server_id, student_repo_modes:['managed']}`
  — which materializes the Forgejo template repo (`it_org-it_course_py/template`) and locks
  the binding on first PUT (the old DB-fallback for course creation is obsolete). New
  `fixtures/forgejo.py` (admin basic-auth client + `repo_exists`/`repo_tree` helpers,
  replaces the deleted gitlab fixture). `suites/06_release/test_hierarchy_and_binding.py`
  (5 passed): hierarchy, binding materialized+locked, template repo exists in Forgejo,
  staff seated, and lecturer→seat-tutor = 403 (ceiling). Also asserts the template_url is
  the public host, not `forgejo:3030`.
  AC: `GET /courses/{id}/git` shows configured+locked binding on the managed server.
- [x] **P5.3 Authoring & release.** ✅ Done + validated 2026-07-13. `fixtures/authoring.py`:
  lena creates a group, enrols the 3 students (with group), builds a unit + 6 assignment
  contents, assigns each example **by `example_id`** (identifiers dot-mangle `_`→`.`), and
  triggers `generate-student-template`; polls the Forgejo template repo until all 6
  assignment folders land (folders are named by the example *identifier*, `_`→`.`).
  `suites/06_release/test_authoring_and_release.py` (5 passed): enrolment, unit+6
  assignments, examples assigned, template populated, and no `*_master.py`/`test.yaml`/
  `localTests/` leakage into the student template.
  **Two backend bugs found (worked around by sending explicit values; flagged for P4):**
  (1) `POST /course-content-types` drops the DTO's `color` default → NULL row → the
  `CourseContentType` Get/List DTOs (`color: str`) then 500 the whole list;
  (2) `POST /course-contents` drops the `position` default → NOT NULL violation.
  Both look like CrudRouter create using `exclude_unset` without DB column defaults.
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

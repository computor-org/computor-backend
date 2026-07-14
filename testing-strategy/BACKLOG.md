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

- [ ] **P3.1 OpenAPI inventory + coverage guard.** *(follow-up — not yet built.)* Fixture
  pulling `GET /openapi.json`; `test_coverage_guard.py` failing on endpoints in neither
  `MATRIX` nor `EXCLUDED`. The matrix is solid without it; the guard would force a
  matrix/exclusion decision on every new endpoint. Deferred.
- [x] **P3.2 Expand the matrix.** ✅ Done + validated 2026-07-14. `fixtures/permission_matrix.py`
  reworked onto the 8-persona axis (`admin/uma/orga/exma/lena/tobi/student/anon`),
  **characterized** against the live backend (probe → calibrate) so it documents real
  conventions: list reads 200/401; example reads claim-gated (uma/tobi/student 403);
  hierarchy detail visibility (uma/exma 404); git-binding read = lecturer cohort; org/
  family/course PATCH = admin+org-manager(+lecturer for course), else 404. Body
  placeholders (`{student_user_id}`) resolve from `matrix_ids`.
- [x] **P3.3 Ceiling & relationship rows.** ✅ Done. Invite creation (admin+uma 201, others
  403), git-server-create denials, and the **ceiling** (lecturer seats `_tutor` → 403,
  others 404) are matrix rows; authorized mutating cells are `UNSET` (skip) to avoid
  polluting state. (Cross-student isolation / tutor-authoring live in the lifecycle suites.)
- [x] **P3.4 Per-persona spec files.** ✅ Done. Legacy skip-conftest + 7 old role files
  removed; 8 per-persona files parametrize over `MATRIX`. `reports/latest.md` renders the
  endpoint × persona cross-tab. **180 passed, 4 skipped** (the UNSET cells) in ~4s.

## P4 — Payload & exception contracts (new `suites/04_contracts/`) → [05](05-payload-validation.md)

- [x] **P4.1 Assertion helpers.** ✅ Done 2026-07-14. `helpers/assertions.py`:
  `assert_error(resp, status, code)` pins `(status, error_code)`; `assert_shape(resp, model)`
  validates a 2xx body against a DTO. `helpers/` is no longer empty.
- [x] **P4.2 Validation shapes.** ✅ Done + validated. `suites/04_contracts/test_validation.py`:
  invite bounds (max_uses 0/101, expiry 366) and an invalid ltree org path all → **400
  VAL_001** (not 422); documents that an empty invite body is valid (defaults).
- [x] **P4.3 Domain exceptions.** ✅ Done + validated. `test_domain_errors.py`: auth 401
  (bogus bearer / malformed ctp_ / unauth — via `detail`, no error_code), unknown invite
  token → 404, revoked invite → rejected, **delete org with children → 409 CONFLICT_001**,
  **rebind locked course git → 409 CONFLICT_001**, re-upload same example version → **400
  VERSION_001**. (Submission caps / RATE_003 deferred — they need careful state setup.)
- [x] **P4.4 Happy-path shapes.** ✅ Done + validated. `test_payload_shapes.py`: invite
  create/public-metadata (no raw-token leak), course git binding (`has_token` false, public
  host URL, locked), provisioned repo (one-time `clone_token`, public host). **18 passed.**

## P5 — Golden-path lifecycle (`suites/05…08`) → [03](03-personas-and-scenario.md), [06](06-integration-suites.md)

- [x] **P5.1 Examples fixtures + suite.** ✅ Done + validated 2026-07-13.
  `fixtures/examples.py` discovers the 6 `itpcp.pgph.py.*` examples, reads their text
  files (skips binary content assets), resolves the seeded MinIO repo, and uploads via
  `POST /examples/upload` (`{repository_id, directory, files}`); idempotent (VERSION_001
  → fetch existing). Also exposes `correct_solution_files()` for P5.4. `suites/05_examples`
  (4 passed, 1 xfail): all 6 upload + list + version; org-manager upload → 403.
  AC met: 6 examples in `GET /examples`; re-run idempotent.
  **Permission bug found (xfail'd):** a course `_lecturer` can upload to the *global*
  example library, though `role_setup.py:71` documents lecturers as assign-only (uploading
  is `_example_manager`). `test_lecturer_cannot_upload_examples` asserts the design-correct
  403 under `xfail(strict=False)` — flip to a plain assert when the backend is fixed.
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
- [x] **P5.4 Student workflow.** ✅ Done + validated 2026-07-14. `fixtures/submissions.py`:
  each student provisions their Forgejo repo (one-time `clone_token`, public `http_url`),
  then per assignment submits a ZIP (`submission_create` JSON + file → `{artifacts:[id]}`)
  and triggers `POST /tests {artifact_id}` (1.2s spacing for the 1/s limit), polling
  `GET /tests/status/{id}` (string status) to terminal. Reuse is tied to the content-
  addressed `version_identifier` (dodges the duplicate-test 500). `suites/07_student_workflow`
  (6 passed, slow): all provisioned, all results terminal, **correct scores 1.0 on all 6**,
  empty < 1.0, mixed splits, and correct ≥ empty per assignment.
  **Key realizations:** the example "stubs" ship *pre-solved* (stub == solution), so the
  empty case submits synthesised broken content; the correct case submits **all**
  correctSolution files (some tests need `additionalFiles`); some tests award partial
  credit for broken input (slogic → 0.5), so "empty" asserts `< 1.0`, not `== 0.0`.
  **Blocker found + fixed** (committed 460795b4): worker token must be `ctp_` + exactly 32
  url-safe chars; the 42-char body seeded but failed auth (401) so tests never ran.
  **Stale-session fix:** course-role claims bake into the token at login, but personas log
  in before seating → lena/tobi/students re-authenticate after their membership fixture
  (`fixtures/clients.py`). Follow-up (user hint): pre-create the worker token via the
  computor CLI. Backend bugs for P4: duplicate-test **500** (should be 4xx); token
  loose-vs-exact length mismatch (bootstrap accepts what auth rejects).
- [x] **P5.5 Grading & final state.** ✅ Done + validated 2026-07-14. `fixtures/grading.py`:
  tobi grades all 18 cells via `PATCH /tutors/course-members/{cm}/course-contents/{cc}`
  (result==1.0 → CORRECTED@1.0, else CORRECTION_NECESSARY@0.0). `suites/08_full_lifecycle`
  (5 passed): tutor lists submission-groups, every cell graded, `/course-member-gradings`
  `overall_average_grading` = 1.0 / 0.0 / 0.5 for correct / empty / mixed (strict ordering
  correct > mixed > empty), student sees own grade. `reporting.py` renders the
  **Golden-Path Grading Outcomes** table into `reports/latest.md`.
  AC met: table shows s_correct **1.00**, s_empty **0.00**, s_mixed **0.50**.

## P6 — Backend unit cleanup (`computor_backend/tests/`) → [07](07-backend-unit-suite.md)

- [~] **P6.1 Marker discipline.** Partial (2026-07-14). `pytest.ini` gains `keycloak` +
  `coder` markers and a default `-m "not coder and not keycloak"`; collection was
  **unblocked** — two modules (`test_course_member_import.py`, `test_temporal_client.py`)
  import symbols renamed/removed by backend refactors (`import_course_members` →
  `import_course_member`; `TEMPORAL_HOST` gone) and were `collect_ignore`d in the tests
  conftest (a single stale import was failing the whole 1005-test collection).
  **Remaining:** marking the live-Postgres/Redis/MinIO tests so `./test.sh` is fully
  hermetic-green, and env-driven Postgres DSN. (Suite now collects 1005 with 0 errors.)
- [ ] **P6.2 Permission-suite consolidation.** *(Deferred — needs per-test review.)* Five
  `test_permissions_*` files (9/16/8/10/11 tests) overlap; merging safely requires
  diffing each assertion to avoid dropping unique coverage. Left as a scoped follow-up.
- [~] **P6.3 Stale-behavior removal.** Partial. The two import-broken stale modules are
  quarantined (`collect_ignore`) pending rewrite for the current API; deleting/rewriting
  the GitLab-era + local-login tests is deferred (per-test review, sync with
  `refactor/2026.10-cleanup`).
- [x] **P6.4 Coder quarantine.** ✅ Done + validated 2026-07-14. `pytestmark =
  pytest.mark.coder` on `test_coder_forwardauth.py`, `test_coder_provision_errors.py`,
  `test_workspace_token_ttl.py` (+ `keycloak` on the two keycloak files). Verified:
  `-m coder` → 14 tests, `-m keycloak` → 5, default run deselects all 19.

## P7 — Web e2e expansion (`computor-web/e2e/`) → [08](08-web-e2e.md)

- [x] **P7.1 `e2e/fixtures.ts`.** ✅ Done + validated 2026-07-14. Created the shared module
  the config/README already referenced: `PERSONAS` (admin/userManager/lecturer/tutor/
  student), `injectAuth`, a `mockApi` router (custom handlers first, then defaults for
  `/user`+`user_roles`/`/user/scopes`/`/user/views`/`/messages`), and typed builders
  (`buildUsers`, `buildInvite`). `admin-users.spec.ts` refactored onto it — still green.
- [x] **P7.2 Tooling.** ✅ Done. `"typecheck": "tsc --noEmit"` added (yarn); passes with
  0 errors project-wide.
- [x] **P7.3 Invite specs.** ✅ Done + validated. `invites-admin.spec.ts` (list + Active
  badge, revoked/expired/used badges, non-manager forbidden) and `invite-accept.spec.ts`
  (valid-token form, unknown-token "Invite Not Found", password-mismatch, completed
  "Account ready"). **Full e2e suite: 10 passed** headless, no backend.
  (Gotchas fixed: role gates read `user_roles` from `/user`; `getByText` is a
  case-insensitive substring match, so titles/badges use `getByRole`/`exact`.)
- [ ] **P7.4 Management specs.** *(Follow-up — the `fixtures.ts` foundation makes these
  straightforward.)* `courses.spec.ts`, `members-groups.spec.ts`, `examples.spec.ts`,
  `git-servers.spec.ts` (forgejo default).
- [ ] **P7.5 Role-view + login specs.** *(Follow-up.)* `role-dashboards.spec.ts`,
  `login-redirect.spec.ts`.

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

# 06 — Integration Suite Specifications

Per-suite refactor spec for `integration-tests/suites/`. Numbering keeps the dependency
order; `04_deployment` (GitLab) is deleted and its number reused for the contracts
suite. Markers (in `integration-tests/pyproject.toml`) change accordingly:
drop `gitlab`, `deployment`; add `contracts`, `invites`, `forgejo`.

## 01_smoke — stack reachability

**Today:** API `/docs` + `/openapi.json`, GitLab health + `/api/v4/user`, MinIO health,
Temporal UI.
**Target:**
- keep API, MinIO, Temporal checks;
- **drop** both GitLab checks;
- **add** Keycloak `GET :9000/health/ready` (mgmt port) and realm reachability
  (`GET /realms/computor/.well-known/openid-configuration` on 18180);
- **add** Forgejo `GET /api/healthz` + admin-token sanity (`GET /api/v1/user`);
- **add** backend-bootstrap assertions: `GET /git-servers` (as admin) contains the
  managed Forgejo (`managed: true`) — proves `ensure_managed_forgejo_registered` ran;
  the `itpcp.exec.py` Service exists (proves `DEPLOYMENTS_DIR` staging +
  `ensure_bootstrap_services` worked). These two are the canary for the two known
  bootstrap gaps ([02](02-architecture.md) §3).

Files: rewrite `suites/01_smoke/test_stack_reachable.py`; update
`scripts/wait_for_services.sh` to poll the new set.

## 02_auth — identity, sessions, invites

**Today:** local login/logout/refresh/whoami/api-tokens — local login is gone.
**Target:**
- **SSO login dance** (the `fixtures/keycloak_auth.py` helper under test): happy path
  returns token + refresh; wrong password → login form re-served (no token); the token
  works as Bearer (`GET /user`); bogus/expired bearer → 401.
- `POST /auth/refresh`, `/auth/logout` against the session tokens.
- **API tokens** (kept from today): mint `ctp_` (plaintext once), auth via
  `X-API-Token`, list, revoke → 204 then 401.
- **Invite lifecycle** (marker `invites`): create (admin and `uma`; `lena` → 403),
  list, public `GET /invites/{token}`, accept happy path (user exists in Keycloak +
  backend, granted roles present via `GET /user-roles`), revoke → accept fails,
  expiry / max-uses / email-restriction / double-accept covered in `04_contracts`.
- The **persona seeding fixture** ([02](02-architecture.md) §5) is exercised here first;
  all later suites consume its session-scoped clients.

Files: rewrite `suites/02_auth/*`; new `fixtures/keycloak_auth.py`; rewrite
`fixtures/users.py`, `fixtures/clients.py`.

## 03_permissions — the matrix

Per [04-permission-matrix.md](04-permission-matrix.md): expand
`fixtures/permission_matrix.py` to full router-group coverage, add the OpenAPI
coverage-guard test, update the per-role spec files to the new persona axis, keep the
cross-tab reporting. Read-only rows may run under `pytest-xdist`; rows that mutate use
namespaced throwaway objects.

Files: `fixtures/permission_matrix.py`, `suites/03_permissions/test_<persona>.py` (one
per persona + `test_anonymous.py` + `test_coverage_guard.py`).

## 04_contracts — payloads & exceptions (replaces GitLab deployment suite)

Per [05-payload-validation.md](05-payload-validation.md). Delete
`test_gitlab_provider.py` and `test_gitlab_course_group_only.py` with the suite rename.

Files: new `suites/04_contracts/test_{invites,hierarchy,members,examples,submissions,
tests_rate,auth_tokens}_contract.py`; new `helpers/assertions.py`.

## 05_examples — example library

Scenario Phase 2 ([03](03-personas-and-scenario.md) steps 9–10): `exma` uploads the 6
Python examples (ZIP path) into the seeded MinIO repository; list/versions/download
assertions; permission side-cases. Idempotent re-run: re-upload of the same
`version_tag` asserted as the documented conflict (contract case), fixture skips upload
if the version already exists.

Files: `suites/05_examples/test_upload_python_examples.py`; new
`fixtures/examples.py` (locates `computor-testing/examples/itpcp.pgph.py/*`, builds
upload ZIPs, exposes `example_identifiers` to later suites).

## 06_release — hierarchy, course, authoring, release

Scenario Phases 1 & 3 (steps 5–8, 11–16): org/family/course + Forgejo binding, member
seating (incl. the ceiling denial), groups, student enrolment, contents (1 unit + 6
assignments), example assignment, `generate-student-template`, Forgejo-side template
verification (via a small `fixtures/forgejo.py` admin client — replaces the deleted
`fixtures/gitlab.py`).

Notes:
- Workflow polling with explicit timeout + status in failure message.
- Template content assertion includes the **negative**: no `*_master.py`, no
  `test.yaml` in the student template.

Files: `suites/06_release/test_{hierarchy,course_git_binding,members_and_groups,
contents_and_assignment,generate_template}.py`; new `fixtures/course.py` rewrite
(currently seeds via legacy assumptions), new `fixtures/forgejo.py`.

## 07_student_workflow — provision, submit, test

Scenario Phase 4 (steps 17–22), parametrized over the three students × 6 assignments.
Serial execution (rate limit + Temporal load); marker `student` + `slow`.

Key implementation notes:
- Real `git clone` of the provisioned repo using the one-time token (subprocess `git`,
  against `GIT_SERVER_URL_PUBLIC`) — this is the regression guard for public-URL
  rewriting and Forgejo self-migration.
- ZIP builder per case (correct/empty/mixed) from `fixtures/examples.py`.
- Result polling helper with per-example timeout; assert against `result_json` score,
  not just status.

Files: `suites/07_student_workflow/test_{provision_repository,submit_and_test}.py`;
`fixtures/submissions.py` (zip builder, submit+test+poll helper).

## 08_full_lifecycle — grading & the final picture

Scenario Phase 5 (steps 23–26): tutor lists ungraded, downloads a spot-check artifact,
grades all 18 cells, final assertions from three perspectives (tutor aggregate, each
student's own view, lecturer via `/course-member-gradings`), grading-outcome table
rendered into `reports/latest.md` (extend `reporting.py`).

This suite is also where "everything worked end to end" is pinned: it depends on
05/06/07 having run in the same session (enforce via module-level dependency fixtures
that fail fast with a clear message if the prerequisite state is missing).

Files: `suites/08_full_lifecycle/test_{tutor_grading,final_state}.py`; `reporting.py`
extension.

## Cross-cutting cleanups (with the suite work)

- ✅ Done 2026-07-13 (P1.1): GitLab fully removed — compose service, `fixtures/gitlab.py`,
  `scripts/bootstrap_gitlab.py`, `suites/04_deployment/`, smoke checks, `python-gitlab`
  dep, `GITLAB_*` env keys, `.env.gitlab-local`, top-level `run_gitlab_test.sh`, stale
  `.pytest_cache`; markers updated (`gitlab`/`deployment` → `contracts`/`invites`/
  `forgejo`); both READMEs rewritten (phantom `data/` claim and macOS paths gone).
- Still with P1: `.env.integration.template` gains the Keycloak/Forgejo/worker-token
  keys; README documents the new services once they exist.

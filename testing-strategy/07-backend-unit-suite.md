# 07 — Backend Unit Suite Cleanup

Target: `computor-backend/src/computor_backend/tests/` (~68 files). The runtime package
`computor_backend/testing/` (grading-engine dispatch) is explicitly **not** touched.
Entry point stays `computor-backend/src/pytest.ini` + top-level `test.sh`.

## 1. Principles

- **Default run = hermetic.** `./test.sh` runs only tests needing no external service
  (SQLite/mocks). Everything live (Postgres, Keycloak, Docker) is opt-in by marker.
- **One concept, one file.** The permission logic currently spread over five mocked
  suites collapses into one.
- **Excluded features carry markers, not deletions**, where the code they test still
  ships (Coder). Tests for *removed* behavior (local passwords, GitLab login) are
  deleted.

## 2. Marker discipline (pytest.ini)

| Marker | Meaning | In default run? |
|---|---|---|
| `unit` (implicit default) | SQLite/mocks only | ✅ |
| `integration` | needs live Postgres (align the fixture default with the real stack: env-driven DSN, not hardcoded `codeability@localhost:5432`) | ❌ (`-m integration`) |
| `keycloak` | needs live Keycloak | ❌ |
| `docker` | needs Docker (existing marker, keep) | ❌ |
| `coder` | Coder feature tests — excluded by policy | ❌ (only `-m coder`) |
| `slow` | existing, keep | ✅ unless `-m "not slow"` |

Enforce `--strict-markers` and add `addopts = -m "not integration and not keycloak and
not docker and not coder"` so the default is hermetic without remembering flags.

## 3. File dispositions

### Consolidate — permission tests (5 → 1 + live matrix)

| File | Disposition |
|---|---|
| `test_permissions_comprehensive.py`, `test_permissions_comprehensive_fixed.py`, `test_permissions_mocked.py`, `test_permissions_practical.py`, `test_permissions_simple.py` | Merge into one `test_permissions.py` (mocked): keep the union of *distinct* cases, drop duplicates; `_fixed` supersedes `comprehensive` where they conflict |
| `test_course_access_matrix.py` | Keep as the live-Postgres matrix, marker `integration` |
| Keep as-is (distinct concerns) | `test_permission_handlers.py`, `test_scoped_role_principal.py`, `test_scoped_handlers_characterization.py`, `test_message_permissions.py`, `test_user_role_admin_escalation.py`, `test_ownership_require.py`, `test_principal_permitted_role_floor.py`, `test_user_scopes.py` |

### Fix — live-service tests

| File | Disposition |
|---|---|
| `test_keycloak.py` | Rewrite from `__main__`-script style to pytest with marker `keycloak`; endpoint/realm from env, not hardcoded `localhost:8180` |
| `test_keycloak_token_refresh.py`, `test_sso_api.py` | Marker `keycloak` where they hit a live server; mock otherwise |
| Postgres session fixture (`fixtures.py`) | DSN from env with the stack's real defaults; document `test.sh` exports |

### Delete — removed behavior

| File | Reason |
|---|---|
| Local-login paths in `test_auth.py` | `POST /auth/login` / password columns removed (keep the cookie/refresh coverage: `test_auth_refresh_cookie.py`, `test_token_refresh.py`) |
| `test_gitlab_managed.py` + GitLab-era cases in `test_git_service.py`, `test_git_ops.py`, `test_course_creation.py` | **Delete — GitLab is omitted entirely** (owner decision 2026-07-13; Forgejo is the only git server). No conditional keeps |
| `test_password_hashing.py` | **Verify first**: if hashing still serves API/git tokens, keep + rename to say so; if it only served user passwords, delete |

### Quarantine — excluded features

| File | Disposition |
|---|---|
| `test_coder_forwardauth.py`, `test_coder_provision_errors.py`, `test_workspace_token_ttl.py` | Marker `coder`; excluded from default run; not deleted (feature still ships) |

### Keep untouched (healthy)

Forgejo layer (`test_forgejo_naming.py`, `test_course_git_descriptor.py`,
`test_student_repo_name.py`, `test_student_courses_dto.py`,
`test_submission_group_repository_mapper.py`, `test_token_resolution.py`), DTO suites
(`test_dto_*.py`), storage (`test_storage_minio.py`, `test_storage_security.py` — marker
check: MinIO-live parts get `docker`), Temporal (`test_temporal_*.py` — live parts get
`docker`), messages, documents, models, plugin system, consent, tutor-test auth.

## 4. What backend unit tests do NOT take over

The integration harness owns: real SSO dances, invite redemption against live Keycloak,
Forgejo provisioning, Temporal test execution, the golden path. Unit tests stay at the
handler/logic boundary with the existing `test_client_factory` override pattern
(`get_current_principal`/`get_db`). No new live-stack dependencies get added here — if a
test wants three live services, it belongs in `integration-tests/`.

## 5. Definition of done

- `./test.sh` green on a machine with **no services running**.
- `pytest -m integration` green against the dev stack (`startup.sh` services).
- No `test_permissions_*` duplicates; file count drops accordingly.
- `grep -rl "auth/login\|password/admin/set" computor_backend/tests/` → empty.
- Coder tests only run with `-m coder`.

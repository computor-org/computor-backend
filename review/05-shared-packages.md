# Refactoring Plan: Shared Python Packages

**Scope:** `computor-types/`, `computor-client/`, `computor-cli/`, `computor-utils/`, `computor-coder/`, plus cross-package relationships with `computor-backend`
**Reviewed:** 2026-07-07 (branch `release/2026.10`)

## Package map (read first)

| Package | Purpose | LOC (py) | Key deps | Relationships |
|---|---|---|---|---|
| `computor-types` | Pydantic DTOs + `EntityInterface` definitions — but also YAML deployment configs, password hashing, secret encryption | 11,347 (~85 modules) | pydantic, email-validator, keycove, argon2-cffi, pydantic-yaml | Imported by everything: backend (158 files), client, cli, utils. Bottom of the stack. |
| `computor-client` | Async httpx API client. **Hybrid:** `endpoints/` (52 modules) is auto-generated from the live OpenAPI spec (`http://localhost:8000/openapi.json`) by `computor-backend/src/computor_backend/scripts/generate_python_clients.py` via `bash generate.sh python-client`; core (`client.py` 497, `base.py` 521, `http.py` 445, `exceptions.py` 577) is hand-written | 8,711 | computor-types, httpx | Used by cli; also imported by backend Temporal tasks (`tasks/temporal_tutor_testing.py`, `temporal_student_testing.py`) though backend's pyproject declares no local deps. |
| `computor-cli` | Click CLI (`computor` entry point) | 5,120 | computor-types, computor-client, computor-utils, click, httpx | Wraps computor-client but bypasses it constantly. |
| `computor-utils` | One module: `vsix_utils.py` (81 LOC) VSIX manifest parsing | 90 | computor-types | Used by `computor-backend/api/extensions.py` and `computor-cli/deployment.py`. |
| `computor-coder` | **No longer a Python package.** Git-tracked content is only `deployment/` (2 shell scripts + Coder workspace template). Plugin code moved to `computor-backend/src/computor_backend/coder/` (commits `7ff3c31a`, `ffb48b0c`). Stale untracked `src/computor_coder.egg-info/` remains. | 0 | — | Referenced by `startup.sh:269-271` (templates) only. |

Backend/types relationship is healthy layering, not duplication — `computor_backend/interfaces/*` subclass the `computor_types` interfaces to attach SQLAlchemy models (e.g. `interfaces/course.py:15` extends `computor_types.courses.CourseInterface`); only 5 ad-hoc `BaseModel`s in all of `computor_backend/api/`. Docker `docker/base/Dockerfile:51-63` installs types/utils/client/backend editable (cli is not installed in containers).

---

## TASK-501: Kill the CLI sync-over-async shim sprawl; give computor-client a sync facade

- **Category:** duplication — **Priority: P1** — **Effort: L**
- **Files:** `computor-cli/src/computor_cli/deployment.py:64-131` (`SyncHTTPWrapper` #1, reads `computor_client._http._default_headers`, `._auth_provider._access_token`); `computor-cli/src/computor_cli/documents.py:38-59` (`SyncHTTPWrapper` #2, same class name, wraps a **different** private attr `computor_client._client`); `computor-cli/src/computor_cli/consent.py:67-76` (`_api_client` raw `httpx.Client`); `computor-cli/src/computor_cli/auth.py:31-41` (`_verify_token` raw httpx); `delete.py:66-146` (`run_async(client._http.delete(...))`). 39 private-attribute accesses (`._http`/`._client`/`._auth_provider`/`._access_token`) across cli; 17 raw-httpx sites.

**Problem:** computor-client is async-only, so the sync CLI has grown three independent sync shims plus a `run_async` helper (`utils.py:3`) called at the top of nearly every command (11× each in `deployment.py` and `service_cli.py`). Each shim digs into computor-client private attributes to steal base_url/headers/token, duplicating auth-header construction and error formatting; the two `SyncHTTPWrapper` classes have drifted (they wrap different attributes).

**Steps:**
1. In computor-client, expose read-only `base_url`, `timeout`, and `auth_headers` on `ComputorClient` (base_url already exists at `client.py:113`; add the rest) so no consumer needs `_http`/`_auth_provider`.
2. Add one sync facade to computor-client (e.g. `computor_client/sync.py`: `SyncComputorClient` built on `httpx.Client`, or a thin `asyncio.run`-based proxy) providing get/post/patch/delete + raise-with-body error handling reusing `exceptions.py`.
3. Make `get_computor_client` in `computor-cli/auth.py:134` synchronous — it contains zero awaits — and delete the `run_async(get_computor_client(...))` pattern everywhere.
4. Replace both `SyncHTTPWrapper` classes, `consent._api_client`, and `_verify_token` with the new facade; route `delete.py`'s `client._http.delete` calls through it.
5. Delete `computor_cli/utils.py:run_async` once no callers remain (it also uses deprecated `asyncio.get_event_loop`).

**Risks / verification:** Token-header semantics differ per shim (`Authorization: Bearer` vs `X-API-Token`) — preserve each call site's header. Test `computor login/status`, `deployment apply --dry-run`, `documents`, `consent`, and delete commands against a dev backend.

---

## TASK-502: Make client codegen offline-capable; stop hand-editing generated code

- **Category:** consistency — **Priority: P1** — **Effort: M**
- **Files:** `computor-backend/src/computor_backend/scripts/generate_python_clients.py:25` (`fetch_openapi_spec(url="http://localhost:8000/openapi.json")`); commit `3a2ef88b` ("drop generated auth_gitlab_register method … Surgical edit of the generated client to avoid unrelated regeneration drift") editing `computor-client/src/computor_client/endpoints/authentication.py`; all 52 `endpoints/*.py` carry "Auto-generated … do regenerate" headers.

**Problem:** Regeneration needs a running backend, so small API removals get hand-patched into generated files. The commit message itself documents that a full regen produces "unrelated drift" — i.e. the checked-in generated code no longer matches the current OpenAPI spec, and hand edits will be silently reverted on the next regen.

**Steps:**
1. Change `fetch_openapi_spec` to import the FastAPI app (`computor_backend.server`) and call `app.openapi()` offline, keeping the URL mode as a fallback flag.
2. Run `bash generate.sh python-client` once; commit the full drift as a dedicated `chore(codegen)` commit so generated state == spec again.
3. Add a CI job (or pre-merge script) that regenerates and fails on `git diff --exit-code computor-client/src/computor_client/endpoints`.
4. Add "DO NOT EDIT" to the generated-header template in `generate_python_clients.py`.

**Risks / verification:** Offline `app.openapi()` may differ from the served spec if routers are conditionally mounted at startup (check `server.py` for env-gated routers, e.g. coder); the one-time drift commit needs review for accidental endpoint removals.

---

## TASK-503: Split `computor-cli/deployment.py` (2,149 LOC = 42% of the package)

- **Category:** god-file — **Priority: P2** — **Effort: M**
- **Files:** `computor-cli/src/computor_cli/deployment.py`: `SyncHTTPWrapper` (64), `_deploy_users` (226), `_deploy_services` (474), `_deploy_course_content_types` (816), `_deploy_course_contents` (862, ~320 lines), `_generate_student_templates` (1184), `_link_backends_to_deployed_courses` (1285), zip/toposort/meta helpers (1540–1665), `apply` command (1822), documents-style upload helpers (1665–1807).

**Problem:** One module mixes HTTP transport shims, deployment orchestration for five entity families, archive utilities, dependency toposort, and the click commands. It's the file every deployment change touches, impossible to unit-test in pieces.

**Steps:**
1. Create `computor_cli/deploy/` package; move helpers by domain: `users.py`, `services.py`, `contents.py` (content types + contents), `examples.py` (`_ensure_example_repository`, zip, toposort, meta reading), `extensions.py`.
2. Move `SyncHTTPWrapper` out entirely (superseded by TASK-501's facade).
3. Keep `deployment.py` as the thin click-command module importing from `deploy/`.
4. Give the shared mutable state (`deployed_services` dict threaded through 4 functions) a small `DeploymentState` dataclass.

**Risks / verification:** Pure code motion, but functions share closures over `auth`/`client` — keep signatures identical first, restructure second. Smoke-test `computor deployment apply` + `validate` on a sample config.

---

## TASK-504: Move crypto out of the DTO package (password hashing near-dead, encryption backend-only)

- **Category:** dead-code / packaging — **Priority: P2** — **Effort: M**
- **Files:** `computor-types/src/computor_types/password_utils.py` (368 LOC, argon2); `computor-types/src/computor_types/encryption.py` (36 LOC, keycove, reads `TOKEN_SECRET` env); deps in `computor-types/pyproject.toml:27-31` (`argon2-cffi`, `keycove>=0.1.0  # TODO: Remove after migration complete`). Verified consumers of `password_utils`: only `computor-backend/.../tests/test_password_hashing.py` and `computor-backend/.../scripts/create_service_users.py:41`. `encryption.py` consumers: 9 backend files (git_provider, temporal tasks, business_logic) — backend-only.

**Problem:** The DTO package ships crypto utilities and env-var access, forcing argon2-cffi and keycove onto every consumer. `password_utils` has no production auth consumer (auth is token/Keycloak-based). `encryption.py`'s docstring references a legacy `computor_types.tokens` module that no longer exists.

**Steps:**
1. Move `encryption.py` to `computor_backend/utils/encryption.py` (or into computor-utils if non-backend consumers are anticipated — see TASK-508); update the 9 backend imports.
2. Move `password_utils.py` next to its two consumers in computor-backend; alternatively delete all but `create_password_hash` + validation if the rest is unused (verify `PasswordValidationError` isn't referenced from `password_management.py` DTOs first).
3. Drop `argon2-cffi` and `keycove` from `computor-types/pyproject.toml`; add them to backend's pyproject.
4. Fix the stale `computor_types.tokens` docstring reference.

**Risks / verification:** `encryption.py` is wire-compatible with legacy `encrypt_api_key` data — do NOT change the keycove primitive or `TOKEN_SECRET` key handling, only the module location. Run backend git-provider/temporal test suites.

---

## TASK-505: Rename `deployments_refactored.py`; decouple CLI auth config from deployment types

- **Category:** consistency — **Priority: P2** — **Effort: M**
- **Files:** `computor-types/src/computor_types/deployments_refactored.py` (774 LOC, largest module in the package; DEPRECATED fields at lines 381, 441); 19 importing files incl. `computor-backend/business_logic/deployment.py`, `computor-cli/deployment.py`; `computor-cli/src/computor_cli/config.py:2` (CLI auth profile extends `BaseDeployment`); `computor-cli/src/computor_cli/auth.py:21,105` (uses `DeploymentFactory.read_deployment_from_file` to load `~/.computor/active_profile.yaml`). Sibling modules `deployment.py` (126), `deployment_base.py` (46), `course_deployment.py`, `lecturer_deployments.py` compound the naming confusion.

**Problem:** The "_refactored" suffix is fossilized migration naming — this IS the canonical module now, and four `deployment*` modules with unrelated purposes (hierarchy configs vs content-deployment tracking DTOs) actively mislead. The CLI additionally abuses `DeploymentFactory`/`BaseDeployment` as a general YAML config mechanism for its auth profile.

**Steps:**
1. Rename to `computor_types/deployment_config.py`; leave `deployments_refactored.py` as a one-line re-export shim (`from .deployment_config import *  # deprecated`) for one release.
2. Mechanically update the 19 imports.
3. Extract the YAML read/write plumbing (`DeploymentFactory.read_deployment_from_file`, `write_deployment`) into `computor_types/yaml_config.py` so `CLIAuthConfig` stops importing deployment types.
4. Schedule removal of the two DEPRECATED `execution_backends` fields (lines 381, 441) — confirm no YAML configs in `data/`/`docs/examples/` still use them.

**Risks / verification:** String-based imports or docs referencing the old module name; `integration-tests/suites/04_deployment/` imports it — run that suite.

---

## TASK-506: Remove the `computor-coder` dead package shell

- **Category:** dead-code — **Priority: P2** — **Effort: S**
- **Files:** Git-tracked content is only `computor-coder/deployment/{create-user.sh,generate-secret.sh,templates/python3.13/*}`; untracked `computor-coder/src/computor_coder.egg-info/` whose `SOURCES.txt` lists 8 source modules and a pyproject that no longer exist (code now at `computor-backend/src/computor_backend/coder/`); `startup.sh:269-271,428-430` references the templates dir.

**Problem:** The directory looks like a Python package but contains zero Python. The stale egg-info can shadow imports in editable installs.

**Steps:**
1. Delete `computor-coder/src/` (egg-info only; untracked — also `pip uninstall computor-coder` in dev venvs that still have the editable install).
2. Move `computor-coder/deployment/` to `ops/coder/` (an `ops/` dir already exists) or `docker/coder-templates/`.
3. Update the `startup.sh:269` template path and grep for other references (`wipe-coder*.sh`, `align-coder-postgres.sh` at repo root).
4. Remove the now-empty `computor-coder/` directory.

**Risks / verification:** `startup.sh`'s template import loop breaks if the path isn't updated; verify coder template push on a stack with `CODER_ENABLED=true` (note: Coder is excluded from the integration-test compose stack).

---

## TASK-507: Packaging hygiene — declare local deps, align pins, add py.typed

- **Category:** dependency-hygiene — **Priority: P2** — **Effort: M**
- **Files:** `computor-backend/pyproject.toml:23-24` ("computor-types and computor-utils must be installed separately") — yet backend also imports `computor_client` (`tasks/temporal_tutor_testing.py`), which the comment doesn't mention; backend pins hard (`httpx==0.27.0`, `pydantic==2.11.0`) while libs float (`httpx>=0.27.0`, `pydantic>=2.0`); `py.typed` exists only in computor-client — absent from computor-types/-cli/-utils despite computor-types being THE typing package; `computor-cli/pyproject.toml` lacks the `[tool.setuptools] package-dir` block the others have; ruff/mypy config exists only in computor-client; versions: client 0.2.0 vs 0.1.0 everywhere else; identical author/urls/license blocks duplicated across 5 pyprojects.

**Problem:** The install order and local-dependency graph live in `docker/base/Dockerfile:40-63` and developers' heads, not in metadata. A plain `pip install ./computor-backend` produces a broken install.

**Steps:**
1. Declare the local deps in backend's `[project.dependencies]` (`computor-types`, `computor-utils`, `computor-client`) — the two-layer Docker install already handles them via `--no-deps` editable reinstall, so nothing changes there.
2. Add `py.typed` + package-data stanza to computor-types (highest value), then cli/utils.
3. Add the missing `[tool.setuptools]`/`packages.find` block to computor-cli's pyproject.
4. Consider a `uv` workspace (or root `constraints.txt`) so httpx/pydantic pins are stated once; at minimum align `httpx` and `pydantic` floors/pins across the five files.
5. Optional: hoist shared ruff/mypy config to a root config consumed by all packages.

**Risks / verification:** Newly-declared local deps break `pip install` from a wheel/sdist context where sibling paths don't exist — document `pip install -e` order in README; rebuild `docker/base` to verify layer caching still works.

---

## TASK-508: Give computor-utils a purpose (or fold it away)

- **Category:** packaging — **Priority: P3** — **Effort: S**
- **Files:** `computor-utils/src/computor_utils/vsix_utils.py` (81 LOC) + `__init__.py` (9); consumers: `computor-backend/api/extensions.py`, `computor-cli/deployment.py`.

**Problem:** A full distribution (pyproject, README, egg-info, Docker layer) for one module is disproportionate — but it is also the only correctly-layered shared-utility home in the repo.

**Steps (choose one, coordinate with TASK-504):**
1. Preferred: keep computor-utils and make it the destination for the crypto modules from TASK-504, giving it a real reason to exist ("shared non-DTO helpers").
2. If TASK-504 moves crypto into backend instead: fold `vsix_utils.py` into `computor_types/vsix_utils.py` (its models `VsixMetadata`/`VsixManifestError` already live in computor-types), update the 2 imports, delete the package, remove it from `docker/base/Dockerfile:40-63` and cli/backend dependency lists.

**Risks / verification:** Docker base image layer list and pip-install order in setup scripts must be updated in the same change; grep for `computor-utils` in `docker/`, `scripts/`, `setup-env.sh`.

---

## TASK-509: Deduplicate per-command CLI boilerplate

- **Category:** duplication — **Priority: P3** — **Effort: S**
- **Files:** `computor-cli/src/computor_cli/service_cli.py` (815 LOC; `client = run_async(get_computor_client(auth))` at 12 sites: lines 60, 159, 217, 288, 350, 427, 509, 591, 649, 712, 782, …); same pattern 11× in `deployment.py`, 3× in `api_token_cli.py`, 5× in `delete.py`, 2× each in `crud.py`/`grading.py`; `crud.py:31-85` — two 10+-branch if/elif chains (`GET_CLIENT_ATTRIBUTE`, `GET_QUERY_CLASS`) mapping endpoint constants.

**Steps:**
1. Extend `@authenticate` (`computor-cli/auth.py:97`) — or add a `@with_client` decorator — that injects `client` alongside `auth`; delete the 30+ inline creations.
2. Replace `GET_CLIENT_ATTRIBUTE` with `getattr(client, table.replace('-', '_'))` (the dynamic resolution in `ComputorClient.__getattr__`, `client.py:282`, already handles this) and `GET_QUERY_CLASS` with a dict literal.

**Risks / verification:** Decorator ordering with click options; commands passing `force_new=True` need an escape hatch. Test one command per module.

---

## TASK-510: Harden `computor_types/__init__.py` (silent import-failure swallowing in `get_all_dtos`)

- **Category:** consistency — **Priority: P3** — **Effort: M**
- **Files:** `computor-types/src/computor_types/__init__.py` (252 LOC): hand-maintained partial re-export of ~85 modules; `get_all_dtos()` (lines 15-52) walks all packages with `except Exception: continue`, silently skipping any interface module that fails to import.

**Problem:** The re-export list drifts (newer modules like `workspace_roles`, `tutor_*` aren't in it) while consumers overwhelmingly import from submodules anyway; `get_all_dtos()` is load-bearing for backend permission setup, and a broken transitive import degrades to **silently missing permissions** rather than an error.

**Steps:**
1. In `get_all_dtos()`, collect import failures and raise/log them instead of bare `continue` (backend permission setup should fail loudly).
2. Shrink `__init__.py` to `__version__`, base classes, and `get_all_dtos` — or generate the export list in `generate.sh`. Grep for `from computor_types import X` (non-base X) consumers FIRST to size the break.

**Risks / verification:** Any consumer importing DTOs from the package root breaks — the grep in step 2 is mandatory; backend `permissions/role_setup.py` behavior changes if a module was silently failing today (that's the point, but verify in staging).

---

## TASK-511: Rename the colliding test-spec modules in computor-types

- **Category:** consistency — **Priority: P3** — **Effort: S**
- **Files:** `computor-types/src/computor_types/testing.py` (338 LOC, test.yaml spec models), `tests.py` (TestJob queue DTO), `testing_report.py` (testSummary.json models).

**Problem:** Three near-identically named modules cover three different domains (spec, job dispatch, report); `tests.py` collides mentally (and in tab-completion) with actual test directories and pytest conventions.

**Steps:**
1. Rename `tests.py` → `test_jobs.py` with a deprecation re-export shim; update importers (grep `computor_types.tests`).
2. Grep the `computor-testing` package for imports of these modules before the rename.
3. Optionally add a module docstring cross-reference table in `testing.py`.

**Risks / verification:** Minimal; run backend + computor-testing imports after the rename.

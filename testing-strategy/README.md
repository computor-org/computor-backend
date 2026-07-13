# Testing Strategy — computor-fullstack

This directory is the plan of record for refactoring and extending the automated tests of
computor-fullstack. It describes **what** to build and **why**; the ordered, checkable work
items live in [BACKLOG.md](BACKLOG.md). Nothing here is implementation — every document is
grounded in the code as of branch `release/2026.10` (verified 2026-07-13).

## Why now

- The integration harness (`integration-tests/`) is **broken**: the backend dropped local
  password auth (no `POST /auth/login`, no password columns), so the auth and permission
  suites cannot authenticate at all. Its entire git layer targets **GitLab, which the
  project abandoned for Forgejo**. Suites 05–08 (examples, release, student workflow, full
  lifecycle) were never implemented.
- The backend unit suite (`computor-backend/src/computor_backend/tests/`) has grown to
  ~68 files with heavy duplication (five overlapping permission suites) and stale
  GitLab-era and script-style tests.
- The web e2e suite (`computor-web/e2e/`) is one spec and is missing the shared fixtures
  module its own README promises.
- There is **no CI** anywhere in the repository.

## Goals

1. **A runnable integration harness** against a self-contained Docker stack with the real
   auth path (Keycloak) and the real git server (Forgejo).
2. **Three complementary testing approaches** at the API tier:
   - a **permission matrix**: every endpoint × every role → expected status;
   - **payload & exception contracts**: correct DTO handling, boundary cases, and
     `(status, error_code)` assertions;
   - a **role-based lifecycle scenario** ("golden path"): org-manager builds the
     hierarchy, a lecturer authors a course from real Python examples, students submit
     correct/empty/mixed solutions, a tutor grades, and the final state proves it.
3. **Personas act only through the public API**, exactly like real users: onboarded via
   invite links, authenticated via Keycloak, driving the same endpoints the VSCode
   extension uses. No direct DB writes for scenario actions (DB access is for assertions
   and idempotency checks only).
4. **A cleaned-up backend unit suite** with marker discipline and no dead weight.
5. **A broader mocked web e2e suite** now; a thin live-stack smoke tier later.

## Scope exclusions

| Excluded | Meaning |
|---|---|
| GitLab | **Omitted entirely — Forgejo is the only git server.** The integration-harness GitLab sweep (P1.1) was executed 2026-07-13: compose service, fixtures, suites, bootstrap script, env keys, and the dead `run_gitlab_test.sh` are gone. Remaining GitLab unit tests in the backend suite are deleted in P6. |
| Coder workspaces | Not tested. Existing `test_coder_*` backend unit tests are quarantined behind a marker, excluded from default runs. |
| `computor-testing/` | Not a test target — it is the assignment-testing framework students' code runs against. Its `examples/itpcp.pgph.py/*` directories **are** the fixture data for the golden path. |

## Test tiers

| Tier | Location | Runs against | Typical runtime |
|---|---|---|---|
| Backend unit | `computor-backend/src/computor_backend/tests/` | SQLite/mocks by default; live services (Postgres, Keycloak) opt-in via markers | seconds |
| API integration | `integration-tests/` | Full Docker stack: Postgres, Redis, MinIO, Temporal (+ workers), **Keycloak**, **Forgejo**, API | minutes (stateful, session-accumulating) |
| Web e2e | `computor-web/e2e/` | Playwright vs `next dev`, backend mocked at the network layer; later a `live` project vs the integration stack | seconds–minutes |

## Document map

| Doc | Content |
|---|---|
| [01-current-state.md](01-current-state.md) | Inventory of everything that exists today, what is broken, stale, or duplicated |
| [02-architecture.md](02-architecture.md) | Target integration stack, auth fixture design, state model, reporting, risks |
| [03-personas-and-scenario.md](03-personas-and-scenario.md) | The canonical personas and the golden-path scenario as a numbered endpoint script |
| [04-permission-matrix.md](04-permission-matrix.md) | Permission-matrix approach: endpoint inventory, expectations, conventions, coverage guard |
| [05-payload-validation.md](05-payload-validation.md) | Payload & exception testing: error-code contracts and boundary cases |
| [06-integration-suites.md](06-integration-suites.md) | Suite-by-suite specification for `integration-tests/suites/01…08` |
| [07-backend-unit-suite.md](07-backend-unit-suite.md) | Cleanup plan for `computor_backend/tests/` |
| [08-web-e2e.md](08-web-e2e.md) | Playwright refactor and coverage plan for `computor-web/e2e/` |
| [09-ci-and-tooling.md](09-ci-and-tooling.md) | Entry points, report artifacts, optional CI |
| [BACKLOG.md](BACKLOG.md) | **The step-by-step backlog** — phased, checkable, each item names the files it touches |

## How the tiers run

Today:
- Backend unit: `./test.sh` (or `cd computor-backend/src && pytest`, config `computor-backend/src/pytest.ini`).
- Integration: `cd integration-tests && make env up test down` — **currently fails** (see 01).
- Web e2e: `cd computor-web && yarn test:e2e` (needs `npx playwright install chromium` once).

Target (unchanged entry points, fixed content):
- Backend unit: `./test.sh` runs only `unit`-marked (default) tests; live-service tests opt-in via `-m` markers.
- Integration: `make env up test down` against the rebuilt stack; `make test SUITE=03` style filtering by marker.
- Web e2e: `yarn test:e2e` (mocked project); later `yarn test:e2e --project=live` against a running integration stack.

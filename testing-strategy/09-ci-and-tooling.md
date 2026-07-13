# 09 — CI & Tooling

There is no CI today; everything runs manually. This doc keeps the manual entry points
first-class (they are what developers actually use) and treats CI as an optional final
phase — the suites must be green and stable locally before automating them.

## 1. Entry points (target)

| Command | Runs | Requirements |
|---|---|---|
| `./test.sh` | backend unit suite, hermetic default (`-m "not integration and not keycloak and not docker and not coder"`) | nothing running |
| `./test.sh -m integration` (pass-through args) | live-Postgres backend tests | dev stack (`startup.sh`) |
| `cd integration-tests && make env` | writes `.env.integration` from template; stages Keycloak realm (secret substitution) + `deployments/` YAMLs | — |
| `make up` | build + start the stack, `wait_for_services.sh`, bootstrap | Docker |
| `make test` | full pytest run (suites 01→08 in order) | stack up |
| `make test MARKERS="permissions or contracts"` | filtered run | stack up |
| `make report` | regenerate/open `reports/latest.md` | after a run |
| `make down` / `make clean` | stop / stop + volume wipe (**the** reset for realm/state) | — |
| `cd computor-web && yarn typecheck && yarn test:e2e` | mocked Playwright project | nothing running |
| `yarn test:e2e --project=live` (P8) | live smoke tier | integration stack up |

Conventions honored: `startup.sh`/`stop.sh` stay the only way to run the *dev* stack;
the integration stack is self-contained under `integration-tests/` and never shares
volumes/ports with it. No credential defaults in compose beyond the committed
IT-template values (which are test-only by construction, but still use
`${VAR:?must be set}` for anything secret-like, per repo convention).

## 2. Report artifacts

- `integration-tests/reports/latest.md` — matrix cross-tab + grading-outcome table
  ([02](02-architecture.md) §7). Committed? No — gitignore it; CI uploads it as an
  artifact instead. Keep one committed `reports/example.md` snapshot for documentation.
- Playwright: keep `trace: on-first-retry`; HTML report as CI artifact.

## 3. Optional CI (GitHub Actions, phase P8)

| Workflow | Trigger | Jobs |
|---|---|---|
| `backend-unit.yml` | PR to `release/*`, `main` | `./test.sh` (hermetic) — fast gate |
| `web.yml` | PR touching `computor-web/` | `yarn typecheck` + mocked `yarn test:e2e` (playwright container) |
| `integration.yml` | nightly + manual dispatch | `make env up test down` on a beefy runner; upload `reports/latest.md`; **not** a PR gate initially (stack boot ≈ minutes, Keycloak/Temporal warmup) |

Notes:
- PR gates stay under ~5 min; the integration stack is nightly until it proves stable
  (flake budget: promote to PR gate only after N consecutive green nights).
- Repo convention: all work branches off `release/2026.10`; CI triggers must include
  `release/*` branches, and nothing ever auto-pushes to `main`.

# CI workflows — HELD (not active)

These GitHub Actions workflows are **drafts kept here on purpose, not live CI**.
GitHub only runs workflow files located directly in `.github/workflows/`, so
while they sit under `testing-strategy/ci/` they will **never trigger** — no PR
gates, no nightly runs, nothing.

## To activate (later, when you want CI)

```bash
mkdir -p .github/workflows
git mv testing-strategy/ci/*.yml .github/workflows/
```

Then push. First-run notes:

- **web-e2e.yml** — `yarn typecheck` + the mocked Playwright suite. Hermetic
  (backend is network-mocked); should be green as-is.
- **backend-unit.yml** — runs the `-m unit` subset only (~64 tests). The
  editable-install step (`pip install -e computor-types …`) is a starting point;
  the exact sibling-package set / extras may need tuning on the first run.
- **integration.yml** — the full harness (`make up`/`test`/`clean`), nightly +
  manual. Heavy (image builds + Keycloak/Forgejo boot + ~18 real test runs);
  keep it off the PR path until it has a stable streak.

All three target `release/**` (and `main`) branches and never auto-push to
`main`.

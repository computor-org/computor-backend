# scripts/

Developer utilities. Nothing here is required at runtime — scripts the running stack
depends on live under `ops/` (see [`ops/README.md`](../ops/README.md)).

| Path | Purpose |
|------|---------|
| `add-testing-language.sh` | Adds a per-language testing worker: mints its token into `.env`, writes `data/deployments/testing-worker-<language>.yaml` and prints the compose block. See [service accounts](../docs/service-accounts.md#one-worker-per-language) |
| `bench/` | SQL benchmarks: a synthetic dataset in a throwaway `computor_bench` database plus a timing harness for the hot read queries. Details in [`bench/README.md`](bench/README.md) |
| `check_client_drift.py` | Fails when the checked-in Python client no longer matches the API (regenerates into a temp dir and diffs). Run by the pre-commit hook; manual: `python3 scripts/check_client_drift.py` |
| `check_dto_location.py` | Fails when an API-facing pydantic model is declared in the backend instead of `computor-types`. Manual: `python3 scripts/check_dto_location.py` |
| `check_forbidden_imports.py` | Architecture guard: blocks backend-only imports (fastapi, sqlalchemy, `computor_backend`, …) in `computor-types`/`computor-client`. Run by the pre-commit hook; manual: `python3 scripts/check_forbidden_imports.py` |
| `git-hooks/` | Pre-commit hook (secret scanning, the import guard and client-drift check above, web styling ratchet). Install once: `bash scripts/git-hooks/install-hooks.sh` — details in [`git-hooks/README.md`](git-hooks/README.md) |
| `utilities/backfill_skip_result_values.py`, `utilities/scrub_result_path_properties.py` | One-off data repairs for stored test results; each script's docstring explains its use |
| `utilities/ensure_venv.sh` | `ensure_venv()` helper that auto-activates `.venv`; sourced by `generate.sh` and `seed.sh` |

Run everything from the project root. Related root entry points: `./computor.sh`
(stack lifecycle + tests), `./setup-env.sh` (creates `.env`), `generate.sh` (codegen),
`seed.sh` (dev seeder).

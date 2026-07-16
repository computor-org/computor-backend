# scripts/

Developer utilities. Nothing here is required at runtime — scripts the running stack
depends on live under `ops/` (see [`ops/README.md`](../ops/README.md)).

| Path | Purpose |
|------|---------|
| `check_forbidden_imports.py` | Architecture guard: blocks backend-only imports (fastapi, sqlalchemy, `computor_backend`, …) in `computor-types`/`computor-cli`/`computor-client`. Run by the pre-commit hook; manual: `python3 scripts/check_forbidden_imports.py` |
| `git-hooks/` | Pre-commit hook (secret scanning + the import guard above). Install once: `bash scripts/git-hooks/install-hooks.sh` — details in [`git-hooks/README.md`](git-hooks/README.md) |
| `utilities/ensure_venv.sh` | `ensure_venv()` helper that auto-activates `.venv`; sourced by `generate.sh` and `seed.sh` |

Run everything from the project root. Related root entry points: `./computor.sh`
(stack lifecycle + tests), `./setup-env.sh` (creates `.env`), `generate.sh` (codegen),
`seed.sh` (dev seeder).

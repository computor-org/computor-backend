# Computor Documentation

Computor is a university programming-course management platform: a monorepo of Python
packages (DTOs, HTTP client, CLI, FastAPI backend) plus a Next.js web frontend and a
Coder workspace integration.

## Doc map

| Doc | Read it for |
|-----|-------------|
| **[architecture.md](architecture.md)** | The packages, the layered backend, data flow, and infrastructure services. |
| **[development.md](development.md)** | Setup, the daily cycle, adding an entity end-to-end, migrations, code generation, and tests. |
| **[backend-patterns.md](backend-patterns.md)** | The three patterns the backend is built on: EntityInterface/DTOs, RBAC permissions, and Temporal workflows. |
| **[git-integration.md](git-integration.md)** | How a course connects to git — in-system Forgejo vs. external GitLab, delivery modes, and configuring it from a deployment file. |
| **[../ops/docs/SELF_UPDATE.md](../ops/docs/SELF_UPDATE.md)** | One-click system updates from the admin UI (System → Updates) or `./computor.sh update` — config, update flow, rollback, and the rules that keep changes update-friendly. |

New here? Read them in that order. For a specific task, jump straight to the relevant doc.

## Quick start

```bash
# 1. Editable installs (order matters: types → client → cli → backend)
python3.10 -m venv .venv && source .venv/bin/activate
pip install -e computor-types/ -e computor-client/ -e computor-cli/ -e computor-backend/

# 2. Environment: generate .env with fresh secrets (never overwrites an existing .env)
./setup-env.sh

# 3. Docker services (postgres, redis, temporal, minio, traefik, workers)
./computor.sh up dev -d

# 4. Backend on :8000 (runs migrations + seeds admin automatically)
bash api.sh

# 5. Frontend on :3000 (separate terminal)
bash web.sh
```

In **dev**, only the supporting services run in Docker — the API and frontend run locally
via `api.sh` / `web.sh`. In **prod** (`./computor.sh up prod -d`) everything runs in Docker.
Always drive the stack through `./computor.sh`
(`up`/`down`/`status`/`maintenance`/`update`/`test`), never `docker compose` directly.
See [development.md](development.md) for the full walkthrough.

## Service URLs

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| API docs (Swagger / ReDoc) | http://localhost:8000/docs · `/redoc` |
| Web frontend | http://localhost:3000 |
| Temporal UI | http://localhost:8088 |
| MinIO console | http://localhost:9001 |

## Conventions

- **Branches**: `feat/*`, `fix/*`, `refactor/*`, `docs/*`. Branch off the active release
  branch and PR back into it; use the same branch name across sibling repos.
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) —
  `feat(scope): subject`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- **Python**: PEP 8, 120-col lines, type hints on all signatures, `snake_case` files.
- **DTOs**: suffix by role — `UserCreate`, `UserGet`, `UserList`, `UserUpdate`, `UserQuery`;
  interfaces end in `Interface`. See [backend-patterns.md](backend-patterns.md).
- **After changing DTOs or models**: regenerate artifacts with `bash generate.sh all`
  and validate the web build with `npx tsc --noEmit`.

## Getting help

- **Interactive API reference**: http://localhost:8000/docs (server running).
- **Project overview / troubleshooting**: [`CLAUDE.md`](../CLAUDE.md).
- **Ops** (Docker, env vars): [`ops/docs/`](../ops/docs/).

# Computor

A university programming course management platform with automated GitLab integration for repository and group management.

## Packages

| Package | Description |
|---------|-------------|
| `computor-types` | Pydantic DTOs - shared data structures for API contracts |
| `computor-client` | Auto-generated async HTTP client library |
| `computor-cli` | Command-line interface for admin and dev tasks |
| `computor-backend` | FastAPI server with business logic and Temporal workflows |
| `computor-web` | Next.js frontend application |

## Prerequisites

- Debian-based Linux recommended
- Docker >= 29.x and Docker Compose >= 5.x
- Git
- Python 3.10 (development only)

## Quick Start

### Development Mode

```bash
# Clone and setup
git clone <repository-url> <dir-name>
cd <dir-name>

# Create virtual environment
python3.10 -m venv .venv
source .venv/bin/activate

# Install packages (editable mode for development)
pip install -e computor-types/
pip install -e computor-client/
pip install -e computor-cli/
pip install -e computor-utils/
pip install -e computor-backend/

# Configure environment
cp ops/environments/.env.common.template .env  # Then edit .env with your configuration

# Start Docker services (PostgreSQL, Redis, Temporal, MinIO)
./computor.sh up dev -d

# Start the API server (runs migrations + creates admin user automatically)
bash api.sh

# Start the web frontend (separate terminal)
bash web.sh

# Tip: Run without -d to see Docker service logs (useful for debugging).
# This requires additional terminals for api.sh and web.sh:
#   Terminal 1: ./computor.sh up dev
#   Terminal 2: bash api.sh
#   Terminal 3: bash web.sh
```

- API: http://localhost:8000/docs
- Web: http://localhost:3000

### Production Mode

No local Python installation required — everything runs in Docker containers.

```bash
# Clone and configure
git clone <repository-url> <dir-name>
cd <dir-name>
cp ops/environments/.env.common.template .env  # Then edit .env with your production configuration

# Start all services (builds Docker images, runs migrations, starts API)
./computor.sh up prod --build -d

# To enable Coder workspace support, set CODER_ENABLED=true in .env
```

### computor.sh

The single CLI for operating the stack. `startup.sh`, `stop.sh`, and
`maintenance.sh` still work as thin wrappers around it.

```
Usage: ./computor.sh <command> [dev|prod] [docker-compose-options]

  up          Start the stack (dev is the default environment)
  down        Stop the stack (auto-detects dev/prod when omitted)
  status      Show services + maintenance state
  maintenance enter|exit|status — full maintenance mode (static page, services stopped)
  update      check|status|run — self-update (see ops/docs/SELF_UPDATE.md)

Optional services are controlled via .env flags: CODER_ENABLED, KEYCLOAK_ENABLED,
GIT_SERVER=forgejo, MATLAB_ENABLED, UPDATE_ENABLED.

Examples:
  ./computor.sh up dev -d             # Dev services, detached
  ./computor.sh up prod --build -d    # Rebuild images and start detached
  ./computor.sh down                  # Stop whatever is running
  ./computor.sh maintenance enter prod
```

### System updates

With `UPDATE_ENABLED=true` (plus `SYSTEM_REPO_URL`/`SYSTEM_REPO_BRANCH` in `.env`),
admins can check for new commits on the tracked branch and run a one-click update
from the web UI (**System → Updates**) — maintenance page, rebuild, restart, and
automatic rollback if the new version fails its health check. Details:
[ops/docs/SELF_UPDATE.md](ops/docs/SELF_UPDATE.md).

### api.sh (development)

```
Usage: ./api.sh [OPTIONS]

  --no-migrations     Skip running Alembic migrations before starting
  --verbose, -v       Show WebSocket connection logs + HTTP requests
  --debug, -d         Show all debug logs (very verbose)
  --quiet, -q         Show only errors (hides HTTP requests too)
```

### web.sh (development)

```
Usage: ./web.sh [OPTIONS]

  --port, -p PORT     Set dev server port (default: 3000)
  --install, -i       Run yarn install before starting

Environment Variables:
  NEXT_PUBLIC_API_URL    Backend API URL (default: http://localhost:8000)
  COMPUTOR_WEB_PORT      Dev server port (default: 3000)
```

## Documentation

Start at **[docs/README.md](docs/README.md)** — the index and quick start. From there:

- [Architecture](docs/architecture.md) — packages, layered backend, infrastructure
- [Development](docs/development.md) — setup, daily cycle, entities, migrations, codegen, tests
- [Backend Patterns](docs/backend-patterns.md) — EntityInterface/DTOs, permissions, Temporal
- [Git Integration](docs/git-integration.md) — course git: Forgejo vs. GitLab, deploy-from-file
- [Self-Update](ops/docs/SELF_UPDATE.md) — one-click system updates from the admin UI / CLI

## License

MIT

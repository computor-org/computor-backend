# Docker Compose Setup Guide

## Overview

The Computor platform uses a modular Docker Compose architecture that separates core services from optional components like Coder workspace management.

## Architecture

### File Structure

```
computor-backend/
├── ops/docker/
│   ├── docker-compose.base.yaml   # Core shared services
│   ├── docker-compose.dev.yaml    # Development-specific services
│   ├── docker-compose.prod.yaml   # Production-specific services
│   ├── docker-compose.coder.yaml  # Optional Coder addon
│   ├── docker-compose.web.yaml    # Frontend (auto-loaded in prod)
│   └── docker-compose.*.yaml      # Further overlays (keycloak, forgejo, matlab, ...)
├── .env                            # Active environment file
├── setup-env.sh                    # Creates .env (generates .env.common with fresh secrets)
└── computor.sh                     # Lifecycle CLI (up/down/status/maintenance/update/test)
```

### Service Organization

**Core Services** (always running):
- PostgreSQL (main database)
- Redis (cache)
- Temporal + PostgreSQL (workflow orchestration)
- MinIO (object storage)
- Traefik (reverse proxy)
- Static file server

**Development Services** (dev only):
- Temporal UI
- Development workers with hot reload

**Production Services** (prod only):
- Uvicorn API server
- Frontend application (`docker-compose.web.yaml`)
- Production workers

**Optional Coder Services** (when enabled):
- Coder server and its PostgreSQL
- Docker registry for workspace images
- Workspace ingress
- Coder Temporal worker (image builds and template provisioning)

## Quick Start

### 1. Initial Setup

```bash
# Clone and navigate to the project
git clone https://github.com/computor-org/computor-backend.git
cd computor-backend

# Run the setup script to create the .env file
./setup-env.sh

# Or for non-interactive setup:
./setup-env.sh --auto
```

### 2. Start Services

#### Development Mode

```bash
./computor.sh up dev -d
```

#### Production Mode

```bash
./computor.sh up prod -d
```

Coder workspace support is controlled via `CODER_ENABLED=true` in `.env`.

### 3. Stop Services

```bash
./computor.sh down dev    # development stack
./computor.sh down prod   # production stack
```

`./computor.sh` composes the correct overlay set from the `.env` feature flags.
Avoid running `docker compose` directly with hand-listed `-f` flags — it bypasses
the script's overlay logic.

## Environment Configuration

### Environment Files

The runtime scripts read a single `.env` in the repository root.
`./setup-env.sh` generates `.env.common` with fresh secrets from
`ops/environments/.env.common.template` and copies it to `.env` if none
exists. Dev vs. prod is the argument to `./computor.sh`, not a separate file.
See [ENV_CONFIGURATION.md](ENV_CONFIGURATION.md).

### Templates vs Real Files

- **Templates** (`*.template`) - Committed to git, contain placeholders
- **Real files** (`.env`, `.env.common`) - Gitignored, contain actual secrets

### Key Configuration Variables

#### Common Variables
- `SYSTEM_DEPLOYMENT_PATH` - Base path for data storage
- `POSTGRES_PASSWORD` - Database password
- `TOKEN_SECRET` - JWT signing secret
- `API_ADMIN_PASSWORD` - Admin user password

#### Coder Variables (when enabled)
- `CODER_URL` - How the backend reaches Coder (set by `setup-env.sh`)
- `CODER_ADMIN_EMAIL` - Admin email address
- `CODER_ADMIN_PASSWORD` - Admin password
- `CODER_ADMIN_API_SECRET` - API access token

## Advanced Usage

### Manual Docker Compose Commands

`./computor.sh` is the supported entry point. For ad-hoc read-only commands,
reuse the file list it assembles (in prod a bare compose command fails
interpolation, because public URLs are derived from `PUBLIC_DOMAIN` at launch):

```bash
source ops/lib/common.sh
load_env && derive_public_urls dev && pin_project_name && assemble_compose_files dev
docker compose $COMPOSE_FILES logs -f temporal-worker
```

### Service URLs

All service ports are bound to `127.0.0.1` by default — they're reachable
from the host (and over SSH tunnels) but **not** from the surrounding network.
Traefik on `${TRAEFIK_HTTP_PORT:-8080}` is the public entrypoint behind a
TLS-terminating proxy on the same host; set `TRAEFIK_BIND_ADDRESS=0.0.0.0` only
if that proxy runs on another host, and firewall the port to it.

#### Development (from the host)
- Traefik / public entrypoint: http://localhost:8080
- API (direct): http://localhost:8000
- Temporal UI: http://localhost:8088
- MinIO Console: http://localhost:9001
- Coder API (if enabled): http://localhost:7080
- Postgres: localhost:5432 → container 5437 (`psql -h localhost -p 5432`)
- Redis: localhost:6379

#### Production (from the host)
- Traefik / public entrypoint: http://your-host:8080
  - `/api` → uvicorn
  - `/docs` → documents
  - `/coder/{user}/{workspace}/` → coder workspaces
  - `/` → frontend
- API (direct, host-only): http://localhost:8000
- Coder API (direct, host-only): http://localhost:7080

### Database Access

The system uses three **separate** PostgreSQL instances on different ports:

- `postgres` (host 5432 → container 5437) — Main application database `computor`
- `temporal-postgres` (5433) — Temporal workflow database `temporal`
- `coder-postgres` (5439) — Coder workspace database `coder` (only when
  `CODER_ENABLED=true`)

Each instance has its own data directory under `${SYSTEM_DEPLOYMENT_PATH}/`.

### Networking

All services share the `computor-network` Docker network for internal communication.

## Troubleshooting

### Port Conflicts

If you encounter port conflicts:

1. Check which ports are in use:
   ```bash
   netstat -tulpn | grep LISTEN
   ```

2. Modify port mappings in `.env`:
   ```bash
   TRAEFIK_HTTP_PORT=8081
   POSTGRES_EXTERNAL_PORT=5434
   ```

### Permission Issues

If you see permission errors:

```bash
# Fix ownership of deployment directory
sudo chown -R $(whoami):$(whoami) /opt/computor

# Or use a different path in .env:
SYSTEM_DEPLOYMENT_PATH=/home/$USER/computor-data
```

### Coder Issues

If Coder fails to start:

1. Check Docker group ID:
   ```bash
   getent group docker | cut -d: -f3
   ```

2. Set `DOCKER_GID` in `.env` (left empty, `./computor.sh up` detects it)

3. Ensure Docker socket is accessible:
   ```bash
   ls -la /var/run/docker.sock
   ```

## Security Notes

1. **Never commit `.env` files** to version control
2. **Use strong passwords** — credential env vars (e.g. `POSTGRES_PASSWORD`,
   `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `TEMPORAL_POSTGRES_PASSWORD`,
   `CODER_POSTGRES_*`) have **no defaults**; see
   [ENV_CONFIGURATION.md](ENV_CONFIGURATION.md#fail-closed-variables).
3. **All service ports bound to `127.0.0.1`** by default, Traefik included —
   services are reachable from the host (and SSH tunnels) but not from the
   network.
4. **HTTPS** is expected to be terminated upstream (e.g. nginx in front of
   Traefik:8080). No TLS inside the compose stack.
5. **Docker socket** is exposed read-only to Traefik via `tecnativa/docker-socket-proxy`
   in production (dev mounts the socket directly). `temporal-worker-coder` uses
   its own allowlist proxy (`coder-worker-socket-proxy`: builds, image push and
   volume inspect/delete, no container create or exec; see
   `ops/docs/CODER_INTEGRATION.md`). The Coder server has no socket either:
   its provisioner uses `coder-provisioner-socket-proxy`, which admits only
   the workspace lifecycle and refuses privileged containers, host binds and
   host namespaces.
6. **Coder registry isolation:** `coder-registry` is deliberately left off the
   `computor-network`, so workspace containers (which DO live on that network)
   can't reach it over TCP. The host docker daemon talks to it via the
   `127.0.0.1:5000` port binding, so pushes from `temporal-worker-coder` and
   pulls during workspace creation still work — but neither goes through a
   network path that user workspaces can intercept.
7. **Rotate tokens regularly** especially API tokens.

## Support

For issues or questions:
1. Check the logs: `docker compose $COMPOSE_FILES logs [service-name]`
   (file list assembled as under *Manual Docker Compose Commands*)
2. Review configuration: `docker compose $COMPOSE_FILES config`
3. Consult the main documentation
4. Open an issue on GitHub

## Shared deployments

Operators run `./computor.sh update check`, `update status`, and `update run prod`
from their own accounts. They need access to the deployment checkout, its `.git`
and `.env`, the operator-managed configuration directories, and the Docker daemon.
Running the command as the original checkout owner is unnecessary.

Put the operators in one group that owns the deployment checkout, its `.git`
and `.env` through default ACLs, without changing file owners or the
service/database UIDs, and set `core.sharedRepository=group`. Each operator
then runs, with their own login, from the deployment checkout:

```bash
./computor.sh update check
./computor.sh update status
./computor.sh update run prod
```

`check` is read-only and returns 10 when an update is available. `run` performs
builds, maintenance and a restart; use the deployment's backup and release gates
before running it. The CLI checks writable Git state before acquiring an update
lock and reports unreadable configuration with deployment-access instructions.
Git ownership exceptions are scoped to the selected checkout for each script
invocation. For manual Git commands in a shared checkout, use
`git -c safe.directory=<checkout> -C <checkout> ...`.

The shared group can read deployment secrets and modify deployed code; include
only authorized operators. Default ACLs and `core.sharedRepository=group` keep
new Git/source files usable by all operators, including under `umask 077`.
Tooling that replaces the deployment tree must reapply the policy and keep
group access on env and recovery files. No blanket sudo rule
is needed for routine application administration. Host packages, nginx/TLS,
SSH, systemd and group enrollment remain the host administrator's responsibility.

For the optional updater sidecar, set `COMPUTOR_DEPLOY_GID` in `.env` to the
numeric operator GID. Both the watcher and detached runner receive this
supplementary group as well as the Docker socket group.

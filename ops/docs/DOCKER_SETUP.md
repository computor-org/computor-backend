# Docker Compose Setup Guide

## Overview

The Computor platform now uses a modular Docker Compose architecture that separates core services from optional components like Coder workspace management.

## Architecture

### File Structure

```
computor-fullstack/
├── ops/docker/
│   ├── docker-compose.base.yaml   # Core shared services
│   ├── docker-compose.dev.yaml    # Development-specific services
│   ├── docker-compose.prod.yaml   # Production-specific services
│   ├── docker-compose.coder.yaml  # Optional Coder addon
│   └── docker-compose.web.yaml    # Frontend (auto-loaded in prod)
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
- Optional Keycloak SSO

**Production Services** (prod only):
- Uvicorn API server
- Frontend application
- Production workers

**Optional Coder Services** (when enabled):
- Coder server
- Docker registry for workspaces
- Workspace image builders
- Template provisioning

## Quick Start

### 1. Initial Setup

```bash
# Clone and navigate to the project
git clone <repository>
cd computor-fullstack

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

The system uses a layered environment configuration:

1. **`.env.common`** - Shared variables for all environments
2. **`.env.dev`** or **`.env.prod`** - Environment-specific overrides
3. **`.env.coder`** - Coder-specific configuration (optional)
4. **`.env`** - Consolidated file (auto-generated for backward compatibility)

### Templates vs Real Files

- **Templates** (`*.template`) - Committed to git, contain placeholders
- **Real files** (`.env.*`) - Gitignored, contain actual secrets

### Key Configuration Variables

#### Common Variables
- `SYSTEM_DEPLOYMENT_PATH` - Base path for data storage
- `POSTGRES_PASSWORD` - Database password
- `TOKEN_SECRET` - JWT signing secret
- `API_ADMIN_PASSWORD` - Admin user password

#### Coder Variables (when enabled)
- `CODER_DOMAIN` - Your Coder instance domain
- `CODER_ADMIN_EMAIL` - Admin email address
- `CODER_ADMIN_PASSWORD` - Admin password
- `CODER_ADMIN_API_SECRET` - API access token

## Advanced Usage

### Manual Docker Compose Commands

`./computor.sh` is the supported entry point. If you really need to invoke
compose directly:

```bash
# Development
docker compose \
  -f ops/docker/docker-compose.base.yaml \
  -f ops/docker/docker-compose.dev.yaml \
  up -d

# Production with Coder
docker compose \
  -f ops/docker/docker-compose.base.yaml \
  -f ops/docker/docker-compose.prod.yaml \
  -f ops/docker/docker-compose.web.yaml \
  -f ops/docker/docker-compose.coder.yaml \
  up -d

# View logs
docker compose \
  -f ops/docker/docker-compose.base.yaml \
  -f ops/docker/docker-compose.dev.yaml \
  logs -f temporal-worker
```

### Service URLs

All non-Traefik service ports are bound to `127.0.0.1` only — they're reachable
from the host (and over SSH tunnels) but **not** from the surrounding network.
Only Traefik on `${TRAEFIK_HTTP_PORT:-8080}` is exposed publicly.

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

## Migration from Old Structure

If you're migrating from the old docker-compose structure:

1. Backup your existing environment files:
   ```bash
   cp .env .env.backup
   cp .env.dev .env.dev.old
   cp .env.prod .env.prod.old
   ```

2. Run the setup script:
   ```bash
   ./setup-env.sh
   ```

3. Copy any custom values from your old files to the new ones

4. Stop old services and start with new structure:
   ```bash
   docker-compose -f docker-compose-dev.yaml down
   ./computor.sh up dev -d
   ```

## Troubleshooting

### Port Conflicts

If you encounter port conflicts:

1. Check which ports are in use:
   ```bash
   netstat -tulpn | grep LISTEN
   ```

2. Modify port mappings in `.env.common`:
   ```bash
   TRAEFIK_HTTP_PORT=8081
   POSTGRES_EXTERNAL_PORT=5433
   ```

### Permission Issues

If you see permission errors:

```bash
# Fix ownership of deployment directory
sudo chown -R $(whoami):$(whoami) /opt/computor

# Or use a different path in .env.common:
SYSTEM_DEPLOYMENT_PATH=/home/$USER/computor-data
```

### Coder Issues

If Coder fails to start:

1. Check Docker group ID:
   ```bash
   getent group docker | cut -d: -f3
   ```

2. Update `DOCKER_GID` in `.env.coder`

3. Ensure Docker socket is accessible:
   ```bash
   ls -la /var/run/docker.sock
   ```

## Security Notes

1. **Never commit `.env` files** to version control
2. **Use strong passwords** — credential env vars (e.g. `POSTGRES_PASSWORD`,
   `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `TEMPORAL_POSTGRES_PASSWORD`,
   `CODER_POSTGRES_*`) have **no defaults** — compose will fail to start if
   any are missing.
3. **All service ports bound to `127.0.0.1`** except Traefik's 8080 — services
   are reachable from the host (and SSH tunnels) but not from the intranet.
4. **HTTPS** is expected to be terminated upstream (e.g. nginx in front of
   Traefik:8080). No TLS inside the compose stack.
5. **Docker socket** is exposed read-only to Traefik via `tecnativa/docker-socket-proxy`
   in production (dev mounts the socket directly). Coder and `temporal-worker-coder`
   need RW socket access for container provisioning and image builds; both run
   with `no-new-privileges`.
6. **Coder registry isolation:** `coder-registry` is deliberately left off the
   `computor-network`, so workspace containers (which DO live on that network)
   can't reach it over TCP. The host docker daemon talks to it via the
   `127.0.0.1:5000` port binding, so pushes from `temporal-worker-coder` and
   pulls during workspace creation still work — but neither goes through a
   network path that user workspaces can intercept.
7. **Rotate tokens regularly** especially API tokens.

## Support

For issues or questions:
1. Check the logs: `docker-compose logs [service-name]`
2. Review configuration: `docker-compose config`
3. Consult the main documentation
4. Open an issue on GitHub
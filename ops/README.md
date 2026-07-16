# Ops Directory Structure

This directory contains all operational configurations and infrastructure files for the Computor platform.

## Directory Layout

```
ops/
├── docker/                     # Docker Compose configurations
│   ├── docker-compose.base.yaml      # Core shared services
│   ├── docker-compose.dev.yaml       # Development-specific
│   ├── docker-compose.prod.yaml      # Production-specific
│   └── docker-compose.coder.yaml     # Optional Coder addon
│
├── environments/              # Environment configuration templates
│   ├── .env.common.template   # Shared configuration
│   ├── .env.dev.template      # Development settings
│   ├── .env.prod.template     # Production settings
│   └── .env.coder.template    # Coder addon settings
│
├── lib/                       # Shared bash library for ./computor.sh
│   ├── common.sh              # env loading, COMPOSE_FILES assembly, maintenance
│   └── update.sh              # self-update executor (see docs/SELF_UPDATE.md)
│
└── docs/                      # Operational documentation
    ├── DOCKER_SETUP.md        # Complete Docker setup guide
    ├── REVERSE_PROXY.md       # nginx (TLS) → Traefik production setup
    └── SELF_UPDATE.md         # One-click updates from the admin UI / CLI
```

## Quick Reference

### Starting Services

From the project root directory (`startup.sh`/`stop.sh`/`maintenance.sh` remain as
wrappers around `computor.sh`):

```bash
# Development
./computor.sh up dev -d

# Production
./computor.sh up prod -d

# Stop / status / maintenance / self-update
./computor.sh down
./computor.sh status
./computor.sh maintenance enter prod     # static maintenance page, services stopped
./computor.sh update check               # see docs/SELF_UPDATE.md

# Optional services are .env flags: CODER_ENABLED, KEYCLOAK_ENABLED,
# GIT_SERVER=forgejo, MATLAB_ENABLED, UPDATE_ENABLED
```

### Environment Setup

From the project root directory:

```bash
# Interactive setup
./setup-env.sh

# Automated setup with defaults
./setup-env.sh --auto

# Force overwrite existing configs
./setup-env.sh --force
```

### Direct Docker Compose Usage

Avoid raw `docker compose` for lifecycle operations: the overlay list depends on the
`.env` feature flags, and in prod the public URLs are derived from `PUBLIC_DOMAIN` at
launch — a bare compose command fails interpolation. `./computor.sh` (via
`ops/lib/common.sh`) handles both. For ad-hoc read-only commands (logs, ps), reuse the
assembled file list:

```bash
source ops/lib/common.sh
load_env && derive_public_urls dev && pin_project_name && assemble_compose_files dev
docker compose $COMPOSE_FILES logs -f [service-name]
```

## Environment Files

The actual environment files (`.env.*`) are created in the project root directory from the templates in `ops/environments/`:

- `.env.common` - Created from `ops/environments/.env.common.template`
- `.env.dev` - Created from `ops/environments/.env.dev.template`
- `.env.prod` - Created from `ops/environments/.env.prod.template`
- `.env.coder` - Created from `ops/environments/.env.coder.template`
- `.env` - Auto-generated consolidated file

## Key Services

### Core Services (base.yaml)
- PostgreSQL (main database)
- Redis (cache)
- Temporal + PostgreSQL (workflows)
- MinIO (object storage)
- Traefik (reverse proxy)

### Development Services (dev.yaml)
- Temporal UI
- Development workers
- Optional Keycloak SSO

### Production Services (prod.yaml)
- Uvicorn API server
- Frontend application
- Production workers

### Coder Services (coder.yaml)
- Coder server
- Docker registry
- Workspace builders
- Template provisioning

## Notes

- The startup scripts (`startup.sh` and `setup-env.sh`) remain in the project root for convenience
- Environment files are created in the project root, not in ops/
- All Docker Compose files use relative paths from the project root
- The `docker/postgres-init/` directory in the project root contains database initialization scripts
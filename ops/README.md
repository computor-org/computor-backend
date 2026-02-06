# Ops Directory Structure

This directory contains all operational configurations and infrastructure files for the Computor platform.

## Directory Layout

```
ops/
├── docker/                     # Docker Compose configurations
│   ├── docker-compose.base.yaml      # Core shared services
│   ├── docker-compose.dev.yaml       # Development-specific
│   ├── docker-compose.prod.yaml      # Production-specific
│   ├── docker-compose.coder.yaml     # Optional Coder addon
│   ├── docker-compose-dev.yaml.old   # Legacy dev config (deprecated)
│   └── docker-compose-prod.yaml.old  # Legacy prod config (deprecated)
│
├── environments/              # Environment configuration templates
│   ├── .env.common.template   # Shared configuration
│   ├── .env.dev.template      # Development settings
│   ├── .env.prod.template     # Production settings
│   └── .env.coder.template    # Coder addon settings
│
├── scripts/                   # Operational scripts (legacy/utilities)
│   └── startup.sh.old         # Old startup script for reference
│
└── docs/                      # Operational documentation
    └── DOCKER_SETUP.md        # Complete Docker setup guide
```

## Quick Reference

### Starting Services

From the project root directory:

```bash
# Development
./startup.sh dev -d

# Development with Coder
./startup.sh dev --coder -d

# Production
./startup.sh prod -d

# Production with Coder
./startup.sh prod --coder -d
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

If you need to run docker-compose directly:

```bash
# Development
docker-compose -f ops/docker/docker-compose.base.yaml \
               -f ops/docker/docker-compose.dev.yaml \
               up -d

# Development with Coder
docker-compose -f ops/docker/docker-compose.base.yaml \
               -f ops/docker/docker-compose.dev.yaml \
               -f ops/docker/docker-compose.coder.yaml \
               up -d

# View logs
docker-compose -f ops/docker/docker-compose.base.yaml \
               -f ops/docker/docker-compose.dev.yaml \
               logs -f [service-name]
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
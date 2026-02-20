# Docker Compose Setup Guide

## Overview

The Computor platform now uses a modular Docker Compose architecture that separates core services from optional components like Coder workspace management.

## Architecture

### File Structure

```
computor-fullstack/
├── docker-compose.base.yaml      # Core shared services
├── docker-compose.dev.yaml       # Development-specific services
├── docker-compose.prod.yaml      # Production-specific services
├── docker-compose.coder.yaml     # Optional Coder addon
├── .env.common.template          # Shared environment template
├── .env.dev.template             # Development environment template
├── .env.prod.template            # Production environment template
├── .env.coder.template           # Coder environment template
├── setup-env.sh                  # Environment setup script
└── startup.sh                    # Service startup script
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

# Run the setup script to create environment files
./setup-env.sh

# Or for non-interactive setup:
./setup-env.sh --auto
```

### 2. Start Services

#### Development Mode

```bash
./startup.sh dev -d
```

#### Production Mode

```bash
./startup.sh prod -d
```

Coder workspace support is controlled via `CODER_ENABLED=true` in `.env`.

### 3. Stop Services

```bash
# Development
docker-compose -f docker-compose.base.yaml -f docker-compose.dev.yaml down

# Development with Coder
docker-compose -f docker-compose.base.yaml -f docker-compose.dev.yaml -f docker-compose.coder.yaml down

# Production
docker-compose -f docker-compose.base.yaml -f docker-compose.prod.yaml down
```

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

```bash
# Development with specific services
docker-compose \
  -f docker-compose.base.yaml \
  -f docker-compose.dev.yaml \
  up -d postgres redis temporal

# Production with Coder
docker-compose \
  -f docker-compose.base.yaml \
  -f docker-compose.prod.yaml \
  -f docker-compose.coder.yaml \
  up -d

# View logs
docker-compose \
  -f docker-compose.base.yaml \
  -f docker-compose.dev.yaml \
  logs -f temporal-worker
```

### Service URLs

#### Development
- API: http://localhost:8000
- Temporal UI: http://localhost:8088
- MinIO Console: http://localhost:9001
- Traefik Dashboard: http://localhost:8080
- Coder (if enabled): https://coder.localhost:8446

#### Production
- API: http://localhost:8000/api
- Frontend: http://localhost:8080
- Coder (if enabled): https://your-coder-domain:8446

### Database Access

The system uses a single PostgreSQL instance with multiple databases:

- `computor` - Main application database
- `coder` - Coder workspace database (created when Coder is enabled)
- `temporal` - Temporal workflow database (separate instance)

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
   ./startup.sh dev -d
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
2. **Use strong passwords** - the setup script generates secure ones
3. **Restrict MinIO ports** in production (already configured)
4. **Enable HTTPS** for production deployments
5. **Rotate tokens regularly** especially API tokens

## Support

For issues or questions:
1. Check the logs: `docker-compose logs [service-name]`
2. Review configuration: `docker-compose config`
3. Consult the main documentation
4. Open an issue on GitHub
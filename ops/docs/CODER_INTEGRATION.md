# Coder Integration Guide

## Two Deployment Options

The Computor platform supports Coder in two different ways:

### 1. Integrated Coder (Recommended)
**Location**: `ops/docker/docker-compose.coder.yaml`
**Config**: `.env.coder` (in project root)
**Usage**: Set `CODER_ENABLED=true` in `.env`, then `./startup.sh dev -d`

- Runs as part of Computor stack
- Shares PostgreSQL with Computor (uses `coder` database)
- Managed by main startup/stop scripts
- Single Traefik instance for routing
- Configured via `.env.coder` in root

### 2. Standalone Coder
**Location**: `computor-coder/deployment/`
**Config**: `computor-coder/deployment/.env`
**Usage**: `cd computor-coder/deployment && ./install.sh`

- Independent Coder installation
- Own PostgreSQL database
- Separate Docker Compose stack
- Own Traefik instance
- Configured via its own `.env` file

## Configuration Files

### For Integrated Deployment

Create `.env.coder` in project root:
```bash
# From template
cp ops/environments/.env.coder.template .env.coder
# Edit as needed
vim .env.coder
```

Key variables:
- `CODER_DOMAIN` - Your Coder domain
- `CODER_ADMIN_EMAIL` - Admin email
- `CODER_ADMIN_PASSWORD` - Admin password
- Uses shared `POSTGRES_*` from `.env.common`

### For Standalone Deployment

Create `.env` in `computor-coder/deployment/`:
```bash
cd computor-coder/deployment
cp .env.example .env
vim .env
```

Key variables:
- `CODER_DIR` - Installation directory
- `CODER_POSTGRES_*` - Separate database config
- `CODER_PORT` - External port
- All self-contained

## When to Use Which?

### Use Integrated Coder when:
- You want everything managed together
- You're already running Computor
- You want shared resources (PostgreSQL, network)
- You prefer single-point management

### Use Standalone Coder when:
- You want Coder independent of Computor
- You're deploying on a separate server
- You need custom PostgreSQL configuration
- You want to manage Coder separately

## Migration Between Modes

### From Standalone to Integrated:
1. Backup Coder data from standalone PostgreSQL
2. Stop standalone Coder: `cd computor-coder/deployment && ./stop.sh`
3. Setup integrated: `./setup-env.sh` and configure `.env.coder`
4. Set `CODER_ENABLED=true` in `.env` and start: `./startup.sh dev -d`
5. Restore data to shared PostgreSQL `coder` database

### From Integrated to Standalone:
1. Backup Coder data from shared PostgreSQL `coder` database
2. Stop integrated: `./stop.sh dev`
3. Setup standalone: `cd computor-coder/deployment && ./install.sh`
4. Restore data to standalone PostgreSQL

## Environment Variable Mapping

| Standalone `.env` | Integrated `.env.coder` | Notes |
|-------------------|-------------------------|--------|
| `CODER_DIR` | `CODER_DIR` | Same |
| `CODER_DOMAIN` | `CODER_DOMAIN` | Same |
| `CODER_PORT` | `CODER_EXTERNAL_PORT` | Different naming |
| `CODER_POSTGRES_PORT` | Uses `POSTGRES_EXTERNAL_PORT` | Shared DB |
| `CODER_POSTGRES_USER` | Uses `POSTGRES_USER` | Shared DB |
| `CODER_POSTGRES_PASSWORD` | Uses `POSTGRES_PASSWORD` | Shared DB |
| `CODER_ADMIN_EMAIL` | `CODER_ADMIN_EMAIL` | Same |
| `CODER_ADMIN_PASSWORD` | `CODER_ADMIN_PASSWORD` | Same |
| `DOCKER_GID` | `DOCKER_GID` | Same |

## Quick Start

### Integrated Coder (Recommended)
```bash
# Setup environment
./setup-env.sh

# Start Computor with Coder
./startup.sh dev -d

# Access Coder
# https://your-coder-domain:8446
```

### Standalone Coder
```bash
# Navigate to deployment directory
cd computor-coder/deployment

# Configure
cp .env.example .env
vim .env

# Install and start
./install.sh -D coder.example.com -P 8446 \
  -u admin -e admin@example.com -w secretpass

# Access Coder
# https://coder.example.com:8446
```

## Integration with Computor Backend

When Coder is enabled (either mode), the Computor backend can:
- Create Coder users automatically
- Provision workspaces for students
- Manage workspace lifecycles
- Provide SSO integration

The backend uses these environment variables:
- `CODER_ENABLED` - Enable Coder features
- `CODER_URL` - Internal API URL
- `CODER_ADMIN_API_SECRET` - API authentication

## Troubleshooting

### Port Conflicts
If running both modes on the same machine, ensure different ports:
- Integrated uses ports from `.env.coder`
- Standalone uses ports from `computor-coder/deployment/.env`

### Database Issues
- Integrated: Check `coder` database exists in shared PostgreSQL
- Standalone: Check separate PostgreSQL container is running

### Network Issues
- Integrated: All services on `computor-network`
- Standalone: Separate `coder-network`

## Best Practices

1. **Don't mix modes** - Use either integrated OR standalone, not both
2. **Backup before switching** - Always backup Coder data
3. **Check ports** - Avoid conflicts between modes
4. **Use integrated for development** - Easier management
5. **Consider standalone for production** - Better isolation
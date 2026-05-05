# Getting Started with Computor Development

This guide will help you set up your development environment and get the Computor platform running locally.

## Prerequisites

### Required Software

- **Python 3.10+**: Primary backend language
- **Docker & Docker Compose**: For service orchestration
- **Git**: Version control
- **PostgreSQL 16** (via Docker)

### Recommended Tools

- **VS Code** or **PyCharm**: IDE with Python support
- **Postman** or **HTTPie**: API testing
- **pgAdmin** or **DBeaver**: Database management
- **Docker Desktop**: Container management UI

## Initial Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd computor-fullstack
```

### 2. Create Python Virtual Environment

```bash
# Create virtual environment
python3.10 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Linux/Mac
# or
.venv\Scripts\activate  # On Windows
```

### 3. Install Python Packages

Install all packages in **development mode** (editable):

```bash
# Install in order (types first, then client, then CLI, then backend)
pip install -e computor-types/
pip install -e computor-client/
pip install -e computor-cli/
pip install -e computor-backend/
```

**Why development mode?**
- Changes take effect immediately without reinstalling
- You can edit the code and see changes right away
- Ideal for development workflow

### 4. Configure Environment Variables

Create `.env` file in the project root:

```bash
cp .env.dev .env
```

Edit `.env` and configure:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=computor
DB_USER=postgres
DB_PASSWORD=postgres

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Temporal
TEMPORAL_HOST=localhost
TEMPORAL_PORT=7233
TEMPORAL_NAMESPACE=default

# MinIO
MINIO_HOST=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# GitLab (configure your GitLab instance)
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your-gitlab-token
GITLAB_GROUP_ID=your-group-id

# Application
SECRET_KEY=your-secret-key-here
DEBUG=true
LOG_LEVEL=INFO
```

### 5. Start Docker Services

Start the docker-managed infrastructure (Postgres, Redis, Temporal + UI, MinIO, Traefik, workers):

```bash
bash startup.sh dev -d
```

In dev mode the FastAPI server and the Next.js frontend run **locally**, not in containers — only the supporting services live in docker.

Default port mapping (configurable via `.env`):
- PostgreSQL: 5432 (external) → 5437 (internal)
- Redis: 6379
- Temporal Server: 7233
- Temporal UI: 8088
- MinIO: 9000 (API), 9001 (console)
- Traefik: 8080

**Verify services are running**:

```bash
docker ps
```

You should see containers for postgres, redis, temporal, temporal-ui, minio, traefik, and the temporal worker fleet.

### 6. Start the API

```bash
bash api.sh
```

`api.sh` runs Alembic migrations, creates the admin user from `API_ADMIN_USER` / `API_ADMIN_PASSWORD` in `.env`, applies roles, and then starts uvicorn. No separate `migrations.sh` step is needed in the normal flow.

The API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Redoc**: http://localhost:8000/redoc

### 7. Start the Web Frontend

In a separate terminal:

```bash
bash web.sh
```

Frontend will be at http://localhost:3000 (proxies API calls to `:8000`).


## Verification

### Test the API

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Get API version
curl http://localhost:8000/api/v1/version

# Login (get token)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
```

### Test the CLI

```bash
# Check CLI installation
computor --help

# Login
computor login

# List organizations
computor rest organizations list
```

### Access Service UIs

- **API Documentation**: http://localhost:8000/docs
- **Temporal UI**: http://localhost:8088
- **MinIO Console**: http://localhost:9001 (minioadmin / minioadmin)

## Development Workflow

### Starting Your Day

```bash
# Activate virtual environment
source .venv/bin/activate

# Pull latest changes
git pull

# Update dependencies (if requirements changed)
pip install -e computor-backend/ --upgrade

# Start Docker services (if not running)
bash startup.sh dev -d

# Start backend API (runs migrations automatically)
bash api.sh

# In a separate terminal: start the web frontend
bash web.sh
```

### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** in the appropriate package:
   - DTOs: `computor-types/`
   - Backend logic: `src/computor_backend/`
   - CLI: `computor-cli/`
   - Client: `computor-client/`

3. **Run tests**:
   ```bash
   bash test.sh
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: your commit message"
   ```

### Stopping Services

```bash
# Stop backend API
Ctrl+C

# Stop Docker services (auto-detects dev/prod from running containers)
bash stop.sh
# or be explicit:
bash stop.sh dev
```

## Common Setup Issues

### Issue: Port Already in Use

**Problem**: Service fails to start because port is already in use.

**Solution**:
```bash
# Find process using port (e.g., 8000)
lsof -i :8000

# Kill the process
kill -9 <PID>
```

### Issue: Database Connection Failed

**Problem**: Cannot connect to PostgreSQL.

**Solution**:
1. Check Docker container is running: `docker ps | grep postgres`
2. Check environment variables in `.env`
3. Test connection: `psql -h localhost -U postgres -d computor`

### Issue: Alembic Migration Fails

**Problem**: Migration fails with "table already exists" or similar error.

**Solution**:
```bash
# Drop all tables and start fresh (development only!)
# stop.sh intentionally disables -v; remove the postgres data dir manually instead.
bash stop.sh
sudo rm -rf "${SYSTEM_DEPLOYMENT_PATH}/postgres"
bash startup.sh dev -d
bash migrations.sh
```

### Issue: Import Errors

**Problem**: Python cannot find `computor_types`, `computor_client`, etc.

**Solution**:
```bash
# Reinstall packages in development mode
pip install -e computor-types/
pip install -e computor-client/
pip install -e computor-cli/
pip install -e computor-backend/
```

### Issue: Temporal Worker Not Connecting

**Problem**: Temporal workflows fail with connection error.

**Solution**:
1. Check Temporal server is running: `docker ps | grep temporal`
2. Check `TEMPORAL_HOST` and `TEMPORAL_PORT` in `.env`
3. View Temporal UI: http://localhost:8088

### Issue: GitLab Integration Fails

**Problem**: GitLab operations fail with authentication error.

**Solution**:
1. Verify `GITLAB_TOKEN` has correct permissions:
   - `api` scope
   - Maintainer/Owner role in the group
2. Check `GITLAB_URL` format (no trailing slash)
3. Test token: `curl -H "PRIVATE-TOKEN: your-token" https://gitlab.com/api/v4/user`

## IDE Setup

### VS Code

**Recommended Extensions**:
- Python
- Pylance
- Python Test Explorer
- Docker
- GitLens
- REST Client

**Settings** (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "computor-backend/src/computor_backend/tests"
  ],
  "editor.rulers": [120],
  "editor.formatOnSave": true
}
```

### PyCharm

1. **Set Python Interpreter**: Settings → Project → Python Interpreter → Select `.venv/bin/python`
2. **Mark Source Roots**: Right-click on `computor-backend/src` → Mark Directory as → Sources Root
3. **Configure pytest**: Settings → Tools → Python Integrated Tools → Default test runner → pytest
4. **Enable Docker**: Settings → Build, Execution, Deployment → Docker → Add Docker daemon

## Next Steps

Now that your environment is set up:

1. Read [Code Organization](02-code-organization.md) to understand the codebase structure
2. Review [Development Workflow](03-development-workflow.md) for daily practices
3. Explore [Backend Architecture](04-backend-architecture.md) to understand the system design
4. Try making a simple change and running tests

## Useful Commands Reference

```bash
# Backend
bash api.sh              # Start API server (runs migrations automatically)
bash web.sh              # Start Next.js dev server (dev only)
bash migrations.sh       # Run migrations standalone (rarely needed)
bash test.sh             # Run tests

# Code Generation
bash generate.sh types          # Generate TypeScript types
bash generate.sh python-client  # Generate Python client
bash generate.sh schema         # Generate OpenAPI schema

# Docker stack
bash startup.sh dev -d   # Dev: docker services only (API/web run locally)
bash startup.sh prod -d  # Prod: everything in docker (API + web + workers)
bash stop.sh             # Stop services (auto-detects env)
docker ps                # List running containers
docker logs <container>  # View container logs

# Database
alembic revision --autogenerate -m "message"  # Create migration
alembic upgrade head                          # Apply migrations
alembic downgrade -1                          # Rollback one migration

# CLI
computor --help         # Show CLI help
computor login          # Login to API
computor worker start   # Start Temporal worker
```

---

**Next**: [Code Organization →](02-code-organization.md)

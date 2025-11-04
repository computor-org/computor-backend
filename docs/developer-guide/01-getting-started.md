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

Start all required infrastructure services:

```bash
bash startup.sh
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Temporal Server (port 7233)
- Temporal UI (port 8088)
- MinIO (port 9000, console 9001)

**Verify services are running**:

```bash
docker ps
```

You should see containers for postgres, redis, temporal, and minio.

### 6. Run Database Migrations

Create the database schema:

```bash
bash migrations.sh
```

This runs Alembic migrations to create all tables.

### 7. Initialize System

Create the admin user and seed base data:

```bash
bash initialize_system.sh
```

This creates:
- Admin user with credentials from `.env`
- Base roles and permissions
- Default course content types
- Sample data (if seeder is run)

**Optional: Seed development data**:

```bash
cd computor-backend/src
python seeder.py
cd ../..
```

### 8. Start the Backend API

```bash
bash api.sh
```

The API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Redoc**: http://localhost:8000/redoc


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
bash startup.sh

# Run migrations (if new migrations exist)
bash migrations.sh

# Start backend API
bash api.sh
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

# Stop Docker services
bash stop.sh
# or
docker-compose -f docker-compose-dev.yaml down
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
docker-compose -f docker-compose-dev.yaml down -v
bash startup.sh
bash migrations.sh
bash initialize_system.sh
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
bash api.sh              # Start API server
bash migrations.sh       # Run migrations
bash test.sh            # Run tests

# Code Generation
bash generate.sh types      # Generate TypeScript types
bash generate.sh python-client    # Generate Python client
bash generate.sh schema     # Generate OpenAPI schema

# Docker
bash startup.sh         # Start all services
bash stop.sh            # Stop all services
docker ps               # List running containers
docker logs <container> # View container logs

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

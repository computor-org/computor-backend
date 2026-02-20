# Computor

A university programming course management platform with automated GitLab integration for repository and group management.

## Packages

| Package | Description |
|---------|-------------|
| `computor-types` | Pydantic DTOs - shared data structures for API contracts |
| `computor-client` | Auto-generated async HTTP client library |
| `computor-cli` | Command-line interface for admin and dev tasks |
| `computor-backend` | FastAPI server with business logic and Temporal workflows |
| `computor-utils` | Shared utility functions |

## Prerequisites

- Docker & Docker Compose
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
bash startup.sh dev -d

# Start the API (runs migrations + creates admin user automatically)
bash api.sh
```

The API will be available at http://localhost:8000/docs

### Production Mode

No local Python installation required — everything runs in Docker containers.

```bash
# Clone and configure
git clone <repository-url> <dir-name>
cd <dir-name>
cp .env.common .env  # Then edit .env with your production configuration

# Start all services (builds Docker images, runs migrations, starts API)
bash startup.sh prod --build -d

# With Coder workspace support
bash startup.sh prod --coder --build -d
```

### startup.sh

```
Usage: ./startup.sh [dev|prod] [--coder] [docker-compose-options]

  dev              Development services only (default)
  prod             Production services (includes API server)
  --coder          Enable Coder workspace integration
  -d               Run in detached mode
  --build          Rebuild Docker images before starting

Examples:
  ./startup.sh dev -d              # Dev services, detached
  ./startup.sh dev --coder -d      # Dev services + Coder, detached
  ./startup.sh prod                # Production (foreground)
  ./startup.sh prod --coder        # Production + Coder
  ./startup.sh prod --build -d     # Rebuild images and start detached
```

### api.sh (development)

```
Usage: ./api.sh [OPTIONS]

  --no-migrations     Skip running Alembic migrations before starting
  --verbose, -v       Show WebSocket connection logs + HTTP requests
  --debug, -d         Show all debug logs (very verbose)
  --quiet, -q         Show only errors (hides HTTP requests too)
```

## Documentation

- [Architecture Overview](docs/architecture-overview.md)
- [Developer Guidelines](docs/developer-guideline.md)

## License

MIT

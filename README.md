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
| `computor-utils` | Shared utility functions |

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
bash startup.sh dev -d

# Start the API server (runs migrations + creates admin user automatically)
bash api.sh

# Start the web frontend (separate terminal)
bash web.sh

# Tip: Run without -d to see Docker service logs (useful for debugging).
# This requires additional terminals for api.sh and web.sh:
#   Terminal 1: bash startup.sh dev
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
bash startup.sh prod --build -d

# To enable Coder workspace support, set CODER_ENABLED=true in .env
```

### startup.sh

```
Usage: ./startup.sh [dev|prod] [docker-compose-options]

  dev              Development services only (default)
  prod             Production services (includes API server)
  -d               Run in detached mode
  --build          Rebuild Docker images before starting

Coder workspace support is controlled via CODER_ENABLED=true in .env.

Examples:
  ./startup.sh dev -d              # Dev services, detached
  ./startup.sh prod                # Production (foreground)
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

- [Architecture Overview](docs/architecture-overview.md)
- [Developer Guidelines](docs/developer-guideline.md)

## License

MIT

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

- Python 3.10
- Docker & Docker Compose
- Git

## Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd computor-fullstack

# Create virtual environment
python3.10 -m venv .venv
source .venv/bin/activate

# Install packages
pip install -e computor-types/
pip install -e computor-client/
pip install -e computor-cli/
pip install -e computor-utils/
pip install -e computor-backend/

# Start Docker services (PostgreSQL, Redis, Temporal, MinIO)
bash startup.sh -d

# Run database migrations
bash migrations.sh

# Initialize admin user
bash initialize_system.sh

# Start the API server
bash api.sh
```

The API will be available at http://localhost:8000/docs

## Documentation

- [Architecture Overview](docs/architecture-overview.md)
- [Developer Guidelines](docs/developer-guideline.md)

## License

MIT

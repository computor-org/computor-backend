# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Computor Full-Stack project.

## Project Overview

Computor is a university programming course management platform with automated GitLab integration for repository and group management.

### Tech Stack
- **Backend**: Python/FastAPI with SQLAlchemy ORM and Pydantic DTOs
- **Database**: PostgreSQL 16 with Alembic migrations
- **Task Orchestration**: Temporal.io for asynchronous workflows
- **Storage**: MinIO (S3-compatible object storage)
- **Caching**: Redis (implementation in progress)
- **Authentication**: Built-in local authentication with plugin support for SSO providers
- **Infrastructure**: Docker Compose orchestration

## Architecture

### Backend Structure (`/src/computor_backend/`)

#### Core Components

1. **Model Layer** (`model/`)
   - SQLAlchemy ORM models defining database schema
   - Single source of truth for data structure
   - Alembic migrations generated from model changes
   - Key entities: Organization, CourseFamilies, Courses, Users, Roles

2. **API Layer** (`api/`)
   - Thin FastAPI endpoints organized by resource
   - RESTful design with consistent patterns
   - Permission-based access control
   - Delegates to business logic layer

3. **Business Logic Layer** (`business_logic/`)
   - Fat business logic functions with explicit parameters
   - Reusable, testable, and cacheable
   - Orchestrates data access via repositories
   - Contains core application logic

4. **Repository Layer** (`repositories/`)
   - Data access abstraction layer
   - Gathers data from multiple sources: PostgreSQL database, MinIO object storage, Redis cache, filesystem
   - Encapsulates complex queries and data operations
   - Provides clean interface for business logic to access data

5. **Temporal Tasks** (`tasks/`) **[HOT AREA - ACTIVE DEVELOPMENT]**
   - Asynchronous workflow orchestration
   - GitLab API integration for group/repository creation
   - Key workflows:
     - `temporal_hierarchy_management.py` - Organization/Course hierarchy creation
     - `temporal_student_template_v2.py` - Student template repository generation
     - `temporal_examples.py` - Example deployment workflows
     - `temporal_student_testing.py` - Student submission testing
   - Worker management via CLI commands

#### Service Components

- **server.py** - FastAPI app initialization and endpoint registration
- **database.py** - SQLAlchemy session management
- **minio_client.py** - MinIO object storage client
- **redis_cache.py** - Redis caching (minimal usage, future expansion planned)
- **gitlab_utils.py** - GitLab API utilities
- **settings.py** - Configuration management


## Development Commands

### Backend Setup
```bash
# Environment setup
python3.10 -m venv .venv
source .venv/bin/activate
pip install -e computor-backend/

# Database migrations
bash migrations.sh                    # Run migrations
alembic revision --autogenerate -m "description"  # Generate migration
alembic upgrade head                  # Apply migrations

# Seed development data (optional)
cd src && python seeder.py

# Install CLI
pip install -e src
```

### Backend Services
```bash
# Start services
bash startup.sh              # Start all Docker services
bash api.sh                  # Start FastAPI only (development)

# Docker Compose
docker-compose -f docker-compose-dev.yaml up -d   # Development environment
docker-compose -f docker-compose-prod.yaml up -d  # Production environment

# Temporal workers
ctutor worker start                               # Start Temporal worker
ctutor worker start --queues=computor-tasks      # Specific queue
ctutor worker status                              # Check worker status
python -m computor_backend.tasks.temporal_worker   # Direct worker start

# Temporal UI
# Access at http://localhost:8088 when Docker services are running
```

### Code Generation
```bash
# Unified generator (recommended)
bash generate.sh                       # Generate all artifacts
bash generate.sh types                 # Generate TypeScript interfaces
bash generate.sh clients               # Generate TypeScript clients
bash generate.sh python-client         # Generate Python client
bash generate.sh validators            # Generate TypeScript validators
bash generate.sh schema                # Generate JSON schema
bash generate.sh error-codes           # Generate error code definitions
bash generate.sh types --watch         # Watch mode for types

# Or via CLI:
computor generate-types                # Via CLI
computor generate-types --watch        # Watch mode

```

## Current Implementation Status

### ✅ Completed Features
- SQLAlchemy models and Alembic migrations
- Pydantic DTOs with EntityInterface pattern
- FastAPI REST endpoints
- Temporal workflow framework
- GitLab API integration for group/repo creation
- Built-in local authentication with Bearer tokens
- Plugin-based authentication system
- MinIO object storage
- TypeScript interface generation
- Python client auto-generation

### 🚧 In Progress
- GitLab repository content initialization
- Student template generation workflows
- Comprehensive Redis caching strategy

### 📋 Planned
- Additional SSO provider plugins (Keycloak, GitLab, etc.)
- Advanced course content management
- Student submission testing workflows
- Performance monitoring and metrics

## Key Workflows

### GitLab Integration Flow
1. Organization created → GitLab group created
2. Course Family created → Subgroup under organization
3. Course created → Subgroup under course family with:
   - Students subgroup
   - Assignments repositories
   - Student template repository
   - Reference repository

### Temporal Workflow Pattern
```python
# Workflows are defined in tasks/temporal_*.py
# Executed asynchronously via Temporal server
# Monitored through Temporal UI
# Triggered via API endpoints or CLI
```

## Testing
```bash
bash test.sh                          # Run all tests
bash test.sh --unit                   # Unit tests only
bash test.sh --integration            # Integration tests only
pytest src/computor_backend/tests/      # Direct pytest

# Key test files:
# - test_temporal_workflows.py         # Temporal workflow tests
# - test_gitlab_builder_*.py           # GitLab integration tests
# - test_models.py                     # SQLAlchemy model tests
# - test_api_endpoints.py              # API endpoint tests
```

## Configuration

### Environment Variables
- Database: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- Redis: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
- Temporal: `TEMPORAL_HOST`, `TEMPORAL_PORT`, `TEMPORAL_NAMESPACE`
- MinIO: `MINIO_HOST`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
- GitLab: `GITLAB_URL`, `GITLAB_TOKEN` (URL can be domain name like "https://gitlab.com" or with port like "http://localhost:8080")

### Service URLs (Development)
- FastAPI: http://localhost:8000
- Temporal UI: http://localhost:8088
- MinIO Console: http://localhost:9001

## Development Principles

### Code Organization
- **Models** define database structure (single source of truth)
- **Interfaces** define API contracts (DTOs)
- **API** implements business logic using Models and Interfaces
- **Tasks** handle asynchronous operations via Temporal

### Best Practices
- Test-driven development where practical
- Clear separation of concerns
- Type safety with Pydantic and TypeScript
- Async operations via Temporal workflows
- Consistent error handling and logging

### Git Workflow
- Feature branches from `main`
- Clear, descriptive commit messages
- PR reviews before merging
- No direct commits to `main`

## Important Notes

- Temporal workers must be running for async operations
- GitLab token must have appropriate permissions for group/repo creation
- GitLab URL can be with or without port (e.g., "https://gitlab.com" or "http://localhost:8080")
- Redis is configured but not heavily utilized yet
- Database migrations should only be generated from model changes
- Authentication uses built-in local auth by default; SSO providers available as plugins

## Troubleshooting

### Common Issues
1. **Temporal worker not connecting**: Check TEMPORAL_HOST and ensure Temporal server is running
2. **GitLab operations failing**: Verify GitLab token permissions and URL configuration (URL can be domain or with port)
3. **Database migrations failing**: Ensure database is running and credentials are correct

Note: Some documentation may be outdated. This CLAUDE.md file represents the current system state.
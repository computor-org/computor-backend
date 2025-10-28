# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Computor Full-Stack project.

## Project Overview

Computor is a university programming course management platform with automated GitLab integration for repository and group management.

### Tech Stack
- **Backend**: Python/FastAPI with SQLAlchemy ORM and Pydantic DTOs
- **Frontend**: React 19 + TypeScript with Material-UI
- **Database**: PostgreSQL 16 with Alembic migrations
- **Task Orchestration**: Temporal.io for asynchronous workflows
- **Storage**: MinIO (S3-compatible object storage)
- **Caching**: Redis (implementation in progress)
- **Authentication**: Keycloak SSO with OpenID Connect
- **Infrastructure**: Docker Compose orchestration

## Architecture

### Backend Structure (`/src/computor_backend/`)

#### Core Components

1. **Model Layer** (`model/`)
   - SQLAlchemy ORM models defining database schema
   - Single source of truth for data structure
   - Alembic migrations generated from model changes
   - Key entities: Organization, CourseFamilies, Courses, Users, Roles

2. **Interface Layer** (`interface/`)
   - Pydantic DTOs for request/response validation
   - EntityInterface base classes for consistent DTO patterns
   - Type-safe data transfer objects
   - Automatic TypeScript generation support

3. **API Layer** (`api/`)
   - FastAPI endpoints organized by resource
   - RESTful design with consistent patterns
   - Permission-based access control
   - Endpoints work with Interface DTOs and Model entities

4. **Temporal Tasks** (`tasks/`) **[HOT AREA - ACTIVE DEVELOPMENT]**
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

### Frontend Structure (`/frontend/`)

- **React 19 + TypeScript** application
- **Material-UI** component library
- **Pages**: Organizations, CourseFamilies, Courses, Users, Tasks
- **Services**: API client, authentication (SSO + basic auth)
- **Generated Types**: Auto-generated from backend Pydantic models

## Development Commands

### Backend Setup
```bash
# Environment setup
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r src/requirements.txt

# Database migrations
bash migrations.sh                    # Run migrations
alembic revision --autogenerate -m "description"  # Generate migration
alembic upgrade head                  # Apply migrations

# Initialize system
bash initialize_system.sh            # Create admin user and base data
cd src && python seeder.py           # Seed development data

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

### Frontend Development

#### Legacy Frontend (React + Material-UI)
```bash
bash frontend.sh             # Start development server
# Or directly:
cd frontend
yarn install                 # Install dependencies
yarn start                   # Development server
yarn build                   # Production build
yarn test                    # Run tests
```

#### New Frontend (Next.js 15 + GitLab UI)
```bash
bash frontend-next.sh        # Start development server
# Or directly:
cd frontend-next
npm install                  # Install dependencies
npm run dev                  # Development server (with Turbopack)
npm run build                # Production build
npm start                    # Production server
```

### TypeScript Generation
```bash
bash generate_types.sh                # Generate TypeScript interfaces
ctutor generate-types                  # Via CLI
ctutor generate-types --watch          # Watch mode
```

## Current Implementation Status

### ✅ Completed Features
- SQLAlchemy models and Alembic migrations
- Pydantic DTOs with EntityInterface pattern
- FastAPI REST endpoints
- Temporal workflow framework
- GitLab API integration for group/repo creation
- Keycloak SSO authentication
- MinIO object storage
- TypeScript interface generation
- Basic frontend with React + Material-UI

### 🚧 In Progress
- GitLab repository content initialization
- Student template generation workflows
- Comprehensive Redis caching strategy

### 📋 Planned
- Advanced course content management
- Student submission testing workflows
- Performance monitoring and metrics
- Enhanced frontend features

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
- GitLab: `GITLAB_URL`, `GITLAB_TOKEN`
- Keycloak: `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`

### Service URLs (Development)
- FastAPI: http://localhost:8000
- Frontend (Legacy): http://localhost:3000 - React + Material-UI
- Frontend (New): http://localhost:3000 - Next.js 15 + GitLab UI
- Temporal UI: http://localhost:8088
- MinIO Console: http://localhost:9001
- Keycloak: http://localhost:8080

**Note**: Both frontends run on port 3000 - run only one at a time, or configure different ports.

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
- Redis is configured but not heavily utilized yet
- Frontend is functional but under active development
- Database migrations should only be generated from model changes

## Troubleshooting

### Common Issues
1. **Temporal worker not connecting**: Check TEMPORAL_HOST and ensure Temporal server is running
2. **GitLab operations failing**: Verify GitLab token permissions and URL configuration
3. **Database migrations failing**: Ensure database is running and credentials are correct
4. **Frontend type errors**: Regenerate TypeScript interfaces with `bash generate_types.sh`

Note: Some documentation may be outdated. This CLAUDE.md file represents the current system state.
- and what if the url has no port because it is a domain name like "https://gitlab.com"? is this also possible?
# Computor Developer Guidelines

**Welcome to the Computor Full-Stack Development Guide!**

This guide provides comprehensive documentation for developers working on the Computor university programming course management platform. The documentation is organized into focused sections for easy reference.

## Quick Start

1. Read the [Architecture Overview](architecture-overview.md) to understand the system structure
2. Set up your development environment using [Getting Started](developer-guide/01-getting-started.md)
3. Review [Code Organization](developer-guide/02-code-organization.md) to understand the codebase layout
4. Familiarize yourself with [Development Workflow](developer-guide/03-development-workflow.md)

## Documentation Structure

### Essential Reading

- **[Getting Started](developer-guide/01-getting-started.md)** - Environment setup, installation, and first steps
- **[Code Organization](developer-guide/02-code-organization.md)** - Directory structure, modules, and package layout
- **[Development Workflow](developer-guide/03-development-workflow.md)** - Daily development practices, git workflow, and testing

### Core Concepts

- **[Backend Architecture](developer-guide/04-backend-architecture.md)** - API layer, business logic, models, and services
- **[EntityInterface Pattern](developer-guide/05-entityinterface-pattern.md)** - DTO pattern and code generation
- **[Permission System](developer-guide/06-permission-system.md)** - RBAC, roles, claims, and access control
- **[Database & Migrations](developer-guide/07-database-migrations.md)** - SQLAlchemy models, Alembic, and schema management

### Advanced Topics

- **[Temporal Workflows](developer-guide/08-temporal-workflows.md)** - Async task orchestration and GitLab integration

## Key Principles

### 1. Separation of Concerns

Computor uses a layered architecture with clear boundaries:

- **computor-types**: Pure Pydantic DTOs (no dependencies)
- **computor-testing**: Test execution framework (depends on types)
- **computor-client**: HTTP client (depends on types only)
- **computor-utils**: Shared utilities (depends on types only)
- **computor-cli**: Command-line interface (depends on client and types)
- **computor-backend**: FastAPI server (depends on types, utils; uses all layers)
- **computor-web**: Next.js frontend (consumes generated TypeScript types/clients)

### 2. Business Logic Separation

**Always delegate to business logic layer:**

```python
# ❌ Bad: Logic in API endpoint
@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str, db: Session = Depends(get_db)):
    artifact = db.query(SubmissionArtifact).filter_by(id=artifact_id).first()
    if not artifact:
        raise NotFoundException()
    return artifact

# ✅ Good: Thin endpoint, fat business logic
@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    return get_artifact_with_details(artifact_id, permissions, db)
```

**Benefits**: Testability, reusability, caching, and clean separation.

### 3. Permission-First Design

**Every endpoint must check permissions:**

```python
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.core import check_course_permissions

@router.get("/courses/{course_id}")
async def get_course(
    course_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    course = db.query(Course).filter_by(id=course_id).first()
    if not course:
        raise NotFoundException()

    # Check permissions
    check_course_permissions(permissions, course, "read")

    return course
```

### 4. Type Safety Everywhere

- Use Pydantic models for all API contracts
- Generate TypeScript interfaces from Pydantic models
- Leverage type hints in Python code
- Use SQLAlchemy models with proper type annotations

### 5. Test-Driven Development

- Write tests for business logic functions
- Use pytest for all testing
- Maintain separation between unit and integration tests
- Mock external services in tests

## Code Style & Conventions

### Python

- **PEP 8** compliant with 120-character line limit
- **Type hints** for all function signatures
- **Docstrings** for public functions and classes
- **Import order**: stdlib, third-party, local (separated by blank lines)

```python
"""Module docstring."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_types.users import UserGet, UserCreate
```

### Naming Conventions

- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: `_leading_underscore`
- **DTOs**: Suffix with action (`UserCreate`, `UserGet`, `UserList`, `UserUpdate`)
- **Interfaces**: Suffix with `Interface` (`UserInterface`)

### API Endpoints

- **RESTful routes**: `/{resource}`
- **ID parameters**: Use UUID strings
- **Query parameters**: Use Pydantic models
- **Response models**: Always specify `response_model`

### Git Commit Messages

```
<type>: <subject>
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `update`

**Example**:
```
feat: add artifact grading endpoint
```

## Project Structure Overview

```
computor-fullstack/
├── computor-types/           # 📦 Pure Pydantic DTOs (shared data contracts)
│   └── src/computor_types/
│       ├── base.py          # EntityInterface base class
│       ├── testing.py       # test.yaml models (ComputorTestSuite)
│       ├── testing_report.py # testSummary.json models (ComputorReport)
│       ├── codeability_meta.py # meta.yaml models (CodeAbilityMeta)
│       ├── deployments_refactored.py # Deployment configs
│       ├── gitlab.py        # GitLab configs
│       ├── users.py         # User DTOs
│       ├── courses.py       # Course DTOs
│       └── ...
│
├── computor-testing/         # 📦 Test execution framework
│   ├── ctcore/              # Core framework, model re-exports
│   ├── ctbackends/          # Language backends (Python, Octave, R, Julia, C, Fortran, Document)
│   └── ...
│
├── computor-client/          # 📦 Auto-generated Python HTTP client
│   └── src/computor_client/
│       ├── client.py        # ComputorClient main class
│       ├── endpoints/       # Generated endpoint clients
│       └── exceptions.py
│
├── computor-cli/             # 📦 Command-line interface
│   └── src/computor_cli/
│       ├── main.py          # CLI entry point
│       ├── commands/        # CLI command groups
│       └── config.py
│
├── computor-backend/         # 📦 FastAPI backend server
│   └── src/computor_backend/
│       ├── api/              # Thin API endpoints
│       ├── business_logic/   # Fat business logic layer
│       ├── model/            # SQLAlchemy ORM models
│       ├── repositories/     # Data access layer
│       ├── permissions/      # RBAC and access control
│       ├── tasks/            # Temporal workflows
│       ├── services/         # Infrastructure services
│       ├── auth/             # Auth providers (Keycloak, etc.)
│       ├── plugins/          # Authentication plugins
│       ├── coder/            # Coder workspace integration
│       ├── generator/        # Code generation (TS types, clients)
│       ├── exceptions/       # Structured error handling
│       ├── middleware/       # FastAPI middleware
│       ├── database.py       # DB session management
│       ├── settings.py       # Configuration
│       └── server.py         # FastAPI app
│
├── computor-utils/           # 📦 Shared Python utilities
│   └── src/computor_utils/
│       ├── vsix_utils.py    # VSIX metadata parsing
│       └── deployment_mapping/
│
├── computor-web/             # 📦 Next.js web frontend
│   └── src/
│       ├── api/             # API client layer
│       ├── components/      # React components
│       ├── generated/       # Auto-generated TS types/clients
│       └── ...
│
├── computor-coder/           # Coder workspace deployment
│   └── deployment/
│       └── templates/       # Terraform templates
│
├── data/                     # Configuration data (auth plugins)
├── docker/                   # Dockerfiles
├── docs/                     # Documentation
├── ops/                      # Operations & Docker Compose configs
├── plugins/                  # Authentication plugins
├── scripts/                  # Utility scripts and git hooks
└── tests/                    # Integration / end-to-end tests
```

## Development Environment

### Required Services

- **PostgreSQL 16**: Database
- **Redis**: Caching and session storage
- **Temporal**: Workflow orchestration
- **MinIO**: S3-compatible object storage

### Quick Setup

See [README.md](../README.md) for installation and setup instructions.

### Service URLs

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Temporal UI**: http://localhost:8088
- **MinIO Console**: http://localhost:9001
- **Redis**: localhost:6379

## Common Tasks

### Adding a New Entity

1. Create DTOs in `computor-types/src/computor_types/your_entity.py`
2. Create SQLAlchemy model in `computor-backend/src/computor_backend/model/your_entity.py`
3. Generate migration: `alembic revision --autogenerate -m "add your_entity"`
4. Apply migration: `alembic upgrade head`
5. Regenerate artifacts: `bash generate.sh all` (types, schemas, clients)

### Creating an API Endpoint

1. Implement business logic in `business_logic/`
2. Create thin endpoint in `api/`
3. Register endpoint in router
4. Add permission checks
5. Write tests

## Getting Help

### Documentation

- **Architecture**: [architecture-overview.md](architecture-overview.md)
- **CLAUDE.md**: High-level project overview
- **API Docs**: http://localhost:8000/docs (when server is running)

### Code Reference

- **Example endpoints**: `computor-backend/src/computor_backend/api/submissions.py`
- **Example business logic**: `computor-backend/src/computor_backend/business_logic/submissions.py`
- **Example model**: `computor-backend/src/computor_backend/model/artifact.py`
- **Example tests**: `computor-backend/src/computor_backend/tests/`

### Common Issues

See the [CLAUDE.md](../CLAUDE.md) Troubleshooting section for solutions to common problems.

## Contributing

1. Create a feature branch from `main`
2. Make your changes following the code style
3. Write/update tests
4. Update documentation if needed
5. Create a pull request
6. Ensure CI passes
7. Request code review

## Next Steps

Choose your path:

- **Backend Developer**: Start with [Backend Architecture](developer-guide/04-backend-architecture.md)
- **Architecture**: Start with [Architecture Overview](architecture-overview.md)

---

**Last Updated**: 2026-03-04
**Maintainers**: Computor Development Team

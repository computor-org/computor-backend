# Code Organization

This guide explains the directory structure and organization of the Computor codebase.

## Monorepo Structure

Computor is organized as a **monorepo with 4 independent Python packages**:

```
computor-fullstack/
├── computor-types/          # Package 1: Pure Pydantic DTOs
├── computor-client/         # Package 2: Auto-generated HTTP client
├── computor-cli/            # Package 3: Command-line interface
├── src/computor_backend/    # Package 4: FastAPI server
├── docs/                    # Documentation
├── docker/                  # Docker configurations
├── scripts/                 # Utility scripts
└── *.sh                     # Shell scripts for development
```

## Package 1: computor-types

**Location**: `computor-types/src/computor_types/`

**Purpose**: Single source of truth for data structures (DTOs).

```
computor-types/
├── pyproject.toml           # Package metadata
├── setup.py
└── src/
    └── computor_types/
        ├── __init__.py      # Package exports, get_all_dtos()
        ├── base.py          # EntityInterface, BaseEntityGet, BaseEntityList
        ├── users.py         # User DTOs
        ├── organizations.py # Organization DTOs
        ├── courses.py       # Course DTOs
        ├── submissions.py   # Submission DTOs
        ├── artifacts.py     # Artifact DTOs
        ├── results.py       # Result DTOs
        └── ...              # 58 total files
```

### Key Files

- **`base.py`**: `EntityInterface` abstract class, base DTO models
- **`__init__.py`**: `get_all_dtos()` function for discovery
- **Each `*.py`**: Entity-specific DTOs following naming convention:
  - `{Entity}Interface`: EntityInterface subclass
  - `{Entity}Create`: Create DTO
  - `{Entity}Get`: Single entity response DTO
  - `{Entity}List`: List item DTO
  - `{Entity}Update`: Update DTO
  - `{Entity}Query`: Query parameters DTO

### Example: users.py

```python
from computor_types.base import EntityInterface, BaseEntityGet, BaseEntityList
from pydantic import BaseModel, EmailStr

class UserInterface(EntityInterface):
    """User entity interface."""
    create = "UserCreate"
    get = "UserGet"
    list = "UserList"
    update = "UserUpdate"
    query = "UserQuery"

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str

class UserGet(BaseEntityGet):
    id: str
    username: str
    email: EmailStr
    full_name: str
    is_active: bool

class UserList(BaseEntityList):
    id: str
    username: str
    email: EmailStr
    full_name: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None

class UserQuery(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
```

### Dependencies

```toml
dependencies = [
    "pydantic>=2.0",
    "email-validator>=2.0",
]
```

**Zero backend dependencies** - pure data structures only.

## Package 2: computor-client

**Location**: `computor-client/src/computor_client/`

**Purpose**: Type-safe Python HTTP client for the Computor API.

```
computor-client/
├── pyproject.toml
└── src/
    └── computor_client/
        ├── __init__.py          # Package exports
        ├── client.py            # ComputorClient main class
        ├── base_endpoint.py     # BaseEndpointClient (CRUD)
        ├── exceptions.py        # HTTP exceptions
        └── endpoints/           # Generated endpoint clients
            ├── __init__.py
            ├── users.py         # UsersEndpoint
            ├── organizations.py # OrganizationsEndpoint
            ├── courses.py       # CoursesEndpoint
            └── ...              # 25 total endpoint clients
```

### Key Files

- **`client.py`**: Main `ComputorClient` aggregator class
- **`base_endpoint.py`**: Generic CRUD operations
- **`endpoints/*.py`**: Auto-generated endpoint clients (one per entity)
- **`exceptions.py`**: HTTP status code exceptions

### Usage Example

```python
from computor_client import ComputorClient

async with ComputorClient(base_url="http://localhost:8000") as client:
    # Authenticate
    await client.authenticate(username="admin", password="secret")

    # CRUD operations
    orgs = await client.organizations.list()
    user = await client.users.get("user-id")
    course = await client.courses.create(course_dto)
    await client.users.update("user-id", update_dto)
```

### Dependencies

```toml
dependencies = [
    "computor-types>=0.1.0",
    "httpx>=0.27.0",
    "pydantic>=2.0",
]
```

## Package 3: computor-cli

**Location**: `computor-cli/src/computor_cli/`

**Purpose**: Command-line interface for API operations and administrative tasks.

```
computor-cli/
├── pyproject.toml
└── src/
    └── computor_cli/
        ├── __init__.py
        ├── main.py              # CLI entry point (Click)
        ├── config.py            # Configuration management
        ├── commands/            # Command groups
        │   ├── __init__.py
        │   ├── login.py         # login command
        │   ├── rest.py          # rest command (CRUD)
        │   ├── admin.py         # admin command
        │   ├── worker.py        # worker command
        │   └── generate.py      # generate-* commands
        └── utils/
            ├── auth.py          # Auth helpers
            └── output.py        # Output formatters
```

### Key Commands

```bash
computor login                  # Authenticate with API
computor profiles               # Manage auth profiles
computor rest {entity} {action} # CRUD operations
computor admin                  # Administrative commands
computor worker start           # Start Temporal worker
computor generate-types         # Generate TypeScript types
computor generate-clients       # Generate TypeScript client
computor generate-schema        # Generate OpenAPI schema
computor generate-validators    # Generate validators
```

### Configuration

Stored in `~/.computor/`:
- `config.yaml`: CLI configuration
- `profiles.yaml`: Authentication profiles

### Dependencies

```toml
dependencies = [
    "computor-types>=0.1.0",
    "computor-client>=0.1.0",
    "click>=8.0",
    "pydantic>=2.0",
    "httpx>=0.27.0",
    "pyyaml>=6.0",
]
```

## Package 4: computor-backend

**Location**: `src/computor_backend/`

**Purpose**: FastAPI server providing REST API and business logic.

```
src/
├── computor_backend/
│   ├── __init__.py
│   ├── server.py            # FastAPI app initialization
│   ├── database.py          # SQLAlchemy session management
│   ├── settings.py          # Configuration (from env vars)
│   ├── redis_cache.py       # Redis client
│   │
│   ├── api/                 # 🔵 API Layer (thin endpoints)
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── organizations.py
│   │   ├── courses.py
│   │   ├── submissions.py
│   │   ├── auth.py
│   │   └── ...              # 30+ API modules
│   │
│   ├── business_logic/      # 🟢 Business Logic Layer (fat logic)
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── organizations.py
│   │   ├── courses.py
│   │   ├── submissions.py
│   │   ├── crud.py          # Generic CRUD operations
│   │   └── ...              # 20+ business logic modules
│   │
│   ├── model/               # 🔴 Model Layer (SQLAlchemy ORM)
│   │   ├── __init__.py
│   │   ├── base.py          # Base model class
│   │   ├── auth.py          # User, Account, Profile, Session
│   │   ├── organization.py  # Organization
│   │   ├── course.py        # Course, CourseFamily, CourseMember
│   │   ├── artifact.py      # SubmissionArtifact, SubmissionGrade
│   │   ├── result.py        # Result, TestCase
│   │   ├── deployment.py    # Deployment
│   │   └── ...              # 15+ model modules
│   │
│   ├── repositories/        # 🟡 Repository Layer (data access)
│   │   ├── __init__.py
│   │   ├── base.py          # BaseRepository
│   │   ├── user.py
│   │   ├── course.py
│   │   ├── session_repo.py  # Session repository
│   │   ├── submission_artifact.py
│   │   └── ...              # 20+ repository modules
│   │
│   ├── permissions/         # 🟣 Permission Layer (RBAC)
│   │   ├── __init__.py
│   │   ├── core.py          # Permission checking
│   │   ├── auth.py          # get_current_principal, AuthenticationService
│   │   ├── principal.py     # Principal, Claims
│   │   ├── handlers.py      # Permission registry
│   │   └── handlers_impl.py # Permission handlers
│   │
│   ├── tasks/               # ⚡ Task Layer (Temporal workflows)
│   │   ├── __init__.py
│   │   ├── temporal_client.py
│   │   ├── temporal_worker.py
│   │   ├── temporal_hierarchy_management.py
│   │   ├── temporal_student_template_v2.py
│   │   ├── temporal_student_testing.py
│   │   ├── temporal_examples.py
│   │   └── ...
│   │
│   ├── services/            # 🔧 Service Layer (infrastructure)
│   │   ├── __init__.py
│   │   ├── storage_service.py  # MinIO client
│   │   ├── gitlab_utils.py     # GitLab API
│   │   └── ...
│   │
│   ├── auth/                # 🔐 External auth admin clients
│   │   ├── __init__.py
│   │   └── keycloak_admin.py   # Keycloak admin client
│   │
│   ├── plugins/             # 🔌 Authentication plugins
│   │   ├── __init__.py
│   │   ├── base.py          # Base plugin classes
│   │   ├── registry.py      # Plugin registry
│   │   └── ...              # Authentication provider plugins
│   │
│   ├── alembic/             # Database migrations
│   │   ├── env.py
│   │   └── versions/        # Migration scripts
│   │
│   ├── middleware/          # FastAPI middleware
│   ├── exceptions/          # Custom exceptions
│   ├── utils/               # Utility functions
│   ├── testing/             # Test utilities
│   └── tests/               # Test suite
│       ├── test_api_*.py
│       ├── test_business_logic_*.py
│       ├── test_models.py
│       └── ...
│
└── defaults/                # Default data (YAML)
    └── deployments/
```

### Layer Responsibilities

#### 🔵 API Layer (`api/`)

**Responsibility**: Thin endpoints that delegate to business logic.

**Pattern**:
```python
# api/submissions.py
from computor_backend.business_logic.submissions import get_artifact_with_details

@router.get("/artifacts/{artifact_id}")
async def get_artifact_endpoint(
    artifact_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    return get_artifact_with_details(artifact_id, permissions, db)
```

#### 🟢 Business Logic Layer (`business_logic/`)

**Responsibility**: Fat business logic, reusable functions.

**Pattern**:
```python
# business_logic/submissions.py
def get_artifact_with_details(
    artifact_id: str,
    permissions: Principal,
    db: Session,
) -> SubmissionArtifactGet:
    # Permission checks
    check_artifact_access(artifact_id, permissions, db)

    # Business logic
    artifact = db.query(SubmissionArtifact).get(artifact_id)
    if not artifact:
        raise NotFoundException("Artifact not found")

    # Additional logic, validation, etc.
    return artifact
```

#### 🔴 Model Layer (`model/`)

**Responsibility**: SQLAlchemy ORM models, database schema.

**Pattern**:
```python
# model/artifact.py
from sqlalchemy import Column, String, DateTime, ForeignKey
from computor_backend.model.base import Base

class SubmissionArtifact(Base):
    __tablename__ = "submission_artifacts"

    id = Column(String, primary_key=True)
    submission_group_id = Column(String, ForeignKey("submission_groups.id"))
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
```

#### 🟡 Repository Layer (`repositories/`)

**Responsibility**: Complex queries, data access abstraction.

**Pattern**:
```python
# repositories/submission_artifact.py
class SubmissionArtifactRepository(BaseRepository[SubmissionArtifact]):
    def get_by_submission_group(
        self, submission_group_id: str
    ) -> List[SubmissionArtifact]:
        return self.db.query(SubmissionArtifact)\
            .filter_by(submission_group_id=submission_group_id)\
            .order_by(SubmissionArtifact.created_at.desc())\
            .all()
```

#### 🟣 Permission Layer (`permissions/`)

**Responsibility**: RBAC, access control, permission checking.

**Pattern**:
```python
# permissions/core.py
def check_course_permissions(
    principal: Principal,
    course: Course,
    action: str,
) -> None:
    if not principal.can_access_course(course.id, action):
        raise ForbiddenException(f"No permission to {action} course")
```

#### ⚡ Task Layer (`tasks/`)

**Responsibility**: Temporal workflows, async operations.

**Pattern**:
```python
# tasks/temporal_examples.py
@workflow.defn
class ExampleDeploymentWorkflow:
    @workflow.run
    async def run(self, deployment_id: str) -> str:
        # Async workflow logic
        await workflow.execute_activity(
            deploy_example_activity,
            deployment_id,
            start_to_close_timeout=timedelta(minutes=10),
        )
        return "Success"
```

#### 🔧 Service Layer (`services/`)

**Responsibility**: Infrastructure services (MinIO, GitLab, etc.).

**Pattern**:
```python
# services/storage_service.py
class StorageService:
    def upload_file(self, bucket: str, path: str, data: bytes) -> str:
        self.minio_client.put_object(bucket, path, io.BytesIO(data), len(data))
        return f"{bucket}/{path}"
```

## Shell Scripts (Root Directory)

```bash
api.sh                      # Start FastAPI backend
startup.sh                  # Start Docker services
stop.sh                     # Stop Docker services
migrations.sh               # Run Alembic migrations
test.sh                     # Run tests
generate_types.sh           # Generate TypeScript types
generate_clients.sh         # Generate Python client
generate_schema.sh          # Generate OpenAPI schema
```

## File Naming Conventions

### Python Files

- **Module files**: `snake_case.py`
- **Test files**: `test_*.py`
- **Model files**: `{entity}.py` (e.g., `user.py`, `course.py`)
- **API files**: `{entity}.py` or `{feature}.py`
- **Business logic files**: `{entity}.py` or `{feature}.py`

## Import Patterns

### Within Backend

```python
# DTOs from computor-types
from computor_types.users import UserInterface, UserCreate, UserGet

# Backend modules
from computor_backend.model.auth import User
from computor_backend.permissions.auth import get_current_principal
from computor_backend.business_logic.users import create_user_logic
from computor_backend.repositories.user import UserRepository
```

### From CLI/Client

```python
# Types
from computor_types.users import UserCreate

# Client
from computor_client import ComputorClient
```

## Configuration Files

### Python Packages

- `pyproject.toml`: Modern Python package metadata
- `setup.py`: Compatibility layer
- `requirements.txt`: Dependencies (backend only)

### Database

- `alembic.ini`: Alembic configuration
- `src/computor_backend/alembic/env.py`: Alembic environment

### Docker

- `docker-compose-dev.yaml`: Development services
- `docker-compose-prod.yaml`: Production services
- `docker/`: Individual Dockerfiles

## Next Steps

- Read [Development Workflow](03-development-workflow.md) to understand daily practices
- Explore [Backend Architecture](04-backend-architecture.md) for detailed backend design
- Review [EntityInterface Pattern](05-entityinterface-pattern.md) to understand the DTO pattern

---

**Previous**: [← Getting Started](01-getting-started.md) | **Next**: [Development Workflow →](03-development-workflow.md)

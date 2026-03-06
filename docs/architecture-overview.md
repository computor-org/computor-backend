# Computor System Architecture Overview

## 🏗️ Architecture: Modular Multi-Package System

The Computor platform is structured as a **monorepo with multiple independent packages**, providing clean separation of concerns and reusable components.

```
computor-fullstack/
│
├── computor-types/          # 📦 Pure Pydantic DTOs (shared data contracts)
├── computor-testing/        # 📦 Test execution framework (Python, Octave, R, Julia, C, Fortran, Document)
├── computor-client/         # 📦 Auto-generated Python HTTP client
├── computor-cli/            # 📦 Command-line interface
├── computor-backend/        # 📦 FastAPI server (REST API + business logic)
├── computor-utils/          # 📦 Shared Python utility functions
├── computor-web/            # 📦 Next.js web frontend
├── computor-coder/          # Coder workspace deployment (templates + scripts)
│
├── data/                    # Configuration data (auth plugins, Keycloak)
├── docker/                  # Dockerfiles and container configs
├── docs/                    # Project documentation
├── ops/                     # Operations (environments, deployment configs)
├── plugins/                 # Authentication plugins
├── scripts/                 # Utility scripts and git hooks
└── tests/                   # Integration / end-to-end tests
```

---

## 📦 Package 1: computor-types

**Location**: `computor-types/src/computor_types/`

Pure Pydantic DTO package with zero backend dependencies.

### Purpose
- Single source of truth for data structures
- Type-safe DTOs for API contracts
- Shared between backend, client, and CLI

### Key Components
- **EntityInterface Pattern**: Base class defining CRUD operations and endpoints
- **DTOs**: Request/response models (Create, Get, List, Update, Query)
- **Test & Report Models**: Source of truth for `test.yaml` and `testSummary.json` formats
- **Meta Models**: Source of truth for `meta.yaml` format (old + new)
- **Deployment Configs**: GitLab, organization/course hierarchy configs

### Notable Features
- No SQLAlchemy dependencies (pure Pydantic)
- `get_all_dtos()` function for auto-discovery
- TypeScript interfaces and JSON schemas auto-generated via `bash generate.sh`

### Dependencies
```toml
dependencies = [
    "pydantic>=2.0",
    "email-validator>=2.0",
]
```

---

## 📦 Package 1b: computor-testing

**Location**: `computor-testing/`

Test execution framework for evaluating student code submissions.

### Purpose
- Execute tests defined in `test.yaml` against student submissions
- Support multiple languages: Python, Octave/MATLAB, R, Julia, C, Fortran, Document analysis
- Produce standardized test reports (`testSummary.json`)

### Key Components
- **Language backends**: `ctbackends/` — one backend per language (Python, Octave, R, Julia, C, Fortran, Document)
- **Core framework**: `ctcore/` — test orchestration, model re-exports, utilities
- **CLI**: `computor-tester` command for running tests locally or in CI

### Model Dependency
All Pydantic models are imported from `computor-types` (source of truth):
```python
# ctcore/models.py is a pure re-export shim
from computor_types.testing import ComputorTestSuite, ComputorTest, ...
from computor_types.testing_report import ComputorReport, ...
from computor_types.codeability_meta import CodeAbilityMeta, ...
```

### Dependencies
```toml
dependencies = [
    "computor-types>=0.1.0",
    "pyyaml>=6.0",
    # ... language-specific dependencies
]
```

---

## 📦 Package 2: computor-client

**Location**: `computor-client/src/computor_client/`

Auto-generated Python HTTP client library for the Computor API.

### Purpose
- Type-safe HTTP client for backend API
- Auto-generated from `EntityInterface` definitions
- Async/await support with httpx

### Key Components
- **ComputorClient**: Main client aggregator class
- **BaseEndpointClient**: Generic CRUD operations
- **25 Auto-generated Clients**: One per entity type
- **Custom Exceptions**: HTTP status code mapping

### Generated Clients
```python
from computor_client import ComputorClient

async with ComputorClient(base_url="http://localhost:8000") as client:
    await client.authenticate(username="admin", password="secret")

    orgs = await client.organizations.list()
    user = await client.users.get("user-id")
    course = await client.courses.create(course_dto)
```

### Dependencies
```toml
dependencies = [
    "computor-types>=0.1.0",
    "httpx>=0.27.0",
    "pydantic>=2.0",
]
```

---

## 📦 Package 3: computor-cli

**Location**: `computor-cli/src/computor_cli/`

Command-line interface for administrative and development tasks.

### Purpose
- CLI for API operations
- Worker management
- Code generation (TypeScript, OpenAPI)
- Admin tasks

### Working Commands (9)
```bash
computor login              # Authenticate with API
computor profiles           # Manage auth profiles
computor rest               # CRUD operations
computor admin              # Administrative commands
computor worker             # Temporal worker management
computor generate-types     # TypeScript interface generation
computor generate-clients   # TypeScript client generation
computor generate-schema    # OpenAPI schema generation
computor generate-validators # Validator generation
```

### Configuration
- Stored in `~/.computor/`
- Profile-based authentication
- Support for basic auth and GitLab SSO

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

---

## 📦 Package 4: computor-backend

**Location**: `computor-backend/src/computor_backend/`

FastAPI server providing REST API and business logic.

### Entry Points
- **`server.py`**: FastAPI app initialization and startup logic
- **Shell Scripts**: `api.sh`, `startup.sh`, `migrations.sh`

### Architecture Layers

#### 1. **API Layer** (`api/`)
- **Thin endpoints** that delegate to business logic
- FastAPI routers organized by resource
- Permission-based access control
- Uses DTOs from `computor_types`

**Key Modules**:
- `users.py`, `organizations.py`, `courses.py`, etc.
- Auto-generated CRUD via `CrudRouter` and `LookUpRouter`
- Custom endpoints for complex operations

#### 2. **Business Logic Layer** (`business_logic/`)
- Core business logic separated from API layer
- Reusable functions with explicit parameters
- Designed for caching and testing
- Permission checks and validation

**Example**:
```python
# In business_logic/submissions.py
def get_submission_artifact(
    artifact_id: str,
    permissions: Principal,
    db: Session,
) -> SubmissionArtifact:
    # Business logic here
    pass

# In api/submissions.py
@router.get("/artifacts/{artifact_id}")
async def get_artifact_endpoint(
    artifact_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    # Delegate to business logic
    return get_submission_artifact(artifact_id, permissions, db)
```

#### 3. **Model Layer** (`model/`)
- SQLAlchemy ORM models
- Single source of truth for database schema
- Alembic migrations generated from model changes

**Key Models**:
- `User`, `Organization`, `CourseFamily`, `Course`
- `CourseContent`, `CourseMember`, `Submission`
- `Result`, `Example`, `Deployment`

#### 4. **Repository Layer** (`repositories/`)
- Data access layer helpers
- Complex queries beyond basic CRUD
- Encapsulation of database operations

#### 5. **Permission Layer** (`permissions/`)
- RBAC system with claims
- Role hierarchy: `_owner` → `_maintainer` → `_lecturer` → `_tutor` → `_student`
- `get_current_principal` dependency
- `check_course_permissions()` helpers

#### 6. **Task Layer** (`tasks/`)
- Temporal.io workflow orchestration
- Asynchronous operations (GitLab API, deployment, testing)

**Key Workflows**:
- `temporal_hierarchy_management.py` - Organization/Course creation
- `temporal_student_template_v2.py` - Student template generation
- `temporal_student_testing.py` - Submission testing
- `temporal_examples.py` - Example deployment

#### 7. **Service Layer** (`services/`)
- Infrastructure services
- `storage_service.py` - MinIO (S3-compatible) client
- Git helpers, deployment sync
- Version resolution

#### 8. **Authentication** (`auth/` and `plugins/`)
- Built-in local authentication (username/password with Bearer tokens)
- Plugin-based authentication system for external providers
- SSO providers (Keycloak, GitLab) available as plugins

#### 9. **Coder Integration** (`coder/`)
- Coder workspace API client and service layer
- Schema definitions for workspace provisioning
- Configuration and exception handling

#### 10. **Code Generation** (`generator/`)
- TypeScript type generation from Pydantic models
- Client generation, validator generation
- OpenAPI schema generation

#### 11. **Supporting Modules**
- **`exceptions/`** - Structured error handling and error registry
- **`interfaces/`** - Internal interface definitions
- **`middleware/`** - FastAPI middleware (CORS, logging, etc.)
- **`custom_types/`** - Custom type definitions

### Runtime Configuration
- **`settings.py`**: Environment-based configuration
- **`database.py`**: SQLAlchemy session management
- **`redis_cache.py`**: Redis caching client
- **`minio_client.py`**: MinIO object storage client
- **`gitlab_utils.py`**: GitLab API utilities

### Import Pattern
```python
# DTOs from computor-types
from computor_types.organizations import OrganizationInterface, OrganizationCreate

# Backend modules
from computor_backend.model import Organization
from computor_backend.permissions.auth import get_current_principal
from computor_backend.business_logic.organizations import create_organization_logic
```

### Dependencies
```toml
dependencies = [
    "computor-types>=0.1.0",
    "fastapi>=0.104.0",
    "sqlalchemy>=2.0",
    "alembic>=1.12",
    "temporalio>=1.3.0",
    # ... many more
]
```

---

## 📦 Package 5: computor-utils

**Location**: `computor-utils/src/computor_utils/`

Shared Python utility functions used across packages.

### Purpose
- Reusable utilities shared between backend and other Python packages
- VSIX extension metadata parsing
- Deployment mapping utilities

### Key Components
- **`vsix_utils.py`** - VSIX package metadata parsing for VS Code extensions
- **`deployment_mapping/`** - `DeploymentMapper`, `DeploymentMappingConfig`, `FieldTransformer`

### Dependencies
```toml
dependencies = [
    "computor-types>=0.1.0",
]
```

---

## 📦 Package 6: computor-web

**Location**: `computor-web/`

Next.js web frontend for the Computor platform.

### Purpose
- Web-based user interface for students, tutors, and administrators
- Communicates with the backend via REST API

### Tech Stack
- **Framework**: Next.js with TypeScript
- **Styling**: PostCSS (Tailwind CSS)
- **Linting**: ESLint

### Key Directories
- **`src/api/`** - API client layer
- **`src/components/`** - React components
- **`src/contexts/`** - React context providers
- **`src/generated/`** - Auto-generated TypeScript types and clients
- **`src/interfaces/`** - TypeScript interface definitions
- **`src/services/`** - Frontend service layer
- **`src/types/`** - TypeScript type definitions
- **`src/utils/`** - Utility functions
- **`src/config/`** - Configuration

---

## 📂 computor-coder

**Location**: `computor-coder/`

Coder workspace deployment configuration (not a Python package).

### Purpose
- Terraform templates for provisioning Coder workspaces
- Workspace creation scripts and tooling

### Key Components
- **`deployment/templates/`** - Terraform templates (Python, MATLAB, etc.)
- **`deployment/create-user.sh`** - User creation helper
- **`deployment/generate-secret.sh`** - Secret generation

---

## 🗄️ Infrastructure Services

### PostgreSQL Database
- SQLAlchemy ORM
- Alembic migrations
- Audit fields: `created_by`, `updated_by`, timestamps
- Soft delete: `archived_at`

### Redis Cache
- Configuration ready
- Minimal usage currently
- Future expansion planned for business logic caching

### MinIO Object Storage
- S3-compatible storage
- File uploads, downloads, presigned URLs
- Console: http://localhost:9001

### Temporal.io
- Workflow orchestration
- Async task execution
- GitLab API integration
- UI: http://localhost:8088

---

## 🔄 Data Flow

### API Request Flow
```
Client Request
    ↓
[API Endpoint] (FastAPI router)
    ↓
[Permission Check] (get_current_principal)
    ↓
[Business Logic] (business_logic/)
    ↓
[Repository/Model] (SQLAlchemy)
    ↓
[Database] (PostgreSQL)
```

### Temporal Workflow Flow
```
API Request
    ↓
[Task Submission] (tasks/temporal_client.py)
    ↓
[Temporal Server]
    ↓
[Workflow Execution] (tasks/temporal_*.py)
    ↓
[External Services] (GitLab API, MinIO, etc.)
```

---

## 🎯 Key Design Patterns

### 1. **EntityInterface Pattern**
Single source of truth for API contracts (defined in `computor-types`)

### 2. **Repository Pattern**
Data access layer abstraction (in `repositories/`)

### 3. **Business Logic Separation**
Thin API endpoints, fat business logic layer (in `business_logic/`)

### 4. **Auto-Code Generation** (`bash generate.sh`)
- TypeScript interfaces from Pydantic models (`generate.sh types`)
- JSON schemas for `meta.yaml` and `test.yaml` (`generate.sh schemas`)
- TypeScript API clients (`generate.sh clients`)
- Python HTTP clients from `EntityInterface` (`generate.sh python-client`)

### 5. **Dependency Injection**
FastAPI dependencies for auth, database, services

---

## 📊 System Statistics

### Code Base Size
- **computor-types**: 58 files, ~500KB
- **computor-client**: 26 files, ~50KB (18K lines auto-generated)
- **computor-cli**: 18 files, ~80KB
- **computor-backend**: ~200 files, ~2MB
- **computor-utils**: Shared utilities
- **computor-web**: Next.js frontend

### API Coverage
- **25 auto-generated clients** for entity types
- **100+ REST endpoints**
- **15+ Temporal workflows**

---

---

## 🔍 Notable Behaviors

- **Startup**: Seeds admin accounts, applies roles, initializes authentication system
- **Migrations**: Generated from SQLAlchemy model changes
- **Permissions**: Role-based with course-level granularity
- **Temporal Integration**: First-class async task support
- **GitLab Integration**: Automated group/repository management
- **Caching**: Redis configured but minimally used (future expansion)
- **Authentication**: Built-in local authentication with plugin support for external providers

---

## 📚 Documentation

- **CLAUDE.md**: Project overview and developer guide
- **docs/developer-guide/**: Detailed developer guides (getting started, code organization, backend architecture, etc.)
- **docs/developer-guideline.md**: Backend development guidelines
- **Package READMEs**: Installation and usage for each package

---

## 🎯 Next Steps

- Migrate remaining CLI commands to use `computor_client`
- Expand Redis caching in business logic layer
- Complete repository mirroring implementation
- Implement additional SSO providers as plugins
- Add comprehensive API documentation
- Enhance testing coverage

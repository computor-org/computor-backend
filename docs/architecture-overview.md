# Computor System Architecture Overview

## 🏗️ Architecture: Modular Multi-Package System

The Computor platform is structured as a **monorepo with 4 independent packages**, providing clean separation of concerns and reusable components.

```
/home/theta/computor/computor-fullstack/
│
├── computor-types/          # 📦 Pure Pydantic DTOs
├── computor-client/         # 📦 Auto-generated HTTP client
├── computor-cli/            # 📦 Command-line interface
├── src/computor_backend/    # 📦 FastAPI server
├── frontend/                # 🎨 React frontend (Material-UI)
└── frontend-next/           # 🎨 Next.js frontend (GitLab UI)
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
- **58 Interface Files**: Organizations, Users, Courses, Assignments, Submissions, etc.

### Notable Features
- No SQLAlchemy dependencies (pure Pydantic)
- `get_all_dtos()` function for auto-discovery
- Type-checking blocks for forward references
- Independent, installable package

### Dependencies
```toml
dependencies = [
    "pydantic>=2.0",
    "email-validator>=2.0",
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

## 📦 Package 4: computor_backend

**Location**: `src/computor_backend/`

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

#### 8. **Authentication** (`auth/`)
- Authentication plugins
- Keycloak SSO provider (OpenID Connect)
- Basic auth fallback

### Runtime Configuration
- **`settings.py`**: Environment-based configuration
- **`database.py`**: SQLAlchemy session management
- **`redis_cache.py`**: Redis caching client

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

## 🎨 Frontend (frontend/)

**Legacy React application** with Material-UI.

### Tech Stack
- React 19 + TypeScript
- React Router, MUI 6
- React Query, TanStack Table
- React Hook Form, Redux Toolkit

### Structure
- **`App.tsx`**: Routing, layout, authentication
- **`pages/`**: Dashboards, admin views
- **`components/`**: Navigation, modals, tables, forms
- **`hooks/`**: Auth, sidebar, data fetching
- **`services/`**: HTTP clients for backend API
- **`api/`**: API client, type definitions

### Service URLs (Development)
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

---

## 🎨 Frontend (frontend-next/)

**New Next.js 15 application** with GitLab UI.

### Tech Stack
- Next.js 15 + TypeScript
- GitLab UI components
- Turbopack for fast dev server

### Structure
- Modern Next.js App Router
- Server and client components
- GitLab design system

### Service URLs (Development)
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

**Note**: Both frontends run on port 3000 - only run one at a time.

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

### Keycloak SSO
- OpenID Connect authentication
- Multi-tenant support
- UI: http://localhost:8080

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

### 4. **Auto-Code Generation**
- Python clients from `EntityInterface`
- TypeScript types from Pydantic models
- OpenAPI schema generation

### 5. **Dependency Injection**
FastAPI dependencies for auth, database, services

---

## 📊 System Statistics

### Code Base Size
- **computor-types**: 58 files, ~500KB
- **computor-client**: 26 files, ~50KB (18K lines auto-generated)
- **computor-cli**: 18 files, ~80KB
- **computor_backend**: ~200 files, ~2MB
- **Total**: ~300 files, ~25,000 lines of code

### API Coverage
- **25 auto-generated clients** for entity types
- **100+ REST endpoints**
- **15+ Temporal workflows**

---

## 🚀 Deployment

### Development Setup
```bash
# Install all packages
pip install -e computor-types/
pip install -e computor-client/
pip install -e computor-cli/
pip install -e src/

# Start services
bash startup.sh        # Docker services
bash api.sh            # Backend API
bash frontend.sh       # React frontend
```

### Production Considerations
- All 4 packages publishable to PyPI
- Docker Compose orchestration
- Environment-based configuration
- Alembic migrations for database schema

---

## 🔍 Notable Behaviors

- **Startup**: Seeds admin accounts, applies roles, initializes auth plugins
- **Migrations**: Generated from SQLAlchemy model changes
- **Permissions**: Role-based with course-level granularity
- **Temporal Integration**: First-class async task support
- **GitLab Integration**: Automated group/repository management
- **Caching**: Redis configured but minimally used (future expansion)
- **Authentication**: Multiple strategies (SSO, Basic, mock)

---

## 📚 Documentation

- **CLAUDE.md**: Project overview and developer guide
- **REFACTORING_COMPLETE_FINAL.md**: Complete refactoring summary
- **docs/guideline.md**: Backend development guidelines
- **Package READMEs**: Installation and usage for each package

---

## 🎯 Next Steps

- Migrate remaining 4 CLI commands to use `computor_client`
- Expand Redis caching in business logic layer
- Complete repository mirroring implementation
- Enhance frontend with Next.js application
- Add comprehensive API documentation

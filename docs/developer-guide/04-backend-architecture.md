# Backend Architecture

This guide explains the architecture and design patterns used in the Computor backend.

## Architecture Overview

Computor backend follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────┐
│              HTTP Request                        │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│          🔵 API Layer (Thin)                    │
│  - FastAPI routers                              │
│  - Request/response handling                    │
│  - Dependency injection                         │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│       🟣 Permission Layer                       │
│  - RBAC checks                                  │
│  - Principal/Claims                             │
│  - Permission handlers                          │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│       🟢 Business Logic Layer (Fat)             │
│  - Core business rules                          │
│  - Validation                                   │
│  - Orchestration                                │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│       🟡 Repository Layer                       │
│  - Complex queries                              │
│  - Data access abstraction                      │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│       🔴 Model Layer                            │
│  - SQLAlchemy ORM models                        │
│  - Database schema                              │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│           PostgreSQL Database                    │
└─────────────────────────────────────────────────┘

         ┌──────────────────┐
         │ ⚡ Task Layer    │
         │  (Temporal)      │
         │  - Async work    │
         │  - GitLab API    │
         └────────┬─────────┘
                  │
         ┌────────▼─────────┐
         │  🔧 Services     │
         │  - MinIO         │
         │  - GitLab        │
         │  - Redis         │
         └──────────────────┘
```

## Layer Details

### 🔵 API Layer

**Location**: `computor-backend/src/computor_backend/api/`

**Responsibility**: Thin HTTP endpoints that delegate to business logic.

**Principles**:
- No business logic in endpoints
- Minimal request/response transformation
- Dependency injection for services
- Always include permission checks

**Example**:

```python
# api/submissions.py
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.business_logic.submissions import get_artifact_with_details
from computor_types.artifacts import SubmissionArtifactGet

router = APIRouter(prefix="/submissions", tags=["submissions"])

@router.get("/artifacts/{artifact_id}", response_model=SubmissionArtifactGet)
async def get_artifact_endpoint(
    artifact_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Get submission artifact by ID."""
    # Just delegate - no business logic here
    return get_artifact_with_details(artifact_id, permissions, db)
```

**Key Points**:
- Use `Annotated` for dependency injection
- Always inject `Principal` for permissions
- Always inject `Session` for database access
- Specify `response_model` for validation
- Keep endpoints simple (1-5 lines of logic)

### 🟣 Permission Layer

**Location**: `computor-backend/src/computor_backend/permissions/`

**Responsibility**: Access control, RBAC, permission checking.

**Key Components**:
- `Principal`: Current user with claims and permissions
- `Claims`: User's roles and permissions
- Permission handlers: Entity-specific permission logic
- Permission registry: Maps models to handlers

**Example**:

```python
# permissions/core.py
from computor_backend.permissions.principal import Principal
from computor_backend.api.exceptions import ForbiddenException

def check_course_permissions(
    principal: Principal,
    course: Course,
    action: str,
    required_role: str = "_student",
) -> None:
    """Check if user has permission to perform action on course."""
    if principal.is_admin:
        return  # Admins can do anything

    # Check if user is a member of the course
    if not principal.has_course_role(course.id, required_role):
        raise ForbiddenException(
            f"User does not have {required_role} role in course {course.id}"
        )
```

**Role Hierarchy**:
```
_owner > _maintainer > _lecturer > _tutor > _student
```

Higher roles inherit permissions from lower roles.

### 🟢 Business Logic Layer

**Location**: `computor-backend/src/computor_backend/business_logic/`

**Responsibility**: Core business rules, validation, orchestration.

**Principles**:
- Pure functions with explicit parameters
- No dependency on FastAPI/HTTP
- Reusable across API, CLI, tasks
- Designed for testability and caching

**Example**:

```python
# business_logic/submissions.py
from sqlalchemy.orm import Session
from computor_backend.model.artifact import SubmissionArtifact
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.core import check_course_permissions
from computor_backend.api.exceptions import NotFoundException, ForbiddenException
from computor_types.artifacts import SubmissionArtifactGet

def get_artifact_with_details(
    artifact_id: str,
    permissions: Principal,
    db: Session,
) -> SubmissionArtifactGet:
    """
    Get submission artifact with permission checks.

    Args:
        artifact_id: Artifact ID
        permissions: Current user's permissions
        db: Database session

    Returns:
        Artifact DTO

    Raises:
        NotFoundException: Artifact not found
        ForbiddenException: No permission to access
    """
    # Fetch artifact
    artifact = db.query(SubmissionArtifact)\
        .filter_by(id=artifact_id)\
        .first()

    if not artifact:
        raise NotFoundException("Artifact not found")

    # Check permissions
    submission_group = artifact.submission_group
    course_content = submission_group.course_content
    course = course_content.course

    # Tutors and above can see all artifacts
    # Students can only see their own
    if not permissions.has_course_role(course.id, "_tutor"):
        # Check if student is in the submission group
        is_member = any(
            m.student_id == permissions.user_id
            for m in submission_group.members
        )
        if not is_member:
            raise ForbiddenException("Cannot access other students' artifacts")

    # Return DTO
    return SubmissionArtifactGet.from_orm(artifact)
```

**Key Points**:
- Accept explicit parameters (no global state)
- Check permissions early
- Validate input data
- Use exceptions for error handling
- Return DTOs, not ORM models
- Add docstrings with Args, Returns, Raises

### 🟡 Repository Layer

**Location**: `computor-backend/src/computor_backend/repositories/`

**Responsibility**: Data access, complex queries, query abstraction.

**When to Use**:
- Complex queries with joins
- Reusable query patterns
- Performance-critical queries
- Queries used in multiple places

**Example**:

```python
# repositories/submission_artifact.py
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from computor_backend.model.artifact import SubmissionArtifact
from computor_backend.repositories.base import BaseRepository

class SubmissionArtifactRepository(BaseRepository[SubmissionArtifact]):
    """Repository for submission artifacts."""

    def __init__(self, db: Session):
        super().__init__(db, SubmissionArtifact)

    def get_by_submission_group(
        self,
        submission_group_id: str,
        include_grades: bool = False,
    ) -> List[SubmissionArtifact]:
        """Get all artifacts for a submission group."""
        query = self.db.query(SubmissionArtifact)\
            .filter_by(submission_group_id=submission_group_id)

        if include_grades:
            query = query.options(joinedload(SubmissionArtifact.grades))

        return query.order_by(SubmissionArtifact.created_at.desc()).all()

    def get_latest_by_content(
        self,
        course_content_id: str,
        student_id: str,
    ) -> Optional[SubmissionArtifact]:
        """Get latest artifact for a course content and student."""
        return self.db.query(SubmissionArtifact)\
            .join(SubmissionArtifact.submission_group)\
            .join(SubmissionGroup.members)\
            .filter(and_(
                SubmissionGroup.course_content_id == course_content_id,
                SubmissionGroupMember.student_id == student_id,
            ))\
            .order_by(SubmissionArtifact.created_at.desc())\
            .first()

    def count_by_course(self, course_id: str) -> int:
        """Count artifacts submitted in a course."""
        return self.db.query(SubmissionArtifact)\
            .join(SubmissionArtifact.submission_group)\
            .join(SubmissionGroup.course_content)\
            .filter(CourseContent.course_id == course_id)\
            .count()
```

**Base Repository**:

```python
# repositories/base.py
from typing import Generic, TypeVar, Type, List, Optional
from sqlalchemy.orm import Session

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations."""

    def __init__(self, db: Session, model_class: Type[T]):
        self.db = db
        self.model_class = model_class

    def get(self, id: str) -> Optional[T]:
        """Get by ID."""
        return self.db.query(self.model_class).filter_by(id=id).first()

    def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        """List all."""
        return self.db.query(self.model_class).offset(skip).limit(limit).all()

    def create(self, entity: T) -> T:
        """Create entity."""
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, entity: T) -> T:
        """Update entity."""
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: T) -> None:
        """Delete entity."""
        self.db.delete(entity)
        self.db.commit()
```

### 🔴 Model Layer

**Location**: `computor-backend/src/computor_backend/model/`

**Responsibility**: SQLAlchemy ORM models, database schema definition.

**Example**:

```python
# model/artifact.py
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from computor_backend.model.base import Base

class SubmissionArtifact(Base):
    """Student submission artifact (file uploaded by student)."""
    __tablename__ = "submission_artifacts"

    id = Column(String, primary_key=True)
    submission_group_id = Column(
        String,
        ForeignKey("submission_groups.id"),
        nullable=False
    )
    file_path = Column(String, nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))

    # Relationships
    submission_group = relationship(
        "SubmissionGroup",
        back_populates="artifacts"
    )
    grades = relationship(
        "SubmissionGrade",
        back_populates="artifact",
        cascade="all, delete-orphan"
    )
    reviews = relationship(
        "SubmissionReview",
        back_populates="artifact",
        cascade="all, delete-orphan"
    )

    # Audit fields inherited from Base:
    # created_at, updated_at, created_by, updated_by, archived_at
```

**Base Model**:

```python
# model/base.py
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Base(Base):
    """Base model with audit fields."""
    __abstract__ = True

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String)
    updated_by = Column(String)
    archived_at = Column(DateTime)  # Soft delete
```

### ⚡ Task Layer (Temporal)

**Location**: `computor-backend/src/computor_backend/tasks/`

**Responsibility**: Asynchronous workflows, long-running operations.

**Use Cases**:
- GitLab repository creation
- Student template generation
- Submission testing
- Example deployment
- Batch operations

**Example Workflow**:

```python
# tasks/temporal_examples.py
from datetime import timedelta
from temporalio import workflow, activity
from computor_backend.model.example import Example

@activity.defn
async def deploy_example_activity(example_id: str) -> str:
    """Deploy an example to GitLab."""
    # Database session setup
    db = get_db_session()

    try:
        example = db.query(Example).filter_by(id=example_id).first()
        if not example:
            raise ValueError(f"Example {example_id} not found")

        # Deploy to GitLab
        gitlab_client = get_gitlab_client()
        repo = gitlab_client.create_repository(
            name=example.name,
            description=example.description,
        )

        # Update example with repo URL
        example.repository_url = repo.url
        db.commit()

        return repo.url

    finally:
        db.close()

@workflow.defn
class ExampleDeploymentWorkflow:
    """Workflow for deploying examples."""

    @workflow.run
    async def run(self, example_id: str) -> str:
        """Run the deployment workflow."""
        # Execute activity with timeout
        repo_url = await workflow.execute_activity(
            deploy_example_activity,
            example_id,
            start_to_close_timeout=timedelta(minutes=10),
        )

        return repo_url
```

**Starting a Workflow**:

```python
# In business logic or API endpoint
from computor_backend.tasks.temporal_client import get_temporal_client

async def deploy_example(example_id: str):
    """Start example deployment workflow."""
    client = await get_temporal_client()

    handle = await client.start_workflow(
        ExampleDeploymentWorkflow.run,
        example_id,
        id=f"deploy-example-{example_id}",
        task_queue="computor-tasks",
    )

    return handle.id
```

### 🔧 Service Layer

**Location**: `computor-backend/src/computor_backend/services/`

**Responsibility**: Infrastructure services (MinIO, GitLab, Redis).

**Example**:

```python
# services/storage_service.py
import io
from minio import Minio
from computor_backend.settings import settings

class StorageService:
    """MinIO object storage service."""

    def __init__(self):
        self.client = Minio(
            settings.MINIO_HOST,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

    def upload_file(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file to MinIO."""
        # Ensure bucket exists
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

        # Upload
        self.client.put_object(
            bucket,
            path,
            io.BytesIO(data),
            len(data),
            content_type=content_type,
        )

        return f"{bucket}/{path}"

    def download_file(self, bucket: str, path: str) -> bytes:
        """Download file from MinIO."""
        response = self.client.get_object(bucket, path)
        data = response.read()
        response.close()
        response.release_conn()
        return data

    def get_presigned_url(
        self,
        bucket: str,
        path: str,
        expires: int = 3600,
    ) -> str:
        """Get presigned download URL."""
        return self.client.presigned_get_object(
            bucket,
            path,
            expires=timedelta(seconds=expires),
        )

# Singleton instance
_storage_service = None

def get_storage_service() -> StorageService:
    """Get storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
```

## Data Flow Examples

### Simple GET Request

```
1. HTTP GET /api/v1/courses/{id}
2. API endpoint: get_course_endpoint()
3. Permission check: get_current_principal()
4. Business logic: get_course(id, permissions, db)
5. Permission check: check_course_permissions()
6. Database query: db.query(Course).get(id)
7. Return DTO: CourseGet.from_orm(course)
8. HTTP response: 200 OK with JSON
```

### Complex POST Request with Workflow

```
1. HTTP POST /api/v1/examples/deploy
2. API endpoint: deploy_example_endpoint()
3. Permission check: get_current_principal()
4. Business logic: deploy_example(example_id, permissions, db)
5. Permission check: check_lecturer_permissions()
6. Start Temporal workflow: ExampleDeploymentWorkflow
7. Return workflow ID
8. HTTP response: 202 Accepted with workflow ID

[Asynchronously]
9. Temporal worker picks up workflow
10. Activity: deploy_example_activity()
11. GitLab API: create repository
12. Database update: save repository URL
13. Workflow completes
```

## Design Patterns

### Dependency Injection

FastAPI's dependency injection system is used throughout:

```python
from fastapi import Depends
from sqlalchemy.orm import Session

def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),  # Injected
    permissions: Principal = Depends(get_current_principal),  # Injected
):
    return get_user_logic(user_id, permissions, db)
```

### Repository Pattern

Used for complex queries and data access abstraction:

```python
# In business logic
from computor_backend.repositories.submission_artifact import SubmissionArtifactRepository

def get_student_artifacts(student_id: str, course_id: str, db: Session):
    repo = SubmissionArtifactRepository(db)
    return repo.get_by_student_and_course(student_id, course_id)
```

### Service Pattern

Used for infrastructure services:

```python
from computor_backend.services.storage_service import get_storage_service

def upload_submission(file_data: bytes, path: str):
    storage = get_storage_service()
    return storage.upload_file("submissions", path, file_data)
```

### Handler Registry Pattern

Used for permissions:

```python
# Permission handlers registered at startup
from computor_backend.permissions.handlers import permission_registry
from computor_backend.permissions.handlers_impl import CoursePermissionHandler

permission_registry.register(Course, CoursePermissionHandler(Course))

# Later, check permissions
handler = permission_registry.get_handler(Course)
handler.check_read_permission(principal, course)
```

## Best Practices

### 1. Thin Controllers, Fat Services

❌ **Bad**: Business logic in API endpoint
```python
@router.post("/artifacts/{artifact_id}/grade")
async def grade_artifact(artifact_id: str, grade_data: GradeCreate, db: Session = Depends(get_db)):
    artifact = db.query(SubmissionArtifact).get(artifact_id)
    if not artifact:
        raise NotFoundException()

    grade = SubmissionGrade(id=str(uuid4()), **grade_data.dict())
    db.add(grade)
    db.commit()
    return grade
```

✅ **Good**: Delegate to business logic
```python
@router.post("/artifacts/{artifact_id}/grade")
async def grade_artifact(
    artifact_id: str,
    grade_data: GradeCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    return create_artifact_grade(artifact_id, grade_data, permissions, db)
```

### 2. Always Check Permissions

❌ **Bad**: No permission check
```python
def get_course(course_id: str, db: Session):
    return db.query(Course).get(course_id)
```

✅ **Good**: Permission check included
```python
def get_course(course_id: str, permissions: Principal, db: Session):
    course = db.query(Course).get(course_id)
    check_course_permissions(permissions, course, "read")
    return course
```

### 3. Return DTOs, Not ORM Models

❌ **Bad**: Return ORM model
```python
def get_user(user_id: str, db: Session) -> User:
    return db.query(User).get(user_id)
```

✅ **Good**: Return DTO
```python
def get_user(user_id: str, db: Session) -> UserGet:
    user = db.query(User).get(user_id)
    return UserGet.from_orm(user)
```

### 4. Use Type Hints

❌ **Bad**: No type hints
```python
def create_course(course_data, permissions, db):
    # ...
```

✅ **Good**: Full type hints
```python
def create_course(
    course_data: CourseCreate,
    permissions: Principal,
    db: Session,
) -> CourseGet:
    # ...
```

### 5. Handle Errors Consistently

Use custom exceptions:

```python
from computor_backend.api.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException,
)

def get_artifact(artifact_id: str, permissions: Principal, db: Session):
    artifact = db.query(SubmissionArtifact).get(artifact_id)

    if not artifact:
        raise NotFoundException("Artifact not found")

    if not can_access_artifact(permissions, artifact):
        raise ForbiddenException("Cannot access this artifact")

    if artifact.archived_at:
        raise BadRequestException("Artifact has been archived")

    return artifact
```

## Next Steps

- Learn about [EntityInterface Pattern](05-entityinterface-pattern.md)
- Understand [Permission System](06-permission-system.md)
- Explore [Database & Migrations](07-database-migrations.md)

---

**Previous**: [← Development Workflow](03-development-workflow.md) | **Next**: [EntityInterface Pattern →](05-entityinterface-pattern.md)

# Development Workflow

This guide covers the day-to-day development workflow for Computor developers.

## Daily Development Cycle

### Starting Work

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Pull latest changes
git checkout main
git pull origin main

# 3. Start Docker services (if not running)
bash startup.sh

# 4. Run any new migrations
bash migrations.sh

# 5. Start backend API
bash api.sh

# 6. (Optional) Start frontend in another terminal
bash frontend.sh
```

### Making Changes

#### 1. Create Feature Branch

```bash
# Create and checkout feature branch
git checkout -b feat/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description

# Or for refactoring
git checkout -b refactor/what-youre-refactoring
```

#### 2. Make Your Changes

Follow the appropriate workflow based on what you're changing:

##### Adding a New Entity

See [Adding New Entities](#adding-new-entities) section below.

##### Modifying Existing Endpoint

1. Update business logic in `computor-backend/src/computor_backend/business_logic/`
2. Update API endpoint in `computor-backend/src/computor_backend/api/` (if needed)
3. Update tests
4. Run tests: `bash test.sh`

##### Updating Database Schema

1. Modify SQLAlchemy model in `computor-backend/src/computor_backend/model/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review and edit migration in `computor-backend/src/computor_backend/alembic/versions/`
4. Test migration: `alembic upgrade head`
5. Test rollback: `alembic downgrade -1` then `alembic upgrade head`

#### 3. Run Tests

```bash
# Run all tests
bash test.sh

# Run specific test file
pytest computor-backend/src/computor_backend/tests/test_submissions.py

# Run specific test function
pytest computor-backend/src/computor_backend/tests/test_submissions.py::test_upload_artifact

# Run with coverage
pytest --cov=computor_backend --cov-report=html

# Run only unit tests
bash test.sh --unit

# Run only integration tests
bash test.sh --integration
```

#### 4. Commit Changes

```bash
# Stage changes
git add .

# Commit with conventional commit message
git commit -m "feat(submissions): add artifact grading endpoint"

# Push to remote
git push origin feat/your-feature-name
```

### Committing Code

#### Conventional Commits

Use the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring (no functional changes)
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, build, etc.)
- `perf`: Performance improvements
- `style`: Code style changes (formatting, etc.)

**Examples**:

```bash
# Feature
git commit -m "feat(submissions): add artifact grading endpoint"

# Bug fix
git commit -m "fix(auth): resolve token expiration issue"

# Documentation
git commit -m "docs(api): update submission endpoint documentation"

# Refactor
git commit -m "refactor(business_logic): extract submission validation logic"

# With body and footer
git commit -m "feat(courses): add course member bulk import

Add endpoint to import multiple course members from CSV.
Includes validation and error reporting.

Refs: #123
Closes: #456"
```

### Creating Pull Requests

```bash
# Push your branch
git push origin feat/your-feature-name

# Create PR using GitHub CLI
gh pr create --title "Feature: Add artifact grading" --body "Description of changes"

# Or create PR via web interface
```

**PR Template**:

```markdown
## Description
Brief description of changes

## Changes
- Change 1
- Change 2
- Change 3

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## Common Development Tasks

### Adding New Entities

Complete workflow for adding a new entity (e.g., "Assignment"):

#### 1. Create DTOs in computor-types

**File**: `computor-types/src/computor_types/assignments.py`

```python
from typing import Optional
from pydantic import BaseModel
from computor_types.base import EntityInterface, BaseEntityGet, BaseEntityList

class AssignmentInterface(EntityInterface):
    """Assignment entity interface."""
    create = "AssignmentCreate"
    get = "AssignmentGet"
    list = "AssignmentList"
    update = "AssignmentUpdate"
    query = "AssignmentQuery"

class AssignmentCreate(BaseModel):
    title: str
    description: str
    course_id: str
    due_date: Optional[datetime] = None

class AssignmentGet(BaseEntityGet):
    id: str
    title: str
    description: str
    course_id: str
    due_date: Optional[datetime] = None

class AssignmentList(BaseEntityList):
    id: str
    title: str
    course_id: str
    due_date: Optional[datetime] = None

class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None

class AssignmentQuery(BaseModel):
    course_id: Optional[str] = None
    title: Optional[str] = None
```

#### 2. Create SQLAlchemy Model

**File**: `computor-backend/src/computor_backend/model/assignment.py`

```python
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from computor_backend.model.base import Base

class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(String, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    due_date = Column(DateTime)

    # Relationships
    course = relationship("Course", back_populates="assignments")

    # Audit fields (inherited from Base)
    # created_at, updated_at, created_by, updated_by, archived_at
```

Update related models (e.g., `Course`) to add relationship:

```python
# In computor-backend/src/computor_backend/model/course.py
class Course(Base):
    # ... existing fields ...

    assignments = relationship("Assignment", back_populates="course")
```

#### 3. Generate and Apply Migration

```bash
# Generate migration
cd computor-backend
alembic revision --autogenerate -m "add assignments table"

# Review the generated migration file in:
# src/computor_backend/alembic/versions/XXXX_add_assignments_table.py

# Apply migration
alembic upgrade head

# Test rollback
alembic downgrade -1
alembic upgrade head
```

#### 4. Create Repository

**File**: `computor-backend/src/computor_backend/repositories/assignment.py`

```python
from typing import List, Optional
from sqlalchemy.orm import Session
from computor_backend.model.assignment import Assignment
from computor_backend.repositories.base import BaseRepository

class AssignmentRepository(BaseRepository[Assignment]):
    def __init__(self, db: Session):
        super().__init__(db, Assignment)

    def get_by_course(self, course_id: str) -> List[Assignment]:
        return self.db.query(Assignment)\
            .filter_by(course_id=course_id)\
            .order_by(Assignment.due_date.asc())\
            .all()

    def get_upcoming(self, course_id: str) -> List[Assignment]:
        from datetime import datetime
        return self.db.query(Assignment)\
            .filter(
                Assignment.course_id == course_id,
                Assignment.due_date >= datetime.now()
            )\
            .order_by(Assignment.due_date.asc())\
            .all()
```

#### 5. Create Business Logic

**File**: `computor-backend/src/computor_backend/business_logic/assignments.py`

```python
from typing import List
from sqlalchemy.orm import Session
from computor_backend.model.assignment import Assignment
from computor_backend.repositories.assignment import AssignmentRepository
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.core import check_course_permissions
from computor_backend.api.exceptions import NotFoundException
from computor_types.assignments import AssignmentGet, AssignmentCreate, AssignmentUpdate

def create_assignment(
    assignment_data: AssignmentCreate,
    permissions: Principal,
    db: Session,
) -> AssignmentGet:
    """Create a new assignment."""
    # Check permissions
    course = db.query(Course).filter_by(id=assignment_data.course_id).first()
    if not course:
        raise NotFoundException("Course not found")

    check_course_permissions(permissions, course, "create_assignment")

    # Create assignment
    assignment = Assignment(
        id=str(uuid4()),
        **assignment_data.dict(),
        created_by=permissions.user_id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return AssignmentGet.from_orm(assignment)

def get_assignment(
    assignment_id: str,
    permissions: Principal,
    db: Session,
) -> AssignmentGet:
    """Get assignment by ID."""
    assignment = db.query(Assignment).filter_by(id=assignment_id).first()
    if not assignment:
        raise NotFoundException("Assignment not found")

    check_course_permissions(permissions, assignment.course, "read")

    return AssignmentGet.from_orm(assignment)
```

#### 6. Create API Endpoints

**File**: `computor-backend/src/computor_backend/api/assignments.py`

```python
from typing import Annotated, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.business_logic.assignments import (
    create_assignment,
    get_assignment,
    list_assignments,
    update_assignment,
    delete_assignment,
)
from computor_types.assignments import (
    AssignmentCreate,
    AssignmentGet,
    AssignmentList,
    AssignmentUpdate,
)

router = APIRouter(prefix="/assignments", tags=["assignments"])

@router.post("/", response_model=AssignmentGet, status_code=status.HTTP_201_CREATED)
async def create_assignment_endpoint(
    assignment_data: AssignmentCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Create a new assignment."""
    return create_assignment(assignment_data, permissions, db)

@router.get("/{assignment_id}", response_model=AssignmentGet)
async def get_assignment_endpoint(
    assignment_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Get assignment by ID."""
    return get_assignment(assignment_id, permissions, db)

@router.get("/", response_model=List[AssignmentList])
async def list_assignments_endpoint(
    course_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """List assignments for a course."""
    return list_assignments(course_id, permissions, db)

@router.put("/{assignment_id}", response_model=AssignmentGet)
async def update_assignment_endpoint(
    assignment_id: str,
    assignment_data: AssignmentUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Update an assignment."""
    return update_assignment(assignment_id, assignment_data, permissions, db)

@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment_endpoint(
    assignment_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Delete an assignment."""
    delete_assignment(assignment_id, permissions, db)
```

Register router in `server.py`:

```python
# In computor-backend/src/computor_backend/server.py
from computor_backend.api.assignments import router as assignments_router

app.include_router(assignments_router, prefix="/api/v1")
```

#### 7. Create Tests

**File**: `computor-backend/src/computor_backend/tests/test_assignments.py`

```python
import pytest
from computor_backend.model.assignment import Assignment
from computor_types.assignments import AssignmentCreate

def test_create_assignment(client, admin_token, test_course):
    """Test creating an assignment."""
    assignment_data = {
        "title": "Test Assignment",
        "description": "Test description",
        "course_id": test_course.id,
    }

    response = client.post(
        "/api/v1/assignments/",
        json=assignment_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Assignment"
    assert data["course_id"] == test_course.id

def test_get_assignment(client, admin_token, test_assignment):
    """Test getting an assignment."""
    response = client.get(
        f"/api/v1/assignments/{test_assignment.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_assignment.id
    assert data["title"] == test_assignment.title
```

#### 8. Register Permission Handler

**File**: `computor-backend/src/computor_backend/permissions/core.py`

```python
# Add to initialize_permission_handlers()
from computor_backend.model.assignment import Assignment
from computor_backend.permissions.handlers_impl import CourseContentPermissionHandler

permission_registry.register(Assignment, CourseContentPermissionHandler(Assignment))
```

#### 9. Generate TypeScript Types and Client

```bash
# Generate TypeScript interfaces
bash generate_types.sh

# Generate TypeScript client
bash generate_clients.sh
```

#### 10. Test Everything

```bash
# Run tests
bash test.sh

# Test API manually
bash api.sh
# Open http://localhost:8000/docs
# Test the new endpoints
```

### Modifying Existing Endpoints

When modifying existing functionality:

1. **Update business logic first** (`business_logic/`)
2. **Update API endpoint** if signature changes (`api/`)
3. **Update tests** to cover new behavior
4. **Update DTOs** if data structure changes (`computor-types/`)
5. **Run tests** to ensure nothing breaks

### Working with Database

#### Creating Migrations

```bash
# Auto-generate migration from model changes
cd computor-backend
alembic revision --autogenerate -m "add column to users"

# Create empty migration for data migrations
alembic revision -m "populate default values"
```

#### Editing Migrations

Always review auto-generated migrations:

```python
# computor-backend/src/computor_backend/alembic/versions/XXXX_add_column.py

def upgrade():
    # Review and edit if needed
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))

    # Add data migrations if needed
    op.execute("UPDATE users SET phone = '' WHERE phone IS NULL")

def downgrade():
    op.drop_column('users', 'phone')
```

#### Applying Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Upgrade to specific version
alembic upgrade abc123

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade abc123

# Show current version
alembic current

# Show migration history
alembic history
```

### Code Generation

#### TypeScript Interface Generation

```bash
# Generate TypeScript interfaces from Pydantic models
bash generate_types.sh

# Or use CLI
computor generate-types

# Watch mode (regenerate on changes)
computor generate-types --watch
```

Generated files: `computor-backend/frontend/src/types/`

#### TypeScript Client Generation

```bash
# Generate TypeScript client
bash generate_clients.sh

# Or use CLI
computor generate-clients
```

Generated files: `generated/typescript-client/`

#### OpenAPI Schema Generation

```bash
# Generate OpenAPI schema
bash generate_schema.sh

# Or use CLI
computor generate-schema
```

Generated file: `generated/openapi.json`

## Testing Workflow

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=computor_backend --cov-report=html

# Specific test file
pytest computor-backend/src/computor_backend/tests/test_submissions.py

# Specific test
pytest computor-backend/src/computor_backend/tests/test_submissions.py::test_upload_artifact

# By marker
pytest -m "unit"
pytest -m "integration"

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Show print statements
pytest -s
```

### Writing Tests

#### Unit Test Example

```python
# test_business_logic_submissions.py
import pytest
from computor_backend.business_logic.submissions import validate_submission

def test_validate_submission_success():
    """Test successful submission validation."""
    result = validate_submission(
        file_size=1024,
        file_type="text/plain",
        max_size=2048,
    )
    assert result is True

def test_validate_submission_too_large():
    """Test submission validation fails for large file."""
    with pytest.raises(BadRequestException):
        validate_submission(
            file_size=3000,
            file_type="text/plain",
            max_size=2048,
        )
```

#### Integration Test Example

```python
# test_api_submissions.py
import pytest

def test_upload_submission_integration(client, student_token, test_course):
    """Test full submission upload workflow."""
    # Create submission
    response = client.post(
        f"/api/v1/courses/{test_course.id}/submissions/upload",
        files={"file": ("test.txt", b"content", "text/plain")},
        headers={"Authorization": f"Bearer {student_token}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data

    # Verify submission exists
    submission_id = data["id"]
    response = client.get(
        f"/api/v1/submissions/{submission_id}",
        headers={"Authorization": f"Bearer {student_token}"}
    )

    assert response.status_code == 200
```

### Test Fixtures

Common fixtures are defined in `conftest.py`:

```python
# computor-backend/src/computor_backend/tests/conftest.py

@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)

@pytest.fixture
def db():
    """Database session."""
    # Setup
    session = SessionLocal()
    yield session
    # Teardown
    session.close()

@pytest.fixture
def admin_token(client):
    """Admin authentication token."""
    response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin"
    })
    return response.json()["access_token"]

@pytest.fixture
def test_course(db):
    """Test course object."""
    course = Course(id="test-course", name="Test Course")
    db.add(course)
    db.commit()
    yield course
    db.delete(course)
    db.commit()
```

## Debugging

### Backend Debugging

#### Print Debugging

```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

#### VS Code Debugger

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "computor_backend.server:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

#### PyCharm Debugger

1. Edit Configurations → Add New → Python
2. Script path: Select `uvicorn`
3. Parameters: `computor_backend.server:app --reload`
4. Set breakpoints and run in debug mode

### Database Debugging

```bash
# Connect to database
psql -h localhost -U postgres -d computor

# View tables
\dt

# Describe table
\d users

# Query data
SELECT * FROM users;

# View migrations
SELECT * FROM alembic_version;
```

### API Debugging

#### Using FastAPI Docs

Open http://localhost:8000/docs and test endpoints interactively.

#### Using curl

```bash
# Login
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  | jq -r '.access_token')

# Get organizations
curl http://localhost:8000/api/v1/organizations \
  -H "Authorization: Bearer $TOKEN"
```

#### Using HTTPie

```bash
# Login
http POST :8000/api/v1/auth/login username=admin password=admin

# Get organizations with token
http :8000/api/v1/organizations "Authorization: Bearer $TOKEN"
```

## Git Workflow

### Branch Strategy

- `main`: Production-ready code
- `feat/*`: Feature branches
- `fix/*`: Bug fix branches
- `refactor/*`: Refactoring branches
- `docs/*`: Documentation branches

### Before Committing

```bash
# 1. Run tests
bash test.sh

# 2. Check code style (if linter configured)
flake8 computor-backend/src/computor_backend/

# 3. Run type checker (if mypy configured)
mypy computor-backend/src/computor_backend/

# 4. Stage changes
git add .

# 5. Commit
git commit -m "feat(submissions): add grading endpoint"

# 6. Push
git push origin feat/your-feature-name
```

### Keeping Branch Updated

```bash
# Pull latest main
git checkout main
git pull origin main

# Rebase your branch
git checkout feat/your-feature-name
git rebase main

# Or merge
git merge main
```

## Next Steps

- Learn about [Backend Architecture](04-backend-architecture.md)
- Understand [EntityInterface Pattern](05-entityinterface-pattern.md)
- Explore [Permission System](06-permission-system.md)

---

**Previous**: [← Code Organization](02-code-organization.md) | **Next**: [Backend Architecture →](04-backend-architecture.md)

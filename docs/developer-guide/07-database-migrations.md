# Database & Migrations

This guide covers database management, SQLAlchemy models, and Alembic migrations in Computor.

## Database Architecture

### Technology Stack

- **PostgreSQL 16**: Primary database
- **SQLAlchemy 2.0**: ORM for database access
- **Alembic**: Database migration tool
- **psycopg2**: PostgreSQL adapter

### Database Schema

The database follows a normalized relational schema with the following entity groups:

1. **Auth**: Users, Accounts, Profiles, Sessions
2. **Organization**: Organizations, CourseFamilies
3. **Course**: Courses, CourseContent, CourseMembers, CourseGroups
4. **Submission**: SubmissionGroups, SubmissionArtifacts, SubmissionGrades
5. **Result**: Results, TestCases
6. **Execution**: ExecutionBackends, Deployments
7. **Example**: Examples, ExampleRepositories, ExampleVersions
8. **System**: Roles, Claims, Groups

## SQLAlchemy Models

### Base Model

All models inherit from a base class with audit fields:

```python
# computor-backend/src/computor_backend/model/base.py
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class AuditMixin:
    """Mixin for audit fields."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String)
    updated_by = Column(String)
    archived_at = Column(DateTime)  # Soft delete

class Base(Base, AuditMixin):
    """Base model with audit fields."""
    __abstract__ = True
```

### Example Model

```python
# computor-backend/src/computor_backend/model/course.py
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.orm import relationship
from computor_backend.model.base import Base

class Course(Base):
    """Course model."""
    __tablename__ = "courses"

    # Primary key
    id = Column(String, primary_key=True)

    # Basic fields
    name = Column(String(255), nullable=False)
    description = Column(Text)
    course_family_id = Column(String, ForeignKey("course_families.id"), nullable=False)

    # Date fields
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # Status
    is_active = Column(Boolean, default=True)

    # Relationships
    course_family = relationship("CourseFamily", back_populates="courses")
    members = relationship("CourseMember", back_populates="course", cascade="all, delete-orphan")
    contents = relationship("CourseContent", back_populates="course", cascade="all, delete-orphan")

    # Audit fields inherited from Base:
    # created_at, updated_at, created_by, updated_by, archived_at

    def __repr__(self):
        return f"<Course(id={self.id}, name={self.name})>"
```

### Model Patterns

#### Foreign Keys

Always use proper foreign key constraints:

```python
class CourseMember(Base):
    __tablename__ = "course_members"

    id = Column(String, primary_key=True)
    course_id = Column(String, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)

    # Relationships
    course = relationship("Course", back_populates="members")
    user = relationship("User")
```

#### Relationships

Define bidirectional relationships:

```python
# Parent model
class Course(Base):
    __tablename__ = "courses"
    id = Column(String, primary_key=True)

    # One-to-many relationship
    members = relationship("CourseMember", back_populates="course")

# Child model
class CourseMember(Base):
    __tablename__ = "course_members"
    id = Column(String, primary_key=True)
    course_id = Column(String, ForeignKey("courses.id"))

    # Many-to-one relationship
    course = relationship("Course", back_populates="members")
```

#### Cascade Deletes

Use cascades to maintain referential integrity:

```python
class Course(Base):
    __tablename__ = "courses"

    # Delete members when course is deleted
    members = relationship(
        "CourseMember",
        back_populates="course",
        cascade="all, delete-orphan"
    )

    # Delete contents when course is deleted
    contents = relationship(
        "CourseContent",
        back_populates="course",
        cascade="all, delete-orphan"
    )
```

#### Indexes

Add indexes for frequently queried columns:

```python
from sqlalchemy import Index

class SubmissionArtifact(Base):
    __tablename__ = "submission_artifacts"

    id = Column(String, primary_key=True)
    submission_group_id = Column(String, ForeignKey("submission_groups.id"))
    created_at = Column(DateTime, nullable=False)

    # Add index for faster queries
    __table_args__ = (
        Index('ix_submission_artifacts_group_id', 'submission_group_id'),
        Index('ix_submission_artifacts_created_at', 'created_at'),
    )
```

#### Unique Constraints

Enforce uniqueness at database level:

```python
from sqlalchemy import UniqueConstraint

class CourseMember(Base):
    __tablename__ = "course_members"

    id = Column(String, primary_key=True)
    course_id = Column(String, ForeignKey("courses.id"))
    user_id = Column(String, ForeignKey("users.id"))

    # Ensure user can only be member once per course
    __table_args__ = (
        UniqueConstraint('course_id', 'user_id', name='uq_course_member'),
    )
```

## Alembic Migrations

### Configuration

Alembic is configured in `alembic.ini` and `computor-backend/src/computor_backend/alembic/env.py`:

```python
# computor-backend/src/computor_backend/alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import all models for autogenerate
from computor_backend.model.base import Base
from computor_backend.model.auth import User, Account, Profile
from computor_backend.model.organization import Organization
from computor_backend.model.course import Course, CourseMember, CourseContent
# ... import all models

target_metadata = Base.metadata

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()
```

### Creating Migrations

#### Auto-Generate Migration

Let Alembic detect model changes:

```bash
# From computor-backend directory
alembic revision --autogenerate -m "add submission grades table"
```

This creates a new migration file in `computor-backend/src/computor_backend/alembic/versions/`.

#### Review Generated Migration

**Always review auto-generated migrations** before applying:

```python
# versions/abc123_add_submission_grades_table.py
"""add submission grades table

Revision ID: abc123
Revises: def456
Create Date: 2025-01-15 10:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'abc123'
down_revision = 'def456'
branch_labels = None
depends_on = None

def upgrade():
    # Auto-generated
    op.create_table(
        'submission_grades',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('artifact_id', sa.String(), nullable=False),
        sa.Column('grade', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['artifact_id'], ['submission_artifacts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Add indexes (manually if needed)
    op.create_index('ix_submission_grades_artifact_id', 'submission_grades', ['artifact_id'])

def downgrade():
    op.drop_index('ix_submission_grades_artifact_id', 'submission_grades')
    op.drop_table('submission_grades')
```

#### Manual Migration

For data migrations or complex changes:

```bash
alembic revision -m "populate default course roles"
```

```python
# versions/abc124_populate_default_course_roles.py
"""populate default course roles

Revision ID: abc124
Revises: abc123
"""
from alembic import op
import sqlalchemy as sa

revision = 'abc124'
down_revision = 'abc123'

def upgrade():
    # Insert default roles
    op.execute("""
        INSERT INTO course_roles (id, name, hierarchy_level)
        VALUES
            ('_student', 'Student', 1),
            ('_tutor', 'Tutor', 2),
            ('_lecturer', 'Lecturer', 3),
            ('_maintainer', 'Maintainer', 4),
            ('_owner', 'Owner', 5)
    """)

def downgrade():
    op.execute("DELETE FROM course_roles WHERE id IN ('_student', '_tutor', '_lecturer', '_maintainer', '_owner')")
```

### Applying Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific number of migrations
alembic upgrade +2

# Apply to specific revision
alembic upgrade abc123

# Show current version
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic history --indicate-current
```

### Rolling Back Migrations

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade abc123

# Rollback all migrations
alembic downgrade base
```

### Migration Best Practices

#### 1. Test Migrations Locally

Always test migrations before deploying:

```bash
# Backup database first
pg_dump -h localhost -U postgres computor > backup.sql

# Apply migration
alembic upgrade head

# Test application
bash api.sh
# Run tests, check functionality

# If issues, rollback
alembic downgrade -1

# Restore backup if needed
psql -h localhost -U postgres computor < backup.sql
```

#### 2. Make Migrations Reversible

Always implement `downgrade()`:

```python
def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(20)))

def downgrade():
    op.drop_column('users', 'phone')
```

#### 3. Handle Data Migrations Carefully

Use separate migrations for schema and data changes:

```python
# Migration 1: Add column (nullable)
def upgrade():
    op.add_column('users', sa.Column('status', sa.String(20), nullable=True))

# Migration 2: Populate data
def upgrade():
    op.execute("UPDATE users SET status = 'active' WHERE status IS NULL")

# Migration 3: Make non-nullable
def upgrade():
    op.alter_column('users', 'status', nullable=False)
```

#### 4. Avoid Breaking Changes

Add columns as nullable first:

```python
# ✅ Good: Add as nullable, populate, then make non-nullable
# Migration 1
def upgrade():
    op.add_column('courses', sa.Column('code', sa.String(20), nullable=True))

# Migration 2 (after deployment and data population)
def upgrade():
    op.alter_column('courses', 'code', nullable=False)

# ❌ Bad: Add as non-nullable immediately
def upgrade():
    op.add_column('courses', sa.Column('code', sa.String(20), nullable=False))
```

## Database Sessions

### Session Management

Database sessions are managed via FastAPI dependency injection:

```python
# computor-backend/src/computor_backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from computor_backend.settings import settings

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Using Sessions in Endpoints

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from computor_backend.database import get_db

@router.get("/courses/{course_id}")
async def get_course(
    course_id: str,
    db: Session = Depends(get_db),
):
    course = db.query(Course).filter_by(id=course_id).first()
    return course
```

### Transaction Management

#### Auto-Commit Pattern

Most operations use auto-commit:

```python
def create_course(course_data: CourseCreate, db: Session) -> Course:
    """Create course."""
    course = Course(id=str(uuid4()), **course_data.dict())
    db.add(course)
    db.commit()  # Commit transaction
    db.refresh(course)  # Refresh to get generated fields
    return course
```

#### Manual Transaction

For complex operations requiring atomic commits:

```python
def enroll_students_bulk(course_id: str, student_ids: List[str], db: Session):
    """Enroll multiple students atomically."""
    try:
        for student_id in student_ids:
            member = CourseMember(
                id=str(uuid4()),
                course_id=course_id,
                user_id=student_id,
                role="_student",
            )
            db.add(member)

        db.commit()  # All or nothing
    except Exception as e:
        db.rollback()  # Rollback on error
        raise
```

#### Using Context Manager

```python
from contextlib import contextmanager

@contextmanager
def transaction(db: Session):
    """Transaction context manager."""
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise

# Usage
with transaction(db):
    db.add(user)
    db.add(profile)
    # Both committed or both rolled back
```

## Querying

### Basic Queries

```python
# Get by ID
user = db.query(User).filter_by(id=user_id).first()

# Get by multiple fields
user = db.query(User).filter_by(username="admin", is_active=True).first()

# Get all
users = db.query(User).all()

# Get with limit/offset
users = db.query(User).offset(10).limit(20).all()

# Count
count = db.query(User).count()

# Check existence
exists = db.query(User).filter_by(id=user_id).first() is not None
```

### Filtering

```python
from sqlalchemy import and_, or_, not_

# Simple filter
courses = db.query(Course).filter(Course.is_active == True).all()

# Multiple conditions (AND)
courses = db.query(Course).filter(
    Course.is_active == True,
    Course.start_date <= datetime.now(),
).all()

# OR conditions
courses = db.query(Course).filter(
    or_(
        Course.name.like("%Python%"),
        Course.name.like("%Java%"),
    )
).all()

# NOT condition
courses = db.query(Course).filter(
    not_(Course.archived_at.isnot(None))
).all()

# IN operator
courses = db.query(Course).filter(Course.id.in_(course_ids)).all()
```

### Joins

```python
from sqlalchemy.orm import joinedload

# Inner join
results = db.query(Course)\
    .join(CourseFamily)\
    .filter(CourseFamily.name == "Computer Science")\
    .all()

# Left outer join
results = db.query(Course)\
    .outerjoin(CourseMember)\
    .all()

# Eager loading (avoid N+1 queries)
courses = db.query(Course)\
    .options(joinedload(Course.course_family))\
    .all()

# Multiple eager loads
courses = db.query(Course)\
    .options(
        joinedload(Course.course_family),
        joinedload(Course.members),
    )\
    .all()
```

### Ordering

```python
# Ascending
courses = db.query(Course).order_by(Course.name).all()

# Descending
courses = db.query(Course).order_by(Course.created_at.desc()).all()

# Multiple orders
courses = db.query(Course)\
    .order_by(Course.course_family_id, Course.name)\
    .all()
```

### Aggregation

```python
from sqlalchemy import func

# Count
member_count = db.query(func.count(CourseMember.id))\
    .filter(CourseMember.course_id == course_id)\
    .scalar()

# Sum
total_size = db.query(func.sum(SubmissionArtifact.file_size))\
    .filter(SubmissionArtifact.submission_group_id == group_id)\
    .scalar()

# Average
avg_grade = db.query(func.avg(SubmissionGrade.grade))\
    .join(SubmissionArtifact)\
    .filter(SubmissionArtifact.submission_group_id == group_id)\
    .scalar()

# Group by
stats = db.query(
    Course.id,
    func.count(CourseMember.id).label('member_count')
)\
    .join(CourseMember)\
    .group_by(Course.id)\
    .all()
```

## Database Utilities

### Soft Delete

Implement soft delete using `archived_at`:

```python
def soft_delete_course(course_id: str, user_id: str, db: Session):
    """Soft delete course."""
    course = db.query(Course).filter_by(id=course_id).first()
    if not course:
        raise NotFoundException("Course not found")

    course.archived_at = datetime.utcnow()
    course.updated_by = user_id
    db.commit()

def get_active_courses(db: Session):
    """Get only non-archived courses."""
    return db.query(Course)\
        .filter(Course.archived_at.is_(None))\
        .all()
```

### Bulk Operations

```python
# Bulk insert
members = [
    CourseMember(id=str(uuid4()), course_id=course_id, user_id=uid, role="_student")
    for uid in student_ids
]
db.bulk_save_objects(members)
db.commit()

# Bulk update
db.query(CourseMember)\
    .filter(CourseMember.course_id == course_id)\
    .update({"role": "_tutor"})
db.commit()

# Bulk delete
db.query(CourseMember)\
    .filter(CourseMember.course_id == course_id)\
    .delete()
db.commit()
```

## Testing with Database

### Test Database Setup

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from computor_backend.model.base import Base

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine("postgresql://postgres:postgres@localhost/computor_test")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db(test_engine):
    """Create test database session."""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()

    yield session

    session.rollback()
    session.close()
```

### Test Fixtures

```python
@pytest.fixture
def test_course(db):
    """Create test course."""
    course = Course(
        id="test-course-1",
        name="Test Course",
        course_family_id="test-family-1",
    )
    db.add(course)
    db.commit()
    yield course
    db.delete(course)
    db.commit()
```

## Troubleshooting

### Common Issues

#### Issue: Migration Conflict

**Problem**: Multiple developers created migrations from same base.

**Solution**: Rebase migrations:

```bash
# Pull latest migrations
git pull

# Delete your migration file
rm computor-backend/src/computor_backend/alembic/versions/your_migration.py

# Regenerate
alembic revision --autogenerate -m "your change"
```

#### Issue: Alembic Out of Sync

**Problem**: Database schema doesn't match Alembic version.

**Solution**: Stamp current version:

```bash
# Check current database state
alembic current

# Stamp database with correct version
alembic stamp head
```

#### Issue: Foreign Key Violation

**Problem**: Cannot delete record due to foreign key constraint.

**Solution**: Use cascade delete or delete children first:

```python
# Option 1: Cascade delete (in model)
members = relationship("CourseMember", cascade="all, delete-orphan")

# Option 2: Delete children first
db.query(CourseMember).filter_by(course_id=course_id).delete()
db.query(Course).filter_by(id=course_id).delete()
db.commit()
```

## Next Steps

- Learn about [Temporal Workflows](08-temporal-workflows.md)
- Explore [Repository Pattern](09-repository-pattern.md)
- Review [Testing Guide](11-testing-guide.md)

---

**Previous**: [← Permission System](06-permission-system.md) | **Next**: [Temporal Workflows →](08-temporal-workflows.md)

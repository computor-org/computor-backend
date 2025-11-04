# Permission System

This guide explains Computor's Role-Based Access Control (RBAC) system and how to implement permission checks.

## Overview

Computor uses a **hierarchical RBAC system** with:
- **User roles**: System-wide roles (admin, user)
- **Course roles**: Course-specific roles (_owner, _maintainer, _lecturer, _tutor, _student)
- **Claims**: Fine-grained permissions
- **Principal**: Current user with all their permissions
- **Permission handlers**: Entity-specific permission logic

## Core Concepts

### Principal

The `Principal` class represents the authenticated user with all their permissions:

```python
# computor-backend/src/computor_backend/permissions/principal.py
from dataclasses import dataclass
from typing import Dict, Set, Optional

@dataclass
class Principal:
    """Represents an authenticated user with permissions."""
    user_id: str
    username: str
    is_admin: bool
    claims: 'Claims'

    def has_course_role(self, course_id: str, required_role: str) -> bool:
        """Check if user has a specific role in a course."""
        if self.is_admin:
            return True

        user_role = self.claims.course_roles.get(course_id)
        if not user_role:
            return False

        return is_role_sufficient(user_role, required_role)

    def can_access_course(self, course_id: str, action: str) -> bool:
        """Check if user can perform action on course."""
        if self.is_admin:
            return True

        return course_id in self.claims.course_roles
```

### Claims

Claims represent all permissions a user has:

```python
@dataclass
class Claims:
    """User's permissions and roles."""
    user_id: str
    username: str
    is_admin: bool
    roles: Set[str]                    # System roles
    groups: Set[str]                   # User groups
    course_roles: Dict[str, str]       # {course_id: role}
    organization_roles: Dict[str, str] # {org_id: role}

    @classmethod
    def from_user(cls, user: User, db: Session) -> 'Claims':
        """Build claims from user and database."""
        # Load user's course memberships
        course_roles = {}
        memberships = db.query(CourseMember)\
            .filter_by(user_id=user.id)\
            .all()

        for member in memberships:
            course_roles[member.course_id] = member.role

        return cls(
            user_id=user.id,
            username=user.username,
            is_admin=user.is_admin,
            roles=set(user.roles),
            groups=set(),
            course_roles=course_roles,
            organization_roles={},
        )
```

### Role Hierarchy

Course roles follow a hierarchy where higher roles inherit lower role permissions:

```
_owner > _maintainer > _lecturer > _tutor > _student
```

```python
# computor-backend/src/computor_backend/permissions/principal.py
course_role_hierarchy = {
    "_owner": 5,
    "_maintainer": 4,
    "_lecturer": 3,
    "_tutor": 2,
    "_student": 1,
}

def is_role_sufficient(user_role: str, required_role: str) -> bool:
    """Check if user's role meets the required role."""
    user_level = course_role_hierarchy.get(user_role, 0)
    required_level = course_role_hierarchy.get(required_role, 0)
    return user_level >= required_level
```

**Examples**:
- Lecturer has all permissions of tutor and student
- Owner has all permissions of maintainer, lecturer, tutor, and student
- Tutor can access student resources but not lecturer resources

## Getting Current Principal

Use the `get_current_principal` dependency in all API endpoints:

```python
# API endpoint
from typing import Annotated
from fastapi import Depends
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal

@router.get("/courses/{course_id}")
async def get_course(
    course_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    return get_course_logic(course_id, permissions, db)
```

The `get_current_principal` function:

```python
# computor-backend/src/computor_backend/permissions/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_principal(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Principal:
    """Get current authenticated user as Principal."""
    token = credentials.credentials

    # Verify token and get user
    user = verify_token(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    # Build claims
    claims = build_claims(user, db)

    # Create principal
    return Principal(
        user_id=user.id,
        username=user.username,
        is_admin=user.is_admin,
        claims=claims,
    )
```

## Permission Checking Patterns

### Pattern 1: Course-Level Permissions

Check if user has required role in a course:

```python
# business_logic/courses.py
from computor_backend.permissions.core import check_course_permissions
from computor_backend.api.exceptions import NotFoundException, ForbiddenException

def get_course(
    course_id: str,
    permissions: Principal,
    db: Session,
) -> CourseGet:
    """Get course by ID."""
    # Fetch course
    course = db.query(Course).filter_by(id=course_id).first()
    if not course:
        raise NotFoundException("Course not found")

    # Check permissions - requires at least _student role
    check_course_permissions(permissions, course, "read", required_role="_student")

    return CourseGet.from_orm(course)
```

The `check_course_permissions` function:

```python
# computor-backend/src/computor_backend/permissions/core.py
def check_course_permissions(
    principal: Principal,
    course: Course,
    action: str,
    required_role: str = "_student",
) -> None:
    """Check if user has permission to perform action on course."""
    # Admins bypass all checks
    if principal.is_admin:
        return

    # Check course role
    if not principal.has_course_role(course.id, required_role):
        raise ForbiddenException(
            f"Requires {required_role} role or higher in course {course.id}"
        )
```

### Pattern 2: Resource Owner Permissions

Check if user owns a resource:

```python
def update_submission_artifact(
    artifact_id: str,
    update_data: SubmissionArtifactUpdate,
    permissions: Principal,
    db: Session,
) -> SubmissionArtifactGet:
    """Update submission artifact."""
    # Fetch artifact
    artifact = db.query(SubmissionArtifact).filter_by(id=artifact_id).first()
    if not artifact:
        raise NotFoundException("Artifact not found")

    # Get related entities
    submission_group = artifact.submission_group
    course = submission_group.course_content.course

    # Permission logic:
    # - Tutors and above can update any artifact
    # - Students can only update their own artifacts
    if not permissions.has_course_role(course.id, "_tutor"):
        # Check if student is member of submission group
        is_member = any(
            m.student_id == permissions.user_id
            for m in submission_group.members
        )
        if not is_member:
            raise ForbiddenException("Cannot update other students' artifacts")

    # Update artifact
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(artifact, field, value)

    artifact.updated_by = permissions.user_id
    db.commit()
    db.refresh(artifact)

    return SubmissionArtifactGet.from_orm(artifact)
```

### Pattern 3: Admin-Only Permissions

Restrict actions to admins:

```python
def delete_organization(
    organization_id: str,
    permissions: Principal,
    db: Session,
) -> None:
    """Delete organization (admin only)."""
    # Admin check
    if not permissions.is_admin:
        raise ForbiddenException("Only admins can delete organizations")

    # Fetch and delete
    org = db.query(Organization).filter_by(id=organization_id).first()
    if not org:
        raise NotFoundException("Organization not found")

    db.delete(org)
    db.commit()
```

### Pattern 4: Multi-Level Permissions

Check permissions at multiple levels:

```python
def create_course_content(
    content_data: CourseContentCreate,
    permissions: Principal,
    db: Session,
) -> CourseContentGet:
    """Create course content (lecturer only)."""
    # Fetch course
    course = db.query(Course).filter_by(id=content_data.course_id).first()
    if not course:
        raise NotFoundException("Course not found")

    # Check permissions - requires lecturer role
    check_course_permissions(
        permissions,
        course,
        "create_content",
        required_role="_lecturer"
    )

    # Create content
    content = CourseContent(
        id=str(uuid4()),
        **content_data.dict(),
        created_by=permissions.user_id,
    )
    db.add(content)
    db.commit()
    db.refresh(content)

    return CourseContentGet.from_orm(content)
```

## Permission Handlers

Permission handlers provide entity-specific permission logic:

```python
# computor-backend/src/computor_backend/permissions/handlers_impl.py
from computor_backend.permissions.handlers import BasePermissionHandler

class CoursePermissionHandler(BasePermissionHandler):
    """Permission handler for Course entity."""

    def check_read_permission(self, principal: Principal, entity: Course) -> None:
        """Check read permission for course."""
        if principal.is_admin:
            return

        # Must be at least a student in the course
        if not principal.has_course_role(entity.id, "_student"):
            raise ForbiddenException(f"No access to course {entity.id}")

    def check_write_permission(self, principal: Principal, entity: Course) -> None:
        """Check write permission for course."""
        if principal.is_admin:
            return

        # Must be at least a lecturer to modify course
        if not principal.has_course_role(entity.id, "_lecturer"):
            raise ForbiddenException(f"No permission to modify course {entity.id}")

    def check_delete_permission(self, principal: Principal, entity: Course) -> None:
        """Check delete permission for course."""
        if principal.is_admin:
            return

        # Must be owner to delete course
        if not principal.has_course_role(entity.id, "_owner"):
            raise ForbiddenException(f"Only owners can delete course {entity.id}")
```

### Registering Permission Handlers

Handlers are registered at application startup:

```python
# computor-backend/src/computor_backend/permissions/core.py
from computor_backend.permissions.handlers import permission_registry
from computor_backend.permissions.handlers_impl import (
    CoursePermissionHandler,
    CourseMemberPermissionHandler,
    SubmissionArtifactPermissionHandler,
)
from computor_backend.model.course import Course, CourseMember
from computor_backend.model.artifact import SubmissionArtifact

def initialize_permission_handlers():
    """Initialize and register all permission handlers."""
    # Course-related entities
    permission_registry.register(Course, CoursePermissionHandler(Course))
    permission_registry.register(CourseMember, CourseMemberPermissionHandler(CourseMember))

    # Submission entities
    permission_registry.register(
        SubmissionArtifact,
        SubmissionArtifactPermissionHandler(SubmissionArtifact)
    )

    # ... more registrations
```

## Common Permission Scenarios

### Scenario 1: Student Viewing Their Submissions

```python
def list_student_submissions(
    course_id: str,
    permissions: Principal,
    db: Session,
) -> List[SubmissionArtifactList]:
    """List submissions for current student."""
    # Check course access
    if not permissions.has_course_role(course_id, "_student"):
        raise ForbiddenException(f"Not enrolled in course {course_id}")

    # Get student's submission groups
    groups = db.query(SubmissionGroup)\
        .join(SubmissionGroupMember)\
        .filter(
            SubmissionGroupMember.student_id == permissions.user_id,
            SubmissionGroup.course_content.has(course_id=course_id)
        )\
        .all()

    # Get artifacts from these groups
    artifacts = []
    for group in groups:
        artifacts.extend(group.artifacts)

    return [SubmissionArtifactList.from_orm(a) for a in artifacts]
```

### Scenario 2: Tutor Viewing All Submissions

```python
def list_all_submissions(
    course_id: str,
    permissions: Principal,
    db: Session,
) -> List[SubmissionArtifactList]:
    """List all submissions in course (tutor+)."""
    # Fetch course
    course = db.query(Course).filter_by(id=course_id).first()
    if not course:
        raise NotFoundException("Course not found")

    # Check permissions - requires tutor role
    check_course_permissions(permissions, course, "read", required_role="_tutor")

    # Get all artifacts in course
    artifacts = db.query(SubmissionArtifact)\
        .join(SubmissionGroup)\
        .join(CourseContent)\
        .filter(CourseContent.course_id == course_id)\
        .order_by(SubmissionArtifact.created_at.desc())\
        .all()

    return [SubmissionArtifactList.from_orm(a) for a in artifacts]
```

### Scenario 3: Lecturer Creating Assignments

```python
def create_assignment(
    assignment_data: CourseContentCreate,
    permissions: Principal,
    db: Session,
) -> CourseContentGet:
    """Create assignment (lecturer only)."""
    # Fetch course
    course = db.query(Course).filter_by(id=assignment_data.course_id).first()
    if not course:
        raise NotFoundException("Course not found")

    # Check permissions - requires lecturer
    check_course_permissions(
        permissions,
        course,
        "create_assignment",
        required_role="_lecturer"
    )

    # Create assignment
    assignment = CourseContent(
        id=str(uuid4()),
        **assignment_data.dict(),
        created_by=permissions.user_id,
    )
    db.add(assignment)
    db.commit()

    return CourseContentGet.from_orm(assignment)
```

### Scenario 4: Admin Overriding Permissions

```python
def force_delete_submission(
    submission_id: str,
    permissions: Principal,
    db: Session,
) -> None:
    """Force delete submission (admin only)."""
    # Admin check
    if not permissions.is_admin:
        raise ForbiddenException("Only admins can force delete submissions")

    # Delete without further checks
    submission = db.query(SubmissionArtifact).filter_by(id=submission_id).first()
    if not submission:
        raise NotFoundException("Submission not found")

    db.delete(submission)
    db.commit()
```

## Testing Permissions

### Unit Tests

Test permission logic in isolation:

```python
# tests/test_permissions.py
import pytest
from computor_backend.permissions.principal import Principal, Claims
from computor_backend.permissions.core import check_course_permissions
from computor_backend.api.exceptions import ForbiddenException

def test_student_can_read_course():
    """Test that students can read courses they're enrolled in."""
    claims = Claims(
        user_id="student-1",
        username="student",
        is_admin=False,
        roles=set(),
        groups=set(),
        course_roles={"course-1": "_student"},
        organization_roles={},
    )
    principal = Principal(
        user_id="student-1",
        username="student",
        is_admin=False,
        claims=claims,
    )

    course = Course(id="course-1", name="Test Course")

    # Should not raise exception
    check_course_permissions(principal, course, "read", required_role="_student")

def test_student_cannot_modify_course():
    """Test that students cannot modify courses."""
    claims = Claims(
        user_id="student-1",
        username="student",
        is_admin=False,
        roles=set(),
        groups=set(),
        course_roles={"course-1": "_student"},
        organization_roles={},
    )
    principal = Principal(
        user_id="student-1",
        username="student",
        is_admin=False,
        claims=claims,
    )

    course = Course(id="course-1", name="Test Course")

    # Should raise ForbiddenException
    with pytest.raises(ForbiddenException):
        check_course_permissions(principal, course, "update", required_role="_lecturer")

def test_lecturer_can_modify_course():
    """Test that lecturers can modify courses."""
    claims = Claims(
        user_id="lecturer-1",
        username="lecturer",
        is_admin=False,
        roles=set(),
        groups=set(),
        course_roles={"course-1": "_lecturer"},
        organization_roles={},
    )
    principal = Principal(
        user_id="lecturer-1",
        username="lecturer",
        is_admin=False,
        claims=claims,
    )

    course = Course(id="course-1", name="Test Course")

    # Should not raise exception
    check_course_permissions(principal, course, "update", required_role="_lecturer")

def test_admin_bypasses_all_checks():
    """Test that admins bypass all permission checks."""
    claims = Claims(
        user_id="admin-1",
        username="admin",
        is_admin=True,
        roles=set(),
        groups=set(),
        course_roles={},  # No course roles
        organization_roles={},
    )
    principal = Principal(
        user_id="admin-1",
        username="admin",
        is_admin=True,
        claims=claims,
    )

    course = Course(id="course-1", name="Test Course")

    # Should not raise exception even without course role
    check_course_permissions(principal, course, "update", required_role="_owner")
```

### Integration Tests

Test permissions in API endpoints:

```python
# tests/test_api_permissions.py
def test_student_can_view_own_submissions(client, student_token, test_submission):
    """Test that students can view their own submissions."""
    response = client.get(
        f"/api/v1/submissions/artifacts/{test_submission.id}",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 200

def test_student_cannot_view_other_submissions(client, student_token, other_student_submission):
    """Test that students cannot view other students' submissions."""
    response = client.get(
        f"/api/v1/submissions/artifacts/{other_student_submission.id}",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 403

def test_tutor_can_view_all_submissions(client, tutor_token, any_submission):
    """Test that tutors can view all submissions in their course."""
    response = client.get(
        f"/api/v1/submissions/artifacts/{any_submission.id}",
        headers={"Authorization": f"Bearer {tutor_token}"}
    )
    assert response.status_code == 200
```

## Best Practices

### 1. Always Check Permissions

Every business logic function should check permissions:

```python
# ✅ Good
def get_resource(resource_id: str, permissions: Principal, db: Session):
    check_permissions(permissions, resource_id)
    return fetch_resource(resource_id, db)

# ❌ Bad
def get_resource(resource_id: str, db: Session):
    return fetch_resource(resource_id, db)  # No permission check!
```

### 2. Check Permissions Early

Check permissions before expensive operations:

```python
# ✅ Good
def process_submission(submission_id: str, permissions: Principal, db: Session):
    submission = db.query(Submission).get(submission_id)
    check_permissions(permissions, submission)  # Check first
    expensive_operation(submission)  # Then process

# ❌ Bad
def process_submission(submission_id: str, permissions: Principal, db: Session):
    submission = db.query(Submission).get(submission_id)
    expensive_operation(submission)  # Process first
    check_permissions(permissions, submission)  # Check after!
```

### 3. Use Descriptive Error Messages

```python
# ✅ Good
if not permissions.has_course_role(course_id, "_tutor"):
    raise ForbiddenException(
        f"Requires tutor role or higher to grade submissions in course {course_id}"
    )

# ❌ Bad
if not permissions.has_course_role(course_id, "_tutor"):
    raise ForbiddenException("Access denied")
```

### 4. Admin Bypass Pattern

Always allow admins to bypass checks:

```python
# ✅ Good
def check_permissions(permissions: Principal, resource):
    if permissions.is_admin:
        return  # Admins bypass all checks

    # Regular permission logic
    if not has_access(permissions, resource):
        raise ForbiddenException()

# ❌ Bad
def check_permissions(permissions: Principal, resource):
    # No admin bypass - admins blocked too!
    if not has_access(permissions, resource):
        raise ForbiddenException()
```

### 5. Separate Permission Logic

Keep permission logic in business layer, not API:

```python
# ✅ Good: Permission logic in business layer
# api/courses.py
@router.get("/courses/{course_id}")
async def get_course(course_id: str, permissions: Annotated[Principal, Depends(get_current_principal)], db: Session = Depends(get_db)):
    return get_course_logic(course_id, permissions, db)

# business_logic/courses.py
def get_course_logic(course_id: str, permissions: Principal, db: Session):
    course = db.query(Course).get(course_id)
    check_course_permissions(permissions, course, "read")
    return course

# ❌ Bad: Permission logic in API
@router.get("/courses/{course_id}")
async def get_course(course_id: str, permissions: Annotated[Principal, Depends(get_current_principal)], db: Session = Depends(get_db)):
    course = db.query(Course).get(course_id)
    if not permissions.has_course_role(course_id, "_student"):
        raise ForbiddenException()
    return course
```

## Next Steps

- Learn about [Database & Migrations](07-database-migrations.md)
- Explore [Temporal Workflows](08-temporal-workflows.md)
- Review [API Development](10-api-development.md)

---

**Previous**: [← EntityInterface Pattern](05-entityinterface-pattern.md) | **Next**: [Database & Migrations →](07-database-migrations.md)

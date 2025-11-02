"""
Refactored permissions module using the handler registry pattern.
This module provides a cleaner, more maintainable approach to permission management.
"""

from typing import Any, List, Optional, Dict, Iterable
from sqlalchemy.orm import Session
from sqlalchemy import select

from computor_backend.api.exceptions import ForbiddenException
from computor_backend.permissions.handlers import permission_registry
from computor_backend.permissions.handlers_impl import (
    UserPermissionHandler,
    AccountPermissionHandler,
    ProfilePermissionHandler,
    StudentProfilePermissionHandler,
    CoursePermissionHandler,
    OrganizationPermissionHandler,
    CourseFamilyPermissionHandler,
    CourseContentTypePermissionHandler,
    CourseContentPermissionHandler,
    CourseMemberPermissionHandler,
    ReadOnlyPermissionHandler,
    ResultPermissionHandler,
    MessagePermissionHandler,
    ExamplePermissionHandler
)

# Import refactored Principal and related classes
from computor_backend.permissions.principal import (
    Principal,
    Claims,
    build_claims,
    course_role_hierarchy
)

# Import models for registration
from computor_backend.model.auth import User, Account, Profile, StudentProfile, Session as UserSession
from computor_backend.model.course import (
    Course, CourseFamily, CourseMember, CourseContent,
    CourseContentType, CourseContentKind, CourseRole, CourseGroup,
    CourseMemberComment,
    SubmissionGroup, SubmissionGroupMember
)
from computor_backend.model.organization import Organization
from computor_backend.model.result import Result
from computor_backend.model.message import Message
from computor_backend.model.artifact import (
    SubmissionArtifact, ResultArtifact,
    SubmissionGrade, SubmissionReview
)
from computor_backend.model.role import Role, RoleClaim, UserRole
from computor_backend.model.group import Group, GroupClaim, UserGroup
from computor_backend.model.example import Example, ExampleRepository, ExampleVersion, ExampleDependency
from computor_backend.model.language import Language
from computor_backend.model.service import Service, ServiceType, ApiToken


def initialize_permission_handlers():
    """Initialize and register all permission handlers"""
    
    # User-related entities
    permission_registry.register(User, UserPermissionHandler(User))
    permission_registry.register(Account, AccountPermissionHandler(Account))
    permission_registry.register(Profile, ProfilePermissionHandler(Profile))
    permission_registry.register(StudentProfile, StudentProfilePermissionHandler(StudentProfile))
    permission_registry.register(UserSession, ProfilePermissionHandler(UserSession))
    
    # Organization and Course hierarchy
    permission_registry.register(Organization, OrganizationPermissionHandler(Organization))
    permission_registry.register(CourseFamily, CourseFamilyPermissionHandler(CourseFamily))
    permission_registry.register(Course, CoursePermissionHandler(Course))
    
    # Course-related entities
    permission_registry.register(CourseContentType, CourseContentTypePermissionHandler(CourseContentType))
    permission_registry.register(CourseContent, CourseContentPermissionHandler(CourseContent))
    permission_registry.register(CourseMember, CourseMemberPermissionHandler(CourseMember))
    permission_registry.register(CourseGroup, CourseMemberPermissionHandler(CourseGroup))
    permission_registry.register(CourseMemberComment, CourseMemberPermissionHandler(CourseMemberComment))
    permission_registry.register(SubmissionGroup, CourseMemberPermissionHandler(SubmissionGroup))
    permission_registry.register(SubmissionGroupMember, CourseMemberPermissionHandler(SubmissionGroupMember))
    
    # Read-only entities
    permission_registry.register(CourseRole, ReadOnlyPermissionHandler(CourseRole))
    permission_registry.register(CourseContentKind, ReadOnlyPermissionHandler(CourseContentKind))
    permission_registry.register(Language, ReadOnlyPermissionHandler(Language))
    
    # Example entities (lecturer-only access)
    permission_registry.register(Example, ExamplePermissionHandler(Example))
    permission_registry.register(ExampleRepository, ExamplePermissionHandler(ExampleRepository))
    permission_registry.register(ExampleVersion, ExamplePermissionHandler(ExampleVersion))
    permission_registry.register(ExampleDependency, ExamplePermissionHandler(ExampleDependency))
    
    # System entities - admin only by default
    permission_registry.register(Role, ReadOnlyPermissionHandler(Role))  # Roles are read-only lookup tables
    permission_registry.register(RoleClaim, ReadOnlyPermissionHandler(RoleClaim))  # Role claims are read-only
    permission_registry.register(UserRole, ReadOnlyPermissionHandler(UserRole))  # UserRole associations are read-only
    permission_registry.register(Group, ReadOnlyPermissionHandler(Group))  # Groups are read-only lookup tables
    permission_registry.register(GroupClaim, ReadOnlyPermissionHandler(GroupClaim))  # Group claims are read-only
    permission_registry.register(UserGroup, UserPermissionHandler(UserGroup))  # UserGroup can be managed
    permission_registry.register(Result, ResultPermissionHandler(Result))
    permission_registry.register(Message, MessagePermissionHandler(Message))

    # Service accounts, service types, and API tokens - admin only
    permission_registry.register(Service, UserPermissionHandler(Service))
    permission_registry.register(ServiceType, ReadOnlyPermissionHandler(ServiceType))
    permission_registry.register(ApiToken, UserPermissionHandler(ApiToken))

    # Artifact models - use CourseMemberPermissionHandler for course-scoped access
    permission_registry.register(SubmissionArtifact, CourseMemberPermissionHandler(SubmissionArtifact))
    permission_registry.register(ResultArtifact, CourseMemberPermissionHandler(ResultArtifact))
    permission_registry.register(SubmissionGrade, CourseMemberPermissionHandler(SubmissionGrade))
    permission_registry.register(SubmissionReview, CourseMemberPermissionHandler(SubmissionReview))


def check_admin(permissions: Principal) -> bool:
    """Check if principal has admin privileges"""
    return permissions.is_admin


def check_permissions(permissions: Principal, entity: Any, action: str, db: Session):
    """
    Main entry point for permission checking.
    Uses the registry pattern to delegate to appropriate handlers.
    """
    return permission_registry.check_permissions(permissions, entity, action, db)


def get_permitted_course_ids(permissions: Principal, minimum_role: str, db: Session) -> List[str]:
    """Get list of course IDs where user has at least the minimum role"""
    if permissions.is_admin:
        # Admin has access to all courses; return flat list of string IDs
        rows = db.query(Course.id).all()
        try:
            # rows may be a list of 1-tuples or Row objects; take the first column
            return [str(row[0]) for row in rows]
        except Exception:
            # Fallback: try attribute access
            return [str(getattr(row, "id", row)) for row in rows]
    
    return list(permissions.get_courses_with_role(minimum_role))


def check_course_permissions(permissions: Principal, entity: Any, course_role_id: str, db: Session):
    """Check permissions for course-related entities"""
    from computor_backend.permissions.query_builders import CoursePermissionQueryBuilder
    
    if permissions.is_admin:
        return db.query(entity)
    
    # Filter by course membership
    return CoursePermissionQueryBuilder.filter_by_course_membership(
        db.query(entity), entity, permissions.user_id, course_role_id, db
    )


# General helpers
def can_perform_on_resource(
    principal: Principal,
    subject: str,
    action: str | List[str],
    resource_id: Optional[str] = None,
) -> bool:
    """Check permissions directly on a subject (resource) with optional resource_id.

    - General permission: subject:action
    - Dependent permission: subject:action:resource_id
    """
    return principal.permitted(subject, action, resource_id)


def can_perform_with_parents(
    principal: Principal,
    action: str | List[str],
    context: Optional[Dict[str, str]] = None,
    *,
    min_course_role: Optional[str] = None,
    subject_map: Optional[Dict[str, Dict[str, Any]]] = None,
    additional_actions: Optional[Iterable[str]] = None,
) -> bool:
    """Check permissions that depend on parent IDs provided in `context`.

    - If `min_course_role` is provided and `course_id` is present in context,
      validate course-role permission using the role hierarchy.
    - For other *_id keys in context, derive a subject by stripping `_id` or use
      `subject_map` to resolve to a custom subject and action list.
    - For each extra subject, require either dependent permission on the specific ID
      or a general permission for any of the allowed actions.

    subject_map format (optional):
        {
          "execution_backend_id": {"subject": "execution_backend", "actions": ["use"]},
          "foo_id": {"subject": "foo", "actions": ["link", "get"]}
        }
    If a context key is not present in subject_map, the subject defaults to key[:-3]
    and actions default to `additional_actions` or ["create", "update", "use", "link", "assign", "get"].
    """
    if not context:
        # No parents to check, allow by default (caller can still require resource checks separately)
        return True

    # 1) Course role check if requested
    if min_course_role:
        course_id = context.get("course_id")
        if course_id and not principal.permitted("course", action, course_id, course_role=min_course_role):
            return False

    # 2) Additional parent subjects
    default_actions = list(additional_actions or ["create", "update", "use", "link", "assign", "get"])
    for key, value in context.items():
        if key == "course_id" or not key.endswith("_id"):
            continue
        # Resolve subject and actions
        subject_info = (subject_map or {}).get(key) if subject_map else None
        subject = None
        actions = None
        if subject_info:
            subject = subject_info.get("subject")
            actions = subject_info.get("actions") or default_actions
        else:
            subject = key[:-3]
            actions = default_actions

        if value and principal.permitted(subject, actions, str(value)):
            continue
        if principal.permitted(subject, actions):
            continue
        return False

    return True


# Database helper functions (keep existing implementations)
def db_get_claims(user_id: str, db: Session) -> List[tuple]:
    """Get claims for a user from database"""
    from computor_backend.model.role import RoleClaim
    from computor_backend.model.auth import User
    
    values = (
        db.query(RoleClaim.claim_type, RoleClaim.claim_value)
        .select_from(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .join(RoleClaim, RoleClaim.role_id == Role.id)
        .filter(User.id == user_id)
        .distinct(RoleClaim.claim_type, RoleClaim.claim_value)
        .all()
    )
    
    # Convert to list and add default permissions
    values = list(values)
    
    # Add default permissions for read-only entities
    values.extend([
        ("permissions", f"{CourseContentKind.__tablename__}:get"),
        ("permissions", f"{CourseContentKind.__tablename__}:list"),
        ("permissions", f"{CourseRole.__tablename__}:get"),
        ("permissions", f"{CourseRole.__tablename__}:list"),
    ])
    
    return values


def db_get_course_claims(user_id: str, db: Session) -> List[tuple]: #TODO: PERMISSIONS
    """Get course-specific claims for a user"""
    from computor_backend.model.auth import User
    
    course_members = (
        db.query(
            CourseMember.course_id,
            CourseMember.course_role_id
        )
        .select_from(User)
        .join(CourseMember, CourseMember.user_id == User.id)
        .filter(User.id == user_id)
        .all()
    )
    
    course_claims = []
    is_lecturer = False
    
    for course_id, course_role_id in course_members:
        # Store course role as a claim
        course_claims.append(("permissions", f"course:{course_role_id}:{course_id}"))
        
        # Check if user is a lecturer in any course
        if course_role_id in course_role_hierarchy.get_allowed_roles("_lecturer"):
            is_lecturer = True
    
    # Add general permissions for lecturers
    if is_lecturer:
        course_claims.extend([
            ("permissions", f"{Example.__tablename__}:get"),
            ("permissions", f"{Example.__tablename__}:list"),
            ("permissions", f"{Example.__tablename__}:create"),
            ("permissions", f"{Example.__tablename__}:update"),
            ("permissions", f"{Example.__tablename__}:upload"),
            ("permissions", f"{Example.__tablename__}:download"),
        ])
    
    return course_claims


def db_get_roles_claims(user_id: str, db: Session) -> tuple:
    """Get roles and claims for a user"""
    from computor_backend.model.auth import User
    
    values = (
        db.query(RoleClaim.role_id, RoleClaim.claim_type, RoleClaim.claim_value)
        .select_from(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .join(RoleClaim, RoleClaim.role_id == Role.id)
        .filter(User.id == user_id)
        .all()
    )
    
    role_ids = list({row.role_id for row in values})
    claim_values = [(row.claim_type, row.claim_value) for row in values]
    
    return role_ids, claim_values


def db_apply_roles(role_id: str, claims: List[str], db: Session):
    """Apply claims to a role in the database"""
    from sqlalchemy.dialects.postgresql import insert
    
    stmt = insert(RoleClaim).values([
        {"role_id": role_id, "claim_type": ct, "claim_value": cv}
        for ct, cv in claims
    ])
    
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["role_id", "claim_type", "claim_value"]
    )
    db.execute(stmt)
    db.commit()


# Initialize handlers on module import
initialize_permission_handlers()

"""Business logic for the Documents API.

Path validation, scope-aware filesystem mapping, and the reserved-name
collision check that keeps free-form documents from shadowing
entity-owned directories (or vice versa).

Read access is served by the ``static-server`` container at ``/docs``;
this module only handles the write side.
"""

from pathlib import Path
from typing import List, Literal, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from computor_backend.custom_types import Ltree
from computor_backend.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.model.course import Course, CourseFamily
from computor_backend.model.organization import Organization
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.roles import CourseRole, ScopeRole
from computor_backend.settings import settings


DocumentScope = Literal["system", "organization", "course_family", "course"]


def check_documents_write_permission(
    permissions: Principal,
    scope: DocumentScope,
    scope_id: Optional[UUID | str],
) -> None:
    """Authorize a write operation against a documents scope.

    The four levels — admin only, org-scoped ``_developer``+, family-scoped
    ``_developer``+, course ``_lecturer``+ — match the policy in the
    issue spec. Admins bypass everything; everyone else needs the
    scope-specific role.
    """
    if permissions.is_admin:
        return

    if scope == "system":
        raise ForbiddenException(
            detail="Only administrators can write at the system documents root",
        )

    if scope_id is None:
        raise BadRequestException(
            detail="scope_id is required for non-system scopes",
            context={"scope": scope},
        )

    scope_id_str = str(scope_id)

    if scope == "organization":
        if not permissions.has_organization_role(scope_id_str, ScopeRole.DEVELOPER):
            raise ForbiddenException(
                detail="Requires organization _developer or higher to write organization documents",
                context={"organization_id": scope_id_str},
            )
        return

    if scope == "course_family":
        if not permissions.has_course_family_role(scope_id_str, ScopeRole.DEVELOPER):
            raise ForbiddenException(
                detail="Requires course_family _developer or higher to write course-family documents",
                context={"course_family_id": scope_id_str},
            )
        return

    if scope == "course":
        if not permissions.has_course_role(scope_id_str, CourseRole.LECTURER):
            raise ForbiddenException(
                detail="Requires course _lecturer or higher to write course documents",
                context={"course_id": scope_id_str},
            )
        return

    raise BadRequestException(detail=f"Unknown scope: {scope}")


def validate_relative_path(rel: str) -> List[str]:
    """Split and validate a user-supplied relative path.

    Returns the cleaned list of segments. Raises ``BadRequestException``
    on traversal (``..``), absolute paths, or empty/dot segments.
    """
    if rel is None:
        raise BadRequestException(detail="path is required")
    if rel.startswith("/"):
        raise BadRequestException(detail="path must be relative")
    segments = rel.split("/")
    cleaned: List[str] = []
    for segment in segments:
        if segment in ("", ".", ".."):
            raise BadRequestException(
                detail="path must not contain empty segments, '.' or '..'",
                context={"path": rel},
            )
        if "\x00" in segment:
            raise BadRequestException(detail="path contains a null byte")
        cleaned.append(segment)
    if not cleaned:
        raise BadRequestException(detail="path must not be empty")
    return cleaned


def resolve_scope_root(
    scope: DocumentScope,
    scope_id: Optional[UUID | str],
    db: Session,
) -> Path:
    """Return the absolute filesystem root for a documents scope.

    For ``system`` returns ``DOCUMENTS_ROOT``; otherwise descends through
    the entity tree (organization → course_family → course) using each
    entity's ``path``. Raises ``NotFoundException`` when ``scope_id``
    doesn't resolve.
    """
    if not settings.DOCUMENTS_ROOT:
        raise BadRequestException(detail="DOCUMENTS_ROOT is not configured on the server")
    root = Path(settings.DOCUMENTS_ROOT).resolve()

    if scope == "system":
        return root

    if scope_id is None:
        raise BadRequestException(
            detail="scope_id is required for non-system scopes",
            context={"scope": scope},
        )

    # SQLAlchemy + psycopg2's UUID bind processor calls ``uuid.UUID(value)``
    # on the parameter, which fails if ``value`` is already a UUID instance.
    # Coerce to str at the boundary so the rest of the function can pass
    # ``scope_id`` straight into filters regardless of input type.
    scope_id = str(scope_id)

    if scope == "organization":
        org = db.query(Organization).filter(Organization.id == scope_id).first()
        if org is None:
            raise NotFoundException(
                detail="Organization not found",
                context={"organization_id": str(scope_id)},
            )
        return root / str(org.path)

    if scope == "course_family":
        family = db.query(CourseFamily).filter(CourseFamily.id == scope_id).first()
        if family is None:
            raise NotFoundException(
                detail="CourseFamily not found",
                context={"course_family_id": str(scope_id)},
            )
        org = db.query(Organization).filter(Organization.id == family.organization_id).first()
        return root / str(org.path) / str(family.path)

    if scope == "course":
        course = db.query(Course).filter(Course.id == scope_id).first()
        if course is None:
            raise NotFoundException(
                detail="Course not found",
                context={"course_id": str(scope_id)},
            )
        family = db.query(CourseFamily).filter(CourseFamily.id == course.course_family_id).first()
        org = db.query(Organization).filter(Organization.id == course.organization_id).first()
        return root / str(org.path) / str(family.path) / str(course.path)

    raise BadRequestException(detail=f"Unknown scope: {scope}")


def resolve_absolute_path(scope_root: Path, segments: List[str]) -> Path:
    """Join validated segments under ``scope_root``, refusing escapes.

    ``validate_relative_path`` already rejects ``..``; this is the
    second guard that re-checks the resolved path is contained in
    ``scope_root`` (also catches symlink games on the filesystem).
    """
    target = (scope_root / Path(*segments)).resolve()
    try:
        target.relative_to(scope_root)
    except ValueError as e:
        raise BadRequestException(
            detail="path escapes the scope root",
            context={"resolved": str(target)},
        ) from e
    return target


def check_reserved_name_collision(
    scope: DocumentScope,
    scope_id: Optional[UUID | str],
    first_segment: str,
    db: Session,
) -> None:
    """Raise ``ConflictException`` if ``first_segment`` shadows a child entity.

    At the system scope, children are Organizations; at the organization
    scope, children are CourseFamilies; at the course_family scope,
    children are Courses. The course scope has no nested entities.

    Used both for create operations (refuse to overwrite/upload into an
    entity-owned subtree) and for delete operations (refuse to remove
    an entity-bound directory).
    """
    if scope == "course":
        return  # courses have no nested entities

    try:
        candidate = Ltree(first_segment)
    except ValueError:
        # Not a valid Ltree label (e.g. contains spaces) — by construction
        # cannot collide with any entity path. Nothing to enforce.
        return

    if scope == "system":
        hit = db.query(Organization.id).filter(Organization.path == candidate).first()
        if hit:
            raise ConflictException(
                detail="A documents directory cannot share a name with an existing organization",
                context={"name": first_segment, "scope": scope},
            )
        return

    # See ``resolve_scope_root`` — coerce to str so the psycopg2 UUID
    # bind processor doesn't choke on a uuid.UUID instance.
    if scope_id is not None:
        scope_id = str(scope_id)

    if scope == "organization":
        hit = (
            db.query(CourseFamily.id)
            .filter(
                CourseFamily.organization_id == scope_id,
                CourseFamily.path == candidate,
            )
            .first()
        )
        if hit:
            raise ConflictException(
                detail="A documents directory cannot share a name with an existing course family",
                context={
                    "name": first_segment,
                    "scope": scope,
                    "organization_id": str(scope_id),
                },
            )
        return

    if scope == "course_family":
        hit = (
            db.query(Course.id)
            .filter(
                Course.course_family_id == scope_id,
                Course.path == candidate,
            )
            .first()
        )
        if hit:
            raise ConflictException(
                detail="A documents directory cannot share a name with an existing course",
                context={
                    "name": first_segment,
                    "scope": scope,
                    "course_family_id": str(scope_id),
                },
            )
        return


def resolve_listing_target(
    scope: DocumentScope,
    scope_id: Optional[UUID | str],
    path: Optional[str],
    db: Session,
) -> Path:
    """Resolve the target directory for a list operation.

    Empty/None ``path`` → the scope root itself; non-empty path runs
    through the same validation and escape-protection as writes.
    """
    scope_root = resolve_scope_root(scope, scope_id, db)
    if not path:
        return scope_root
    segments = validate_relative_path(path)
    return resolve_absolute_path(scope_root, segments)

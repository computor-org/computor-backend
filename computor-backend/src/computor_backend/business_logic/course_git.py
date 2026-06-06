"""Course-level git business logic.

Currently: the read-side descriptor that tells a client how a student obtains
their repository for a course. Provisioning (Forgejo babysat fork) and BYO
registration land here in later increments.

Invariant: nothing here is in the grading path — submissions are uploaded over
the API; the backend never reads a student's repo. See COURSE_LEVEL_GIT_REFACTOR.md.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from computor_backend.exceptions import ForbiddenException, NotFoundException
from computor_backend.model.course import Course, CourseMember
from computor_backend.model.git_server import CourseGitBinding, GitServer
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal
from computor_types.course_git import (
    CourseGitBindingGet,
    CourseGitBindingUpsert,
    CourseGitDescriptor,
    GitTemplateRef,
)


def build_course_git_descriptor(
    course_id: UUID | str,
    binding: Optional[CourseGitBinding],
    server: Optional[GitServer],
) -> CourseGitDescriptor:
    """Pure projection: (binding, server) -> client descriptor. No DB.

    ``server`` is the binding's ``GitServer`` (or None for pure download /
    unconfigured). Kept separate so this stays trivially unit-testable.
    """
    if binding is None:
        return CourseGitDescriptor(course_id=str(course_id), configured=False)

    template = None
    if server is not None:
        template = GitTemplateRef(
            server_type=server.type,
            base_url=server.base_url,
            repo=binding.template_repo,
            clone_url=binding.template_url,
            default_branch=binding.default_branch or "main",
        )

    return CourseGitDescriptor(
        course_id=str(course_id),
        configured=True,
        delivery=binding.delivery,
        student_repo_modes=list(binding.student_repo_modes or []),
        template=template,
    )


def get_course_git_descriptor(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> CourseGitDescriptor:
    """Descriptor for a course the caller can access.

    Gated on course membership (``_student`` or higher; admins bypass) so a
    course's git config isn't readable by non-members. Returns an
    ``unconfigured`` descriptor (rather than 404) when the course simply has no
    git binding yet, so the client can distinguish that from "not your course".
    """
    user_id = permissions.get_user_id()
    if not user_id:
        raise NotFoundException()

    member = (
        check_course_permissions(permissions, CourseMember, "_student", db)
        .filter(
            CourseMember.course_id == course_id,
            CourseMember.user_id == user_id,
        )
        .first()
    )
    # Members (any course role) and admins may read; everyone else is opaque-404'd.
    if member is None and not permissions.is_admin:
        raise NotFoundException()

    binding = (
        db.query(CourseGitBinding)
        .filter(CourseGitBinding.course_id == course_id)
        .first()
    )
    server = binding.git_server if (binding and binding.git_server_id) else None
    return build_course_git_descriptor(course_id, binding, server)


# ---------------------------------------------------------------------------
# Lecturer-facing binding management
# ---------------------------------------------------------------------------


def can_manage_course_git(principal: Principal, course: Course) -> bool:
    """Lecturer-cohort gate for managing a course's git binding.

    The same cohort that gets the lecturer (creation-pipeline) view: admin,
    ``_organization_manager``, any organization- or course-family-scoped role on
    the course's org/family, or a course role of ``_lecturer`` or higher.
    """
    if principal.is_admin or "_organization_manager" in (principal.roles or []):
        return True
    if course.organization_id and principal.has_organization_role(
        str(course.organization_id), "_developer"
    ):
        return True
    if course.course_family_id and principal.has_course_family_role(
        str(course.course_family_id), "_developer"
    ):
        return True
    return principal.has_course_role(str(course.id), "_lecturer")


def _require_course_git_manage(principal: Principal, course: Course) -> None:
    if not can_manage_course_git(principal, course):
        raise ForbiddenException(
            "You are not allowed to manage this course's git configuration."
        )


def _load_course_or_404(course_id: UUID | str, db: Session) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise NotFoundException("Course not found")
    return course


def _binding_to_get(b: CourseGitBinding) -> CourseGitBindingGet:
    return CourseGitBindingGet(
        id=str(b.id),
        course_id=str(b.course_id),
        delivery=b.delivery,
        git_server_id=str(b.git_server_id) if b.git_server_id else None,
        template_repo=b.template_repo,
        template_url=b.template_url,
        default_branch=b.default_branch,
        student_repo_modes=list(b.student_repo_modes or []),
    )


def upsert_course_git_binding(
    course_id: UUID | str,
    data: CourseGitBindingUpsert,
    permissions: Principal,
    db: Session,
) -> CourseGitBindingGet:
    """Create or replace a course's git binding (lecturer-cohort only)."""
    course = _load_course_or_404(course_id, db)
    _require_course_git_manage(permissions, course)

    if data.git_server_id:
        server = db.query(GitServer).filter(GitServer.id == data.git_server_id).first()
        if not server:
            raise NotFoundException("git_server_id does not reference a known git server")

    binding = (
        db.query(CourseGitBinding)
        .filter(CourseGitBinding.course_id == course.id)
        .first()
    )
    if binding is None:
        binding = CourseGitBinding(course_id=course.id, created_by=permissions.get_user_id())
        db.add(binding)

    binding.delivery = data.delivery
    binding.git_server_id = data.git_server_id
    binding.template_repo = data.template_repo
    binding.template_url = data.template_url
    binding.default_branch = data.default_branch or "main"
    binding.student_repo_modes = list(data.student_repo_modes or [])
    binding.updated_by = permissions.get_user_id()

    db.commit()
    db.refresh(binding)
    return _binding_to_get(binding)


def get_course_git_binding(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> CourseGitBindingGet:
    """Lecturer-facing full view of a course's git binding."""
    course = _load_course_or_404(course_id, db)
    _require_course_git_manage(permissions, course)
    binding = (
        db.query(CourseGitBinding)
        .filter(CourseGitBinding.course_id == course.id)
        .first()
    )
    if not binding:
        raise NotFoundException("This course has no git binding")
    return _binding_to_get(binding)

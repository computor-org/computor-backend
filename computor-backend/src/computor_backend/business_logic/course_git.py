"""Course-level git business logic.

Currently: the read-side descriptor that tells a client how a student obtains
their repository for a course. Provisioning (Forgejo babysat fork) and BYO
registration land here in later increments.

Invariant: nothing here is in the grading path — submissions are uploaded over
the API; the backend never reads a student's repo. See COURSE_LEVEL_GIT_REFACTOR.md.
"""
import logging
import re
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from computor_backend.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.git_provider import get_provider_client_for_server
from computor_backend.model.auth import Account
from computor_backend.model.course import Course, CourseMember
from computor_backend.model.git_server import (
    CourseGitBinding,
    CourseMemberRepository,
    GitServer,
)
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal
from computor_types.course_git import (
    CourseGitBindingGet,
    CourseGitBindingUpsert,
    CourseGitDescriptor,
    CourseMemberRepositoryGet,
    CourseMemberRepositoryRegister,
    GitTemplateRef,
    StudentRepositoryProvisioned,
)

logger = logging.getLogger(__name__)


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


def course_uses_course_level_git(db: Session, course_id: UUID | str) -> bool:
    """True if the course is on the new course-level git model (has a binding).

    Gates the legacy eager GitLab provisioning: bound courses provision student
    repos lazily (Forgejo babysat or BYO), so the legacy enrollment workflow
    must not fire for them. Un-migrated courses (org-level GitLab, no binding)
    keep the existing behaviour.
    """
    return (
        db.query(CourseGitBinding.id)
        .filter(CourseGitBinding.course_id == course_id)
        .first()
        is not None
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

    server = None
    if data.git_server_id:
        server = db.query(GitServer).filter(GitServer.id == data.git_server_id).first()
        if not server:
            raise NotFoundException("git_server_id does not reference a known git server")

    template_repo = (data.template_repo or "").strip() or None
    template_url = (data.template_url or "").strip() or None

    # For a managed Forgejo, make the binding immediately usable: default the
    # template repo from the course's org + path, ensure it actually exists in
    # Forgejo, and default its clone URL — so a course is never bound-but-broken.
    if data.delivery == "git" and server is not None and server.type == "forgejo" and server.managed:
        if not template_repo:
            from computor_backend.model.organization import Organization

            org = db.query(Organization).filter(Organization.id == course.organization_id).first()
            owner = str(org.path).replace(".", "-") if org and org.path is not None else "courses"
            template_repo = f"{owner}/{str(course.path).replace('.', '-')}--template"
        owner, _, repo = template_repo.partition("/")
        if owner and repo:
            try:
                client = get_provider_client_for_server(server)
                if hasattr(client, "ensure_template_repo"):
                    client.ensure_template_repo(owner, repo)
            except Exception as exc:  # best-effort — don't block binding on a Forgejo hiccup
                logger.warning("Could not ensure Forgejo template repo %s: %s", template_repo, exc)
        if not template_url:
            template_url = f"{server.base_url.rstrip('/')}/{template_repo}.git"

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
    binding.template_repo = template_repo
    binding.template_url = template_url
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


# ---------------------------------------------------------------------------
# Forgejo babysat student-repo provisioning
# ---------------------------------------------------------------------------


def student_repo_name(template_repo: str, handle: str) -> str:
    """Collision-free student repo name from a template repo name + a handle.

    Strips a trailing ``template`` token (the legacy bug used the bare
    ``username``, colliding across courses). E.g.
    ``("math--algo--template", "mmusterm") -> "math--algo-mmusterm"``.
    """
    base = re.sub(r"[-_]*template$", "", template_repo, flags=re.IGNORECASE)
    base = base.rstrip("-_.") or "repo"
    return f"{base}-{handle}"


def _resolve_forgejo_handle(user_id: str, db: Session) -> Optional[str]:
    """The student's Forgejo username == their Keycloak handle (preferred_username),
    stored on the OIDC ``Account.properties['username']`` after SSO login."""
    account = (
        db.query(Account)
        .filter(Account.user_id == user_id, Account.type == "oidc")
        .first()
    )
    if account and account.properties:
        return account.properties.get("username")
    return None


def _maybe_heal_forgejo_collaborator(
    rec: CourseMemberRepository, user_id: str, db: Session
) -> None:
    """Retry granting the Forgejo write-collaborator when it failed at first
    provision (the student's Forgejo account didn't exist yet). No-op once the
    collaborator is recorded as added, or for non-Forgejo repos.
    """
    if rec.mode != "forgejo" or not rec.git_server_id:
        return
    props = rec.properties or {}
    if (props.get("forgejo") or {}).get("collaborator_added"):
        return
    server = db.query(GitServer).filter(GitServer.id == rec.git_server_id).first()
    if server is None:
        return
    handle = _resolve_forgejo_handle(user_id, db)
    if not handle:
        return
    owner, _, repo = (rec.repo_ref or "").partition("/")
    if not owner or not repo:
        return
    client = get_provider_client_for_server(server)
    if not hasattr(client, "ensure_collaborator"):
        return
    if client.ensure_collaborator(owner, repo, handle):
        rec.properties = {**props, "forgejo": {**(props.get("forgejo") or {}), "collaborator_added": True}}
        rec.updated_by = user_id
        db.commit()
        logger.info(
            "Healed Forgejo collaborator for course_member %s on %s/%s",
            rec.course_member_id, owner, repo,
        )


def get_student_repository(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> Optional[CourseMemberRepositoryGet]:
    """The current student's recorded repository for a course, or ``None`` if
    they have none yet (the babysitting "do I already have a repo?" check).

    Membership-gated; raises 404 only when the caller is not a course member,
    so the client can distinguish "no repo yet" (null) from "not your course".
    """
    user_id = permissions.get_user_id()
    if not user_id:
        raise NotFoundException()

    member = (
        check_course_permissions(permissions, CourseMember, "_student", db)
        .filter(CourseMember.course_id == course_id, CourseMember.user_id == user_id)
        .first()
    )
    if member is None:
        raise NotFoundException("You are not a member of this course")

    rec = (
        db.query(CourseMemberRepository)
        .filter(CourseMemberRepository.course_member_id == member.id)
        .first()
    )
    return _member_repo_to_get(rec) if rec is not None else None


def _forgejo_admin_basic_auth_for(server: GitServer):
    """Admin basic-auth creds for ``server`` IF it is our configured managed
    Forgejo, else ``None``.

    Minting a per-user clone token needs basic auth (a token can't create a
    token), so we use the ``git_server`` settings admin credentials — but ONLY
    when the registry server is in fact our configured git_server (matched by
    base_url), so our admin password is never sent to some other registered
    instance.
    """
    from computor_backend.git_server.config import get_git_server_settings

    settings = get_git_server_settings()
    if not (settings.is_forgejo and settings.git_server_admin_username and settings.git_server_admin_password):
        return None
    if (server.base_url or "").rstrip("/") != (settings.git_server_url or "").rstrip("/"):
        return None
    return (settings.git_server_admin_username, settings.git_server_admin_password)


def _provisioned_response(
    rec: CourseMemberRepository, user_id: str, db: Session
) -> StudentRepositoryProvisioned:
    """Wrap a repo record with a freshly-minted one-time clone credential.

    For a managed-Forgejo repo we mint (rotating) a repo-scoped PAT for the
    student so `git clone`/push authenticates. The token is never persisted and
    is returned only here. Null until the student exists in Forgejo.
    """
    base = _member_repo_to_get(rec).model_dump()
    clone_token = None
    clone_username = None
    if rec.mode == "forgejo" and rec.git_server_id:
        server = db.query(GitServer).filter(GitServer.id == rec.git_server_id).first()
        handle = _resolve_forgejo_handle(user_id, db)
        creds = _forgejo_admin_basic_auth_for(server) if server is not None else None
        if server is not None and handle and creds:
            client = get_provider_client_for_server(server)
            if hasattr(client, "mint_user_clone_token"):
                clone_token = client.mint_user_clone_token(handle, creds[0], creds[1])
                if clone_token:
                    clone_username = handle
    return StudentRepositoryProvisioned(**base, clone_token=clone_token, clone_username=clone_username)


def _member_repo_to_get(rec: CourseMemberRepository) -> CourseMemberRepositoryGet:
    return CourseMemberRepositoryGet(
        id=str(rec.id),
        course_member_id=str(rec.course_member_id),
        mode=rec.mode,
        server_url=rec.server_url,
        repo_ref=rec.repo_ref,
        http_url=rec.http_url,
        ssh_url=rec.ssh_url,
        web_url=rec.web_url,
    )


def provision_student_repository(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> StudentRepositoryProvisioned:
    """Babysat Forgejo provisioning: fork the course's student-template into a
    repo for the calling student and record it. Idempotent.

    Requires the course to be bound (``delivery='git'``) to a *managed* Forgejo
    server offering the ``forgejo`` student-repo mode, with a template set.
    """
    user_id = permissions.get_user_id()
    if not user_id:
        raise NotFoundException()

    member = (
        check_course_permissions(permissions, CourseMember, "_student", db)
        .filter(CourseMember.course_id == course_id, CourseMember.user_id == user_id)
        .first()
    )
    if member is None:
        raise NotFoundException("You are not a member of this course")

    # Idempotent: one working repo per course membership. On re-provision,
    # self-heal a Forgejo write-collaborator that couldn't be granted the first
    # time (student hadn't logged into Forgejo yet).
    existing = (
        db.query(CourseMemberRepository)
        .filter(CourseMemberRepository.course_member_id == member.id)
        .first()
    )
    if existing is not None:
        _maybe_heal_forgejo_collaborator(existing, user_id, db)
        return _provisioned_response(existing, user_id, db)

    binding = (
        db.query(CourseGitBinding)
        .filter(CourseGitBinding.course_id == course_id)
        .first()
    )
    if binding is None or binding.delivery != "git":
        raise BadRequestException("This course is not configured for git provisioning")
    if "forgejo" not in (binding.student_repo_modes or []):
        raise BadRequestException("This course does not offer Forgejo-hosted repositories")

    server = binding.git_server
    if server is None or server.type != "forgejo" or not server.managed or not server.token:
        raise BadRequestException("No managed Forgejo server is bound to this course")
    if not binding.template_repo:
        raise BadRequestException("This course has no Forgejo template configured")

    owner, _, repo = binding.template_repo.partition("/")
    if not owner or not repo:
        raise BadRequestException("Forgejo template_repo must be in 'owner/repo' form")

    handle = _resolve_forgejo_handle(user_id, db)
    if not handle:
        raise BadRequestException(
            "You have no Forgejo identity yet; sign in once via SSO before provisioning."
        )

    new_name = student_repo_name(repo, handle)
    client = get_provider_client_for_server(server)
    result = client.provision_student_fork(owner, repo, owner, new_name, student_username=handle)

    rec = CourseMemberRepository(
        course_member_id=member.id,
        mode="forgejo",
        git_server_id=server.id,
        server_url=server.base_url,
        repo_ref=f"{owner}/{new_name}",
        http_url=result.http_url,
        ssh_url=result.ssh_url,
        web_url=result.web_url,
        properties=result.properties,
        created_by=user_id,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    logger.info("Provisioned Forgejo repo %s/%s for course_member %s", owner, new_name, member.id)
    return _provisioned_response(rec, user_id, db)


def register_byo_repository(
    course_id: UUID | str,
    data: CourseMemberRepositoryRegister,
    permissions: Principal,
    db: Session,
) -> CourseMemberRepositoryGet:
    """Record where a student's BYO repository lives (e.g. a GitLab repo the
    VSCode extension created with the student's PAT). Upserts the per-member
    record. Tracking only — the backend never reads the repo.
    """
    user_id = permissions.get_user_id()
    if not user_id:
        raise NotFoundException()

    member = (
        check_course_permissions(permissions, CourseMember, "_student", db)
        .filter(CourseMember.course_id == course_id, CourseMember.user_id == user_id)
        .first()
    )
    if member is None:
        raise NotFoundException("You are not a member of this course")

    binding = (
        db.query(CourseGitBinding)
        .filter(CourseGitBinding.course_id == course_id)
        .first()
    )
    if binding is None or data.mode not in (binding.student_repo_modes or []):
        raise BadRequestException(
            f"This course does not offer the '{data.mode}' student-repo mode"
        )

    rec = (
        db.query(CourseMemberRepository)
        .filter(CourseMemberRepository.course_member_id == member.id)
        .first()
    )
    if rec is None:
        rec = CourseMemberRepository(course_member_id=member.id, created_by=user_id)
        db.add(rec)

    rec.mode = data.mode
    # BYO repos live on the student's own instance, not a managed registry server.
    rec.git_server_id = None
    rec.server_url = data.server_url
    rec.repo_ref = data.repo_ref
    rec.http_url = data.http_url
    rec.ssh_url = data.ssh_url
    rec.web_url = data.web_url
    rec.updated_by = user_id

    db.commit()
    db.refresh(rec)
    logger.info("Registered %s repo for course_member %s", data.mode, member.id)
    return _member_repo_to_get(rec)

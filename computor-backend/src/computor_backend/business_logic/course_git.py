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
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.git_provider import get_provider_client_for_server
from computor_backend.model.auth import Account
from computor_backend.model.course import Course, CourseFamily, CourseMember
from computor_backend.model.git_server import (
    CourseGitBinding,
    CourseMemberRepository,
    GitServer,
)
from computor_backend.utils.forgejo_naming import (
    allocate_course_org_name,
    student_repo_name_in_org,
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
from computor_types.encryption import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GitLab credential helpers (per-course token on the binding)
# ---------------------------------------------------------------------------
#
# GitLab courses carry their own credentials on the ``CourseGitBinding`` (a
# group access token + parent group), so an external GitLab needs no shared
# managed registry server — the server row is just a tokenless instance pointer.
# Forgejo is unchanged: it uses the system server's token.


def _get_gitlab_client(server: GitServer, raw_token: Optional[str]):
    """GitLab provider client for ``server`` authenticated with an explicit
    (already-decrypted) token — the course's own binding token."""
    from computor_backend.git_provider import backend_reachable_base_url
    from computor_backend.git_provider.gitlab import GitLabProviderClient

    return GitLabProviderClient(backend_reachable_base_url(server), raw_token or "", None)


def get_gitlab_client_for_binding(binding: CourseGitBinding, server: GitServer):
    """GitLab client using the course's own token (the binding), falling back to
    the registry server's token for legacy managed-GitLab courses."""
    if getattr(binding, "token", None):
        token = decrypt_secret(binding.token)
    elif server is not None and server.token:
        token = decrypt_secret(server.token)
    else:
        token = None
    return _get_gitlab_client(server, token)


def _binding_has_managed_creds(binding: CourseGitBinding, server: Optional[GitServer]) -> bool:
    """Whether the course can back-babysat student repos: a Forgejo system token,
    a legacy managed-GitLab server token, or a per-course GitLab binding token."""
    if server is None:
        return False
    if server.type == "forgejo":
        return bool(server.managed and server.token)
    if server.type == "gitlab":
        return bool(getattr(binding, "token", None) or (server.managed and server.token))
    return False


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


def _binding_lock_state(binding: Optional[CourseGitBinding], db: Session) -> tuple[bool, Optional[str]]:
    """Whether a course's git binding is locked (its identity is immutable).

    A binding locks once it has *materialized* something a change would destroy:
    a created git template, or any provisioned student repository. After that,
    repointing ``git_server_id`` or renaming ``template_repo`` would orphan every
    student's ``origin`` remote, so the binding becomes read-only. A binding that
    has not yet produced anything (no template, no student repos — e.g. a fresh
    or download-only course) stays editable.
    """
    if binding is None:
        return False, None
    student_repos = (
        db.query(CourseMemberRepository)
        .join(CourseMember, CourseMemberRepository.course_member_id == CourseMember.id)
        .filter(CourseMember.course_id == binding.course_id)
        .count()
    )
    if student_repos > 0:
        return True, "Student repositories have already been provisioned for this course."
    if binding.delivery == "git" and binding.template_repo:
        return True, "The git template has already been created for this course."
    return False, None


def _binding_to_get(b: CourseGitBinding, db: Session) -> CourseGitBindingGet:
    locked, lock_reason = _binding_lock_state(b, db)
    parent_group_id = ((b.properties or {}).get("gitlab") or {}).get("parent_group_id")
    return CourseGitBindingGet(
        id=str(b.id),
        course_id=str(b.course_id),
        delivery=b.delivery,
        git_server_id=str(b.git_server_id) if b.git_server_id else None,
        parent_group_id=parent_group_id,
        has_token=bool(b.token),
        template_repo=b.template_repo,
        template_url=b.template_url,
        default_branch=b.default_branch,
        student_repo_modes=list(b.student_repo_modes or []),
        locked=locked,
        lock_reason=lock_reason,
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
    binding = _apply_course_git_binding(course, data, permissions.get_user_id(), db)
    return _binding_to_get(binding, db)


def _apply_course_git_binding(
    course: Course,
    data: CourseGitBindingUpsert,
    user_id,
    db: Session,
) -> CourseGitBinding:
    """Permission-free core of :func:`upsert_course_git_binding`.

    The caller must already be authorized (the lecturer endpoint checks
    git-manage; the course-creation flow checks course-create at the API edge).
    Extracted so a course can be bound to a registry git server during creation,
    not only via a later lecturer call.
    """
    binding = (
        db.query(CourseGitBinding)
        .filter(CourseGitBinding.course_id == course.id)
        .first()
    )
    # Once a binding has materialized a template or student repos, its identity
    # is frozen — changing the server/template/delivery would orphan students'
    # repositories. Reject before any side effects (e.g. Forgejo template calls).
    locked, lock_reason = _binding_lock_state(binding, db)
    if locked:
        raise ConflictException(
            detail=lock_reason
            or "This course's git configuration is locked and cannot be changed."
        )

    server = None
    if data.git_server_id:
        server = db.query(GitServer).filter(GitServer.id == data.git_server_id).first()
        if not server:
            raise NotFoundException("git_server_id does not reference a known git server")

    template_repo = (data.template_repo or "").strip() or None
    template_url = (data.template_url or "").strip() or None

    # For a managed Forgejo, make the binding immediately usable: default the
    # template repo from the course's org + path, ensure it (and the staff-only
    # reference repo) actually exist in Forgejo, and default its clone URL — so a
    # course is never bound-but-broken.
    forgejo_reference_repo = None
    forgejo_layout = None
    if data.delivery == "git" and server is not None and server.type == "forgejo" and server.managed:
        client = get_provider_client_for_server(server)
        if not template_repo:
            # New "course_org" layout: one Forgejo org per course, named from the
            # course's place in the hierarchy. The org is allocated collision-free
            # (short -> family-qualified -> numeric suffix; always <=40 chars), so
            # two families that reuse a course slug never share an org. Student
            # forks are then just the realm-unique handle inside that org.
            from computor_backend.model.organization import Organization

            org = db.query(Organization).filter(Organization.id == course.organization_id).first()
            family = (
                db.query(CourseFamily)
                .filter(CourseFamily.id == course.course_family_id)
                .first()
            )
            org_path = str(org.path) if org and org.path is not None else "courses"
            family_path = str(family.path) if family and family.path is not None else ""
            try:
                owner = allocate_course_org_name(
                    org_path, family_path, str(course.path), str(course.id),
                    # The predicate *claims* the name by creating the org; Forgejo's
                    # 422-on-duplicate makes concurrent allocation race-safe.
                    is_free=lambda name: client.create_course_org(name) == "created",
                )
            except Exception as exc:  # allocating the org is essential — fail loudly
                logger.warning("Forgejo course-org allocation failed: %s", exc)
                raise BadRequestException(
                    "Could not provision the Forgejo organization for this course.",
                    context={"error": str(exc)},
                ) from exc
            template_repo = f"{owner}/template"
            forgejo_reference_repo = f"{owner}/reference"
            forgejo_layout = "course_org"
        owner, _, repo = template_repo.partition("/")
        if owner and repo:
            if forgejo_reference_repo is None:
                # Legacy/explicit layout: reference name derived from the template.
                base = re.sub(r"[-_]*template$", "", repo, flags=re.IGNORECASE).rstrip("-_.") or repo
                forgejo_reference_repo = f"{owner}/{base}--reference"
            reference_repo_name = forgejo_reference_repo.partition("/")[2]
            try:
                if hasattr(client, "ensure_template_repo"):
                    client.ensure_template_repo(owner, repo)
                # The reference (solution) repo is staff-only; students never see it.
                if hasattr(client, "ensure_reference_repo"):
                    client.ensure_reference_repo(owner, reference_repo_name)
            except Exception as exc:  # best-effort — don't block binding on a Forgejo hiccup
                logger.warning("Could not ensure Forgejo repos for %s: %s", template_repo, exc)
        if not template_url:
            template_url = f"{server.base_url.rstrip('/')}/{template_repo}.git"

    # For a managed GitLab, provision the flat course structure under the parent
    # group (course group + template/reference projects + students subgroup) and
    # adopt the template project. Credentials come from the COURSE — the binding's
    # own token + parent_group_id — falling back to a legacy managed server's
    # token, so an external GitLab needs no shared managed registry server.
    gitlab_structure = None
    if data.delivery == "git" and server is not None and server.type == "gitlab":
        gl_token = (
            (data.token or "").strip()
            or (decrypt_secret(binding.token) if (binding is not None and binding.token) else None)
            or (decrypt_secret(server.token) if (server.managed and server.token) else None)
        )
        if gl_token:
            gl_server_props = (server.properties or {}).get("gitlab") or {}
            parent_group_id = data.parent_group_id or gl_server_props.get("parent_group_id")
            if not parent_group_id:
                raise BadRequestException(
                    "A managed GitLab course needs a parent_group_id — set it on the "
                    "course git binding (or, for a legacy managed server, on the server)."
                )
            course_slug = str(course.path).replace(".", "-")
            client = _get_gitlab_client(server, gl_token)
            try:
                gitlab_structure = client.ensure_course_structure(
                    parent_group_id, course_slug, course.title or course_slug
                )
            except Exception as exc:  # materialization is essential — fail loudly
                logger.warning("GitLab course-structure provisioning failed: %s", exc)
                raise BadRequestException(
                    "Could not provision the GitLab course structure on the bound server.",
                    context={"error": str(exc)},
                ) from exc
            template_repo = gitlab_structure.get("template_path") or template_repo
            template_url = gitlab_structure.get("template_url") or template_url

    if binding is None:
        binding = CourseGitBinding(course_id=course.id, created_by=user_id)
        db.add(binding)

    binding.delivery = data.delivery
    binding.git_server_id = data.git_server_id
    binding.template_repo = template_repo
    binding.template_url = template_url
    binding.default_branch = data.default_branch or "main"
    binding.student_repo_modes = list(data.student_repo_modes or [])
    # Per-course GitLab credential: persist the token (encrypted) when supplied;
    # keep an existing one so a metadata-only re-apply doesn't drop it.
    if data.token:
        binding.token = encrypt_secret(data.token)
    # GitLab structure ids (from provisioning) + the parent_group_id both live
    # under properties.gitlab.
    if gitlab_structure is not None or data.parent_group_id:
        gl_props = {**((binding.properties or {}).get("gitlab") or {})}
        if gitlab_structure is not None:
            gl_props.update(gitlab_structure)
        if data.parent_group_id:
            gl_props["parent_group_id"] = data.parent_group_id
        binding.properties = {**(binding.properties or {}), "gitlab": gl_props}
    if forgejo_reference_repo is not None or forgejo_layout is not None:
        forgejo_props = {**((binding.properties or {}).get("forgejo") or {})}
        if forgejo_reference_repo is not None:
            forgejo_props["reference_repo"] = forgejo_reference_repo
        if forgejo_layout is not None:
            forgejo_props["layout"] = forgejo_layout
        binding.properties = {**(binding.properties or {}), "forgejo": forgejo_props}
    binding.updated_by = user_id

    db.commit()
    db.refresh(binding)
    return binding


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
    return _binding_to_get(binding, db)


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


def _resolve_oidc_handle(user_id: str, db: Session) -> Optional[str]:
    """The student's Keycloak handle (``preferred_username``), stored on the OIDC
    ``Account.properties['username']`` after SSO login. Used as the Forgejo
    username and as the managed-GitLab student-repo slug."""
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
    if rec.mode != "managed" or not rec.git_server_id:
        return
    props = rec.properties or {}
    if (props.get("forgejo") or {}).get("collaborator_added"):
        return
    server = db.query(GitServer).filter(GitServer.id == rec.git_server_id).first()
    if server is None or server.type != "forgejo":
        return
    handle = _resolve_oidc_handle(user_id, db)
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


def _ensure_forgejo_account(user_id: str, server: GitServer, db: Session) -> Optional[str]:
    """Make sure the user has a Forgejo account, creating it via the admin API if
    needed, so collaborator/fork grants don't have to wait for a manual Forgejo
    login. Returns the Forgejo handle (preferred_username) or None if unknown.

    Best-effort: needs the user's OIDC handle (set at computor SSO login) and our
    managed-server admin credentials; if either is missing we just return the
    handle (or None) and let the downstream grant self-heal."""
    handle = _resolve_oidc_handle(user_id, db)
    if not handle:
        return None
    creds = _forgejo_admin_basic_auth_for(server)
    if not creds:
        return handle
    from computor_backend.model.auth import User

    user = db.query(User).filter(User.id == user_id).first()
    email = (user.email if user else None) or f"{handle}@users.noreply.local"
    full_name = (
        " ".join(filter(None, [getattr(user, "given_name", None), getattr(user, "family_name", None)]))
        if user
        else handle
    ) or handle
    client = get_provider_client_for_server(server)
    if hasattr(client, "ensure_user"):
        try:
            client.ensure_user(handle, email, full_name, creds[0], creds[1])
        except Exception as exc:  # best-effort — don't block provisioning
            logger.warning("Could not ensure Forgejo account for %s: %s", handle, exc)
    return handle


def _reference_repo_ref(binding: CourseGitBinding) -> Optional[str]:
    """The course's reference (solution) repo ref, by convention from the template:
    ``{owner}/{base}--template`` -> ``{owner}/{base}--reference``. Honours an
    explicit ``binding.properties.forgejo.reference_repo`` if present."""
    props = (binding.properties or {}).get("forgejo") or {}
    if props.get("reference_repo"):
        return props["reference_repo"]
    template = (binding.template_repo or "").strip()
    owner, _, repo = template.partition("/")
    if not owner or not repo:
        return None
    base = re.sub(r"[-_]*template$", "", repo, flags=re.IGNORECASE).rstrip("-_.") or repo
    return f"{owner}/{base}--reference"


def _maybe_grant_forgejo_staff_access(
    member: CourseMember,
    binding: CourseGitBinding,
    server: Optional[GitServer],
    user_id: str,
    db: Session,
) -> None:
    """For ``_lecturer`` and above on a managed-Forgejo course, grant admin
    collaborator on the canonical template AND reference repos (creating the
    reference repo if missing). Students/tutors get NOTHING here — only their own
    fork; they never get access to the template directly or to the reference repo.
    Idempotent; the Forgejo account is ensured first so the grant succeeds without
    a manual login."""
    from computor_backend.permissions.principal import course_role_hierarchy

    if server is None or server.type != "forgejo" or not server.managed:
        return
    if member.course_role_id not in course_role_hierarchy.get_allowed_roles("_lecturer"):
        return
    template = (binding.template_repo or "").strip()
    owner, _, t_repo = template.partition("/")
    if not owner or not t_repo:
        return

    handle = _ensure_forgejo_account(user_id, server, db)
    if not handle:
        return

    client = get_provider_client_for_server(server)
    if not hasattr(client, "ensure_collaborator"):
        return

    reference = _reference_repo_ref(binding)
    if reference and hasattr(client, "ensure_reference_repo"):
        r_owner, _, r_repo = reference.partition("/")
        try:
            client.ensure_reference_repo(r_owner, r_repo)
        except Exception as exc:  # best-effort
            logger.warning("Could not ensure Forgejo reference repo %s: %s", reference, exc)

    granted_template = client.ensure_collaborator(owner, t_repo, handle, permission="admin")
    granted_reference = False
    if reference:
        r_owner, _, r_repo = reference.partition("/")
        granted_reference = client.ensure_collaborator(r_owner, r_repo, handle, permission="admin")

    # In the course_org layout, also give _lecturer+ the GitLab "Reporter"
    # equivalent on every student fork via the org's read-all `graders` team
    # (covers forks created later too — one grant per lecturer, not per fork).
    granted_reader = False
    layout = (binding.properties or {}).get("forgejo", {}).get("layout")
    if layout == "course_org" and hasattr(client, "grant_org_reader"):
        granted_reader = client.grant_org_reader(owner, handle)

    logger.info(
        "Forgejo staff access for %s (role %s): template=%s reference=%s reader=%s",
        handle, member.course_role_id, granted_template, granted_reference, granted_reader,
    )


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
    # Only a managed *Forgejo* repo mints a clone token; for managed GitLab the
    # student uses their own credentials, and ``_forgejo_admin_basic_auth_for``
    # already returns None for a non-Forgejo server (so creds stays None below).
    if rec.mode == "managed" and rec.git_server_id:
        server = db.query(GitServer).filter(GitServer.id == rec.git_server_id).first()
        handle = _resolve_oidc_handle(user_id, db)
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
        provider_type=(rec.git_server.type if rec.git_server else None),
        server_url=rec.server_url,
        repo_ref=rec.repo_ref,
        http_url=rec.http_url,
        ssh_url=rec.ssh_url,
        web_url=rec.web_url,
    )


def _provision_forgejo(
    member: CourseMember,
    binding: CourseGitBinding,
    server: GitServer,
    user_id: str,
    db: Session,
) -> CourseMemberRepository:
    """Fork the Forgejo student-template into a repo for the student and record
    it. The student is added as a write collaborator (best-effort, self-healing)."""
    if not binding.template_repo:
        raise BadRequestException("This course has no Forgejo template configured")
    owner, _, repo = binding.template_repo.partition("/")
    if not owner or not repo:
        raise BadRequestException("Forgejo template_repo must be in 'owner/repo' form")
    handle = _resolve_oidc_handle(user_id, db)
    if not handle:
        raise BadRequestException(
            "You have no Forgejo identity yet; sign in once via SSO before provisioning."
        )
    # In the course_org layout the org already encodes the course, so the fork is
    # just the realm-unique handle; legacy bindings keep the {base}-{handle} form.
    layout = (binding.properties or {}).get("forgejo", {}).get("layout")
    if layout == "course_org":
        new_name = student_repo_name_in_org(handle)
    else:
        new_name = student_repo_name(repo, handle)
    repo_ref = f"{owner}/{new_name}"
    # Identity guard (defends the legacy flat namespace): never adopt a repo that
    # already belongs to a *different* course member. Collisions are impossible in
    # the course_org layout, but this + the DB unique index make any residual
    # clash a loud error instead of silent repo-sharing.
    clash = (
        db.query(CourseMemberRepository)
        .filter(
            CourseMemberRepository.repo_ref == repo_ref,
            CourseMemberRepository.course_member_id != member.id,
        )
        .first()
    )
    if clash is not None:
        raise ConflictException(
            f"Forgejo repository '{repo_ref}' is already in use by another course member"
        )
    client = get_provider_client_for_server(server)
    result = client.provision_student_fork(owner, repo, owner, new_name, student_username=handle)
    rec = CourseMemberRepository(
        course_member_id=member.id,
        mode="managed",
        git_server_id=server.id,
        server_url=server.base_url,
        repo_ref=repo_ref,
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
    return rec


def _provision_gitlab_managed(
    member: CourseMember,
    binding: CourseGitBinding,
    server: GitServer,
    user_id: str,
    db: Session,
) -> CourseMemberRepository:
    """Fork the managed-GitLab ``template`` project into the course's ``students``
    subgroup as the student's repo and record it. Access is granted separately,
    when the student registers their GLPAT — the backend cannot add them until it
    knows their GitLab user id."""
    gl_props = (binding.properties or {}).get("gitlab") or {}
    template_project_id = gl_props.get("template_project_id")
    students_group_id = gl_props.get("students_group_id")
    if not template_project_id or not students_group_id:
        raise BadRequestException(
            "This course's managed-GitLab structure is not provisioned yet."
        )
    handle = _resolve_oidc_handle(user_id, db) or str(member.id)
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", handle).strip("-._") or str(member.id)
    client = get_gitlab_client_for_binding(binding, server)
    result = client.provision_student_fork(template_project_id, students_group_id, slug)
    full_path = (result.properties.get("gitlab") or {}).get("full_path")
    rec = CourseMemberRepository(
        course_member_id=member.id,
        mode="managed",
        git_server_id=server.id,
        server_url=server.base_url,
        repo_ref=full_path,
        http_url=result.http_url,
        ssh_url=result.ssh_url,
        web_url=result.web_url,
        properties=result.properties,
        created_by=user_id,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    logger.info("Provisioned GitLab repo %s for course_member %s", full_path, member.id)
    return rec


def _stamp_repo_on_submission_groups(member: CourseMember, db: Session) -> None:
    """Propagate the member's course repo onto their individual submission groups
    as provider-agnostic ``properties['git']``, so the per-assignment record points
    at the repo even when the repo is provisioned after the groups already exist.
    Best-effort — never blocks provisioning (the repo is already committed)."""
    from computor_backend.repositories.submission_group_provisioning import (
        stamp_member_repo_on_submission_groups,
    )
    try:
        if stamp_member_repo_on_submission_groups(member, db):
            db.commit()
    except Exception as exc:  # auxiliary bookkeeping — don't fail the provision
        logger.warning("Could not stamp repo onto submission groups for %s: %s", member.id, exc)
        db.rollback()


def provision_student_repository(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> StudentRepositoryProvisioned:
    """Babysat provisioning: fork the course's template into a repo for the
    calling student and record it. Idempotent.

    Requires the course to offer the ``managed`` mode (system-hosted) with a
    materialized template. ``managed`` is provider-agnostic; the bound server's
    type picks the backend — Forgejo or GitLab.
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
    if binding is None or binding.delivery != "git":
        raise BadRequestException("This course is not configured for git provisioning")

    server = binding.git_server
    if not _binding_has_managed_creds(binding, server):
        raise BadRequestException("No managed git server is bound to this course")

    # Idempotent: one working repo per course membership. On re-provision,
    # self-heal a Forgejo write-collaborator that couldn't be granted the first
    # time (member hadn't logged into Forgejo yet) and (re)grant staff access for
    # _lecturer+ on the canonical template/reference repos.
    existing = (
        db.query(CourseMemberRepository)
        .filter(CourseMemberRepository.course_member_id == member.id)
        .first()
    )
    if existing is not None:
        _maybe_heal_forgejo_collaborator(existing, user_id, db)
        _maybe_grant_forgejo_staff_access(member, binding, server, user_id, db)
        _stamp_repo_on_submission_groups(member, db)
        return _provisioned_response(existing, user_id, db)

    if "managed" not in (binding.student_repo_modes or []):
        raise BadRequestException("This course does not offer managed (system-hosted) repositories")
    # 'managed' is provider-agnostic; the bound server's type picks the backend.
    if server.type == "forgejo":
        # Make sure the member's Forgejo account exists first, so the fork's
        # collaborator grant (and staff access below) succeed without a manual
        # Forgejo login.
        _ensure_forgejo_account(user_id, server, db)
        rec = _provision_forgejo(member, binding, server, user_id, db)
    elif server.type == "gitlab":
        rec = _provision_gitlab_managed(member, binding, server, user_id, db)
    else:
        raise BadRequestException(f"Unsupported managed server type '{server.type}'")

    # Every member gets their own fork (above); _lecturer+ additionally get admin
    # access to the canonical template + reference repos.
    _maybe_grant_forgejo_staff_access(member, binding, server, user_id, db)
    _stamp_repo_on_submission_groups(member, db)
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


# ---------------------------------------------------------------------------
# Managed-GitLab student access (register a GLPAT, grant repo membership)
# ---------------------------------------------------------------------------

# GitLab member access levels (mirror git_provider.gitlab).
_GITLAB_REPORTER = 20
_GITLAB_MAINTAINER = 40


def _link_gitlab_account(user_id, provider_url, gitlab_username, gitlab_email, db) -> Account:
    """Create or validate the student's GitLab ``Account`` link
    (``provider`` = server url, ``type='gitlab'``, ``provider_account_id`` = the
    GitLab username). Rejects a token whose account is linked to a different user,
    or that does not match the user's existing link."""
    provider = (provider_url or "").rstrip("/")
    existing = (
        db.query(Account)
        .filter(Account.user_id == user_id, Account.provider == provider, Account.type == "gitlab")
        .first()
    )
    if existing is not None:
        if (existing.provider_account_id or "").lower() != gitlab_username.lower():
            raise BadRequestException(
                "The GitLab token does not match your linked GitLab account."
            )
        return existing
    conflict = (
        db.query(Account)
        .filter(
            Account.provider == provider,
            Account.type == "gitlab",
            Account.provider_account_id == gitlab_username,
            Account.user_id != user_id,
        )
        .first()
    )
    if conflict is not None:
        raise BadRequestException("This GitLab account is already linked to another user.")
    account = Account(
        provider=provider,
        type="gitlab",
        provider_account_id=gitlab_username,
        user_id=user_id,
        properties={"email": gitlab_email} if gitlab_email else None,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    logger.info("Linked GitLab account %s -> user %s", gitlab_username, user_id)
    return account


def register_gitlab_managed_access(
    course_id: UUID | str,
    provider_access_token: Optional[str],
    permissions: Principal,
    db: Session,
) -> CourseMemberRepositoryGet:
    """Link the student's GitLab account from their PAT and grant them access to
    their managed-GitLab repository.

    ``GET /api/v4/user`` with the student's own PAT proves their GitLab identity
    (no admin or email-search needed); the backend then uses the registry's group
    token to add them as a Maintainer on their repo (and Reporter on the course
    template, so they can pull upstream). Provisions the repo first if needed.
    Idempotent.
    """
    from computor_backend.business_logic.users import _fetch_gitlab_user_profile

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
    if (
        binding is None
        or binding.delivery != "git"
        or "managed" not in (binding.student_repo_modes or [])
    ):
        raise BadRequestException("This course does not offer managed repositories")

    server = binding.git_server
    if server is None or server.type != "gitlab" or not _binding_has_managed_creds(binding, server):
        raise BadRequestException("No managed GitLab server is bound to this course")

    if not provider_access_token:
        raise BadRequestException("A GitLab personal access token is required")

    # The student's own PAT proves their GitLab identity (current-user endpoint).
    profile = _fetch_gitlab_user_profile(server.base_url, provider_access_token)
    gitlab_user_id = (profile or {}).get("id")
    gitlab_username = (profile or {}).get("username")
    gitlab_email = (profile or {}).get("email")
    if not gitlab_user_id or not gitlab_username:
        raise BadRequestException("Could not determine the GitLab user from the provided token")

    _link_gitlab_account(member.user_id, server.base_url, gitlab_username, gitlab_email, db)

    # Ensure the student's repo exists (fork), then grant membership.
    rec = (
        db.query(CourseMemberRepository)
        .filter(CourseMemberRepository.course_member_id == member.id)
        .first()
    )
    if rec is None:
        rec = _provision_gitlab_managed(member, binding, server, user_id, db)

    project_id = ((rec.properties or {}).get("gitlab") or {}).get("project_id")
    if not project_id:
        raise BadRequestException(
            "Your GitLab repository is missing its project id; re-provision and retry."
        )

    client = get_gitlab_client_for_binding(binding, server)
    client.add_member(project_id, gitlab_user_id, _GITLAB_MAINTAINER)
    # Read access on the course template so the student can pull upstream updates.
    template_project_id = ((binding.properties or {}).get("gitlab") or {}).get("template_project_id")
    if template_project_id:
        client.add_member(template_project_id, gitlab_user_id, _GITLAB_REPORTER)

    rec.properties = {
        **(rec.properties or {}),
        "gitlab": {
            **((rec.properties or {}).get("gitlab") or {}),
            "member_user_id": gitlab_user_id,
            "access_granted": True,
        },
    }
    rec.updated_by = user_id
    db.commit()
    db.refresh(rec)
    logger.info(
        "Granted managed-GitLab access for course_member %s (gitlab user %s)",
        member.id, gitlab_user_id,
    )
    return _member_repo_to_get(rec)


# ---------------------------------------------------------------------------
# Template archive (download mode + external-repo seed source)
# ---------------------------------------------------------------------------


def get_template_archive_source(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> tuple[str, dict, str]:
    """Resolve ``(url, headers, filename)`` for the course template archive on its
    managed git server.

    The backend fetches it with the registry **service token** and streams it to
    the student — used by download mode and to seed an external repo — so the
    student never sees the token. Membership-gated; the template content is
    something every course member is entitled to.
    """
    from urllib.parse import quote

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
    if binding is None or not binding.git_server_id or not binding.template_repo:
        raise BadRequestException("This course has no downloadable template")
    server = binding.git_server
    binding_token = getattr(binding, "token", None)
    if server is None or not (binding_token or server.token):
        raise BadRequestException("This course's git server is not available")

    token = decrypt_secret(binding_token or server.token)
    branch = binding.default_branch or "main"
    base = server.base_url.rstrip("/")
    repo = binding.template_repo
    if server.type == "forgejo":
        owner, _, name = repo.partition("/")
        if not owner or not name:
            raise BadRequestException("Forgejo template_repo must be 'owner/repo'")
        url = f"{base}/api/v1/repos/{owner}/{name}/archive/{branch}.zip"
        headers = {"Authorization": f"token {token}"}
        slug = name
    elif server.type == "gitlab":
        url = (
            f"{base}/api/v4/projects/{quote(repo, safe='')}"
            f"/repository/archive.zip?sha={quote(branch, safe='')}"
        )
        headers = {"PRIVATE-TOKEN": token}
        slug = repo.rstrip("/").split("/")[-1]
    else:
        raise BadRequestException(f"Unsupported git server type '{server.type}'")

    return url, headers, f"{slug}.zip"

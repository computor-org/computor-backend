"""Deploy a single course (identity + content tree) from a course-level config.

This is the server-side counterpart to the CLI's ``_deploy_course_contents``
orchestration (``computor-cli``), but scoped to ONE course under an existing
course family and driven by the web "create course" upload. It takes a
:class:`HierarchicalCourseConfig` (parsed from ``course_deployment.yaml``) and:

  1. authorizes course creation in the family (same gate as ``POST /courses``);
  2. validates the config (content-type kinds, content-type references, paths,
     and that every ``example_identifier`` resolves in the example library);
  3. on apply: creates the course, enrolls the caller as ``_owner`` (so the
     example-assignment ``_lecturer`` gate passes), creates the content types,
     then walks the ``contents`` tree creating ``CourseContent`` rows and
     assigning examples via the existing :func:`assign_example_to_content`.

Validation problems are split into *errors* (block an apply) and *warnings*
(e.g. an unresolved example — the content is still created, just without one).

NOTE: this is intentionally synchronous. ``assign_example_to_content`` commits
per assignment, so a failure midway can leave a partially-populated course
(recoverable); the course + owner + content types are committed up front.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from computor_types.deployment_config import HierarchicalCourseConfig
from computor_types.course_deployment import (
    CourseDeployResult,
    CourseDeploySummary,
    CourseDeployWarning,
)
from computor_types.validation import normalize_version

from computor_backend.custom_types.ltree import Ltree
from computor_backend.database import set_db_user
from computor_backend.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentKind,
    CourseContentType,
    CourseFamily,
    CourseMember,
)
from computor_backend.model.example import Example
from computor_backend.model.organization import Organization
from computor_backend.model.service import Service
from computor_backend.permissions.handlers import permission_registry
from computor_backend.permissions.principal import Principal
from computor_backend.redis_cache import get_cache
from computor_backend.repositories.example_version_repo import ExampleVersionRepository
from computor_backend.business_logic.lecturer_deployment import assign_example_to_content

logger = logging.getLogger(__name__)

# Course-content path segments are validated by a DB CHECK constraint:
# ``^[a-z0-9_]+(\.[a-z0-9_]+)*$``. Each segment provided in the YAML must match
# the per-segment part of that pattern.
_SEGMENT_RE = re.compile(r"^[a-z0-9_]+$")


def _humanize(segment: str) -> str:
    try:
        words = [w.capitalize() for w in segment.replace("_", " ").replace("-", " ").split() if w]
        return " ".join(words) or segment
    except Exception:
        return segment


def _authorize_create(permissions: Principal, family: CourseFamily, db: Session) -> None:
    """Mirror the create-authorization that ``create_db`` applies for courses."""
    if permissions.is_admin:
        return
    handler = permission_registry.get_handler(Course)
    context = {
        "course_family_id": str(family.id),
        "organization_id": str(family.organization_id),
    }
    if handler is None or not handler.can_perform_action(
        permissions, "create", resource_id=None, context=context
    ):
        raise ForbiddenException(
            detail="You don't have permission to create courses in this course family"
        )


def deploy_course_from_config(
    db: Session,
    permissions: Principal,
    course_family_id: str | UUID,
    config: HierarchicalCourseConfig,
    validate_only: bool = False,
) -> CourseDeployResult:
    """Validate and (optionally) apply a single-course deployment config."""

    family = db.query(CourseFamily).filter(CourseFamily.id == course_family_id).first()
    if not family:
        raise NotFoundException(detail="Course family not found")

    _authorize_create(permissions, family, db)

    errors: List[str] = []
    warnings: List[CourseDeployWarning] = []

    # --- content types: validate kinds. The unique key is (slug, kind), NOT slug
    # alone: the same slug may be defined twice with different kinds (e.g. a
    # 'training' unit and a 'training' assignment). A content node's reference is
    # disambiguated by tree structure — a node with children resolves to a
    # non-submittable (unit) type, a leaf to a submittable (assignment) type.
    kinds: Dict[str, CourseContentKind] = {k.id: k for k in db.query(CourseContentKind).all()}
    ct_configs = list(config.content_types or [])
    cts_by_slug: Dict[str, list] = {}
    seen_slug_kind: set = set()
    for ct in ct_configs:
        if ct.kind not in kinds:
            errors.append(
                f"Content type '{ct.slug}' has unknown kind '{ct.kind}' "
                f"(expected one of: {', '.join(sorted(kinds)) or 'none'})"
            )
        key = (ct.slug, ct.kind)
        if key in seen_slug_kind:
            errors.append(f"Duplicate content type '{ct.slug}' (kind '{ct.kind}')")
            continue
        seen_slug_kind.add(key)
        cts_by_slug.setdefault(ct.slug, []).append(ct)

    def _is_submittable(ct) -> bool:
        return bool(kinds.get(ct.kind) and kinds[ct.kind].submittable)

    def _resolve_ct(slug: str, has_children: bool):
        """Pick the content-type config for a reference, disambiguating a shared
        slug by structure. Returns (config | None, mismatch_warning | None)."""
        candidates = cts_by_slug.get(slug)
        if not candidates:
            return None, None
        if len(candidates) == 1:
            ct = candidates[0]
            if has_children and _is_submittable(ct):
                return ct, "is an assignment (submittable) but has nested contents"
            return ct, None
        want_submittable = not has_children
        for ct in candidates:
            if _is_submittable(ct) == want_submittable:
                return ct, None
        return candidates[0], None

    # --- course path must be free within the family
    if not config.path:
        errors.append("The config is missing a course 'path'")
    else:
        existing = (
            db.query(Course)
            .filter(Course.course_family_id == family.id, Course.path == Ltree(config.path))
            .first()
        )
        if existing:
            errors.append(f"A course with path '{config.path}' already exists in this family")

    # --- resolve service slugs (for testing_service_id on assignments)
    service_ids: Dict[str, str] = {}
    for svc in (config.services or []):
        row = db.query(Service).filter(Service.slug == svc.slug).first()
        if row:
            service_ids[svc.slug] = str(row.id)
        else:
            warnings.append(
                CourseDeployWarning(
                    reason=f"Testing service '{svc.slug}' is not registered; assignments will have "
                    f"no testing service, so students can't run tests or submit until one is linked"
                )
            )
    default_service_id: Optional[str] = next(iter(service_ids.values()), None)

    version_repo = ExampleVersionRepository(db, get_cache())
    summary = CourseDeploySummary(content_types=len(seen_slug_kind))

    def _resolve_version_tag(example: Example, requested: Optional[str]) -> Optional[str]:
        """Resolve the concrete semantic version tag to assign (None if none available)."""
        if requested and requested.lower() != "latest":
            normalized = normalize_version(requested)
            return normalized if version_repo.find_by_version_tag(example.id, normalized) else None
        latest = version_repo.find_latest_version(str(example.id))
        return latest.version_tag if latest else None

    def _walk(items, parent_path: Optional[str], ct_rows: Optional[Dict[tuple, CourseContentType]], counter: List[float], seen: Optional[set]):
        """Validate (ct_rows is None) or apply (ct_rows given) the content tree."""
        apply = ct_rows is not None
        for c in items:
            if not c.path:
                errors.append(f"A content under '{parent_path or '<root>'}' is missing a 'path'")
                continue
            if not _SEGMENT_RE.match(c.path):
                errors.append(
                    f"Invalid path segment '{c.path}' — use lowercase letters, digits and underscores only"
                )
            full = f"{parent_path}.{c.path}" if parent_path else c.path
            if seen is not None:
                if full in seen:
                    errors.append(f"Duplicate content path '{full}'")
                seen.add(full)

            ct_cfg, ct_warn = _resolve_ct(c.content_type, bool(c.contents))
            if ct_cfg is None:
                errors.append(f"Content '{full}' references undefined content_type '{c.content_type}'")
                _walk(c.contents or [], full, ct_rows, counter, seen)
                continue
            if ct_warn:
                warnings.append(
                    CourseDeployWarning(path=full, reason=f"Content type '{c.content_type}' {ct_warn}")
                )
            submittable = _is_submittable(ct_cfg)

            if submittable:
                summary.assignments += 1
            else:
                summary.units += 1
                if c.example_identifier:
                    warnings.append(
                        CourseDeployWarning(
                            path=full,
                            example_identifier=c.example_identifier,
                            reason="example_identifier on non-submittable content is ignored",
                        )
                    )

            # Resolve the example (validate it exists + has a version) up front.
            example: Optional[Example] = None
            version_tag: Optional[str] = None
            if submittable and c.example_identifier:
                example = (
                    db.query(Example)
                    .filter(Example.identifier == Ltree(c.example_identifier))
                    .first()
                )
                if not example:
                    warnings.append(
                        CourseDeployWarning(
                            path=full,
                            example_identifier=c.example_identifier,
                            reason="Example not found in the library; content created without an example",
                        )
                    )
                else:
                    version_tag = _resolve_version_tag(example, c.example_version_tag)
                    if not version_tag:
                        warnings.append(
                            CourseDeployWarning(
                                path=full,
                                example_identifier=c.example_identifier,
                                reason=f"No matching version ('{c.example_version_tag or 'latest'}') for example",
                            )
                        )
                    elif not apply:
                        summary.examples_assigned += 1

            if apply:
                ct_row = ct_rows[(ct_cfg.slug, ct_cfg.kind)]
                position = c.position if c.position is not None else counter[0]
                counter[0] += 1.0
                content = CourseContent(
                    title=c.title or _humanize(c.path),
                    description=c.description,
                    path=Ltree(full),
                    course_id=ct_row.course_id,
                    course_content_type_id=ct_row.id,
                    position=position,
                    max_group_size=c.max_group_size or 1,
                    max_test_runs=c.max_test_runs,
                    max_submissions=c.max_submissions,
                    testing_service_id=default_service_id if submittable else None,
                    properties=dict(c.properties) if c.properties else None,
                    created_by=permissions.user_id,
                    updated_by=permissions.user_id,
                )
                db.add(content)
                # Flush so the before_insert listener populates course_content_kind_id /
                # is_submittable and we get the content id for example assignment.
                db.flush()

                if submittable and example and version_tag:
                    try:
                        assign_example_to_content(
                            course_content_id=content.id,
                            example_identifier=c.example_identifier,
                            version_tag=version_tag,
                            permissions=permissions,
                            db=db,
                        )  # commits
                        summary.examples_assigned += 1
                    except Exception as e:  # noqa: BLE001 - surface as a warning, keep going
                        logger.warning("assign-example failed for %s: %s", full, e)
                        warnings.append(
                            CourseDeployWarning(
                                path=full,
                                example_identifier=c.example_identifier,
                                reason=f"Failed to assign example: {e}",
                            )
                        )

            _walk(c.contents or [], full, ct_rows, counter, seen)

    # Validation pass (no writes).
    _walk(config.contents or [], None, None, [1.0], set())

    # --- validate the optional git block (structural only; provisioning happens
    # on apply, never during validate_only).
    if config.git is not None:
        gitcfg = config.git
        valid_modes = {"managed", "external", "download"}
        bad_modes = [m for m in (gitcfg.student_repo_modes or []) if m not in valid_modes]
        if bad_modes:
            errors.append(
                f"git.student_repo_modes has invalid modes {bad_modes} "
                f"(allowed: {sorted(valid_modes)})"
            )
        if gitcfg.provider not in (None, "forgejo", "gitlab"):
            errors.append(
                f"git: unsupported provider '{gitcfg.provider}' (expected 'forgejo' or 'gitlab')"
            )
        if gitcfg.delivery == "git" and gitcfg.provider == "gitlab" and not gitcfg.base_url:
            errors.append("git: an external GitLab requires 'base_url'")

    result = CourseDeployResult(
        validated=True,
        applied=False,
        course_id=None,
        course_path=config.path or "",
        course_title=config.name,
        summary=summary,
        warnings=warnings,
        errors=errors,
    )

    if validate_only:
        return result
    if errors:
        raise BadRequestException(detail="Cannot apply: " + "; ".join(errors))

    # ----- APPLY -----
    set_db_user(db, permissions.user_id)

    course = Course(
        title=config.name,
        description=config.description or "",
        path=Ltree(config.path),
        course_family_id=family.id,
        organization_id=family.organization_id,
        properties={},
        created_by=permissions.user_id,
        updated_by=permissions.user_id,
    )
    db.add(course)
    db.flush()

    # Enroll the caller as owner so they can manage the course immediately and so
    # the (live, DB-backed) _lecturer gate in assign_example_to_content passes.
    db.add(
        CourseMember(
            course_id=course.id,
            user_id=permissions.user_id,
            course_role_id="_owner",
            created_by=permissions.user_id,
            updated_by=permissions.user_id,
        )
    )

    ct_rows: Dict[tuple, CourseContentType] = {}
    for ct in ct_configs:
        key = (ct.slug, ct.kind)
        if key in ct_rows:
            continue
        row = CourseContentType(
            slug=ct.slug,
            title=ct.title,
            description=ct.description,
            color=ct.color or "green",
            properties=dict(ct.properties) if ct.properties else {},
            course_id=course.id,
            course_content_kind_id=ct.kind,
            created_by=permissions.user_id,
            updated_by=permissions.user_id,
        )
        db.add(row)
        ct_rows[key] = row
    db.flush()
    # Commit the course + owner membership + content types before assigning
    # examples (assign_example_to_content authorizes against the live membership).
    db.commit()

    # Reset per-apply counters (the validation pass populated them already).
    summary.assignments = 0
    summary.units = 0
    summary.examples_assigned = 0
    _walk(config.contents or [], None, ct_rows, [1.0], None)
    db.commit()

    # ----- git binding (optional) -----
    # Resolve the portable git reference (provider + base_url -> GitServer) and
    # bind the course. This is the single server-side "git from the file" apply
    # that the web upload AND the VSCode deploy command both inherit. It provisions
    # real provider resources for delivery='git' with managed creds; on failure we
    # keep the already-committed course + contents and surface a warning, so a
    # transient git error doesn't discard the whole deploy (git can be reconfigured
    # from the course's git binding UI). The token is taken literally here — env
    # (${VAR}) interpolation is a client-side concern (the CLI expands before it
    # sends; a web/VSCode upload should carry a real token).
    if config.git is not None:
        try:
            from computor_backend.business_logic.git_registry import resolve_git_server_ref
            from computor_backend.business_logic.course_git import _apply_course_git_binding
            from computor_types.course_git import CourseGitBindingUpsert

            gitcfg = config.git
            server = resolve_git_server_ref(gitcfg.provider, gitcfg.base_url, db)
            _apply_course_git_binding(
                course,
                CourseGitBindingUpsert(
                    delivery=gitcfg.delivery,
                    git_server_id=str(server.id) if server is not None else None,
                    parent_group_id=gitcfg.parent_group_id,
                    token=gitcfg.token,
                    template_repo=gitcfg.template_repo,
                    template_url=gitcfg.template_url,
                    default_branch=gitcfg.default_branch,
                    student_repo_modes=gitcfg.student_repo_modes or [],
                ),
                permissions.user_id,
                db,
            )  # commits the binding (+ any provisioning)
        except Exception as e:  # noqa: BLE001 - keep the course, surface the git failure
            logger.warning("git binding failed for course %s: %s", config.path, e)
            db.rollback()
            result.warnings.append(
                CourseDeployWarning(reason=f"Git binding was not applied: {e}")
            )

    result.applied = True
    result.course_id = str(course.id)
    return result

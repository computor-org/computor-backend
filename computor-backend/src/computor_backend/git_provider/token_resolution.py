"""Single home for course push-credential resolution.

Three storage generations coexist:

1. legacy org-level GitLab: ``organization.properties.gitlab.token``
2. per-course binding token: ``CourseGitBinding.token`` (external GitLab)
3. registry server token: ``GitServer.token`` (managed Forgejo / legacy
   managed GitLab)

Callers deliberately differ in fallback order — template release prefers the
org token (legacy courses keep working mid-migration), the course-git binding
flows never consult the org — so the order is explicit per entry point, not
normalized here.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from computor_backend.utils.encryption import decrypt_secret

logger = logging.getLogger(__name__)


def _decrypt_or_none(encrypted: Optional[str]) -> Optional[str]:
    if not encrypted:
        return None
    try:
        return decrypt_secret(encrypted)
    except Exception as e:
        logger.warning(f"Could not decrypt git token: {e}")
        return None


def resolve_binding_token(binding, server, *, managed_only_server_token: bool = False) -> Optional[str]:
    """Binding token first, then the registry server's token.

    External-GitLab courses carry the group token on the BINDING (the
    git_server is a tokenless instance pointer); managed Forgejo and legacy
    managed GitLab keep it on the git_server. With
    ``managed_only_server_token`` the server token only counts when the
    server is managed (course-creation flow).
    """
    if binding is not None and getattr(binding, "token", None):
        return _decrypt_or_none(binding.token)
    if server is not None and server.token:
        if managed_only_server_token and not server.managed:
            return None
        return _decrypt_or_none(server.token)
    return None


@dataclass
class CoursePushCredentials:
    """Resolved push credentials + URL bases for a course's git remote."""

    token: Optional[str]
    server_type: str  # "gitlab" | "forgejo"
    binding: Optional[object] = None
    git_server: Optional[object] = None
    public_base: Optional[str] = None
    reachable_base: Optional[str] = None
    from_org_properties: bool = False

    def rewrite_to_reachable(self, url: str) -> str:
        """Swap a stored public-base URL to the backend-reachable origin.

        Stored template/clone URLs use the public (student-facing) base; a
        backend component must clone/push via the address it can reach
        (service-DNS in docker, localhost on host). No-op when they match
        or the URL has a different origin.
        """
        if (
            self.public_base
            and self.reachable_base
            and self.reachable_base != self.public_base
            and url.startswith(self.public_base)
        ):
            return self.reachable_base + url[len(self.public_base):]
        return url


def resolve_course_push_credentials(
    db: Session,
    course_id,
    *,
    prefer_org_token: bool = False,
) -> CoursePushCredentials:
    """Resolve the push token + provider type for a course.

    With ``prefer_org_token`` the legacy ``organization.properties.gitlab``
    token wins over the binding/registry chain (template-release order);
    otherwise the binding chain is authoritative.
    """
    from ..model.course import Course
    from ..model.git_server import CourseGitBinding
    from . import backend_reachable_base_url

    creds = CoursePushCredentials(token=None, server_type="gitlab")

    course = db.query(Course).filter(Course.id == course_id).first()
    organization = course.organization if course else None

    if prefer_org_token and organization is not None:
        org_props = organization.properties or {}
        if "gitlab" in org_props:
            token = _decrypt_or_none(org_props.get("gitlab", {}).get("token"))
            if token:
                logger.info(f"Using decrypted GitLab token from organization {organization.title}")
                creds.token = token
                creds.from_org_properties = True

    binding = (
        db.query(CourseGitBinding)
        .filter(CourseGitBinding.course_id == course_id)
        .first()
    )
    if binding is not None and binding.git_server is not None:
        creds.binding = binding
        creds.git_server = binding.git_server
        creds.public_base = (binding.git_server.base_url or "").rstrip("/") or None
        creds.reachable_base = backend_reachable_base_url(binding.git_server)

        if creds.token is None:
            token = resolve_binding_token(binding, binding.git_server)
            if token:
                creds.token = token
                creds.server_type = (binding.git_server.type or "gitlab").lower()
                logger.info(
                    "Using %s token for git server %s (%s)",
                    "binding" if binding.token else "git server",
                    binding.git_server.base_url, creds.server_type,
                )

    if creds.token is None:
        logger.warning(
            f"No git push token found for course {course_id} (org properties or git server)"
        )

    return creds

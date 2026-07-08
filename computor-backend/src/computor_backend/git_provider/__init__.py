import logging
from .base import GitProviderClient

logger = logging.getLogger(__name__)


def backend_reachable_base_url(git_server) -> str:
    """URL a *backend* component (the worker — always in docker — or the prod API,
    also in docker) uses to REACH this server's HTTP API and git remotes.

    For the configured managed Forgejo this is the per-component address from
    ``GIT_SERVER_URL`` (service-DNS like ``computor-forgejo:3030`` inside docker,
    ``localhost:3030`` on the host) — the same way every other in-cluster service
    is reached, needing no host port publishing. External servers are already
    publicly reachable, so their ``base_url`` is used as-is.

    NEVER use this for student-facing values (clone URLs shown in the UI,
    ``template_url``, ``course_member_repository`` URLs): those must stay the
    public ``base_url``.

    Detection uses the location-independent ``managed`` + ``type`` signal rather
    than matching ``base_url`` against ``git_server_url`` (as
    ``_forgejo_admin_basic_auth_for`` does): in the worker the public ``base_url``
    (``localhost``) and the internal ``git_server_url`` (``computor-forgejo``)
    deliberately differ, so a string match would never fire there.
    """
    if getattr(git_server, "managed", False) and (git_server.type or "").lower() == "forgejo":
        from computor_backend.git_server.config import get_git_server_settings

        settings = get_git_server_settings()
        if settings.is_forgejo and settings.git_server_url:
            return settings.git_server_url.rstrip("/")
    return (git_server.base_url or "").rstrip("/")


def get_provider_client_for_server(git_server) -> GitProviderClient:
    """Return a provider client for a ``GitServer`` registry row (course-level model).

    Reads the registry's reversibly-encrypted service token via the
    non-deprecated ``decrypt_secret``.

    The client talks to ``backend_reachable_base_url`` (service-DNS in docker),
    not the public ``base_url`` — so REST calls work from the worker and the prod
    API. Repo URLs the client returns come from the server's own response
    (``clone_url``/``html_url``, built from Forgejo's ``ROOT_URL``), so they stay
    public regardless of how we connect.
    """
    from computor_backend.utils.encryption import decrypt_secret

    token = decrypt_secret(git_server.token) if git_server.token else ""
    base_url = backend_reachable_base_url(git_server)
    if git_server.type == 'forgejo':
        from .forgejo import ForgejoProviderClient
        return ForgejoProviderClient(base_url, token)
    if git_server.type == 'gitlab':
        from .gitlab import GitLabProviderClient
        return GitLabProviderClient(base_url, token, None)
    raise ValueError(f"Unsupported git server type: {git_server.type!r}")

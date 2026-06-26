import logging
from computor_types.encryption import decrypt_secret
from .base import GitProviderClient

logger = logging.getLogger(__name__)


def get_provider_client(git_provider) -> GitProviderClient:
    """Return the right provider client for a GitProvider row."""
    token = _decrypt(git_provider.token)
    if git_provider.type == 'gitlab':
        from .gitlab import GitLabProviderClient
        return GitLabProviderClient(git_provider.url, token, git_provider.organization.db if hasattr(git_provider, 'db') else None)
    if git_provider.type == 'forgejo':
        from .forgejo import ForgejoProviderClient
        return ForgejoProviderClient(git_provider.url, token)
    raise ValueError(f"Unsupported git provider type: {git_provider.type!r}")


def get_provider_client_for_server(git_server) -> GitProviderClient:
    """Return a provider client for a ``GitServer`` registry row (course-level model).

    Unlike ``get_provider_client`` (legacy organization-scoped ``GitProvider``),
    this reads the registry's reversibly-encrypted service token via the
    non-deprecated ``decrypt_secret`` (wire-compatible with the legacy tokens).
    """
    from computor_types.encryption import decrypt_secret

    token = decrypt_secret(git_server.token) if git_server.token else ""
    if git_server.type == 'forgejo':
        from .forgejo import ForgejoProviderClient
        return ForgejoProviderClient(git_server.base_url, token)
    if git_server.type == 'gitlab':
        from .gitlab import GitLabProviderClient
        return GitLabProviderClient(git_server.base_url, token, None)
    raise ValueError(f"Unsupported git server type: {git_server.type!r}")


def get_provider_client_from_db(organization_id: str, db) -> GitProviderClient:
    """Load the git provider for an organization from DB and return its client."""
    from ..model.git_provider import GitProvider
    provider = (
        db.query(GitProvider)
        .filter(GitProvider.organization_id == organization_id)
        .first()
    )
    if not provider:
        raise ValueError(f"No git provider configured for organization {organization_id}")
    token = _decrypt(provider.token)
    if provider.type == 'gitlab':
        from .gitlab import GitLabProviderClient
        return GitLabProviderClient(provider.url, token, db)
    if provider.type == 'forgejo':
        from .forgejo import ForgejoProviderClient
        return ForgejoProviderClient(provider.url, token)
    raise ValueError(f"Unsupported git provider type: {provider.type!r}")


def _decrypt(encrypted_token: str) -> str:
    try:
        return decrypt_secret(encrypted_token)
    except Exception as e:
        raise ValueError(f"Failed to decrypt git provider token: {e}") from e

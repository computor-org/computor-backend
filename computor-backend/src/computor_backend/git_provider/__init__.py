import logging
from computor_types.tokens import decrypt_api_key
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
        return decrypt_api_key(encrypted_token)
    except Exception as e:
        raise ValueError(f"Failed to decrypt git provider token: {e}") from e

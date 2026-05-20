from .config import get_git_server_settings
from .schemas import CreateGitUserRequest, GitUser, GitServerHealthResponse, UpdateGitUserRequest
from .exceptions import (
    GitServerError,
    GitServerDisabledError,
    GitServerConnectionError,
    GitServerAuthError,
    GitUserNotFoundError,
    GitUserAlreadyExistsError,
)


def get_git_client():
    """Return the configured git server client, or raise GitServerDisabledError."""
    settings = get_git_server_settings()
    if not settings.enabled:
        raise GitServerDisabledError("No git server configured (GIT_SERVER is not set)")
    if settings.is_forgejo:
        from .forgejo import get_forgejo_client
        return get_forgejo_client()
    raise GitServerDisabledError(f"Unsupported git server: {settings.git_server!r}")

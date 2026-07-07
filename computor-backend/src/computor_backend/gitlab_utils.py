"""Pure GitLab URL construction helpers (no API access).

API-level helpers (fork, unprotect, member management, client factory) live
in ``computor_backend.git_provider.gitlab``.
"""
from typing import Optional, Dict, Any


def construct_gitlab_http_url(gitlab_base_url: str, full_path: str) -> str:
    """
    Construct a proper GitLab HTTP clone URL from base URL and full path.

    Args:
        gitlab_base_url: Base GitLab URL with protocol and port (e.g., "http://localhost:8084")
        full_path: Full project path (e.g., "testing/<...>/students/emily.davis")

    Returns:
        Complete HTTP clone URL (e.g., "http://localhost:8084/testing/<...>/students/emily.davis.git")
    """
    if not gitlab_base_url or not full_path:
        return None

    # Ensure base URL doesn't end with slash
    base_url = gitlab_base_url.rstrip('/')

    # Ensure full_path doesn't start with slash
    path = full_path.lstrip('/')

    return f"{base_url}/{path}.git"


def construct_gitlab_ssh_url(full_path: str, gitlab_host: Optional[str] = None) -> str:
    """
    Construct a GitLab SSH clone URL from full path.

    Args:
        full_path: Full project path (e.g., "testing/<...>/students/emily.davis")
        gitlab_host: GitLab hostname (defaults to "localhost" if not provided)

    Returns:
        SSH clone URL (e.g., "git@localhost:testing/<...>/students/emily.davis.git")
    """
    if not full_path:
        return None

    host = gitlab_host or "localhost"
    path = full_path.lstrip('/')

    return f"git@{host}:{path}.git"


def construct_gitlab_web_url(gitlab_base_url: str, full_path: str) -> str:
    """
    Construct a GitLab web URL from base URL and full path.

    Args:
        gitlab_base_url: Base GitLab URL with protocol and port (e.g., "http://localhost:8084")
        full_path: Full project path (e.g., "testing/<...>/students/emily.davis")

    Returns:
        Complete web URL (e.g., "http://localhost:8084/testing/<...>/students/emily.davis")
    """
    if not gitlab_base_url or not full_path:
        return None

    # Ensure base URL doesn't end with slash
    base_url = gitlab_base_url.rstrip('/')

    # Ensure full_path doesn't start with slash
    path = full_path.lstrip('/')

    return f"{base_url}/{path}"


def get_gitlab_urls_from_properties(properties: Dict[Any, Any]) -> Dict[str, Optional[str]]:
    """
    Extract and construct proper GitLab URLs from properties dictionary.

    Args:
        properties: Properties dict containing gitlab info with 'url' and 'full_path'

    Returns:
        Dictionary with 'http_url_to_repo', 'ssh_url_to_repo', 'web_url' keys
    """
    if not properties or not isinstance(properties, dict):
        return {
            'http_url_to_repo': None,
            'ssh_url_to_repo': None,
            'web_url': None
        }

    gitlab_props = properties.get('gitlab', {})
    if not isinstance(gitlab_props, dict):
        return {
            'http_url_to_repo': None,
            'ssh_url_to_repo': None,
            'web_url': None
        }

    base_url = gitlab_props.get('url')
    full_path = gitlab_props.get('full_path')

    # Extract host from base URL for SSH
    gitlab_host = None
    if base_url:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            gitlab_host = parsed.hostname
        except ValueError:
            gitlab_host = "localhost"

    return {
        'http_url_to_repo': construct_gitlab_http_url(base_url, full_path),
        'ssh_url_to_repo': construct_gitlab_ssh_url(full_path, gitlab_host),
        'web_url': construct_gitlab_web_url(base_url, full_path)
    }
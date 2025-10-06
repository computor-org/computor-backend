from gitlab import Gitlab, GitlabHttpError
from typing import Optional, Dict, Any

def gitlab_unprotect_branches(gitlab: Gitlab, id: str | int, branch_name):
  try:
    response = gitlab.http_delete(path=f"/projects/{id}/protected_branches/{branch_name}")
    print(f"deleted branch {branch_name} of project {id}")
  except GitlabHttpError as e:
    if e.response_code == 404:
      print(f"Already unprotected branch '{branch_name}' [projectId={id}]")
    else:
      raise e

def gitlab_fork_project(gitlab: Gitlab, fork_id: str | int, dest_path: str, dest_name: str, namespace_id: str | int):
  try:
    gitlab.http_post(path=f"/projects/{fork_id}/fork",
          post_data={
            "path": dest_path,
            "name": dest_name,
            "namespace_id": namespace_id
          })
  except Exception as e:
    print(f"[gitlab_fork_project]{str(e)}")
    raise e

def gitlab_current_user(gitlab: Gitlab):
    return gitlab.http_get(path=f"/user")


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
        except:
            gitlab_host = "localhost"

    return {
        'http_url_to_repo': construct_gitlab_http_url(base_url, full_path),
        'ssh_url_to_repo': construct_gitlab_ssh_url(full_path, gitlab_host),
        'web_url': construct_gitlab_web_url(base_url, full_path)
    }
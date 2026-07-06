from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class GitServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    git_server: str = ""
    # URL the backend uses to REACH the git server (docker-internal host in a
    # containerized deployment, e.g. http://computor-forgejo:3030).
    git_server_url: str = ""
    # URL a *user* can reach the git server at (e.g. http://localhost:3030 or a
    # public https host). Falls back to ``git_server_url`` when unset — correct
    # for host-run dev where the backend already talks to the public URL.
    git_server_url_public: str = ""
    git_server_admin_username: str = ""
    git_server_admin_password: str = ""
    @property
    def enabled(self) -> bool:
        return bool(self.git_server)

    @property
    def is_forgejo(self) -> bool:
        return self.git_server.lower() == "forgejo"

    @property
    def public_url(self) -> str:
        """User-reachable base URL of the git server."""
        return self.git_server_url_public or self.git_server_url


@lru_cache(maxsize=1)
def get_git_server_settings() -> GitServerSettings:
    return GitServerSettings()


def to_public_git_url(url: Optional[str]) -> Optional[str]:
    """Rewrite a stored git URL that uses the backend-internal git host to the
    user-reachable public host.

    Stored template/clone URLs are built from the managed git server's internal
    ``base_url`` (which the backend needs to reach it over the docker network).
    When surfacing those URLs to a client, swap the internal host prefix for the
    public one. URLs that don't start with the internal host (e.g. an external
    GitLab) are returned unchanged.
    """
    if not url:
        return url
    cfg = get_git_server_settings()
    internal = (cfg.git_server_url or "").rstrip("/")
    public = (cfg.public_url or "").rstrip("/")
    if internal and public and internal != public and url.startswith(internal):
        return public + url[len(internal):]
    return url

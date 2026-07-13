import os
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class GitServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    git_server: str = ""
    # URL the backend uses to REACH the git server. This is remapped per
    # deployment by docker-compose: a host-run dev backend talks to the
    # published port (http://localhost:3030), while a containerized backend
    # talks over the docker network — prod compose injects
    # GIT_SERVER_URL=${GIT_SERVER_URL_INTERNAL} (http://computor-forgejo:3030)
    # for the uvicorn service. Never surface this to a user as-is.
    git_server_url: str = ""
    # URL a *user* can reach the git server at (public host, e.g.
    # https://git.example.com). In prod compose this is injected as
    # GIT_SERVER_URL_PUBLIC=${GIT_SERVER_URL}. When unset (host-run dev) it
    # falls back to FORGEJO_ROOT_URL, then to git_server_url — see public_url.
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
        """User-reachable base URL of the git server.

        Prefers the explicit public URL, then FORGEJO_ROOT_URL (set in every
        environment, including host-run dev where git_server_url_public is
        absent), and only then the backend-reachable URL as a last resort.
        """
        return (
            self.git_server_url_public
            or os.environ.get("FORGEJO_ROOT_URL", "")
            or self.git_server_url
        )

    @property
    def internal_hosts(self) -> List[str]:
        """Base URLs that identify the git server on its *internal* side and so
        must be rewritten to ``public_url`` before a URL is shown to a user.

        Covers both the backend-reachable URL this process uses and the
        docker-internal host (``GIT_SERVER_URL_INTERNAL``) that a containerized
        worker bakes into stored template/clone URLs — which a host-run backend
        (whose ``git_server_url`` is ``localhost``) would otherwise fail to
        recognise and leave un-rewritten.
        """
        hosts: List[str] = []
        for candidate in (
            self.git_server_url,
            os.environ.get("GIT_SERVER_URL_INTERNAL", ""),
        ):
            normalized = (candidate or "").rstrip("/")
            if normalized and normalized not in hosts:
                hosts.append(normalized)
        return hosts


@lru_cache(maxsize=1)
def get_git_server_settings() -> GitServerSettings:
    return GitServerSettings()


def to_public_git_url(url: Optional[str]) -> Optional[str]:
    """Rewrite a stored git URL that uses a backend-internal git host to the
    user-reachable public host.

    Stored template/clone URLs are built from the managed git server's internal
    ``base_url`` (which the backend/worker needs to reach it over the docker
    network). When surfacing those URLs to a client, swap the internal host
    prefix for the public one. URLs that don't start with a known internal host
    (e.g. an external GitLab) are returned unchanged.
    """
    if not url:
        return url
    cfg = get_git_server_settings()
    public = (cfg.public_url or "").rstrip("/")
    if not public:
        return url
    for internal in cfg.internal_hosts:
        if internal != public and url.startswith(internal):
            return public + url[len(internal):]
    return url

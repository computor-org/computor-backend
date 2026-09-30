import os
from contextvars import ContextVar
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


# Name the workspace-ingress answers to on the workspace networks. Workspaces
# cannot resolve the public domain (deliberately — that is what keeps them off
# everything else the platform serves) and would need a certificate for it if
# they could, so clone URLs handed to a workspace point here instead.
WORKSPACE_GIT_URL = os.environ.get("WORKSPACE_GIT_URL", "http://computor-git")

# Which flavour of git URL the CURRENT request should be answered with.
#
# Set per request from the X-Computor-Client header, which workspace-ingress
# injects on the route workspaces use to reach the API. Injected headers replace
# whatever the client sent, so a workspace cannot suppress it — and forging it
# from outside buys nothing, since the internal hostname is unreachable there.
#
# A ContextVar rather than a parameter because the alternative is threading a
# flag through every DTO-building call site in business_logic/course_git.py,
# where it would say nothing about the domain — this is a rendering decision
# about the audience, not an input to the logic.
_git_audience: ContextVar[str] = ContextVar("git_audience", default="public")

WORKSPACE_CLIENT_HEADER = "x-computor-client"
WORKSPACE_CLIENT_VALUE = "workspace"


def set_git_audience(audience: str) -> None:
    """Record whether this request is answered for a workspace or a browser."""
    _git_audience.set(audience)


def to_workspace_git_url(url: Optional[str]) -> Optional[str]:
    """Rewrite a stored git URL to the host a Coder workspace can reach.

    The counterpart of :func:`to_public_git_url`: same swap, different
    destination. Called instead of it when the request authenticated with a
    workspace token, so the extension clones through workspace-ingress rather
    than the public domain — which also means an internet-disabled workspace can
    still reach git.
    """
    if not url:
        return url
    cfg = get_git_server_settings()
    public = (cfg.public_url or "").rstrip("/")
    for prefix in [*cfg.internal_hosts, public]:
        if prefix and url.startswith(prefix):
            return WORKSPACE_GIT_URL + url[len(prefix):]
    return url


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
    if _git_audience.get() == WORKSPACE_CLIENT_VALUE:
        # Same URL, different audience: a workspace gets the host it can
        # actually reach. Every caller that renders a git URL for a client goes
        # through here, so this is the one place the choice has to be made.
        return to_workspace_git_url(url)
    cfg = get_git_server_settings()
    public = (cfg.public_url or "").rstrip("/")
    if not public:
        return url
    for internal in cfg.internal_hosts:
        if internal != public and url.startswith(internal):
            return public + url[len(internal):]
    return url


def to_browser_git_url(url: Optional[str]) -> Optional[str]:
    """Rewrite a stored git URL to the host a *browser* can reach — always.

    :func:`to_public_git_url` answers for the requesting audience, so a
    workspace client gets the workspace-internal host (right for git, dead in
    a browser tab: the workspace host resolves nowhere outside the workspace
    networks). URLs that are opened with ``openExternal`` / ``window.open``
    always land in the user's browser regardless of who asked, so they must
    always carry the public host. Ignores the request audience on purpose.
    """
    if not url:
        return url
    cfg = get_git_server_settings()
    public = (cfg.public_url or "").rstrip("/")
    if not public:
        return url
    for internal in [*cfg.internal_hosts, WORKSPACE_GIT_URL]:
        if internal and internal != public and url.startswith(internal):
            return public + url[len(internal):]
    return url

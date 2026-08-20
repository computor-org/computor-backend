"""Configuration for the optional GitHub issue-reporting feature.

Two environment variables decide everything:

``GITHUB_ISSUE_REPORT_REPOSITORY``
    Presence enables the feature. Absent means the deployment has no issue
    reporting at all — the endpoint is never registered and clients hide their
    entry point. Deliberately has no default: "unset" must be distinguishable
    from "configured".

``GITHUB_ISSUE_REPORT_TOKEN``
    A token on that repository with issue-write permission. Required when the
    repository is *private* — that is the whole reason it exists, since a
    private board is one users must not reach themselves. A public repository
    needs no token: GitHub has no anonymous issue creation, so without one the
    backend cannot submit anything and the client simply opens the public
    issues page instead.

Whether the repository is public or private is a fact read from GitHub by the
startup probe (``health.py``), never guessed from configuration.

Mirrors ``git_server/config.py``: a pydantic-settings model behind an
``lru_cache``d accessor, so tests can clear the cache and re-read the env.
"""
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict

# Owner and repository names GitHub itself accepts.
_SEGMENT = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")

GITHUB_HOST = "github.com"
GITHUB_API_URL = "https://api.github.com"


@dataclass(frozen=True)
class RepositoryRef:
    """One GitHub repository, wherever it is hosted."""

    host: str
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def issues_url(self) -> str:
        """The human-facing issues page — only ever handed to a user when the
        repository is public."""
        return f"https://{self.host}/{self.owner}/{self.name}/issues"

    @property
    def default_api_base(self) -> str:
        """github.com has a dedicated API host; GitHub Enterprise serves its API
        under ``/api/v3`` on the same host."""
        if self.host == GITHUB_HOST:
            return GITHUB_API_URL
        return f"https://{self.host}/api/v3"


def _valid_segment(value: str) -> bool:
    return bool(value) and all(character in _SEGMENT for character in value)


def parse_repository(value: str) -> Optional[RepositoryRef]:
    """Parse any GitHub issues page into a repository reference.

    Accepts ``owner/name``, ``https://github.com/owner/name``, the same with a
    trailing ``/issues``, and GitHub Enterprise hosts. Returns ``None`` for
    anything else so the caller can treat the deployment as unconfigured rather
    than half-configured.
    """
    raw = (value or "").strip()
    if not raw:
        return None

    host = GITHUB_HOST
    if "://" in raw or raw.startswith("www."):
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        if not parsed.netloc:
            return None
        host = parsed.netloc.split("@")[-1].lower()
        if host.startswith("www."):
            host = host[4:]
        # api.github.com/repos/owner/name is a plausible paste; treat it as
        # github.com so the derived API base stays correct.
        if host == "api.github.com":
            host = GITHUB_HOST
        path = parsed.path
    else:
        path = raw

    segments = [segment for segment in path.split("/") if segment]
    # Tolerate the trailing page a user would copy from the browser, and the
    # ``repos/`` prefix of an API URL.
    if segments and segments[0] == "repos":
        segments = segments[1:]
    if len(segments) > 2 and segments[2] in ("issues", "pulls", "issues.git"):
        segments = segments[:2]
    if len(segments) != 2:
        return None

    owner, name = segments[0], segments[1]
    if name.endswith(".git"):
        name = name[: -len(".git")]
    if not _valid_segment(owner) or not _valid_segment(name):
        return None
    return RepositoryRef(host=host, owner=owner, name=name)


class IssueReportSettings(BaseSettings):
    """``GITHUB_ISSUE_REPORT_*`` environment configuration."""

    model_config = SettingsConfigDict(env_prefix="GITHUB_ISSUE_REPORT_", extra="ignore")

    repository: str = ""
    token: str = ""
    # Override for the API base. Normally derived from the repository host, so
    # only needed for a GitHub Enterprise install that does not serve /api/v3.
    api_url: str = ""
    labels: str = ""
    # Branch screenshots are committed to, when a report carries one.
    branch: str = "main"
    max_screenshot_bytes: int = 5 * 1024 * 1024
    # Per-user submission budget. A fixed window; 0 disables the limit.
    rate_limit_count: int = 1
    rate_limit_seconds: int = 300

    @property
    def reference(self) -> Optional[RepositoryRef]:
        return parse_repository(self.repository)

    @property
    def configured(self) -> bool:
        """True when this deployment declares an issue tracker at all."""
        return self.reference is not None

    @property
    def has_token(self) -> bool:
        return bool(self.token.strip())

    @property
    def api_base(self) -> str:
        override = self.api_url.strip().rstrip("/")
        if override:
            return override
        reference = self.reference
        return reference.default_api_base if reference else GITHUB_API_URL

    @property
    def issues_url(self) -> Optional[str]:
        reference = self.reference
        return reference.issues_url if reference else None

    @property
    def label_list(self) -> List[str]:
        return [label.strip() for label in self.labels.split(",") if label.strip()]


@lru_cache(maxsize=1)
def get_issue_report_settings() -> IssueReportSettings:
    return IssueReportSettings()

"""
GitLab configuration models.

Single source of truth for GitLab-related deployment configurations.
Used by deployments.py, deployments_refactored.py, and entity DTOs.

GitLabConfigGet: All GitLab properties WITHOUT the token (safe for API responses)
GitLabConfig: Extends GitLabConfigGet WITH the token (for internal/write operations)
"""

from typing import Optional
from pydantic import Field

from computor_types.deployments import BaseDeployment, RepositoryConfig


class GitLabConfigGet(RepositoryConfig):
    url: Optional[str] = None
    full_path: Optional[str] = None
    directory: Optional[str] = None
    registry: Optional[str] = None
    parent: Optional[int] = None
    # Enhanced GitLab properties
    group_id: Optional[int] = None
    parent_id: Optional[int] = None
    namespace_id: Optional[int] = None
    namespace_path: Optional[str] = None
    web_url: Optional[str] = None
    visibility: Optional[str] = None
    last_synced_at: Optional[str] = None


class GitLabConfig(GitLabConfigGet):
    token: Optional[str] = None

"""
Base classes and interfaces for Temporal workflow and activity definitions.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Optional
from urllib.parse import urlparse, urlunparse

from temporalio.common import RetryPolicy

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    """Standard result structure for workflows."""
    status: str
    result: Any
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseWorkflow(ABC):
    """
    Abstract base class for Temporal workflows.

    Workflows orchestrate the execution of activities and handle long-running processes.
    """

    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Get the workflow name."""
        pass

    @classmethod
    def get_task_queue(cls) -> str:
        """Get the default task queue for this workflow."""
        return "computor-tasks"

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        """Get the workflow execution timeout."""
        return timedelta(hours=1)

    @classmethod
    def get_retry_policy(cls) -> RetryPolicy:
        """Get the retry policy for this workflow."""
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=100),
            maximum_attempts=3,
        )


def decrypt_gitlab_token(encrypted_token: Optional[str]) -> Optional[str]:
    """Decrypt a GitLab token. Returns None if token is empty or decryption fails."""
    if not encrypted_token:
        return None
    try:
        from computor_types.tokens import decrypt_api_key
        return decrypt_api_key(encrypted_token)
    except Exception as e:
        logger.warning(f"Could not decrypt GitLab token: {e}")
        return None


def make_git_auth_url(url: str, token: str) -> str:
    """Insert oauth2 token into a git URL for authenticated clone/push."""
    parsed = urlparse(url)
    auth_netloc = f"oauth2:{token}@{parsed.hostname}"
    if parsed.port:
        auth_netloc += f":{parsed.port}"
    return urlunparse((
        parsed.scheme, auth_netloc, parsed.path,
        parsed.params, parsed.query, parsed.fragment
    ))
"""
Base classes and interfaces for Temporal workflow and activity definitions.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable, Dict, Optional, Sequence, Tuple
from urllib.parse import urlparse, urlunparse

from temporalio import workflow
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

    @staticmethod
    def require_params(params: Dict[str, Any], *names: str) -> Optional["WorkflowResult"]:
        """
        Validate that required params are present.

        Returns a failed ``WorkflowResult`` for the first named param that is
        missing/None (treats any falsy value as absent, matching the historical
        ``if not param`` checks), otherwise ``None``.
        """
        for name in names:
            if not params.get(name):
                return WorkflowResult(
                    status="failed",
                    result=None,
                    error=f"{name} is required",
                )
        return None

    @staticmethod
    def default_activity_retry_policy() -> RetryPolicy:
        """
        The standard activity retry policy (5s initial, 1m max interval, 2.0
        backoff, 3 attempts) used verbatim by several single-activity workflows.
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=5),
            maximum_interval=timedelta(minutes=1),
            backoff_coefficient=2.0,
            maximum_attempts=3,
        )

    @staticmethod
    async def run_single_activity(
        activity_fn: Callable,
        args: Sequence[Any],
        timeout: timedelta,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> Any:
        """
        Execute a single activity with a start-to-close timeout and the default
        activity retry policy (unless one is supplied). Convenience wrapper for
        the common single-activity workflow shape.
        """
        return await workflow.execute_activity(
            activity_fn,
            args=list(args),
            start_to_close_timeout=timeout,
            retry_policy=retry_policy or BaseWorkflow.default_activity_retry_policy(),
        )


def decrypt_gitlab_token(encrypted_token: Optional[str]) -> Optional[str]:
    """Decrypt a GitLab token. Returns None if token is empty or decryption fails."""
    if not encrypted_token:
        return None
    try:
        from computor_backend.utils.encryption import decrypt_secret
        return decrypt_secret(encrypted_token)
    except Exception as e:
        logger.warning(f"Could not decrypt GitLab token: {e}")
        return None


def make_git_auth_url(url: str, token: str) -> str:
    """Insert oauth2 token into a git URL for authenticated clone/push (GitLab)."""
    parsed = urlparse(url)
    auth_netloc = f"oauth2:{token}@{parsed.hostname}"
    if parsed.port:
        auth_netloc += f":{parsed.port}"
    return urlunparse((
        parsed.scheme, auth_netloc, parsed.path,
        parsed.params, parsed.query, parsed.fragment
    ))


def make_forgejo_auth_url(url: str, token: str) -> str:
    """Insert a token for authenticated clone/push on Forgejo/Gitea, which
    authenticate with the token as the *username* (not ``oauth2:token`` like
    GitLab)."""
    parsed = urlparse(url)
    auth_netloc = f"{token}@{parsed.hostname}"
    if parsed.port:
        auth_netloc += f":{parsed.port}"
    return urlunparse((
        parsed.scheme, auth_netloc, parsed.path,
        parsed.params, parsed.query, parsed.fragment
    ))


def make_provider_auth_url(url: str, token: str, server_type: str) -> str:
    """Build an authenticated git URL for the given provider type."""
    if not token:
        return url
    if (server_type or "").lower() == "forgejo":
        return make_forgejo_auth_url(url, token)
    return make_git_auth_url(url, token)


def extract_test_counts(test_results: Dict[str, Any]) -> Tuple[int, int, int]:
    """Extract (passed, failed, total) from test results dict."""
    if "summary" in test_results:
        s = test_results["summary"]
        return s.get("passed", 0), s.get("failed", 0), s.get("total", 0)
    return (
        test_results.get("passed", 0),
        test_results.get("failed", 0),
        test_results.get("total", 0),
    )
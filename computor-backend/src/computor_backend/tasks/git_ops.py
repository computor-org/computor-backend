"""Shared git plumbing for Temporal activities.

Clone-or-init, worker identity, and push-with-rebase-retry used to be
hand-rolled (with drift) in the template-release, reference-repo and
assignments-repo flows. These helpers are the single implementation.
All functions are synchronous — call sites are blocking git work already.
"""
import logging
import os

import git

from .temporal_base import make_provider_auth_url
from .worker_settings import get_worker_settings

logger = logging.getLogger(__name__)


def clone_or_init(url: str, token: str | None, server_type: str, dest: str, branch: str = "main") -> git.Repo:
    """Clone ``url`` into ``dest``; on failure initialize a fresh repo.

    HTTP URLs get provider-style token auth when a token is present. The
    init fallback checks out ``branch`` and (for HTTP URLs) registers the
    authenticated remote, so a later push targets the right place.
    """
    auth_url = make_provider_auth_url(url, token, server_type) if (token and 'http' in url) else url

    try:
        return git.Repo.clone_from(auth_url, dest)
    except Exception as e:
        logger.info(f"Could not clone repo, creating new: {e}")
        os.makedirs(dest, exist_ok=True)
        repo = git.Repo.init(dest)
        repo.git.checkout('-b', branch)
        if 'http' in url:
            repo.create_remote('origin', auth_url)
        return repo


def configure_identity(repo: git.Repo) -> tuple[str, str]:
    """Set the worker's commit identity from SYSTEM_GIT_EMAIL/NAME.

    Required in the worker container (no global git config). Returns the
    (email, name) pair for callers that need it elsewhere.
    """
    settings = get_worker_settings()
    git_email = settings.system_git_email
    git_name = settings.system_git_name
    repo.git.config('user.email', git_email)
    repo.git.config('user.name', git_name)
    return git_email, git_name


def push_with_rebase_retry(
    repo: git.Repo,
    branch: str = "main",
    max_attempts: int = 3,
    *,
    set_upstream_fallback: bool = False,
) -> None:
    """Push ``branch``, pulling with rebase and retrying on concurrent pushes.

    ``set_upstream_fallback`` additionally retries a failed push with
    ``-u`` (first push into an empty remote).
    """
    for attempt in range(max_attempts):
        try:
            repo.git.push('origin', branch)
            logger.info(f"Pushed changes to origin/{branch}")
            return
        except git.GitCommandError as push_err:
            err_msg = str(push_err).lower()
            is_conflict = (
                'non-fast-forward' in err_msg
                or 'fetch first' in err_msg
                or 'failed to push' in err_msg
            )
            if is_conflict and attempt < max_attempts - 1:
                logger.warning(
                    f"Push failed (attempt {attempt + 1}/{max_attempts}), "
                    f"pulling with rebase and retrying: {push_err}"
                )
                try:
                    repo.git.pull('--rebase', 'origin', branch)
                except git.GitCommandError as pull_err:
                    if set_upstream_fallback:
                        # Empty remote: nothing to rebase onto, set upstream instead
                        logger.info(f"Rebase failed, trying push with -u flag: {pull_err}")
                        repo.git.push('-u', 'origin', branch)
                        return
                    raise
                continue
            if not is_conflict and set_upstream_fallback:
                logger.info(f"Normal push failed, trying with -u flag: {push_err}")
                repo.git.push('-u', 'origin', branch)
                return
            logger.error(f"Push failed after {attempt + 1} attempt(s): {push_err}")
            raise


def commit_and_push(
    repo: git.Repo,
    message: str,
    branch: str = "main",
    max_attempts: int = 3,
    *,
    set_upstream_fallback: bool = False,
    success_without_remote: bool = True,
) -> bool:
    """Stage everything, commit when dirty, push with rebase-retry.

    Returns True when the repo ends up in sync with the remote (pushed, or
    nothing to do). Raises on push failure. ``success_without_remote``
    controls whether a repo with no 'origin' counts as success (the
    template flow) or not (the assignments mirror, whose callers gate
    deployment-record updates on an actual push).
    """
    repo.git.add(A=True)

    if not (repo.is_dirty() or repo.untracked_files):
        logger.info("No changes to commit")
        return True

    repo.index.commit(message)
    logger.info(f"Committed changes: {message}")

    if 'origin' not in [remote.name for remote in repo.remotes]:
        logger.warning("No remote 'origin' found, skipping push")
        return success_without_remote

    push_with_rebase_retry(
        repo, branch, max_attempts, set_upstream_fallback=set_upstream_fallback
    )
    return True

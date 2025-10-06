"""
Secure Git operations service using GitPython.

This service provides a secure abstraction over git operations,
replacing the unsafe subprocess calls with GitPython library.
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Optional, List

from git import Repo, GitCommandError, InvalidGitRepositoryError
from git.exc import NoSuchPathError

logger = logging.getLogger(__name__)


class GitServiceError(Exception):
    """Custom exception for Git service errors."""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(message)
        self.operation = operation


class GitService:
    """
    Secure git operations service using GitPython library.
    
    This service provides async wrappers around GitPython operations
    and handles authentication securely without embedding tokens in URLs.
    """
    
    def __init__(self, working_dir: Path):
        """
        Initialize GitService with a working directory.
        
        Args:
            working_dir: Base directory for git operations
        """
        self.working_dir = Path(working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"GitService initialized with working directory: {self.working_dir}")
    
    def repository_exists(self, directory: Path) -> bool:
        """
        Check if a directory is a valid git repository.
        
        Args:
            directory: Path to check
            
        Returns:
            True if directory is a git repository, False otherwise
        """
        try:
            Repo(directory)
            return True
        except (InvalidGitRepositoryError, NoSuchPathError):
            return False
    
    async def clone(
        self, 
        url: str, 
        token: str, 
        directory: Path,
        branch: Optional[str] = None
    ) -> Repo:
        """
        Clone a repository using secure authentication.
        
        Args:
            url: Repository URL (https)
            token: Authentication token
            directory: Target directory for clone
            branch: Optional branch to checkout after clone
            
        Returns:
            Cloned repository object
            
        Raises:
            GitServiceError: If cloning fails
        """
        try:
            # Ensure directory exists
            directory.parent.mkdir(parents=True, exist_ok=True)
            
            # Set up environment for secure authentication
            env = os.environ.copy()
            env.update({
                'GIT_ASKPASS': 'echo',
                'GIT_USERNAME': 'oauth2',
                'GIT_PASSWORD': token
            })
            
            # Clone with authentication
            logger.info(f"Cloning repository from {url} to {directory}")
            
            # Run clone in executor to avoid blocking
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(
                None,
                lambda: Repo.clone_from(
                    url,
                    str(directory),
                    env=env,
                    branch=branch
                )
            )
            
            logger.info(f"Successfully cloned repository to {directory}")
            return repo
            
        except GitCommandError as e:
            logger.error(f"Failed to clone repository: {e}")
            raise GitServiceError(
                f"Failed to clone repository: {str(e)}", 
                operation="clone"
            )
        except Exception as e:
            logger.error(f"Unexpected error during clone: {e}")
            raise GitServiceError(
                f"Unexpected error during clone: {str(e)}", 
                operation="clone"
            )
    
    async def create_repository(
        self,
        directory: Path,
        remote_url: str,
        initial_commit_message: Optional[str] = None
    ) -> Repo:
        """
        Create a new git repository with optional initial commit.
        
        Args:
            directory: Directory to initialize as git repo
            remote_url: Remote repository URL
            initial_commit_message: Optional message for initial commit
            
        Returns:
            Created repository object
            
        Raises:
            GitServiceError: If repository creation fails
        """
        try:
            # Ensure directory exists
            directory.mkdir(parents=True, exist_ok=True)
            
            # Initialize repository
            logger.info(f"Initializing new repository at {directory}")
            repo = Repo.init(directory)
            
            # Add remote
            repo.create_remote('origin', remote_url)
            
            # Create initial commit if requested
            if initial_commit_message:
                # Check if there are files to commit
                if any(directory.iterdir()):
                    repo.index.add('*')
                    repo.index.commit(initial_commit_message)
                    logger.info(f"Created initial commit: {initial_commit_message}")
            
            return repo
            
        except Exception as e:
            logger.error(f"Failed to create repository: {e}")
            raise GitServiceError(
                f"Failed to create repository: {str(e)}",
                operation="create_repository"
            )
    
    async def commit_and_push(
        self,
        repo: Repo,
        message: str,
        branch: str = "main",
        patterns: Optional[List[str]] = None,
        push: bool = True
    ) -> bool:
        """
        Commit changes and optionally push to remote.
        
        Args:
            repo: Repository object
            message: Commit message
            branch: Branch to push to
            patterns: Optional file patterns to add (default: all)
            push: Whether to push after commit
            
        Returns:
            True if commit was created, False if nothing to commit
            
        Raises:
            GitServiceError: If commit or push fails
        """
        try:
            # Add files
            if patterns:
                for pattern in patterns:
                    repo.index.add(pattern)
            else:
                repo.index.add('*')
            
            # Check if there are changes to commit
            if not repo.index.diff("HEAD") and not repo.untracked_files:
                logger.info("No changes to commit")
                return False
            
            # Commit changes
            commit = repo.index.commit(message)
            logger.info(f"Created commit: {commit.hexsha[:8]} - {message}")
            
            # Push if requested and remote exists
            if push and 'origin' in repo.remotes:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: repo.remotes.origin.push(branch)
                )
                logger.info(f"Pushed to origin/{branch}")
            
            return True
            
        except GitCommandError as e:
            logger.error(f"Failed to commit/push: {e}")
            raise GitServiceError(
                f"Failed to commit/push: {str(e)}",
                operation="commit_and_push"
            )
    
    async def checkout(
        self,
        repo_path: Path,
        ref: str,
        create: bool = False
    ) -> bool:
        """
        Checkout a branch or commit.
        
        Args:
            repo_path: Path to repository
            ref: Branch name or commit hash
            create: Create branch if it doesn't exist
            
        Returns:
            True if successful
            
        Raises:
            GitServiceError: If checkout fails
        """
        try:
            repo = Repo(repo_path)
            
            # Check if ref is a branch
            if ref in repo.heads:
                repo.heads[ref].checkout()
                logger.info(f"Checked out branch: {ref}")
            elif create:
                # Create new branch
                new_branch = repo.create_head(ref)
                new_branch.checkout()
                logger.info(f"Created and checked out new branch: {ref}")
            else:
                # Assume it's a commit hash
                repo.git.checkout(ref)
                logger.info(f"Checked out commit: {ref}")
            
            return True
            
        except (GitCommandError, InvalidGitRepositoryError) as e:
            logger.error(f"Failed to checkout {ref}: {e}")
            raise GitServiceError(
                f"Failed to checkout {ref}: {str(e)}",
                operation="checkout"
            )
    
    async def pull(self, repo_path: Path, remote: str = "origin") -> bool:
        """
        Pull latest changes from remote.
        
        Args:
            repo_path: Path to repository
            remote: Remote name (default: origin)
            
        Returns:
            True if successful
            
        Raises:
            GitServiceError: If pull fails
        """
        try:
            repo = Repo(repo_path)
            
            # Pull from remote
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: repo.remotes[remote].pull()
            )
            
            logger.info(f"Pulled latest changes from {remote}")
            return True
            
        except (GitCommandError, InvalidGitRepositoryError) as e:
            logger.error(f"Failed to pull: {e}")
            raise GitServiceError(
                f"Failed to pull: {str(e)}",
                operation="pull"
            )
    
    async def fetch_all(self, repo_path: Path) -> bool:
        """
        Fetch all remotes.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            True if successful
            
        Raises:
            GitServiceError: If fetch fails
        """
        try:
            repo = Repo(repo_path)
            
            # Fetch all remotes
            loop = asyncio.get_event_loop()
            for remote in repo.remotes:
                await loop.run_in_executor(
                    None,
                    remote.fetch
                )
            
            logger.info("Fetched all remotes")
            return True
            
        except (GitCommandError, InvalidGitRepositoryError) as e:
            logger.error(f"Failed to fetch: {e}")
            raise GitServiceError(
                f"Failed to fetch: {str(e)}",
                operation="fetch_all"
            )
    
    def get_version_identifier(self, repo_path: Path) -> str:
        """
        Get current commit hash (version identifier).
        
        Args:
            repo_path: Path to repository
            
        Returns:
            Current commit SHA hash
            
        Raises:
            GitServiceError: If getting version fails
        """
        try:
            repo = Repo(repo_path)
            
            # Check if repository has any commits
            try:
                commit = repo.head.commit
                return commit.hexsha
            except ValueError:
                raise GitServiceError(
                    "No commits in repository",
                    operation="get_version_identifier"
                )
                
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            logger.error(f"Failed to get version identifier: {e}")
            raise GitServiceError(
                f"Failed to get version identifier: {str(e)}",
                operation="get_version_identifier"
            )
    
    async def push_branch(
        self,
        repo_path: Path,
        branch: str,
        remote: str = "origin",
        set_upstream: bool = True
    ) -> bool:
        """
        Push a branch to remote.
        
        Args:
            repo_path: Path to repository
            branch: Branch name to push
            remote: Remote name (default: origin)
            set_upstream: Set upstream tracking
            
        Returns:
            True if successful
            
        Raises:
            GitServiceError: If push fails
        """
        try:
            repo = Repo(repo_path)
            
            # Push branch
            loop = asyncio.get_event_loop()
            
            if set_upstream:
                await loop.run_in_executor(
                    None,
                    lambda: repo.remotes[remote].push(
                        refspec=f'{branch}:{branch}',
                        set_upstream=True
                    )
                )
            else:
                await loop.run_in_executor(
                    None,
                    lambda: repo.remotes[remote].push(branch)
                )
            
            logger.info(f"Pushed branch {branch} to {remote}")
            return True
            
        except (GitCommandError, InvalidGitRepositoryError) as e:
            logger.error(f"Failed to push branch: {e}")
            raise GitServiceError(
                f"Failed to push branch: {str(e)}",
                operation="push_branch"
            )
    
    def branch_exists(self, repo_path: Path, branch: str, remote: bool = False) -> bool:
        """
        Check if a branch exists locally or on remote.
        
        Args:
            repo_path: Path to repository
            branch: Branch name
            remote: Check remote branches
            
        Returns:
            True if branch exists
        """
        try:
            repo = Repo(repo_path)
            
            if remote:
                # Check remote branches
                for ref in repo.remotes.origin.refs:
                    if ref.remote_head == branch:
                        return True
                return False
            else:
                # Check local branches
                return branch in repo.heads
                
        except Exception:
            return False
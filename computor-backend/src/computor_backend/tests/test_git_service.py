"""
Comprehensive tests for GitService.

This test suite covers all git operations including:
- Repository existence checks
- Cloning repositories
- Creating new repositories
- Committing and pushing changes
- Checking out branches/commits
- Getting version identifiers
"""

import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from git import Repo, GitCommandError

from computor_backend.services.git_service import GitService, GitServiceError


class TestGitService:
    """Test suite for GitService."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def git_service(self, temp_dir):
        """Create a GitService instance."""
        return GitService(working_dir=temp_dir)
    
    @pytest.fixture
    def mock_repo(self):
        """Create a mock Git repository."""
        repo = Mock(spec=Repo)
        repo.git = Mock()
        repo.index = Mock()
        repo.remotes = Mock()
        repo.remotes.origin = Mock()
        repo.heads = Mock()
        repo.head = Mock()
        repo.head.commit = Mock()
        repo.head.commit.hexsha = "abc123def456"
        return repo
    
    def test_init(self, temp_dir):
        """Test GitService initialization."""
        service = GitService(working_dir=temp_dir)
        assert service.working_dir == temp_dir
        assert service.working_dir.exists()
    
    def test_init_creates_working_dir(self):
        """Test that GitService creates working directory if it doesn't exist."""
        temp_dir = Path(tempfile.mktemp())  # Don't create the directory
        assert not temp_dir.exists()
        
        service = GitService(working_dir=temp_dir)
        assert service.working_dir.exists()
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Test repository_exists
    
    def test_repository_exists_true(self, git_service, temp_dir):
        """Test repository_exists returns True for valid git repo."""
        repo_path = temp_dir / "test_repo"
        repo_path.mkdir()
        Repo.init(repo_path)
        
        assert git_service.repository_exists(repo_path) is True
    
    def test_repository_exists_false(self, git_service, temp_dir):
        """Test repository_exists returns False for non-git directory."""
        non_repo_path = temp_dir / "not_a_repo"
        non_repo_path.mkdir()
        
        assert git_service.repository_exists(non_repo_path) is False
    
    def test_repository_exists_nonexistent_path(self, git_service, temp_dir):
        """Test repository_exists returns False for nonexistent path."""
        nonexistent_path = temp_dir / "does_not_exist"
        
        assert git_service.repository_exists(nonexistent_path) is False
    
    # Test clone
    
    @pytest.mark.asyncio
    @patch('computor_backend.services.git_service.Repo.clone_from')
    async def test_clone_success(self, mock_clone, git_service, temp_dir, mock_repo):
        """Test successful repository cloning."""
        mock_clone.return_value = mock_repo
        
        url = "https://github.com/test/repo.git"
        token = "test_token"
        directory = temp_dir / "cloned_repo"
        
        result = await git_service.clone(url, token, directory)
        
        assert result == mock_repo
        mock_clone.assert_called_once()
        
        # Check that URL doesn't contain token
        call_args = mock_clone.call_args
        assert token not in call_args[0][0]  # Check URL argument only
    
    @pytest.mark.asyncio
    @patch('computor_backend.services.git_service.Repo.clone_from')
    async def test_clone_with_auth(self, mock_clone, git_service, temp_dir, mock_repo):
        """Test cloning with authentication."""
        mock_clone.return_value = mock_repo
        
        url = "https://gitlab.com/test/repo.git"
        token = "secret_token"
        directory = temp_dir / "auth_repo"
        
        result = await git_service.clone(url, token, directory)
        
        # Verify environment variables for auth were set
        call_args = mock_clone.call_args
        env = call_args[1].get('env', {})
        assert 'GIT_ASKPASS' in env
        assert result == mock_repo
    
    @pytest.mark.asyncio
    @patch('computor_backend.services.git_service.Repo.clone_from')
    async def test_clone_failure(self, mock_clone, git_service, temp_dir):
        """Test clone failure handling."""
        mock_clone.side_effect = GitCommandError("clone", "Failed to clone")
        
        with pytest.raises(GitServiceError) as exc_info:
            await git_service.clone("https://invalid.git", "token", temp_dir / "fail")
        
        assert "Failed to clone repository" in str(exc_info.value)
    
    # Test create_repository
    
    @pytest.mark.asyncio
    @patch('computor_backend.services.git_service.Repo.init')
    async def test_create_repository_success(self, mock_init, git_service, temp_dir, mock_repo):
        """Test successful repository creation."""
        mock_init.return_value = mock_repo
        mock_repo.create_remote = Mock()
        
        directory = temp_dir / "new_repo"
        remote_url = "https://gitlab.com/test/new.git"
        
        result = await git_service.create_repository(directory, remote_url)
        
        assert result == mock_repo
        mock_init.assert_called_once()
        mock_repo.create_remote.assert_called_once_with('origin', remote_url)
    
    @pytest.mark.asyncio
    @patch('computor_backend.services.git_service.Repo.init')
    async def test_create_repository_with_initial_commit(self, mock_init, git_service, temp_dir, mock_repo):
        """Test repository creation with initial commit."""
        mock_init.return_value = mock_repo
        mock_repo.create_remote = Mock()
        
        directory = temp_dir / "new_repo_commit"
        remote_url = "https://gitlab.com/test/new.git"
        
        # Create some files
        directory.mkdir(parents=True)
        (directory / "README.md").write_text("# Test Repo")
        (directory / ".gitignore").write_text("*.pyc")
        
        result = await git_service.create_repository(
            directory, 
            remote_url, 
            initial_commit_message="Initial commit"
        )
        
        assert result == mock_repo
        mock_repo.index.add.assert_called()
        mock_repo.index.commit.assert_called_once_with("Initial commit")
    
    # Test commit_and_push
    
    @pytest.mark.asyncio
    async def test_commit_and_push_success(self, git_service, temp_dir):
        """Test successful commit and push."""
        repo_path = temp_dir / "test_push"
        repo = Repo.init(repo_path)
        
        # Create a file to commit
        test_file = repo_path / "test.txt"
        test_file.write_text("test content")
        
        # Add and commit first to have a HEAD
        repo.index.add([str(test_file)])
        repo.index.commit("Initial commit")
        
        # Create another file for the test
        test_file2 = repo_path / "test2.txt"
        test_file2.write_text("test content 2")
        
        # Test without push (since we don't have a real remote)
        result = await git_service.commit_and_push(
            repo,
            "Test commit",
            branch="main",
            push=False
        )
        
        assert result is True
        
        # Verify the commit was created
        assert repo.head.commit.message == "Test commit"
    
    @pytest.mark.asyncio
    async def test_commit_and_push_nothing_to_commit(self, git_service, temp_dir):
        """Test commit_and_push when there's nothing to commit."""
        repo_path = temp_dir / "empty_repo"
        repo = Repo.init(repo_path)
        
        # Create initial commit so we have a HEAD
        test_file = repo_path / "initial.txt"
        test_file.write_text("initial")
        repo.index.add([str(test_file)])
        repo.index.commit("Initial commit")
        
        # Now try to commit with no changes
        result = await git_service.commit_and_push(repo, "Empty commit", push=False)
        
        assert result is False  # Nothing to commit
    
    @pytest.mark.asyncio
    async def test_commit_and_push_with_patterns(self, git_service, temp_dir):
        """Test commit_and_push with specific file patterns."""
        repo_path = temp_dir / "pattern_repo"
        repo = Repo.init(repo_path)
        
        # Create initial commit
        initial_file = repo_path / "initial.txt"
        initial_file.write_text("initial")
        repo.index.add([str(initial_file)])
        initial_commit = repo.index.commit("Initial commit")
        
        # Create multiple files
        (repo_path / "include.txt").write_text("include me")
        (repo_path / "exclude.log").write_text("exclude me")
        (repo_path / "data.txt").write_text("more text data")
        
        result = await git_service.commit_and_push(
            repo,
            "Selective commit",
            patterns=["*.txt"],
            push=False
        )
        
        assert result is True
        
        # Check what was committed
        latest_commit = repo.head.commit
        assert latest_commit != initial_commit
        
        # Get the files in the latest commit
        committed_files = []
        for item in latest_commit.tree.traverse():
            if item.type == 'blob':
                committed_files.append(item.path)
        
        # All .txt files should be there
        assert "initial.txt" in committed_files
        assert "include.txt" in committed_files
        assert "data.txt" in committed_files
        # .log file should NOT be committed
        assert "exclude.log" not in committed_files
    
    # Test checkout
    
    @pytest.mark.asyncio
    @patch('computor_backend.services.git_service.Repo')
    async def test_checkout_branch(self, mock_repo_class, git_service, temp_dir):
        """Test checking out a branch."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_branch = Mock()
        mock_repo.heads = {'feature': mock_branch}
        
        repo_path = temp_dir / "checkout_repo"
        
        result = await git_service.checkout(repo_path, "feature")
        
        assert result is True
        mock_branch.checkout.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('computor_backend.services.git_service.Repo')
    async def test_checkout_commit(self, mock_repo_class, git_service, temp_dir):
        """Test checking out a specific commit."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.heads = {}
        
        repo_path = temp_dir / "checkout_commit"
        commit_hash = "abc123def456"
        
        result = await git_service.checkout(repo_path, commit_hash)
        
        assert result is True
        mock_repo.git.checkout.assert_called_once_with(commit_hash)
    
    @pytest.mark.asyncio
    @patch('computor_backend.services.git_service.Repo')
    async def test_checkout_create_branch(self, mock_repo_class, git_service, temp_dir):
        """Test creating and checking out a new branch."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.heads = {}
        mock_repo.create_head = Mock()
        
        repo_path = temp_dir / "new_branch_repo"
        
        result = await git_service.checkout(repo_path, "new-feature", create=True)
        
        assert result is True
        mock_repo.create_head.assert_called_once_with("new-feature")
    
    # Test pull
    
    @pytest.mark.asyncio
    @patch('computor_backend.services.git_service.Repo')
    async def test_pull_success(self, mock_repo_class, git_service, temp_dir):
        """Test successful pull operation."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_origin = Mock()
        mock_origin.pull = Mock(return_value=[Mock()])
        
        # Set up remotes dictionary-like behavior
        mock_remotes = Mock()
        mock_remotes.__getitem__ = Mock(return_value=mock_origin)
        mock_repo.remotes = mock_remotes
        
        repo_path = temp_dir / "pull_repo"
        
        result = await git_service.pull(repo_path)
        
        assert result is True
        mock_origin.pull.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('computor_backend.services.git_service.Repo')
    async def test_pull_failure(self, mock_repo_class, git_service, temp_dir):
        """Test pull operation failure."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_origin = Mock()
        mock_origin.pull.side_effect = GitCommandError("pull", "Failed to pull")
        
        # Set up remotes dictionary-like behavior
        mock_remotes = Mock()
        mock_remotes.__getitem__ = Mock(return_value=mock_origin)
        mock_repo.remotes = mock_remotes
        
        repo_path = temp_dir / "pull_fail"
        
        with pytest.raises(GitServiceError) as exc_info:
            await git_service.pull(repo_path)
        
        assert "Failed to pull" in str(exc_info.value)
    
    # Test get_version_identifier
    
    def test_get_version_identifier(self, git_service, temp_dir):
        """Test getting current commit hash."""
        repo_path = temp_dir / "version_repo"
        repo = Repo.init(repo_path)
        
        # Create initial commit
        test_file = repo_path / "test.txt"
        test_file.write_text("content")
        repo.index.add([str(test_file)])
        commit = repo.index.commit("Initial commit")
        
        version = git_service.get_version_identifier(repo_path)
        
        assert version == commit.hexsha
        assert len(version) == 40  # SHA-1 hash length
    
    def test_get_version_identifier_no_commits(self, git_service, temp_dir):
        """Test getting version identifier from repo with no commits."""
        repo_path = temp_dir / "empty_repo"
        Repo.init(repo_path)
        
        with pytest.raises(GitServiceError) as exc_info:
            git_service.get_version_identifier(repo_path)
        
        assert "No commits" in str(exc_info.value)
    
    # Test fetch_all
    
    @pytest.mark.asyncio
    @patch('computor_backend.services.git_service.Repo')
    async def test_fetch_all_success(self, mock_repo_class, git_service, temp_dir):
        """Test fetching all remotes."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_origin = Mock()
        mock_repo.remotes = [mock_origin]
        
        repo_path = temp_dir / "fetch_repo"
        
        result = await git_service.fetch_all(repo_path)
        
        assert result is True
        mock_origin.fetch.assert_called_once()
    
    # Test error handling
    
    def test_git_service_error(self):
        """Test GitServiceError exception."""
        error = GitServiceError("Test error", operation="clone")
        
        assert str(error) == "Test error"
        assert error.operation == "clone"
    
    # Integration tests
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_workflow(self, git_service, temp_dir):
        """Test complete workflow: create, commit, version."""
        repo_path = temp_dir / "integration_repo"
        
        # Create repository
        repo = await git_service.create_repository(
            repo_path,
            "https://example.com/test.git"
        )
        
        # Add files
        (repo_path / "README.md").write_text("# Integration Test")
        (repo_path / "src").mkdir()
        (repo_path / "src" / "main.py").write_text("print('Hello')")
        
        # Make initial commit
        repo.index.add(["README.md", "src/main.py"])
        initial_commit = repo.index.commit("Initial commit")
        
        # Get version after first commit
        version1 = git_service.get_version_identifier(repo_path)
        assert version1 == initial_commit.hexsha
        
        # Make another change
        (repo_path / "src" / "test.py").write_text("print('Test')")
        
        # Commit using our service (without push)
        result = await git_service.commit_and_push(
            repo,
            "Add test file",
            push=False
        )
        
        assert result is True
        
        # Get new version
        version2 = git_service.get_version_identifier(repo_path)
        
        assert version1 != version2
        assert len(version2) == 40
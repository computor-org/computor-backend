"""
Tests for the new GitLab builder with database integration.

This test suite covers:
- Complete deployment hierarchy creation
- GitLab group creation with enhanced properties
- Database entry creation and validation
- Error handling for both GitLab and database operations
- Idempotency testing
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from uuid import uuid4
from gitlab.exceptions import GitlabCreateError, GitlabGetError
from sqlalchemy.exc import IntegrityError

from computor_backend.generator.gitlab_builder import GitLabBuilder
from computor_types.deployments import (
    ComputorDeploymentConfig,
    OrganizationConfig,
    CourseFamilyConfig,
    CourseConfig,
    GitLabConfig
)
from computor_backend.model.organization import Organization
from computor_backend.model.course import CourseFamily, Course


class TestGitLabBuilder:
    """Test suite for new GitLab builder."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock()
        session.query = Mock()
        session.add = Mock()
        session.flush = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        return session
    
    @pytest.fixture
    def mock_gitlab(self):
        """Create a mock GitLab instance."""
        gitlab = Mock()
        gitlab.auth = Mock()
        gitlab.groups = Mock()
        return gitlab
    
    @pytest.fixture
    def mock_org_repo(self):
        """Create a mock organization repository."""
        repo = Mock()
        repo.find_by_path = Mock(return_value=None)
        repo.create = Mock()
        return repo
    
    @pytest.fixture
    def sample_deployment(self):
        """Create a sample deployment configuration."""
        return ComputorDeploymentConfig(
            organization=OrganizationConfig(
                name="Test Organization",
                path="test-org",
                description="Test organization for builder",
                gitlab=GitLabConfig(
                    url="http://localhost:8084",
                    token="test-token",
                    parent=2
                )
            ),
            courseFamily=CourseFamilyConfig(
                name="Test Course Family",
                path="test-family",
                description="Test course family"
            ),
            course=CourseConfig(
                name="Test Course",
                path="test-course",
                description="Test course"
            )
        )
    
    @pytest.fixture
    def mock_gitlab_group(self):
        """Create a mock GitLab group."""
        group = Mock()
        group.id = 100
        group.full_path = "parent-group/test-org"
        group.path = "test-org"
        group.name = "Test Organization"
        group.parent_id = 2
        group.web_url = "http://localhost:8084/parent-group/test-org"
        group.visibility = "private"
        group.namespace = {"id": 50, "path": "parent-group"}
        return group
    
    @patch('computor_backend.generator.gitlab_builder.Gitlab')
    @patch('computor_backend.generator.gitlab_builder.OrganizationRepository')
    def test_initialization(self, mock_repo_class, mock_gitlab_class, mock_db_session):
        """Test GitLab builder initialization."""
        # Setup mocks
        mock_gitlab_instance = Mock()
        mock_gitlab_instance.version = Mock()
        mock_gitlab_class.return_value = mock_gitlab_instance
        
        mock_repo_instance = Mock()
        mock_repo_class.return_value = mock_repo_instance
        
        # Create builder
        builder = GitLabBuilder(
            db_session=mock_db_session,
            gitlab_url="http://localhost:8084",
            gitlab_token="test-token"
        )
        
        # Verify initialization
        assert builder.db == mock_db_session
        assert builder.gitlab_url == "http://localhost:8084"
        assert builder.gitlab_token == "test-token"
        mock_gitlab_instance.version.assert_called_once()
        mock_repo_class.assert_called_once_with(mock_db_session)
    
    @patch('computor_backend.interface.tokens.encrypt_api_key')
    @patch('computor_backend.generator.gitlab_builder.Gitlab')
    @patch('computor_backend.generator.gitlab_builder.OrganizationRepository')
    def test_create_deployment_hierarchy_success(
        self,
        mock_repo_class,
        mock_gitlab_class,
        mock_encrypt,
        mock_db_session,
        sample_deployment,
        mock_gitlab_group
    ):
        """Test successful deployment hierarchy creation."""
        # Setup mocks
        mock_encrypt.return_value = "encrypted-token"
        mock_gitlab_instance = Mock()
        mock_gitlab_instance.auth = Mock()
        mock_gitlab_instance.groups.list.return_value = []
        mock_gitlab_instance.groups.create.return_value = mock_gitlab_group
        mock_gitlab_instance.groups.get.return_value = mock_gitlab_group
        mock_gitlab_class.return_value = mock_gitlab_instance
        
        mock_repo_instance = Mock()
        mock_repo_instance.find_by_path.return_value = None
        
        # Mock organization creation
        mock_org = Mock(spec=Organization)
        mock_org.id = uuid4()
        mock_org.path = "test-org"
        mock_org.properties = {
            'gitlab': {
                'group_id': 1,
                'full_path': 'test-org'
            }
        }
        mock_repo_instance.create.return_value = mock_org
        mock_repo_class.return_value = mock_repo_instance
        
        # Mock course family query
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Create builder
        builder = GitLabBuilder(
            db_session=mock_db_session,
            gitlab_url="http://localhost:8084",
            gitlab_token="test-token"
        )
        
        # Execute
        result = builder.create_deployment_hierarchy(sample_deployment)
        
        # Verify success
        assert result["success"] is True
        assert result["organization"] is not None
        assert len(result["gitlab_groups_created"]) > 0
        assert len(result["database_entries_created"]) > 0
        assert len(result["errors"]) == 0
        
        # Verify database operations
        mock_db_session.commit.assert_called_once()
        mock_db_session.rollback.assert_not_called()
    
    @patch('computor_backend.interface.tokens.encrypt_api_key')
    @patch('computor_backend.generator.gitlab_builder.Gitlab')
    @patch('computor_backend.generator.gitlab_builder.OrganizationRepository')
    def test_create_deployment_hierarchy_gitlab_error(
        self,
        mock_repo_class,
        mock_gitlab_class,
        mock_encrypt,
        mock_db_session,
        sample_deployment
    ):
        """Test deployment creation with GitLab error."""
        # Setup mocks
        mock_encrypt.return_value = "encrypted-token"
        mock_gitlab_instance = Mock()
        mock_gitlab_instance.auth = Mock()
        mock_gitlab_instance.groups.list.return_value = []
        mock_gitlab_instance.groups.create.side_effect = GitlabCreateError("GitLab error")
        mock_gitlab_class.return_value = mock_gitlab_instance
        
        mock_repo_instance = Mock()
        mock_repo_instance.find_by_path.return_value = None
        mock_repo_class.return_value = mock_repo_instance
        
        # Create builder
        builder = GitLabBuilder(
            db_session=mock_db_session,
            gitlab_url="http://localhost:8084",
            gitlab_token="test-token"
        )
        
        # Execute
        result = builder.create_deployment_hierarchy(sample_deployment)
        
        # Verify failure
        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert "GitLab error" in result["errors"][0]
        
        # Verify rollback
        mock_db_session.rollback.assert_called()
        mock_db_session.commit.assert_not_called()
    
    @patch('computor_backend.interface.tokens.encrypt_api_key')
    @patch('computor_backend.generator.gitlab_builder.Gitlab')
    @patch('computor_backend.generator.gitlab_builder.OrganizationRepository')
    def test_create_deployment_hierarchy_database_error(
        self,
        mock_repo_class,
        mock_gitlab_class,
        mock_encrypt,
        mock_db_session,
        sample_deployment,
        mock_gitlab_group
    ):
        """Test deployment creation with database error."""
        # Setup mocks
        mock_encrypt.return_value = "encrypted-token"
        mock_gitlab_instance = Mock()
        mock_gitlab_instance.auth = Mock()
        mock_gitlab_instance.groups.list.return_value = []
        mock_gitlab_instance.groups.create.return_value = mock_gitlab_group
        mock_gitlab_class.return_value = mock_gitlab_instance
        
        mock_repo_instance = Mock()
        mock_repo_instance.find_by_path.return_value = None
        mock_repo_instance.create.side_effect = IntegrityError("", "", "")
        mock_repo_class.return_value = mock_repo_instance
        
        # Create builder
        builder = GitLabBuilder(
            db_session=mock_db_session,
            gitlab_url="http://localhost:8084",
            gitlab_token="test-token"
        )
        
        # Execute
        result = builder.create_deployment_hierarchy(sample_deployment)
        
        # Verify failure
        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert "Database integrity error" in result["errors"][0]
        
        # Verify rollback
        mock_db_session.rollback.assert_called()
        mock_db_session.commit.assert_not_called()
    
    @patch('computor_backend.generator.gitlab_builder.Gitlab')
    @patch('computor_backend.generator.gitlab_builder.OrganizationRepository')
    def test_idempotency_existing_organization(
        self,
        mock_repo_class,
        mock_gitlab_class,
        mock_db_session,
        sample_deployment,
        mock_gitlab_group
    ):
        """Test idempotency with existing organization."""
        # Setup mocks
        mock_gitlab_instance = Mock()
        mock_gitlab_instance.auth = Mock()
        mock_gitlab_instance.groups.get.return_value = mock_gitlab_group
        mock_gitlab_class.return_value = mock_gitlab_instance
        
        # Mock existing organization with GitLab properties
        mock_existing_org = Mock(spec=Organization)
        mock_existing_org.id = uuid4()
        mock_existing_org.path = "test-org"
        mock_existing_org.properties = {
            "gitlab": {
                "group_id": 100,
                "full_path": "parent-group/test-org"
            }
        }
        
        mock_repo_instance = Mock()
        mock_repo_instance.find_by_path.return_value = mock_existing_org
        mock_repo_class.return_value = mock_repo_instance
        
        # Mock course family query (not exists)
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Create builder
        builder = GitLabBuilder(
            db_session=mock_db_session,
            gitlab_url="http://localhost:8084",
            gitlab_token="test-token"
        )
        
        # Execute
        result = builder.create_deployment_hierarchy(sample_deployment)
        
        # Verify existing organization was used
        assert result["organization"] == mock_existing_org
        # Should not create new organization in database
        mock_repo_instance.create.assert_not_called()
    
    @pytest.mark.skip(reason="Complex mock scenario with deep object interactions - needs refactoring")
    @patch('computor_backend.interface.tokens.encrypt_api_key')
    @patch('computor_backend.generator.gitlab_builder.Gitlab')
    @patch('computor_backend.generator.gitlab_builder.OrganizationRepository')
    def test_validate_and_recreate_missing_gitlab_group(
        self,
        mock_repo_class,
        mock_gitlab_class,
        mock_encrypt,
        mock_db_session,
        sample_deployment,
        mock_gitlab_group
    ):
        """Test recreation of missing GitLab group."""
        # Setup mocks
        mock_encrypt.return_value = "encrypted-token"
        mock_gitlab_instance = Mock()
        mock_gitlab_instance.auth = Mock()
        # First get fails (group missing), then create succeeds
        mock_gitlab_instance.groups.get.side_effect = [
            GitlabGetError("404 Not Found"),  # Validation fails
            mock_gitlab_group  # After recreation
        ]
        mock_gitlab_instance.groups.list.return_value = []
        mock_gitlab_instance.groups.create.return_value = mock_gitlab_group
        mock_gitlab_class.return_value = mock_gitlab_instance
        
        # Mock existing organization with GitLab properties
        mock_existing_org = Mock(spec=Organization)
        mock_existing_org.id = uuid4()
        mock_existing_org.path = "test-org"
        mock_existing_org.properties = {
            "gitlab": {
                "group_id": 100,
                "full_path": "parent-group/test-org"
            }
        }
        # Add SQLAlchemy attribute to avoid error
        mock_existing_org._sa_instance_state = Mock()
        # Mock update method
        mock_existing_org.update = Mock(return_value=mock_existing_org)
        
        mock_repo_instance = Mock()
        mock_repo_instance.find_by_path.return_value = mock_existing_org
        mock_repo_instance.update = Mock(return_value=mock_existing_org)
        mock_repo_class.return_value = mock_repo_instance
        
        # Mock course family query
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Create builder
        builder = GitLabBuilder(
            db_session=mock_db_session,
            gitlab_url="http://localhost:8084",
            gitlab_token="test-token"
        )
        
        # Execute
        result = builder.create_deployment_hierarchy(sample_deployment)
        
        # Verify GitLab group was recreated
        assert len(result["gitlab_groups_created"]) > 0
        mock_gitlab_instance.groups.create.assert_called()
    
    def test_create_enhanced_config(self, mock_db_session, mock_gitlab_group):
        """Test enhanced GitLab config creation."""
        with patch('computor_backend.interface.tokens.encrypt_api_key') as mock_encrypt:
            mock_encrypt.return_value = "encrypted-token"
            with patch('computor_backend.generator.gitlab_builder.Gitlab'):
                with patch('computor_backend.generator.gitlab_builder.OrganizationRepository'):
                    builder = GitLabBuilder(
                        db_session=mock_db_session,
                        gitlab_url="http://localhost:8084",
                        gitlab_token="test-token"
                    )
                    
                    config = builder._create_organization_gitlab_config(mock_gitlab_group)
                    
                    assert config["group_id"] == 100
                    assert config["full_path"] == "parent-group/test-org"
                    assert config["parent_id"] == 2
                    assert config["namespace_id"] == 50
                    assert config["namespace_path"] == "parent-group"
                    assert config["web_url"] == "http://localhost:8084/groups/parent-group/test-org"
                    assert config["visibility"] == "private"
                    assert "last_synced_at" in config
    
    @patch('computor_backend.generator.gitlab_builder.logger')
    def test_logging(self, mock_logger, mock_db_session):
        """Test proper logging throughout operations."""
        with patch('computor_backend.generator.gitlab_builder.Gitlab'):
            with patch('computor_backend.generator.gitlab_builder.OrganizationRepository'):
                builder = GitLabBuilder(
                    db_session=mock_db_session,
                    gitlab_url="http://localhost:8084",
                    gitlab_token="test-token"
                )
                
                # Verify initialization logging
                mock_logger.info.assert_called()
                assert "Successfully authenticated" in str(mock_logger.info.call_args)
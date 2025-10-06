"""
Test configuration constants for GitLab integration testing.
"""

import os

# Test GitLab instance configuration
TEST_GITLAB_URL = os.environ.get("TEST_GITLAB_URL", "http://localhost:8080")
TEST_GITLAB_TOKEN = os.environ.get("TEST_GITLAB_TOKEN", "")
TEST_GITLAB_GROUP_ID = int(os.environ.get("TEST_GITLAB_GROUP_ID", "1"))

# Test repository URLs (will be constructed from base URL)
def get_test_repo_url(project_path: str) -> str:
    """
    Construct test repository URL.
    
    Args:
        project_path: GitLab project path (e.g., "group/project")
        
    Returns:
        Full repository URL
    """
    return f"{TEST_GITLAB_URL}/{project_path}.git"

# Test data constants
TEST_ORGANIZATION_NAME = "Test Organization"
TEST_ORGANIZATION_PATH = "test-org"
TEST_COURSE_FAMILY_NAME = "Test Course Family"
TEST_COURSE_FAMILY_PATH = "test-course-family"
TEST_COURSE_NAME = "Test Course"
TEST_COURSE_PATH = "test-course"

# Pytest markers for integration tests
INTEGRATION_TEST_MARKER = "integration"
GITLAB_TEST_MARKER = "gitlab"

def gitlab_available() -> bool:
    """
    Check if GitLab test instance is available.
    
    Returns:
        True if GitLab instance can be reached
    """
    try:
        import requests
        response = requests.get(f"{TEST_GITLAB_URL}/api/v4/version", timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def skip_if_no_gitlab():
    """
    Pytest decorator to skip tests if GitLab is not available.
    """
    import pytest
    return pytest.mark.skipif(
        not gitlab_available(),
        reason="GitLab test instance not available"
    )
#!/usr/bin/env python
"""Test students group creation in GitLab."""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env file from project root
env_file = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_file)

from computor_backend.generator.gitlab_builder import GitLabBuilder
from computor_backend.interface.deployments import (
    ComputorDeploymentConfig,
    OrganizationConfig,
    CourseFamilyConfig,
    CourseConfig,
    GitLabConfig
)
from computor_backend.database import get_db
import gitlab

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_deployment():
    """Create a test deployment configuration."""
    return ComputorDeploymentConfig(
        organization=OrganizationConfig(
            name="Test Org Students",
            path="test-org-students",
            description="Test organization for students group",
            gitlab=GitLabConfig(
                parent=1,  # Root namespace
                url="",
                directory=""
            )
        ),
        courseFamily=CourseFamilyConfig(
            name="Test Family Students",
            path="test-family-students",
            description="Test course family for students group",
            gitlab=GitLabConfig(
                parent=None,
                url="",
                directory=""
            )
        ),
        course=CourseConfig(
            name="Test Course Students",
            path="test-course-students",
            description="Test course for students group testing",
            gitlab=GitLabConfig(
                parent=None,
                url="",
                directory=""
            )
        )
    )

async def main():
    """Main test function."""
    # Get database session
    db = next(get_db())
    
    # Get GitLab connection
    gitlab_url = os.getenv("GITLAB_URL", "http://localhost:8084")
    gitlab_token = os.getenv("TEST_GITLAB_TOKEN")
    
    if not gitlab_token:
        logger.error("TEST_GITLAB_TOKEN environment variable not set")
        logger.info("Please run with: TEST_GITLAB_TOKEN='your-token' python test_students_group.py")
        return
    
    gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_token)
    
    try:
        # Test authentication by making a simple API call
        # For group tokens, gl.auth() doesn't work properly
        version = gl.version()
        logger.info("✅ GitLab authentication successful")
        logger.info(f"Connected to GitLab version: {version}")
    except Exception as e:
        logger.error(f"GitLab authentication failed: {e}")
        return
    
    # Create builder
    builder = GitLabBuilder(db=db, gitlab=gl, user_id="test-user")
    
    # Create deployment config
    deployment = create_test_deployment()
    
    try:
        # Create the full hierarchy
        logger.info("Creating organization...")
        org_result = builder._create_organization(deployment, created_by_user_id="test-user")
        
        if not org_result["success"]:
            logger.error(f"Failed to create organization: {org_result['error']}")
            return
        
        organization = org_result["organization"]
        logger.info(f"✓ Organization created: {organization.path}")
        
        logger.info("Creating course family...")
        family_result = builder._create_course_family(
            deployment, 
            organization, 
            created_by_user_id="test-user"
        )
        
        if not family_result["success"]:
            logger.error(f"Failed to create course family: {family_result['error']}")
            return
        
        course_family = family_result["course_family"]
        logger.info(f"✓ Course family created: {course_family.path}")
        
        logger.info("Creating course...")
        course_result = builder._create_course(
            deployment,
            organization,
            course_family,
            created_by_user_id="test-user"
        )
        
        if not course_result["success"]:
            logger.error(f"Failed to create course: {course_result['error']}")
            return
        
        course = course_result["course"]
        logger.info(f"✓ Course created: {course.path}")
        
        # Check if students group was created
        if course.properties and course.properties.get("gitlab", {}).get("students_group"):
            students_info = course.properties["gitlab"]["students_group"]
            logger.info(f"✓ Students group created:")
            logger.info(f"  - Group ID: {students_info['group_id']}")
            logger.info(f"  - Full path: {students_info['full_path']}")
            logger.info(f"  - Web URL: {students_info['web_url']}")
            
            # Verify the group exists in GitLab
            try:
                students_group = gl.groups.get(students_info['group_id'])
                logger.info(f"✓ Verified students group exists in GitLab: {students_group.full_path}")
            except Exception as e:
                logger.error(f"✗ Failed to verify students group in GitLab: {e}")
        else:
            logger.warning("✗ Students group information not found in course properties")
        
        # Commit the changes
        db.commit()
        logger.info("✓ All changes committed to database")
        
    except Exception as e:
        logger.error(f"Error during test: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
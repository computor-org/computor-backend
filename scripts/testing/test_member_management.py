#!/usr/bin/env python
"""Test member management in GitLab groups."""
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
from computor_backend.database import get_db
from computor_backend.model.course import Course
from sqlalchemy_utils import Ltree
import gitlab

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main test function."""
    # Get database session
    db = next(get_db())
    
    # Get GitLab connection
    gitlab_url = os.getenv("GITLAB_URL", "http://localhost:8084")
    gitlab_token = os.getenv("TEST_GITLAB_TOKEN")
    
    if not gitlab_token:
        logger.error("TEST_GITLAB_TOKEN environment variable not set")
        logger.info("Please run with: GITLAB_TOKEN='your-token' python test_member_management.py")
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
    
    try:
        # Find a test course
        test_course = db.query(Course).filter(
            Course.path == Ltree("test-course-students")
        ).first()
        
        if not test_course:
            logger.error("Test course not found. Please run test_students_group.py first.")
            return
        
        logger.info(f"Found test course: {test_course.path}")
        
        # Get or create a test user in GitLab
        test_username = "test_student_1"
        test_user = None
        
        try:
            # Try to find existing user
            users = gl.users.list(username=test_username)
            if users:
                test_user = users[0]
                logger.info(f"Found existing test user: {test_user.username} (ID: {test_user.id})")
            else:
                # Create test user
                test_user = gl.users.create({
                    'email': f'{test_username}@example.com',
                    'username': test_username,
                    'name': 'Test Student 1',
                    'password': 'TestPassword123!',
                    'skip_confirmation': True
                })
                logger.info(f"Created test user: {test_user.username} (ID: {test_user.id})")
        except Exception as e:
            logger.error(f"Error handling test user: {e}")
            return
        
        # Test adding student to course
        logger.info("\n--- Testing add_student_to_course ---")
        result = builder.add_student_to_course(test_course, test_user.id)
        
        if result["success"]:
            logger.info("✓ Successfully added student to course")
        else:
            logger.error(f"✗ Failed to add student: {result['error']}")
        
        # Test adding the same student again (should handle gracefully)
        logger.info("\n--- Testing duplicate student addition ---")
        result = builder.add_student_to_course(test_course, test_user.id)
        
        if result["success"]:
            logger.info("✓ Handled duplicate student addition gracefully")
        else:
            logger.error(f"✗ Failed on duplicate addition: {result['error']}")
        
        # Create a test lecturer user
        test_lecturer_username = "test_lecturer_1"
        test_lecturer = None
        
        try:
            users = gl.users.list(username=test_lecturer_username)
            if users:
                test_lecturer = users[0]
                logger.info(f"Found existing lecturer: {test_lecturer.username} (ID: {test_lecturer.id})")
            else:
                test_lecturer = gl.users.create({
                    'email': f'{test_lecturer_username}@example.com',
                    'username': test_lecturer_username,
                    'name': 'Test Lecturer 1',
                    'password': 'TestPassword123!',
                    'skip_confirmation': True
                })
                logger.info(f"Created test lecturer: {test_lecturer.username} (ID: {test_lecturer.id})")
        except Exception as e:
            logger.error(f"Error handling test lecturer: {e}")
            return
        
        # Test adding lecturer to course
        logger.info("\n--- Testing add_lecturer_to_course ---")
        result = builder.add_lecturer_to_course(test_course, test_lecturer.id)
        
        if result["success"]:
            logger.info("✓ Successfully added lecturer to course")
        else:
            logger.error(f"✗ Failed to add lecturer: {result['error']}")
        
        # Verify memberships
        logger.info("\n--- Verifying memberships ---")
        
        # Check students group
        if test_course.properties and test_course.properties.get("gitlab", {}).get("students_group"):
            students_group_id = test_course.properties["gitlab"]["students_group"]["group_id"]
            students_group = gl.groups.get(students_group_id)
            
            members = students_group.members.list()
            logger.info(f"Students group members: {[m.username for m in members]}")
            
            if any(m.id == test_user.id for m in members):
                logger.info("✓ Student is correctly in students group")
            else:
                logger.error("✗ Student not found in students group")
        
        # Check course group
        if test_course.properties and test_course.properties.get("gitlab", {}).get("group_id"):
            course_group_id = test_course.properties["gitlab"]["group_id"]
            course_group = gl.groups.get(course_group_id)
            
            members = course_group.members.list()
            logger.info(f"Course group members: {[m.username for m in members]}")
            
            if any(m.id == test_lecturer.id for m in members):
                logger.info("✓ Lecturer is correctly in course group")
            else:
                logger.error("✗ Lecturer not found in course group")
        
        # Test removing members
        logger.info("\n--- Testing member removal ---")
        
        # Remove student from students group
        if test_course.properties and test_course.properties.get("gitlab", {}).get("students_group"):
            students_group_id = test_course.properties["gitlab"]["students_group"]["group_id"]
            result = builder.remove_member_from_group(students_group_id, test_user.id)
            
            if result["success"]:
                logger.info("✓ Successfully removed student from students group")
            else:
                logger.error(f"✗ Failed to remove student: {result['error']}")
        
        logger.info("\n✓ Member management test completed")
        
    except Exception as e:
        logger.error(f"Error during test: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
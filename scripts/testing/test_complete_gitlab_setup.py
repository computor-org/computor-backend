#!/usr/bin/env python
"""Test complete GitLab setup with all new features."""
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

def create_demo_deployment():
    """Create a demo deployment configuration."""
    # Use fixed names instead of random suffix to avoid creating multiple instances
    
    return ComputorDeploymentConfig(
        organization=OrganizationConfig(
            name="Demo University",
            path="demo_university",  # Fixed name - no random suffix
            description="Demo university for testing GitLab integration",
            gitlab=GitLabConfig(
                parent=os.environ.get("TEST_GITLAB_GROUP_ID"),
                token=os.environ.get("TEST_GITLAB_TOKEN")
            )
        ),
        courseFamily=CourseFamilyConfig(
            name="Computer Science 2024",
            path="cs_2024",  # Fixed name - no random suffix
            description="Computer Science courses for 2024",
            gitlab=GitLabConfig(
                parent=None,
                url="",
                directory=""
            )
        ),
        course=CourseConfig(
            name="Introduction to Programming",
            path="intro_programming",  # Fixed name - no random suffix
            description="Learn programming fundamentals with Python",
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
    gitlab_url = os.getenv("TEST_GITLAB_URL", os.getenv("GITLAB_URL", "http://localhost:8084"))
    gitlab_token = os.getenv("TEST_GITLAB_TOKEN")
    
    if not gitlab_token:
        logger.error("GITLAB_TOKEN environment variable not set")
        logger.info("Please run with: GITLAB_TOKEN='your-token' python test_complete_gitlab_setup.py")
        logger.info("\nTo get a token:")
        logger.info("1. Go to http://localhost:8084")
        logger.info("2. Login as root/topsecret123")
        logger.info("3. Go to User Settings > Access Tokens")
        logger.info("4. Create a token with 'api' scope")
        return
    
    gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_token)
    
    try:
        # Test authentication by making a simple API call
        # For group tokens, gl.auth() doesn't work properly
        version = gl.version()
        logger.info("✅ GitLab authentication successful")
        logger.info(f"Connected to GitLab version: {version}")
        
        # Try to get user info if it's a personal token
        try:
            user = gl.user
            if user:
                logger.info(f"Connected as user: {user.username}")
            else:
                logger.info("Connected with group/project token")
        except:
            logger.info("Connected with group/project token")
        
        # Test if we can create groups by trying to list groups
        try:
            groups = gl.groups.list(per_page=1)
            logger.info(f"✅ Can access groups API (found {len(groups)} groups)")
        except Exception as e:
            logger.error(f"❌ Cannot access groups API: {e}")
            logger.error("This token may not have 'api' scope or group creation permissions")
            return
            
    except Exception as e:
        logger.error(f"GitLab authentication failed: {e}")
        return
    
    # Create builder
    builder = GitLabBuilder(
        db_session=db,
        gitlab_url=gitlab_url,
        gitlab_token=gitlab_token
    )
    
    # Create deployment config
    deployment = create_demo_deployment()
    
    try:
        logger.info("\n" + "="*60)
        logger.info("CREATING COMPLETE GITLAB HIERARCHY")
        logger.info("="*60)
        
        # Create organization
        logger.info("\n1. Creating Organization...")
        org_result = builder._create_organization(deployment, created_by_user_id=None)
        
        if not org_result["success"]:
            logger.error(f"❌ Failed to create organization: {org_result['error']}")
            return
        
        organization = org_result["organization"]
        logger.info(f"✅ Organization created: {organization.path}")
        logger.info(f"   GitLab Group: {org_result['gitlab_group'].full_path if org_result.get('gitlab_group') else 'existing'}")
        
        # Create course family
        logger.info("\n2. Creating Course Family...")
        family_result = builder._create_course_family(
            deployment, 
            organization, 
            created_by_user_id=None
        )
        
        if not family_result["success"]:
            logger.error(f"❌ Failed to create course family: {family_result['error']}")
            return
        
        course_family = family_result["course_family"]
        logger.info(f"✅ Course family created: {course_family.path}")
        logger.info(f"   GitLab Group: {family_result['gitlab_group'].full_path if family_result.get('gitlab_group') else 'existing'}")
        
        # Create course
        logger.info("\n3. Creating Course...")
        course_result = builder._create_course(
            deployment,
            organization,
            course_family,
            created_by_user_id=None
        )
        
        if not course_result["success"]:
            logger.error(f"❌ Failed to create course: {course_result['error']}")
            return
        
        course = course_result["course"]
        logger.info(f"✅ Course created: {course.path}")
        logger.info(f"   GitLab Group: {course_result['gitlab_group'].full_path if course_result.get('gitlab_group') else 'existing'}")
        
        # Display hierarchy
        logger.info("\n" + "="*60)
        logger.info("CREATED HIERARCHY")
        logger.info("="*60)
        
        if organization.properties and organization.properties.get("gitlab"):
            org_gitlab = organization.properties["gitlab"]
            logger.info(f"\n📁 Organization: {organization.title}")
            logger.info(f"   Path: {organization.path}")
            logger.info(f"   GitLab Group ID: {org_gitlab.get('group_id')}")
            logger.info(f"   GitLab URL: {org_gitlab.get('web_url')}")
        
        if course_family.properties and course_family.properties.get("gitlab"):
            family_gitlab = course_family.properties["gitlab"]
            logger.info(f"\n📁 Course Family: {course_family.title}")
            logger.info(f"   Path: {course_family.path}")
            logger.info(f"   GitLab Group ID: {family_gitlab.get('group_id')}")
            logger.info(f"   GitLab URL: {family_gitlab.get('web_url')}")
        
        if course.properties and course.properties.get("gitlab"):
            course_gitlab = course.properties["gitlab"]
            logger.info(f"\n📁 Course: {course.title}")
            logger.info(f"   Path: {course.path}")
            logger.info(f"   GitLab Group ID: {course_gitlab.get('group_id')}")
            logger.info(f"   GitLab URL: {course_gitlab.get('web_url')}")
            
            if course_gitlab.get("students_group"):
                students = course_gitlab["students_group"]
                logger.info(f"\n   📁 Students Group:")
                logger.info(f"      Group ID: {students.get('group_id')}")
                logger.info(f"      Path: {students.get('full_path')}")
                logger.info(f"      URL: {students.get('web_url')}")
        
        # Test member management
        logger.info("\n" + "="*60)
        logger.info("TESTING MEMBER MANAGEMENT")
        logger.info("="*60)
        
        # Create demo users
        demo_student_username = "demo_student"
        demo_lecturer_username = "demo_lecturer"
        
        # Get or create demo student
        try:
            users = gl.users.list(username=demo_student_username)
            if users:
                demo_student = users[0]
                logger.info(f"\nFound existing demo student: {demo_student.username}")
            else:
                demo_student = gl.users.create({
                    'email': f'{demo_student_username}@example.com',
                    'username': demo_student_username,
                    'name': 'Demo Student',
                    'password': 'DemoPassword123!',
                    'skip_confirmation': True
                })
                logger.info(f"\nCreated demo student: {demo_student.username}")
        except Exception as e:
            logger.warning(f"Could not create demo student: {e}")
            demo_student = None
        
        # Get or create demo lecturer
        try:
            users = gl.users.list(username=demo_lecturer_username)
            if users:
                demo_lecturer = users[0]
                logger.info(f"Found existing demo lecturer: {demo_lecturer.username}")
            else:
                demo_lecturer = gl.users.create({
                    'email': f'{demo_lecturer_username}@example.com',
                    'username': demo_lecturer_username,
                    'name': 'Demo Lecturer',
                    'password': 'DemoPassword123!',
                    'skip_confirmation': True
                })
                logger.info(f"Created demo lecturer: {demo_lecturer.username}")
        except Exception as e:
            logger.warning(f"Could not create demo lecturer: {e}")
            demo_lecturer = None
        
        # Add members to course
        if demo_student:
            result = builder.add_student_to_course(course, demo_student.id)
            if result["success"]:
                logger.info(f"✅ Added {demo_student.username} as student")
            else:
                logger.error(f"❌ Failed to add student: {result['error']}")
        
        if demo_lecturer:
            result = builder.add_lecturer_to_course(course, demo_lecturer.id)
            if result["success"]:
                logger.info(f"✅ Added {demo_lecturer.username} as lecturer")
            else:
                logger.error(f"❌ Failed to add lecturer: {result['error']}")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("SETUP COMPLETE!")
        logger.info("="*60)
        logger.info("\nYou can now visit GitLab to see the created structure:")
        logger.info(f"  {gitlab_url}")
        logger.info("\nLogin as root/topsecret123 to see all groups")
        
        if demo_student:
            logger.info(f"\nStudent login: {demo_student_username} / DemoPassword123!")
        if demo_lecturer:
            logger.info(f"Lecturer login: {demo_lecturer_username} / DemoPassword123!")
        
        # Commit changes
        db.commit()
        logger.info("\n✅ All changes committed to database")
        
    except Exception as e:
        logger.error(f"Error during setup: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
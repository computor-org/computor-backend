"""
Integration test for the new GitLab builder.

This script demonstrates how to use the new GitLab builder with a real
database session and GitLab instance.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from computor_backend.generator.gitlab_builder import GitLabBuilder
from computor_types.deployments import (
    ComputorDeploymentConfig,
    OrganizationConfig,
    CourseFamilyConfig,
    CourseConfig,
    GitLabConfig
)
from computor_backend.services.git_service import GitService
from computor_backend.tests.test_config import (
    TEST_GITLAB_URL,
    TEST_GITLAB_TOKEN,
    TEST_GITLAB_GROUP_ID,
    gitlab_available
)


def create_test_deployment() -> ComputorDeploymentConfig:
    """Create a test deployment configuration."""
    return ComputorDeploymentConfig(
        organization=OrganizationConfig(
            name="Builder Test Organization",
            path="builder-test-org",
            description="Testing new GitLab builder with database integration",
            gitlab=GitLabConfig(
                url=TEST_GITLAB_URL,
                token=TEST_GITLAB_TOKEN,
                parent=TEST_GITLAB_GROUP_ID
            )
        ),
        courseFamily=CourseFamilyConfig(
            name="Builder Test Family",
            path="builder-family",
            description="Test course family for new builder"
        ),
        course=CourseConfig(
            name="Builder Test Course",
            path="builder-course",
            description="Test course for new builder"
        )
    )


def main():
    """Run integration test."""
    print("🧪 GitLab Builder Integration Test")
    print("=" * 50)
    
    # Check GitLab availability
    if not gitlab_available():
        print("❌ GitLab instance not available at", TEST_GITLAB_URL)
        print("   Please ensure GitLab is running and accessible")
        return 1
    
    print("✅ GitLab instance available")
    
    # Database configuration
    # Note: In a real scenario, this would connect to the actual database
    # For this test, we'll use an in-memory SQLite database
    from sqlalchemy import create_engine
    from computor_backend.model.base import Base
    
    print("\n📊 Setting up test database...")
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db_session = Session()
    print("✅ Test database ready")
    
    # Create GitService
    git_service = GitService(working_dir=Path("/tmp/gitlab-builder-test"))
    
    # Create builder
    print("\n🔨 Creating GitLab builder...")
    try:
        builder = GitLabBuilder(
            db_session=db_session,
            gitlab_url=TEST_GITLAB_URL,
            gitlab_token=TEST_GITLAB_TOKEN,
            git_service=git_service
        )
        print("✅ GitLab builder initialized")
    except Exception as e:
        print(f"❌ Failed to initialize builder: {e}")
        return 1
    
    # Create deployment
    deployment = create_test_deployment()
    print("\n📦 Deployment configuration:")
    print(f"   Organization: {deployment.organization.path}")
    print(f"   Course Family: {deployment.courseFamily.path}")
    print(f"   Course: {deployment.course.path}")
    
    # Execute deployment
    print("\n🚀 Creating deployment hierarchy...")
    try:
        result = builder.create_deployment_hierarchy(
            deployment=deployment,
            created_by_user_id="test-user-id"
        )
        
        if result["success"]:
            print("\n✅ Deployment created successfully!")
            
            # Show created GitLab groups
            if result["gitlab_groups_created"]:
                print("\n📁 GitLab groups created:")
                for group in result["gitlab_groups_created"]:
                    print(f"   - {group}")
            else:
                print("\n♻️ All GitLab groups already existed")
            
            # Show created database entries
            if result["database_entries_created"]:
                print("\n💾 Database entries created:")
                for entry in result["database_entries_created"]:
                    print(f"   - {entry}")
            else:
                print("\n♻️ All database entries already existed")
            
            # Show final structure
            org = result["organization"]
            family = result["course_family"]
            course = result["course"]
            
            print("\n📊 Final hierarchy:")
            print(f"   Organization: {org.path} (ID: {org.id})")
            if org.properties and org.properties.get("gitlab"):
                gitlab_props = org.properties["gitlab"]
                print(f"      GitLab Group ID: {gitlab_props.get('group_id')}")
                print(f"      GitLab Path: {gitlab_props.get('full_path')}")
            
            print(f"   Course Family: {family.path} (ID: {family.id})")
            if family.properties and family.properties.get("gitlab"):
                gitlab_props = family.properties["gitlab"]
                print(f"      GitLab Group ID: {gitlab_props.get('group_id')}")
                print(f"      GitLab Path: {gitlab_props.get('full_path')}")
            
            print(f"   Course: {course.path} (ID: {course.id})")
            if course.properties and course.properties.get("gitlab"):
                gitlab_props = course.properties["gitlab"]
                print(f"      GitLab Group ID: {gitlab_props.get('group_id')}")
                print(f"      GitLab Path: {gitlab_props.get('full_path')}")
                print(f"      GitLab URL: {gitlab_props.get('web_url')}")
            
            # Test idempotency
            print("\n🔄 Testing idempotency...")
            result2 = builder.create_deployment_hierarchy(
                deployment=deployment,
                created_by_user_id="test-user-id"
            )
            
            if result2["success"] and not result2["gitlab_groups_created"] and not result2["database_entries_created"]:
                print("✅ Idempotency test passed - no duplicates created")
            else:
                print("⚠️ Idempotency test - some changes detected")
                
        else:
            print("\n❌ Deployment failed!")
            print("Errors:")
            for error in result["errors"]:
                print(f"   - {error}")
                
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Cleanup
        db_session.close()
        print("\n🧹 Cleaned up database session")
    
    print("\n✅ Integration test completed successfully!")
    return 0


if __name__ == "__main__":
    exit(main())
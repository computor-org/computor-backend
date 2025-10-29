#!/usr/bin/env python3
"""
Initialize system data including essential roles and reference data.
This script should be run after database migrations to set up the system.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # computor_backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))  # src

# Load environment variables
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

from computor_backend.database import get_db
from computor_backend.model.role import Role, UserRole
from computor_backend.model.course import CourseRole, CourseContentKind
from computor_types.password_utils import create_password_hash
from computor_backend.model.auth import User, Account
from computor_backend.model.example import ExampleRepository
from computor_backend.auth.keycloak_admin import KeycloakAdminClient, KeycloakUser
import asyncio


def initialize_system_roles(db: Session):
    """Initialize essential system roles (now handled by Alembic migration)."""
    print("🔧 Checking system roles...")
    
    # These are now created in the Alembic migration
    # Just verify they exist
    system_roles = ['_admin', '_user_manager', '_organization_manager']
    
    for role_id in system_roles:
        existing_role = db.query(Role).filter(Role.id == role_id).first()
        if existing_role:
            print(f"   ✅ System role exists: {role_id}")
        else:
            print(f"   ⚠️  System role missing: {role_id} (check migrations)")
    
    db.commit()


def initialize_course_roles(db: Session):
    """Initialize essential course roles (now handled by Alembic migration)."""
    print("🎓 Checking course roles...")
    
    # These are now created in the Alembic migration
    # Just verify they exist
    course_roles = ['_student', '_tutor', '_lecturer', '_maintainer', '_owner']
    
    for role_id in course_roles:
        existing_role = db.query(CourseRole).filter(CourseRole.id == role_id).first()
        if existing_role:
            print(f"   ✅ Course role exists: {role_id}")
        else:
            print(f"   ⚠️  Course role missing: {role_id} (check migrations)")
    
    db.commit()


def initialize_course_content_kinds(db: Session):
    """Initialize course content kinds (now handled by Alembic migration)."""
    print("📚 Checking course content kinds...")
    
    # These are now created in the Alembic migration
    # Just verify they exist
    content_kinds = ['assignment', 'unit']
    
    for kind_id in content_kinds:
        existing_kind = db.query(CourseContentKind).filter(CourseContentKind.id == kind_id).first()
        if existing_kind:
            print(f"   ✅ Content kind exists: {kind_id}")
        else:
            print(f"   ⚠️  Content kind missing: {kind_id} (check migrations)")
    
    db.commit()

def initialize_example_repositories(db: Session):
    """Initialize default example repositories."""
    print("📚 Initializing example repositories...")
    
    # Default MinIO-based example repository
    default_repo = {
        'name': 'Default Examples',
        'description': 'Default repository for programming examples and tutorials',
        'source_type': 'minio',
        'source_url': 'examples-bucket'
    }
    
    # Check if default repository exists
    existing_repo = db.query(ExampleRepository).filter(ExampleRepository.name == default_repo['name']).first()
    if not existing_repo:
        repo = ExampleRepository(**default_repo)
        db.add(repo)
        db.commit()
        print(f"   ✅ Created default example repository: {default_repo['name']}")
    else:
        print(f"   ⚠️  Default example repository already exists: {default_repo['name']}")
    
    db.commit()


async def sync_admin_with_keycloak(admin_username: str, admin_password: str, admin_email: str = 'admin@system.local'):
    """Sync admin user with Keycloak."""
    try:
        keycloak_admin = KeycloakAdminClient()
        
        # Check if admin user exists in Keycloak
        if await keycloak_admin.user_exists(admin_username):
            print(f"   ⚠️  Admin user already exists in Keycloak: {admin_username}")
            # Get user ID to update password
            user_id = await keycloak_admin._get_user_id_by_username(admin_username)
            # Update password to ensure it matches
            await keycloak_admin.set_user_password(user_id, admin_password, temporary=False)
            print(f"   ✅ Updated admin password in Keycloak")
            return user_id
        
        # Create admin user in Keycloak
        keycloak_user = KeycloakUser(
            username=admin_username,
            email=admin_email,
            firstName='System',
            lastName='Administrator',
            enabled=True,
            emailVerified=True,
            credentials=[{
                "type": "password",
                "value": admin_password,
                "temporary": False
            }],
            attributes={
                "system_role": "admin"
            }
        )
        
        provider_user_id = await keycloak_admin.create_user(keycloak_user)
        print(f"   ✅ Created admin user in Keycloak (ID: {provider_user_id})")
        return provider_user_id
        
    except Exception as e:
        print(f"   ⚠️  Failed to sync with Keycloak: {e}")
        print("   ℹ️  Admin user will be created locally only")
        return None


def create_admin_user(db: Session):
    """Create the default admin user and sync with Keycloak."""
    print("👤 Creating admin user...")
    
    # Get credentials from environment variables
    admin_username = os.environ.get('API_ADMIN_USER', 'admin')
    admin_password = os.environ.get('API_ADMIN_PASSWORD', 'admin')
    admin_email = 'admin@system.local'
    
    # Check if admin user already exists
    existing_user = db.query(User).filter(User.username == admin_username).first()
    if existing_user:
        print(f"   ⚠️  Admin user already exists locally: {admin_username}")
        
        # Check if Keycloak account exists
        keycloak_account = db.query(Account).filter(
            Account.user_id == existing_user.id,
            Account.provider == "keycloak"
        ).first()
        
        if not keycloak_account:
            # Sync with Keycloak
            provider_user_id = asyncio.run(sync_admin_with_keycloak(admin_username, admin_password, admin_email))
            if provider_user_id:
                # Create account linking
                account = Account(
                    provider="keycloak",
                    type="oidc",
                    provider_account_id=provider_user_id,
                    user_id=existing_user.id,
                    properties={
                        "email": admin_email,
                        "username": admin_username,
                        "system_admin": True
                    }
                )
                db.add(account)
                db.commit()
                print(f"   ✅ Linked existing admin user to Keycloak")
        else:
            # Update password in Keycloak
            asyncio.run(sync_admin_with_keycloak(admin_username, admin_password, admin_email))
        return
    
    # Sync with Keycloak first
    provider_user_id = asyncio.run(sync_admin_with_keycloak(admin_username, admin_password, admin_email))
    
    # Create admin user locally with Argon2 hashed password
    admin_user = User(
        given_name='System',
        family_name='Administrator',
        email=admin_email,
        username=admin_username,
        password=create_password_hash(admin_password, validate=False),  # Skip validation for admin setup
        password_reset_required=False,  # Admin can login immediately
        user_type='user'
    )
    
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    # Create Keycloak account if sync was successful
    if provider_user_id:
        account = Account(
            provider="keycloak",
            type="oidc",
            provider_account_id=provider_user_id,
            user_id=admin_user.id,
            properties={
                "email": admin_email,
                "username": admin_username,
                "system_admin": True
            }
        )
        db.add(account)
    
    # Assign admin role
    admin_role = UserRole(
        user_id=admin_user.id,
        role_id='_admin'
    )
    
    db.add(admin_role)
    db.commit()
    
    print(f"   ✅ Created admin user (username: {admin_username}, password: ****)")


def main():
    """Initialize all system data."""
    print("🚀 System Data Initialization")
    print("=" * 50)
    
    try:
        with next(get_db()) as db:
            # Initialize in dependency order
            initialize_system_roles(db)
            initialize_course_roles(db)
            initialize_course_content_kinds(db)
            initialize_example_repositories(db)
            create_admin_user(db)
            
        print("=" * 50)
        print("✅ System initialization completed successfully!")
        print("\n🎯 You can now start the application!")
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        raise


if __name__ == "__main__":
    main()
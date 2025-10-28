#!/usr/bin/env python3
"""
Create service users and API tokens for Temporal workers and other services.

This script creates service accounts with API tokens for automated systems.
Run this after system initialization to set up workers and services.

Usage:
    python create_service_users.py [--output-env]

Options:
    --output-env    Output tokens in .env format
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import get_db
from model.auth import User
from model.service import Service, ApiToken
from utils.api_token import generate_api_token
from computor_types.password_utils import create_password_hash
import secrets


# Service definitions
SERVICE_DEFINITIONS = [
    {
        "slug": "temporal-worker-python",
        "name": "Python Testing Worker",
        "service_type": "temporal_worker",
        "username": "temporal-worker-python",
        "email": "worker-python@computor.service",
        "description": "Temporal worker for Python test execution",
        "config": {
            "worker_queue": "testing-python",
            "capabilities": ["python_testing", "code_execution"]
        },
        "token_scopes": [
            "read:courses",
            "read:course_contents",
            "read:submissions",
            "read:results",
            "write:results",
            "execute:tests"
        ]
    },
    {
        "slug": "temporal-worker-matlab",
        "name": "MATLAB Testing Worker",
        "service_type": "temporal_worker",
        "username": "temporal-worker-matlab",
        "email": "worker-matlab@computor.service",
        "description": "Temporal worker for MATLAB test execution",
        "config": {
            "worker_queue": "testing-matlab",
            "capabilities": ["matlab_testing", "code_execution"]
        },
        "token_scopes": [
            "read:courses",
            "read:course_contents",
            "read:submissions",
            "read:results",
            "write:results",
            "execute:tests"
        ]
    },
    {
        "slug": "temporal-worker-general",
        "name": "General Temporal Worker",
        "service_type": "temporal_worker",
        "username": "temporal-worker-general",
        "email": "worker-general@computor.service",
        "description": "General Temporal worker for workflow orchestration",
        "config": {
            "worker_queue": "computor-tasks",
            "capabilities": [
                "gitlab_integration",
                "repository_management",
                "student_template_generation",
                "course_deployment"
            ]
        },
        "token_scopes": [
            "read:courses",
            "read:course_contents",
            "read:organizations",
            "read:repositories",
            "write:repositories",
            "write:gitlab",
            "execute:workflows"
        ]
    }
]


def create_service_user_with_token(service_def: dict, db: Session, admin_user_id: str) -> dict:
    """
    Create a service user, service record, and API token.

    Args:
        service_def: Service definition dictionary
        db: Database session
        admin_user_id: ID of admin user creating the service

    Returns:
        dict: Created resources with token
    """
    slug = service_def["slug"]

    # Check if service user already exists
    existing_user = db.query(User).filter(User.username == service_def["username"]).first()
    if existing_user:
        print(f"  ⚠️  Service user '{service_def['username']}' already exists (ID: {existing_user.id})")

        # Check if service record exists
        existing_service = db.query(Service).filter(Service.user_id == existing_user.id).first()
        if existing_service:
            print(f"  ⚠️  Service '{slug}' already exists")
            return {
                "user_id": str(existing_user.id),
                "service_id": str(existing_service.id),
                "message": "already_exists"
            }

    # Create service user (no password - will use API token)
    user = User(
        username=service_def["username"],
        email=service_def["email"],
        given_name=service_def["name"].split()[0],  # First word as given name
        family_name=" ".join(service_def["name"].split()[1:]),  # Rest as family name
        is_service=True,
        password=None,  # Service users authenticate via API tokens
        created_by=admin_user_id,
        properties={
            "service_type": service_def["service_type"],
            "auto_created": True
        }
    )

    db.add(user)
    db.flush()  # Get user ID

    print(f"  ✅ Created service user: {user.username} (ID: {user.id})")

    # Create service record
    service = Service(
        slug=slug,
        name=service_def["name"],
        description=service_def["description"],
        service_type=service_def["service_type"],
        user_id=user.id,
        config=service_def["config"],
        enabled=True,
        created_by=admin_user_id
    )

    db.add(service)
    db.flush()

    print(f"  ✅ Created service: {service.name} (ID: {service.id})")

    # Generate API token with retry on collision
    max_retries = 5
    token_created = False

    for attempt in range(max_retries):
        try:
            full_token, token_prefix, token_hash = generate_api_token()

            api_token = ApiToken(
                name=f"{service_def['name']} - Main Token",
                description=f"Primary API token for {service_def['name']}",
                user_id=user.id,
                token_hash=token_hash,
                token_prefix=token_prefix,
                scopes=service_def["token_scopes"],
                expires_at=None,  # Never expires (for services)
                created_by=admin_user_id
            )

            db.add(api_token)
            db.flush()  # Check uniqueness constraint

            token_created = True
            print(f"  ✅ Created API token: {token_prefix}... (ID: {api_token.id})")
            break

        except IntegrityError:
            db.rollback()
            if attempt == max_retries - 1:
                raise Exception(f"Failed to generate unique token after {max_retries} attempts")
            print(f"  ⚠️  Token collision, retrying... (attempt {attempt + 1}/{max_retries})")

    db.commit()

    return {
        "user_id": str(user.id),
        "username": user.username,
        "service_id": str(service.id),
        "service_slug": service.slug,
        "token_id": str(api_token.id),
        "token": full_token,
        "token_prefix": token_prefix,
        "scopes": service_def["token_scopes"]
    }


def main():
    """Create service users and API tokens."""
    parser = argparse.ArgumentParser(description="Create service users and API tokens")
    parser.add_argument("--output-env", action="store_true", help="Output tokens in .env format")
    args = parser.parse_args()

    print("\n🤖 Service User Creation")
    print("=" * 60)

    # Get database session
    db_gen = next(get_db())
    db = db_gen

    try:
        # Get admin user (created by initialize_system_data.py)
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("❌ Error: Admin user not found. Run initialize_system.sh first.")
            return 1

        print(f"👤 Using admin user for creation: {admin_user.username} (ID: {admin_user.id})")
        print()

        created_services = []

        # Create each service
        for service_def in SERVICE_DEFINITIONS:
            print(f"🔧 Creating service: {service_def['slug']}")
            try:
                result = create_service_user_with_token(service_def, db, str(admin_user.id))
                created_services.append(result)
                print()
            except Exception as e:
                print(f"  ❌ Error creating service: {e}")
                db.rollback()
                print()
                continue

        # Output summary
        print("=" * 60)
        print("✅ Service creation complete!")
        print()

        if not created_services:
            print("No new services were created (all already exist)")
            return 0

        # Output tokens
        if args.output_env:
            print("📝 Environment variables (.env format):")
            print("-" * 60)
            for service in created_services:
                if "token" in service:
                    env_var_name = service["service_slug"].upper().replace("-", "_") + "_TOKEN"
                    print(f"{env_var_name}={service['token']}")
            print()
        else:
            print("🔑 API Tokens (STORE SECURELY - shown only once!):")
            print("-" * 60)
            for service in created_services:
                if "token" in service:
                    print(f"\n{service['service_slug']}:")
                    print(f"  Token: {service['token']}")
                    print(f"  Scopes: {', '.join(service['scopes'])}")

        print()
        print("⚠️  IMPORTANT: Save these tokens securely!")
        print("   They cannot be retrieved later.")
        print("   Add them to your .env files or secrets manager.")
        print()

        return 0

    except Exception as e:
        print(f"\n❌ Error during service creation: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

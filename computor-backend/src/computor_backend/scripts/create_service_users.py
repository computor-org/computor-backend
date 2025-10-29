#!/usr/bin/env python3
"""
Create service users and API tokens for Temporal workers and other services.

This script creates service accounts with API tokens for automated systems.
Run this after system initialization to set up workers and services.

Usage:
    python create_service_users.py [--output-env] [--predefined-tokens]

Options:
    --output-env           Output tokens in .env format
    --predefined-tokens    Use predefined tokens from environment variables
                          (Looks for TEMPORAL_WORKER_PYTHON_TOKEN, etc.)

Environment Variables (when using --predefined-tokens):
    TEMPORAL_WORKER_PYTHON_TOKEN    Pre-defined token for Python worker
    TEMPORAL_WORKER_MATLAB_TOKEN    Pre-defined token for MATLAB worker
    TEMPORAL_WORKER_GENERAL_TOKEN   Pre-defined token for General worker

Example with predefined tokens:
    export TEMPORAL_WORKER_PYTHON_TOKEN="ctp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
    python create_service_users.py --predefined-tokens --output-env
"""

import sys
import argparse
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy_utils import Ltree
from database import get_db
from model.auth import User
from model.service import Service, ApiToken, ServiceType
from utils.api_token import generate_api_token, prepare_predefined_token
from computor_types.password_utils import create_password_hash
import secrets


# Service definitions
SERVICE_DEFINITIONS = [
    {
        "slug": "temporal-worker-python",
        "name": "Python Testing Worker",
        "service_type_path": "testing.temporal",  # ServiceType path
        "language": "python",  # Language for service matching
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
        "service_type_path": "testing.temporal",  # ServiceType path
        "language": "matlab",  # Language for service matching
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
        "service_type_path": None,  # General workers don't have a specific type
        "language": None,
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


def create_service_user_with_token(
    service_def: dict,
    db: Session,
    admin_user_id: str,
    predefined_token: str = None
) -> dict:
    """
    Create a service user, service record, and API token.

    Args:
        service_def: Service definition dictionary
        db: Database session
        admin_user_id: ID of admin user creating the service
        predefined_token: Optional predefined token value (for deployment)

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
    user_properties = {"auto_created": True}
    if service_def.get("service_type_path"):
        user_properties["service_type_path"] = service_def["service_type_path"]
    if service_def.get("language"):
        user_properties["language"] = service_def["language"]

    user = User(
        username=service_def["username"],
        email=service_def["email"],
        given_name=service_def["name"].split()[0],  # First word as given name
        family_name=" ".join(service_def["name"].split()[1:]),  # Rest as family name
        is_service=True,
        password=None,  # Service users authenticate via API tokens
        created_by=admin_user_id,
        properties=user_properties
    )

    db.add(user)
    db.flush()  # Get user ID

    print(f"  ✅ Created service user: {user.username} (ID: {user.id})")

    # Create service record
    # Look up ServiceType if specified
    service_type_id = None
    if service_def.get("service_type_path"):
        service_type = db.query(ServiceType).filter(
            ServiceType.path == Ltree(service_def["service_type_path"])
        ).first()

        if service_type:
            service_type_id = service_type.id
            print(f"  ✅ Linked to ServiceType: {service_type.path}")
        else:
            print(f"  ⚠️  ServiceType '{service_def['service_type_path']}' not found - run seed_testing_temporal_service_type.py first")

    # Build properties
    properties = {}
    if service_def.get("language"):
        properties["language"] = service_def["language"]

    service = Service(
        slug=slug,
        name=service_def["name"],
        description=service_def["description"],
        service_type_id=service_type_id,
        user_id=user.id,
        config=service_def["config"],
        enabled=True,
        created_by=admin_user_id,
        properties=properties
    )

    db.add(service)
    db.flush()

    print(f"  ✅ Created service: {service.name} (ID: {service.id})")

    # Generate or use predefined API token
    if predefined_token:
        # Use predefined token
        try:
            full_token, token_prefix, token_hash = prepare_predefined_token(predefined_token)
            print(f"  📌 Using predefined token: {token_prefix}...")
        except ValueError as e:
            raise Exception(f"Invalid predefined token: {e}")

        # Check for existing token with same hash
        existing_token = db.query(ApiToken).filter(ApiToken.token_hash == token_hash).first()
        if existing_token:
            print(f"  ⚠️  Token already exists (ID: {existing_token.id})")
            db.rollback()
            return {
                "user_id": str(user.id),
                "username": user.username,
                "service_id": str(service.id),
                "service_slug": service.slug,
                "token_id": str(existing_token.id),
                "token": full_token,
                "token_prefix": token_prefix,
                "scopes": service_def["token_scopes"],
                "message": "token_already_exists"
            }

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
        db.flush()
        print(f"  ✅ Created API token with predefined value: {token_prefix}... (ID: {api_token.id})")

    else:
        # Generate random token with retry on collision
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
    parser.add_argument("--predefined-tokens", action="store_true",
                       help="Use predefined tokens from environment variables")
    args = parser.parse_args()

    print("\n🤖 Service User Creation")
    print("=" * 60)

    if args.predefined_tokens:
        print("📌 Using predefined tokens from environment variables")
        print()

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

            # Check for predefined token in environment
            predefined_token = None
            if args.predefined_tokens:
                env_var_name = service_def["slug"].upper().replace("-", "_") + "_TOKEN"
                predefined_token = os.environ.get(env_var_name)
                if predefined_token:
                    print(f"  📌 Found predefined token in ${env_var_name}")
                else:
                    print(f"  ⚠️  No predefined token found in ${env_var_name}, generating random token")

            try:
                result = create_service_user_with_token(
                    service_def,
                    db,
                    str(admin_user.id),
                    predefined_token=predefined_token
                )
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

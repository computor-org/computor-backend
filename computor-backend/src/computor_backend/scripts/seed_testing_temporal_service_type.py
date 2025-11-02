#!/usr/bin/env python3
"""
Create the testing.temporal ServiceType for temporal testing workers.

This ServiceType is used by all temporal testing workers (Python, MATLAB, etc.).
Individual services are differentiated by their properties (e.g., language).
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy_utils import Ltree
from database import get_db
from model.auth import User
from model.service import ServiceType


def create_testing_temporal_service_type(db: Session, admin_user_id: str) -> ServiceType:
    """
    Create or get the testing.temporal ServiceType.

    Args:
        db: Database session
        admin_user_id: ID of admin user creating the service type

    Returns:
        ServiceType: The created or existing service type
    """
    path = Ltree("testing.temporal")

    # Check if it already exists
    existing = db.query(ServiceType).filter(ServiceType.path == path).first()
    if existing:
        print(f"  ℹ️  ServiceType 'testing.temporal' already exists (ID: {existing.id})")
        return existing

    # Create the service type
    service_type = ServiceType(
        path=path,
        name="Temporal Testing Worker",
        description="Service type for temporal workers that execute student code tests asynchronously",
        category="testing",  # Required field
        schema={
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "description": "Programming language supported by this worker (e.g., python, matlab)",
                    "enum": ["python", "matlab", "java", "cpp", "javascript"]
                },
                "task_queue": {
                    "type": "string",
                    "description": "Temporal task queue for this service type"
                }
            },
            "required": ["language"]
        },
        properties={
            "task_queue": "computor-tasks",  # Default queue
            "async": True
        },
        created_by=admin_user_id
    )

    db.add(service_type)
    db.commit()
    db.refresh(service_type)

    print(f"  ✅ Created ServiceType: testing.temporal (ID: {service_type.id})")
    return service_type


def main():
    """Create the testing.temporal ServiceType."""
    print("\n🏗️  ServiceType Initialization")
    print("=" * 60)

    # Get database session
    db_gen = next(get_db())
    db = db_gen

    try:
        # Get admin user
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("❌ Error: Admin user not found. Run initialize_system.sh first.")
            return 1

        print(f"👤 Using admin user: {admin_user.username} (ID: {admin_user.id})")
        print()

        # Create the service type
        print("🔧 Creating ServiceType: testing.temporal")
        service_type = create_testing_temporal_service_type(db, str(admin_user.id))

        print()
        print("=" * 60)
        print("✅ ServiceType creation complete!")
        print()
        print(f"ServiceType Details:")
        print(f"  Path: {service_type.path}")
        print(f"  Name: {service_type.name}")
        print(f"  ID: {service_type.id}")
        print()

        return 0

    except Exception as e:
        print(f"\n❌ Error during ServiceType creation: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

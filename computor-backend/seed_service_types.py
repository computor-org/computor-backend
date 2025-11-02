#!/usr/bin/env python3
"""
Seed initial service types into the database.

This script creates the foundational service type definitions:
- worker.temporal: Temporal workflow worker
- testing.python: Python code testing
- testing.matlab: MATLAB code testing

These correspond to the existing execution_backend types in the system.

Usage:
    python seed_service_types.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy.orm import Session
from computor_backend.database import SessionLocal
from computor_backend.model.service import ServiceType
from computor_backend.custom_types import Ltree


def seed_service_types(db: Session):
    """
    Seed initial service types.

    Creates service types for:
    1. Temporal worker (existing service type)
    2. Python testing (migrated from execution_backend)
    3. MATLAB testing (migrated from execution_backend)
    """

    service_types = [
        {
            'path': 'worker.temporal',
            'name': 'Temporal Worker',
            'description': 'Temporal workflow task queue worker for asynchronous job processing',
            'category': 'worker',
            'plugin_module': 'computor_backend.tasks.temporal_worker',
            'schema': {
                'type': 'object',
                'properties': {
                    'task_queues': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Task queues this worker listens to'
                    },
                    'max_concurrent_activities': {
                        'type': 'integer',
                        'minimum': 1,
                        'default': 10,
                        'description': 'Maximum concurrent activities'
                    },
                    'max_concurrent_workflows': {
                        'type': 'integer',
                        'minimum': 1,
                        'default': 10,
                        'description': 'Maximum concurrent workflows'
                    }
                },
                'required': ['task_queues']
            },
            'icon': 'work',
            'color': '#4CAF50',
            'enabled': True
        },
        {
            'path': 'testing.python',
            'name': 'Python Testing System',
            'description': 'Python code execution and testing via Temporal workflows',
            'category': 'testing',
            'plugin_module': 'computor_backend.tasks.temporal_student_testing',
            'schema': {
                'type': 'object',
                'properties': {
                    'task_queue': {
                        'type': 'string',
                        'description': 'Temporal task queue name'
                    },
                    'max_retries': {
                        'type': 'integer',
                        'minimum': 0,
                        'default': 5,
                        'description': 'Maximum retry attempts'
                    },
                    'timeout_minutes': {
                        'type': 'integer',
                        'minimum': 1,
                        'default': 10,
                        'description': 'Execution timeout in minutes'
                    },
                    'python_version': {
                        'type': 'string',
                        'enum': ['3.8', '3.9', '3.10', '3.11', '3.12'],
                        'default': '3.10',
                        'description': 'Python version to use'
                    }
                },
                'required': ['task_queue']
            },
            'icon': 'code',
            'color': '#3776AB',  # Python blue
            'enabled': True
        },
        {
            'path': 'testing.matlab',
            'name': 'MATLAB Testing System',
            'description': 'MATLAB code execution and testing via Temporal workflows',
            'category': 'testing',
            'plugin_module': 'computor_backend.tasks.temporal_student_testing',
            'schema': {
                'type': 'object',
                'properties': {
                    'task_queue': {
                        'type': 'string',
                        'description': 'Temporal task queue name'
                    },
                    'max_retries': {
                        'type': 'integer',
                        'minimum': 0,
                        'default': 3,
                        'description': 'Maximum retry attempts'
                    },
                    'timeout_minutes': {
                        'type': 'integer',
                        'minimum': 1,
                        'default': 15,
                        'description': 'Execution timeout in minutes'
                    }
                },
                'required': ['task_queue']
            },
            'icon': 'functions',
            'color': '#FF9800',  # MATLAB orange
            'enabled': True
        }
    ]

    created_count = 0
    skipped_count = 0

    for st_data in service_types:
        # Check if already exists
        existing = db.query(ServiceType).filter(
            ServiceType.path == Ltree(st_data['path'])
        ).first()

        if existing:
            print(f"⏭️  Skipping existing: {st_data['path']} (ID: {existing.id})")
            skipped_count += 1
            continue

        # Create new service type
        service_type = ServiceType(
            path=Ltree(st_data['path']),
            name=st_data['name'],
            description=st_data['description'],
            category=st_data['category'],
            plugin_module=st_data['plugin_module'],
            schema=st_data['schema'],
            icon=st_data['icon'],
            color=st_data['color'],
            enabled=st_data['enabled']
        )

        db.add(service_type)
        print(f"✅ Created: {st_data['path']} (name: {st_data['name']})")
        created_count += 1

    db.commit()

    print(f"\n{'='*60}")
    print(f"Service Type Seeding Complete")
    print(f"{'='*60}")
    print(f"✅ Created:  {created_count}")
    print(f"⏭️  Skipped:  {skipped_count}")
    print(f"📊 Total:    {created_count + skipped_count}")
    print(f"{'='*60}\n")

    # Show all service types
    all_types = db.query(ServiceType).order_by(ServiceType.path).all()
    print(f"All Service Types in Database ({len(all_types)}):")
    print(f"{'='*60}")
    for st in all_types:
        status = "🟢" if st.enabled else "🔴"
        # Convert Ltree to string for formatting
        path_str = str(st.path)
        print(f"{status} {path_str:<25} | {st.name:<30} | {st.category}")
    print(f"{'='*60}")


def main():
    """Main entry point."""
    print(f"\n{'='*60}")
    print("Service Type Seeding Script")
    print(f"{'='*60}\n")

    db = SessionLocal()
    try:
        seed_service_types(db)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

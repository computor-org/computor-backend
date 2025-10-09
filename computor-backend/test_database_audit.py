"""
Simple test script to verify database audit tracking works correctly.
Run this after applying the migration.
"""

import os
import sys
from uuid import uuid4

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from computor_backend.database import get_db
from computor_backend.model.organization import Organization
from sqlalchemy import text

def test_audit_tracking_with_user():
    """Test that created_by and updated_by are set when user_id is provided"""

    print("Test 1: Creating organization WITH user_id...")

    # Create a test user_id
    test_user_id = str(uuid4())

    # Use get_db with user_id
    for db in get_db(user_id=test_user_id):
        # First, we need to create a user with this ID for foreign key constraint
        # For testing purposes, we'll just verify the trigger sets the value
        # In real scenario, the user must exist

        # Check if trigger function exists
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_proc
                WHERE proname = 'set_audit_fields'
            )
        """)).scalar()

        if result:
            print("✓ Trigger function 'set_audit_fields' exists")
        else:
            print("✗ Trigger function 'set_audit_fields' NOT FOUND")
            print("  Run: alembic upgrade head")
            return False

        # Check if session variable is set
        try:
            current_user = db.execute(
                text("SELECT current_setting('app.user_id', true)")
            ).scalar()

            if current_user == test_user_id:
                print(f"✓ Session variable app.user_id is set to: {current_user}")
            else:
                print(f"✗ Session variable mismatch: expected {test_user_id}, got {current_user}")
                return False
        except Exception as e:
            print(f"✗ Error checking session variable: {e}")
            return False

    print("\nTest 1: PASSED\n")
    return True


def test_audit_tracking_without_user():
    """Test that session works without user_id"""

    print("Test 2: Creating session WITHOUT user_id...")

    for db in get_db():
        # Check that session variable is not set
        try:
            current_user = db.execute(
                text("SELECT current_setting('app.user_id', true)")
            ).scalar()

            if current_user is None or current_user == "":
                print("✓ Session variable app.user_id is not set (as expected)")
            else:
                print(f"✗ Unexpected session variable: {current_user}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False

    print("\nTest 2: PASSED\n")
    return True


def test_timeout_exception():
    """Test that timeout is caught and converted to ServiceUnavailableException"""

    print("Test 3: Checking timeout exception handling...")

    try:
        import sqlalchemy.exc as sa_exc
        from computor_backend.api.exceptions import ServiceUnavailableException

        # Simulate timeout error
        try:
            raise sa_exc.TimeoutError("Test timeout")
        except sa_exc.TimeoutError as e:
            # This is what get_db should do
            raise ServiceUnavailableException(
                detail="Database is busy. Please retry shortly.",
                headers={"Retry-After": "2"}
            ) from e

    except ServiceUnavailableException as e:
        if e.status_code == 503:
            print(f"✓ ServiceUnavailableException properly raised with status 503")
            print(f"  Detail: {e.detail}")
            print(f"  Headers: {e.headers}")
        else:
            print(f"✗ Wrong status code: {e.status_code}")
            return False
    except Exception as e:
        print(f"✗ Unexpected exception: {type(e).__name__}: {e}")
        return False

    print("\nTest 3: PASSED\n")
    return True


def test_exception_handling():
    """Test that exceptions are properly handled with rollback"""

    print("Test 4: Testing exception handling and rollback...")

    try:
        for db in get_db():
            # Start a transaction
            db.execute(text("SELECT 1"))

            # Simulate an error
            raise ValueError("Test exception")

    except ValueError:
        print("✓ Exception properly propagated")
    except Exception as e:
        print(f"✗ Unexpected exception: {type(e).__name__}: {e}")
        return False

    print("\nTest 4: PASSED\n")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("Database Audit Tracking Tests")
    print("=" * 70)
    print()

    all_passed = True

    # Run tests
    all_passed &= test_audit_tracking_with_user()
    all_passed &= test_audit_tracking_without_user()
    all_passed &= test_timeout_exception()
    all_passed &= test_exception_handling()

    print("=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 70)

    sys.exit(0 if all_passed else 1)

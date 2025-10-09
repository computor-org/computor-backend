"""
Static code analysis test to verify the database audit implementation.
Does not require database connection.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def test_imports():
    """Test that all necessary imports are available"""
    print("Test 1: Checking imports...")

    try:
        from computor_backend.database import get_db, _get_db
        from computor_backend.api.exceptions import ServiceUnavailableException
        import sqlalchemy.exc as sa_exc

        print("✓ All imports successful")
        print(f"  - get_db: {get_db}")
        print(f"  - _get_db: {_get_db}")
        print(f"  - ServiceUnavailableException: {ServiceUnavailableException}")
        print(f"  - sa_exc.TimeoutError: {sa_exc.TimeoutError}")
        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_service_unavailable_exception():
    """Test ServiceUnavailableException structure"""
    print("\nTest 2: Checking ServiceUnavailableException...")

    try:
        from computor_backend.api.exceptions import ServiceUnavailableException

        # Test instantiation
        exc = ServiceUnavailableException(
            detail="Test message",
            headers={"Retry-After": "2"}
        )

        # Check attributes
        assert exc.status_code == 503, f"Expected 503, got {exc.status_code}"
        assert exc.detail == "Test message", f"Unexpected detail: {exc.detail}"
        assert exc.headers == {"Retry-After": "2"}, f"Unexpected headers: {exc.headers}"

        print("✓ ServiceUnavailableException structure is correct")
        print(f"  - status_code: {exc.status_code}")
        print(f"  - detail: {exc.detail}")
        print(f"  - headers: {exc.headers}")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_get_db_signature():
    """Test that get_db has the correct signature"""
    print("\nTest 3: Checking get_db signature...")

    try:
        from computor_backend.database import get_db
        import inspect

        sig = inspect.signature(get_db)
        params = sig.parameters

        # Check user_id parameter exists
        assert 'user_id' in params, "Missing user_id parameter"

        # Check it's optional (has default)
        user_id_param = params['user_id']
        assert user_id_param.default is None, f"user_id default should be None, got {user_id_param.default}"

        # Check annotation
        annotation = user_id_param.annotation
        print(f"✓ get_db signature is correct")
        print(f"  - user_id parameter: {user_id_param}")
        print(f"  - annotation: {annotation}")
        print(f"  - default: {user_id_param.default}")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_exception_handling_in_get_db():
    """Test that get_db properly catches TimeoutError"""
    print("\nTest 4: Checking exception handling in get_db source...")

    try:
        from computor_backend.database import get_db
        import inspect

        source = inspect.getsource(get_db)

        # Check for timeout handling
        assert 'sa_exc.TimeoutError' in source, "Missing TimeoutError handling"
        assert 'ServiceUnavailableException' in source, "Missing ServiceUnavailableException"
        assert 'Retry-After' in source, "Missing Retry-After header"

        print("✓ Exception handling structure is correct")
        print("  - Catches sa_exc.TimeoutError")
        print("  - Raises ServiceUnavailableException")
        print("  - Includes Retry-After header")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_internal_get_db_structure():
    """Test _get_db internal function structure"""
    print("\nTest 5: Checking _get_db internal function...")

    try:
        from computor_backend.database import _get_db
        import inspect

        source = inspect.getsource(_get_db)

        # Check key components
        assert 'SET LOCAL app.user_id' in source, "Missing SET LOCAL statement"
        assert 'db.commit()' in source, "Missing commit"
        assert 'db.rollback()' in source, "Missing rollback"
        assert 'db.close()' in source, "Missing close"
        assert 'db.in_transaction()' in source, "Missing transaction check"

        print("✓ _get_db structure is correct")
        print("  - Sets app.user_id with SET LOCAL")
        print("  - Commits on success")
        print("  - Rolls back on exception")
        print("  - Always closes session")
        print("  - Checks transaction state")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_migration_exists():
    """Test that the audit trigger migration exists"""
    print("\nTest 6: Checking migration file...")

    try:
        migration_dir = os.path.join(
            os.path.dirname(__file__),
            'src/computor_backend/alembic/versions'
        )

        # Find the audit trigger migration
        migration_file = None
        for filename in os.listdir(migration_dir):
            if 'audit_trigger' in filename.lower():
                migration_file = os.path.join(migration_dir, filename)
                break

        if migration_file:
            print(f"✓ Migration file found: {os.path.basename(migration_file)}")

            # Check migration content
            with open(migration_file, 'r') as f:
                content = f.read()

            assert 'set_audit_fields' in content, "Missing set_audit_fields function"
            assert 'CREATE TRIGGER' in content, "Missing CREATE TRIGGER"
            assert 'app.user_id' in content, "Missing app.user_id reference"
            assert 'created_by' in content, "Missing created_by field"
            assert 'updated_by' in content, "Missing updated_by field"

            print("  - Contains set_audit_fields function")
            print("  - Creates triggers")
            print("  - References app.user_id")
            print("  - Handles created_by and updated_by")
            return True
        else:
            print("✗ Migration file not found")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("Database Audit Implementation - Static Code Analysis")
    print("=" * 70)
    print()

    all_passed = True

    # Run tests
    all_passed &= test_imports()
    all_passed &= test_service_unavailable_exception()
    all_passed &= test_get_db_signature()
    all_passed &= test_exception_handling_in_get_db()
    all_passed &= test_internal_get_db_structure()
    all_passed &= test_migration_exists()

    print()
    print("=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED - Implementation looks correct!")
        print()
        print("Next steps:")
        print("1. Apply migration: alembic upgrade head")
        print("2. Use get_db(user_id) in your endpoints")
        print("3. created_by/updated_by will be automatically tracked")
    else:
        print("✗ SOME TESTS FAILED - Check implementation")
    print("=" * 70)

    sys.exit(0 if all_passed else 1)

#!/usr/bin/env python3
"""
Verification script to ensure audit tracking setup is complete.
"""

import os
import re
from pathlib import Path

def check_database_py():
    """Check that database.py has the necessary functions."""
    db_file = Path("src/computor_backend/database.py")

    if not db_file.exists():
        return False, "database.py not found"

    with open(db_file, 'r') as f:
        content = f.read()

    checks = {
        'get_db function': 'def get_db(' in content,
        'get_db_with_user function': 'def get_db_with_user(' in content,
        'SET LOCAL app.user_id': 'SET LOCAL app.user_id' in content,
    }

    failed = [name for name, passed in checks.items() if not passed]

    if failed:
        return False, f"Missing: {', '.join(failed)}"

    return True, "All functions present"


def check_api_imports():
    """Check that API files import get_db_with_user."""
    api_dir = Path("src/computor_backend/api")

    if not api_dir.exists():
        return False, "API directory not found"

    py_files = [f for f in api_dir.glob("*.py") if f.name not in ['__init__.py', '__pycache__']]

    files_with_getdb = []
    files_with_both = []

    for filepath in py_files:
        with open(filepath, 'r') as f:
            content = f.read()

        has_get_db = 'from' in content and 'get_db' in content
        has_both = has_get_db and 'get_db_with_user' in content

        if has_get_db:
            files_with_getdb.append(filepath.name)
            if has_both:
                files_with_both.append(filepath.name)

    if files_with_getdb and len(files_with_both) != len(files_with_getdb):
        missing = set(files_with_getdb) - set(files_with_both)
        return False, f"{len(missing)} files missing get_db_with_user import: {', '.join(list(missing)[:3])}"

    return True, f"{len(files_with_both)} files have proper imports"


def check_api_usage():
    """Check for endpoints with permissions but still using get_db."""
    api_dir = Path("src/computor_backend/api")

    if not api_dir.exists():
        return False, "API directory not found"

    py_files = [f for f in api_dir.glob("*.py") if f.name not in ['__init__.py']]

    problematic_files = []

    for filepath in py_files:
        with open(filepath, 'r') as f:
            lines = f.readlines()

        # Look for functions with both permissions and get_db
        for i, line in enumerate(lines):
            if ('async def' in line or 'def ' in line) and '(' in line:
                # Collect function signature
                func_lines = [line]
                j = i + 1
                paren_count = line.count('(') - line.count(')')

                while j < len(lines) and paren_count > 0:
                    func_lines.append(lines[j])
                    paren_count += lines[j].count('(') - lines[j].count(')')
                    j += 1

                func_signature = ''.join(func_lines)

                # Check for problem pattern
                has_permissions = 'get_current_principal' in func_signature
                has_old_get_db = 'Depends(get_db)' in func_signature and 'get_db_with_user' not in func_signature

                if has_permissions and has_old_get_db:
                    problematic_files.append((filepath.name, i + 1))

    if problematic_files:
        examples = [f"{f}:{line}" for f, line in problematic_files[:3]]
        return False, f"{len(problematic_files)} endpoints still use get_db with permissions: {', '.join(examples)}"

    return True, "All endpoints with permissions use get_db_with_user"


def check_migration_exists():
    """Check that the audit trigger migration exists."""
    migrations_dir = Path("src/computor_backend/alembic/versions")

    if not migrations_dir.exists():
        return False, "Migrations directory not found"

    migration_files = list(migrations_dir.glob("*audit_trigger*.py"))

    if not migration_files:
        return False, "Audit trigger migration not found"

    # Check migration content
    with open(migration_files[0], 'r') as f:
        content = f.read()

    checks = {
        'set_audit_fields function': 'set_audit_fields' in content,
        'CREATE TRIGGER': 'CREATE TRIGGER' in content,
        'app.user_id': 'app.user_id' in content,
    }

    failed = [name for name, passed in checks.items() if not passed]

    if failed:
        return False, f"Migration incomplete: {', '.join(failed)}"

    return True, f"Migration exists: {migration_files[0].name}"


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("Audit Tracking Setup Verification")
    print("=" * 70)
    print()

    checks = [
        ("Database functions", check_database_py),
        ("API imports", check_api_imports),
        ("API usage", check_api_usage),
        ("Migration exists", check_migration_exists),
    ]

    all_passed = True

    for name, check_func in checks:
        print(f"Checking {name}...", end=" ")

        try:
            passed, message = check_func()

            if passed:
                print(f"✓ PASS")
                print(f"  {message}")
            else:
                print(f"✗ FAIL")
                print(f"  {message}")
                all_passed = False

        except Exception as e:
            print(f"✗ ERROR")
            print(f"  {e}")
            all_passed = False

        print()

    print("=" * 70)
    if all_passed:
        print("✓ ALL CHECKS PASSED!")
        print()
        print("Your audit tracking setup is complete. Next steps:")
        print("1. Apply migration: cd src/computor_backend && alembic upgrade head")
        print("2. Test endpoints and verify created_by/updated_by are populated")
        print("3. Commit changes")
    else:
        print("✗ SOME CHECKS FAILED")
        print()
        print("Please review the failures above and fix them.")

    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())

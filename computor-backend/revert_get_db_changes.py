#!/usr/bin/env python3
"""
Revert all Depends(get_db_with_user) back to Depends(get_db) in API files.
"""

import os
from pathlib import Path

API_DIR = Path("src/computor_backend/api")


def revert_file(filepath: Path) -> int:
    """Revert get_db_with_user to get_db in a file."""
    with open(filepath, 'r') as f:
        content = f.read()

    original = content

    # Replace Depends(get_db_with_user) with Depends(get_db)
    content = content.replace('Depends(get_db_with_user)', 'Depends(get_db)')

    # Remove get_db_with_user from imports if it exists
    content = content.replace('from computor_backend.database import get_db, get_db_with_user',
                              'from computor_backend.database import get_db')
    content = content.replace('from ..database import get_db, get_db_with_user',
                              'from ..database import get_db')

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        return 1
    return 0


def main():
    """Main function."""
    print("=" * 70)
    print("Reverting get_db_with_user to get_db")
    print("=" * 70)
    print()

    if not API_DIR.exists():
        print(f"Error: API directory not found: {API_DIR}")
        return 1

    py_files = list(API_DIR.glob("*.py"))
    py_files = [f for f in py_files if f.name not in ['__init__.py']]

    total_changed = 0
    files_changed = []

    for filepath in sorted(py_files):
        print(f"Processing {filepath.name}...", end=" ")

        try:
            changed = revert_file(filepath)

            if changed:
                print(f"✓ Reverted")
                files_changed.append(filepath.name)
                total_changed += 1
            else:
                print("○ No changes")

        except Exception as e:
            print(f"✗ ERROR: {e}")

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Files processed: {len(py_files)}")
    print(f"Files changed: {total_changed}")

    if files_changed:
        print()
        print("Changed files:")
        for filename in files_changed:
            print(f"  - {filename}")

    print()
    print("=" * 70)
    print("All API files now use Depends(get_db)")
    print("Audit tracking is handled in business_logic/crud.py")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())

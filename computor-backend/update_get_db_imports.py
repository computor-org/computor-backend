#!/usr/bin/env python3
"""
Script to update get_db imports and usages in API files to include get_db_with_user.
This enables automatic audit tracking for created_by/updated_by fields.
"""

import os
import re
from pathlib import Path

# API directory
API_DIR = Path("src/computor_backend/api")

def update_file(filepath: Path) -> tuple[bool, str]:
    """
    Update a single API file to use get_db_with_user where appropriate.

    Returns:
        (changed, message) tuple
    """
    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content
    changes = []

    # Step 1: Update import statement to include get_db_with_user
    import_patterns = [
        (r'from computor_backend\.database import get_db\n',
         'from computor_backend.database import get_db, get_db_with_user\n'),
        (r'from \.\.database import get_db\n',
         'from ..database import get_db, get_db_with_user\n'),
    ]

    for old_import, new_import in import_patterns:
        if re.search(old_import, content) and 'get_db_with_user' not in content:
            content = re.sub(old_import, new_import, content)
            changes.append("Updated import to include get_db_with_user")
            break

    # Step 2: Find endpoints that have both permissions and get_db
    # Pattern: Look for functions with both get_current_principal and get_db

    # Find all function definitions
    function_pattern = r'(async def|def)\s+(\w+)\s*\([^)]*get_current_principal[^)]*\):'
    functions = list(re.finditer(function_pattern, content, re.MULTILINE | re.DOTALL))

    replacements_made = 0
    for match in functions:
        # Get the function definition
        start_pos = match.start()
        end_pos = content.find(':', start_pos) + 1
        func_def = content[start_pos:end_pos]

        # Check if this function has both permissions and db parameters
        has_permissions = 'get_current_principal' in func_def
        has_db = 'Depends(get_db)' in func_def

        if has_permissions and has_db:
            # Replace Depends(get_db) with Depends(get_db_with_user)
            # Only within this function definition
            new_func_def = func_def.replace('Depends(get_db)', 'Depends(get_db_with_user)')

            if new_func_def != func_def:
                content = content[:start_pos] + new_func_def + content[end_pos:]
                replacements_made += 1

    if replacements_made > 0:
        changes.append(f"Updated {replacements_made} endpoint(s) to use get_db_with_user")

    # Only write if changes were made
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True, "; ".join(changes)

    return False, "No changes needed"


def main():
    """Main function to update all API files."""
    print("=" * 70)
    print("Updating API files to use get_db_with_user for audit tracking")
    print("=" * 70)
    print()

    if not API_DIR.exists():
        print(f"Error: API directory not found: {API_DIR}")
        return 1

    # Find all Python files in API directory
    py_files = list(API_DIR.glob("*.py"))
    py_files = [f for f in py_files if f.name not in ['__init__.py', '__pycache__']]

    changed_files = []
    unchanged_files = []

    for filepath in sorted(py_files):
        print(f"Processing {filepath.name}...", end=" ")

        try:
            changed, message = update_file(filepath)

            if changed:
                print(f"✓ UPDATED")
                print(f"  {message}")
                changed_files.append(filepath.name)
            else:
                print("○ No changes")
                unchanged_files.append(filepath.name)

        except Exception as e:
            print(f"✗ ERROR: {e}")

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Files processed: {len(py_files)}")
    print(f"Files updated: {len(changed_files)}")
    print(f"Files unchanged: {len(unchanged_files)}")

    if changed_files:
        print()
        print("Updated files:")
        for filename in changed_files:
            print(f"  - {filename}")

    print()
    print("=" * 70)
    print("Next steps:")
    print("1. Review the changes with: git diff")
    print("2. Test the endpoints to ensure they work correctly")
    print("3. Commit the changes")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())

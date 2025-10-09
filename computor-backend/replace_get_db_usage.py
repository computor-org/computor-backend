#!/usr/bin/env python3
"""
Script to replace Depends(get_db) with Depends(get_db_with_user) in endpoints
that have permissions parameter.
"""

import os
import re
from pathlib import Path

API_DIR = Path("src/computor_backend/api")


def process_file(filepath: Path) -> int:
    """Process a single file and return number of replacements made."""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    changes = 0
    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if this is a function definition
        if ('async def' in line or 'def ' in line) and '(' in line:
            # Collect the entire function signature (may span multiple lines)
            func_start = i
            func_lines = [line]
            paren_count = line.count('(') - line.count(')')

            j = i + 1
            while j < len(lines) and paren_count > 0:
                func_lines.append(lines[j])
                paren_count += lines[j].count('(') - lines[j].count(')')
                j += 1

            func_signature = ''.join(func_lines)

            # Check if function has both permissions AND Depends(get_db)
            has_permissions = 'get_current_principal' in func_signature
            has_get_db = 'Depends(get_db)' in func_signature and 'get_db_with_user' not in func_signature

            if has_permissions and has_get_db:
                # Replace Depends(get_db) with Depends(get_db_with_user)
                func_signature_new = func_signature.replace('Depends(get_db)', 'Depends(get_db_with_user)')

                # Update the lines
                new_func_lines = func_signature_new.split('\n')
                for k, new_line in enumerate(new_func_lines):
                    if func_start + k < len(lines):
                        if k < len(new_func_lines) - 1:
                            lines[func_start + k] = new_line + '\n'
                        else:
                            lines[func_start + k] = new_line

                changes += func_signature.count('Depends(get_db)')
                i = j
                continue

        i += 1

    if changes > 0:
        with open(filepath, 'w') as f:
            f.writelines(lines)

    return changes


def main():
    """Main function."""
    print("=" * 70)
    print("Replacing Depends(get_db) with Depends(get_db_with_user)")
    print("=" * 70)
    print()

    if not API_DIR.exists():
        print(f"Error: API directory not found: {API_DIR}")
        return 1

    py_files = list(API_DIR.glob("*.py"))
    py_files = [f for f in py_files if f.name not in ['__init__.py']]

    total_changes = 0
    files_changed = []

    for filepath in sorted(py_files):
        print(f"Processing {filepath.name}...", end=" ")

        try:
            changes = process_file(filepath)

            if changes > 0:
                print(f"✓ {changes} replacement(s)")
                files_changed.append((filepath.name, changes))
                total_changes += changes
            else:
                print("○ No changes")

        except Exception as e:
            print(f"✗ ERROR: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Files processed: {len(py_files)}")
    print(f"Files changed: {len(files_changed)}")
    print(f"Total replacements: {total_changes}")

    if files_changed:
        print()
        print("Changed files:")
        for filename, count in files_changed:
            print(f"  - {filename}: {count} replacement(s)")

    print()
    print("=" * 70)
    return 0


if __name__ == "__main__":
    exit(main())

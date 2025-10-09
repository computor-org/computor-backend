#!/usr/bin/env python3
"""
Fix malformed docstrings where opening triple-quote is missing.
This was caused by the revert_get_db_changes.py script.
"""
import re
from pathlib import Path

API_DIR = Path("src/computor_backend/api")

def fix_docstrings(filepath: Path) -> bool:
    """Fix missing opening triple-quotes in docstrings."""
    with open(filepath, 'r') as f:
        content = f.read()

    original = content

    # Pattern: function definition followed by lines without opening """
    # Match cases like:
    # ):
    #     Some text here
    #
    #     More text
    #     """

    # Replace pattern where docstring content appears after ): without opening """
    pattern = r'(\):\n)(    [A-Z].*?\n(?:.*?\n)*?    """)'

    def replacement(match):
        indent = match.group(1)  # ):
        content_and_end = match.group(2)
        # Add opening """ with proper indentation
        return indent + '    """\n' + content_and_end

    content = re.sub(pattern, replacement, content)

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    """Main function."""
    print("=" * 70)
    print("Fixing malformed docstrings in API files")
    print("=" * 70)
    print()

    if not API_DIR.exists():
        print(f"Error: API directory not found: {API_DIR}")
        return 1

    py_files = list(API_DIR.glob("*.py"))
    py_files = [f for f in py_files if f.name not in ['__init__.py']]

    total_fixed = 0
    files_fixed = []

    for filepath in sorted(py_files):
        print(f"Processing {filepath.name}...", end=" ")

        try:
            if fix_docstrings(filepath):
                print(f"✓ Fixed")
                files_fixed.append(filepath.name)
                total_fixed += 1
            else:
                print("○ No changes")
        except Exception as e:
            print(f"✗ ERROR: {e}")

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Files processed: {len(py_files)}")
    print(f"Files fixed: {total_fixed}")

    if files_fixed:
        print()
        print("Fixed files:")
        for filename in files_fixed:
            print(f"  - {filename}")

    print()
    print("=" * 70)

    return 0

if __name__ == "__main__":
    exit(main())

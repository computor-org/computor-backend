#!/usr/bin/env python3
"""
Fix remaining import issues in computor-types package.

This script removes imports that don't belong in the types package:
- computor_types.model (SQLAlchemy models)
- computor_types.api (API dependencies)
- computor_types.utils (backend utilities)
- computor_types.redis_cache (Redis implementation)
- computor_types.repositories (Repository pattern - backend only)
- sqlalchemy imports (except in TYPE_CHECKING blocks)
"""

import re
from pathlib import Path


def fix_imports(file_path: Path) -> bool:
    """Fix imports in a single file."""
    content = file_path.read_text()
    original_content = content

    # Remove model imports
    content = re.sub(
        r'^from computor_types\.model import.*$',
        '',
        content,
        flags=re.MULTILINE
    )

    # Remove API imports
    content = re.sub(
        r'^from computor_types\.api import.*$',
        '',
        content,
        flags=re.MULTILINE
    )

    # Remove utils imports
    content = re.sub(
        r'^from computor_types\.utils import.*$',
        '',
        content,
        flags=re.MULTILINE
    )

    # Remove redis_cache imports
    content = re.sub(
        r'^from computor_types\.redis_cache import.*$',
        '',
        content,
        flags=re.MULTILINE
    )

    # Remove repository imports
    content = re.sub(
        r'^from computor_types\.repositories\.\w+ import.*$',
        '',
        content,
        flags=re.MULTILINE
    )

    # Remove SQLAlchemy imports (except in TYPE_CHECKING blocks)
    # We need to be careful here - keep TYPE_CHECKING blocks
    lines = content.split('\n')
    new_lines = []
    in_type_checking = False
    skip_next_blank = False

    for i, line in enumerate(lines):
        if 'if TYPE_CHECKING:' in line:
            in_type_checking = True
            new_lines.append(line)
            continue

        # Exit TYPE_CHECKING block when indentation returns to 0
        if in_type_checking and line and not line.startswith(' ') and not line.startswith('\t'):
            in_type_checking = False

        # Skip SQLAlchemy imports outside TYPE_CHECKING
        if not in_type_checking:
            if re.match(r'^from sqlalchemy(\.\w+)* import', line):
                skip_next_blank = True
                continue

        # Skip extra blank lines after removed imports
        if skip_next_blank and line.strip() == '':
            skip_next_blank = False
            continue

        skip_next_blank = False
        new_lines.append(line)

    content = '\n'.join(new_lines)

    # Clean up multiple consecutive blank lines
    content = re.sub(r'\n\n\n+', '\n\n', content)

    if content != original_content:
        file_path.write_text(content)
        return True
    return False


def main():
    """Main function."""
    types_dir = Path("computor-types/src/computor_types")

    if not types_dir.exists():
        print(f"❌ Types directory not found: {types_dir}")
        return

    print("🔧 Fixing import issues in computor-types...")
    print(f"📂 Directory: {types_dir}")
    print()

    fixed_files = []

    for py_file in types_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        if py_file.name in ["__init__.py"]:
            continue

        try:
            if fix_imports(py_file):
                fixed_files.append(py_file.relative_to(types_dir))
                print(f"✅ Fixed: {py_file.relative_to(types_dir)}")
        except Exception as e:
            print(f"❌ Error fixing {py_file.relative_to(types_dir)}: {e}")

    print()
    print("="*60)
    print(f"✅ Fixed {len(fixed_files)} files")
    if fixed_files:
        print("\nFixed files:")
        for f in sorted(fixed_files):
            print(f"  - {f}")
    print("="*60)


if __name__ == "__main__":
    main()

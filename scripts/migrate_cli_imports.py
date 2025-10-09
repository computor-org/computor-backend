#!/usr/bin/env python3
"""
Migrate CLI imports from computor_backend to computor_types/computor_client.
"""

import re
from pathlib import Path


def update_cli_imports(file_path: Path) -> bool:
    """Update imports in a CLI file."""
    content = file_path.read_text()
    original_content = content

    # Replace interface imports with computor_types
    content = re.sub(
        r'from computor_backend\.interface\.(\w+) import',
        r'from computor_types.\1 import',
        content
    )

    # Replace direct interface imports
    content = re.sub(
        r'from computor_backend\.interface import',
        r'from computor_types import',
        content
    )

    # Replace model imports (these should stay as backend imports for now)
    # Will be updated in Phase 4

    # Update cli internal imports
    content = re.sub(
        r'from computor_backend\.cli\.',
        r'from computor_cli.',
        content
    )

    content = re.sub(
        r'from \.(\w+) import',
        r'from computor_cli.\1 import',
        content
    )

    # Keep backend imports for database, API, tasks, etc. for now
    # These will be updated in Phase 4 when backend is renamed

    if content != original_content:
        file_path.write_text(content)
        return True
    return False


def main():
    """Main migration function."""
    cli_dir = Path("computor-cli/src/computor_cli")

    if not cli_dir.exists():
        print(f"❌ CLI directory not found: {cli_dir}")
        return

    print("🔄 Migrating CLI imports...")
    print(f"📂 Directory: {cli_dir}")
    print()

    updated_files = []

    for py_file in cli_dir.glob("*.py"):
        if py_file.name == "__pycache__":
            continue

        try:
            if update_cli_imports(py_file):
                updated_files.append(py_file.name)
                print(f"✅ Updated: {py_file.name}")
            else:
                print(f"⏭️  No changes: {py_file.name}")
        except Exception as e:
            print(f"❌ Failed to update {py_file.name}: {e}")

    print()
    print("="*60)
    print(f"✅ Migration complete!")
    print(f"   Updated {len(updated_files)} files")
    print("="*60)


if __name__ == "__main__":
    main()

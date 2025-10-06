#!/usr/bin/env python3
"""
Update backend to use computor_types instead of local interface module.
"""

import re
from pathlib import Path


def update_imports(file_path: Path) -> bool:
    """Update imports in a single file."""
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

    # Replace import computor_backend.interface.*
    content = re.sub(
        r'import computor_backend\.interface\.(\w+)',
        r'import computor_types.\1',
        content
    )

    if content != original_content:
        file_path.write_text(content)
        return True
    return False


def main():
    """Main function."""
    backend_dir = Path("src/computor_backend")

    if not backend_dir.exists():
        print(f"❌ Backend directory not found: {backend_dir}")
        return

    print("🔄 Updating backend to use computor_types...")
    print(f"📂 Directory: {backend_dir}")
    print()

    updated_files = []

    for py_file in backend_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        # Skip interface directory itself (will be deleted)
        if "interface" in py_file.parts:
            continue

        try:
            if update_imports(py_file):
                updated_files.append(py_file.relative_to(backend_dir))
                print(f"✅ Updated: {py_file.relative_to(backend_dir)}")
        except Exception as e:
            print(f"❌ Failed to update {py_file.relative_to(backend_dir)}: {e}")

    print()
    print("="*60)
    print(f"✅ Migration complete!")
    print(f"   Updated {len(updated_files)} files")
    print("="*60)


if __name__ == "__main__":
    main()

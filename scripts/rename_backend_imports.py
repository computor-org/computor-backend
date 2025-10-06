#!/usr/bin/env python3
"""
Update all imports from computor_backend to computor_backend.
"""

import re
from pathlib import Path


def update_imports(file_path: Path) -> bool:
    """Update imports in a single file."""
    content = file_path.read_text()
    original_content = content

    # Replace computor_backend with computor_backend
    content = re.sub(
        r'\bcomputor_backend\b',
        'computor_backend',
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

    print("🔄 Updating backend imports from computor_backend to computor_backend...")
    print(f"📂 Directory: {backend_dir}")
    print()

    updated_files = []

    for py_file in backend_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
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

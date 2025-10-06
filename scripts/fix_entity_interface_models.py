#!/usr/bin/env python3
"""
Fix EntityInterface model references - set them to None instead of referencing model classes.
"""

import re
from pathlib import Path

TYPES_DIR = Path(__file__).parent.parent / "computor-types" / "src" / "computor_types"

def fix_model_reference(content: str) -> str:
    """Replace model = ModelClass with model = None in EntityInterface classes."""

    # Pattern: model = SomeModelClass (at class level, not as parameter)
    content = re.sub(
        r'(\n\s+)model = \w+(\s*\n)',
        r'\1model = None  # Set by backend\2',
        content
    )

    return content

def process_file(file_path: Path):
    """Process a single file."""
    content = file_path.read_text()
    original = content

    if 'EntityInterface' in content:
        content = fix_model_reference(content)

    if content != original:
        file_path.write_text(content)
        print(f"✅ Fixed {file_path.name}")
        return True
    return False

def main():
    """Run migration."""
    print("🔄 Fixing EntityInterface model references...")

    fixed_count = 0
    for py_file in TYPES_DIR.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        if process_file(py_file):
            fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} files!")

if __name__ == "__main__":
    main()

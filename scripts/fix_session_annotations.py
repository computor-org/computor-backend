#!/usr/bin/env python3
"""
Replace Session type hints with string annotations to avoid runtime imports.
"""

import re
from pathlib import Path

TYPES_DIR = Path(__file__).parent.parent / "computor-types" / "src" / "computor_types"

def fix_session_annotations(content: str) -> str:
    """Replace db: Session with db: 'Session' in function signatures."""

    # Replace Session type hint with string annotation
    content = re.sub(
        r'\(db: Session,',
        r"(db: 'Session',",
        content
    )
    content = re.sub(
        r'\(db:Session,',
        r"(db: 'Session',",
        content
    )

    # Also handle any model class references in search functions
    # Replace references to model classes with 'Any' since we don't import them
    content = re.sub(
        r'\.filter\((\w+)\.',  # e.g., .filter(Organization.
        r'.filter(',
        content
    )

    return content

def process_file(file_path: Path):
    """Process a single file."""
    content = file_path.read_text()
    original = content

    # Only process files with search functions
    if '_search(' in content:
        content = fix_session_annotations(content)

    if content != original:
        file_path.write_text(content)
        print(f"✅ Fixed {file_path.name}")
        return True
    return False

def main():
    """Run migration."""
    print("🔄 Fixing Session annotations in computor-types...")

    fixed_count = 0
    for py_file in TYPES_DIR.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        if process_file(py_file):
            fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} files!")

if __name__ == "__main__":
    main()

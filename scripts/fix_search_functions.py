#!/usr/bin/env python3
"""
Fix search functions to use TYPE_CHECKING for Session imports.
"""

import re
from pathlib import Path

TYPES_DIR = Path(__file__).parent.parent / "computor-types" / "src" / "computor_types"

def fix_search_function_session(content: str) -> str:
    """Add TYPE_CHECKING import for Session if search function exists."""

    # Check if this file has a search function that uses Session
    if '_search(db: Session' in content or '_search(db:Session' in content:
        # Check if TYPE_CHECKING is already imported
        if 'from typing import' in content and 'TYPE_CHECKING' not in content:
            # Add TYPE_CHECKING to existing typing import
            content = re.sub(
                r'from typing import ([^\n]+)',
                r'from typing import \1, TYPE_CHECKING',
                content,
                count=1
            )
        elif 'TYPE_CHECKING' not in content:
            # Add new TYPE_CHECKING import
            content = "from typing import TYPE_CHECKING\n" + content

        # Add Session import under TYPE_CHECKING
        if 'TYPE_CHECKING' in content and 'from sqlalchemy.orm import Session' not in content:
            # Find where TYPE_CHECKING block starts or add it
            if 'if TYPE_CHECKING:' in content:
                # Add to existing TYPE_CHECKING block
                content = re.sub(
                    r'(if TYPE_CHECKING:\n)',
                    r'\1    from sqlalchemy.orm import Session\n',
                    content,
                    count=1
                )
            else:
                # Create new TYPE_CHECKING block after typing import
                typing_import = re.search(r'from typing import.*\n', content)
                if typing_import:
                    insert_pos = typing_import.end()
                    content = (
                        content[:insert_pos] +
                        '\nif TYPE_CHECKING:\n    from sqlalchemy.orm import Session\n' +
                        content[insert_pos:]
                    )

    return content

def process_file(file_path: Path):
    """Process a single file."""
    content = file_path.read_text()
    original = content

    content = fix_search_function_session(content)

    if content != original:
        file_path.write_text(content)
        print(f"✅ Fixed {file_path.name}")
        return True
    return False

def main():
    """Run migration."""
    print("🔄 Fixing search functions in computor-types...")

    fixed_count = 0
    for py_file in TYPES_DIR.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        if process_file(py_file):
            fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} files!")

if __name__ == "__main__":
    main()

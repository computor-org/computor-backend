#!/usr/bin/env python3
"""
Final cleanup of computor-types package.
Remove all remaining backend/model references.
"""

import re
from pathlib import Path

TYPES_DIR = Path(__file__).parent.parent / "computor-types" / "src" / "computor_types"

def clean_file(file_path: Path) -> bool:
    """Clean a single file."""
    content = file_path.read_text()
    original = content

    # Remove model imports (both relative and absolute)
    content = re.sub(r'^from \.\.model\..*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'^from computor_types\.model\..*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'^from computor_backend\.model\..*$', '', content, flags=re.MULTILINE)

    # Remove any remaining computor_backend references
    content = re.sub(r'from computor_backend\.', 'from computor_types.', content)
    content = re.sub(r'import computor_backend\.', 'import computor_types.', content)

    # Fix relative imports to be absolute
    content = re.sub(r'from \.\.([\w.]+)', r'from computor_types.\1', content)

    # Remove TYPE_CHECKING blocks that import models (they're not needed)
    # But keep Session import
    lines = content.split('\n')
    cleaned_lines = []
    skip_until_blank = False

    for line in lines:
        if 'if TYPE_CHECKING:' in line:
            cleaned_lines.append(line)
            skip_until_blank = False
        elif skip_until_blank and line.strip() and not line.startswith('    '):
            skip_until_blank = False
            cleaned_lines.append(line)
        elif not skip_until_blank:
            cleaned_lines.append(line)

    content = '\n'.join(cleaned_lines)

    # Clean up multiple blank lines
    content = re.sub(r'\n\n\n+', '\n\n', content)

    if content != original:
        file_path.write_text(content)
        return True
    return False

def main():
    """Run cleanup."""
    print("🔄 Final cleanup of computor-types...")

    fixed_count = 0
    for py_file in TYPES_DIR.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        if clean_file(py_file):
            print(f"✅ Cleaned {py_file.name}")
            fixed_count += 1

    print(f"\n✅ Cleaned {fixed_count} files!")

if __name__ == "__main__":
    main()

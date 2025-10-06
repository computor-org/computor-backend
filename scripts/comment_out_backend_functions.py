#!/usr/bin/env python3
"""
Comment out backend-specific functions in types package.

Functions that use SQLAlchemy models, database sessions, or repositories
should remain in the backend, not in the types package.
"""

import re
from pathlib import Path


def comment_out_function(content: str, func_name: str) -> str:
    """Comment out a function definition and its body."""
    # Pattern to match function definition and its body (based on indentation)
    pattern = rf'^((?:async )?def {func_name}\([^)]*\)[^:]*:.*?)(?=\n(?:async )?def |\nclass |\Z)'

    def replacer(match):
        func_text = match.group(0)
        # Add # to each line
        commented = '\n'.join(f'# {line}' if line.strip() else '#' for line in func_text.split('\n'))
        return f'# BACKEND FUNCTION - Moved to backend in Phase 4\n{commented}'

    content = re.sub(pattern, replacer, content, flags=re.MULTILINE | re.DOTALL)
    return content


def fix_file(file_path: Path) -> bool:
    """Fix a single file by commenting out backend functions."""
    content = file_path.read_text()
    original_content = content

    # List of function patterns that should be commented out
    backend_functions = [
        r'_search\s*\(',
        r'post_update_\w+\s*\(',
        r'post_create_\w+\s*\(',
        r'post_delete_\w+\s*\(',
        r'pre_update_\w+\s*\(',
        r'pre_create_\w+\s*\(',
        r'pre_delete_\w+\s*\(',
    ]

    # Find function names that match backend patterns and reference db: Session or Result model
    for pattern in backend_functions:
        # Find all functions matching this pattern
        matches = re.finditer(
            rf'^((?:async )?def (\w*{pattern.replace("(", "")[:-2]}\w*)\([^)]*(?:db:\s*["\']?Session|Result\b)[^)]*\):)',
            content,
            re.MULTILINE
        )

        for match in matches:
            func_name = match.group(2)
            # Comment out this function
            lines = content.split('\n')
            new_lines = []
            in_function = False
            function_indent = None

            for line in lines:
                if f'def {func_name}(' in line:
                    in_function = True
                    function_indent = len(line) - len(line.lstrip())
                    new_lines.append(f'# BACKEND FUNCTION - Moved to backend in Phase 4')
                    new_lines.append(f'# {line}')
                    continue

                if in_function:
                    current_indent = len(line) - len(line.lstrip()) if line.strip() else function_indent + 1

                    # End of function when we hit non-indented content (or another def/class)
                    if line.strip() and current_indent <= function_indent:
                        if not line.strip().startswith('#'):
                            in_function = False
                            new_lines.append(line)
                            continue

                    new_lines.append(f'# {line}' if line.strip() else '#')
                else:
                    new_lines.append(line)

            content = '\n'.join(new_lines)

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

    print("🔧 Commenting out backend functions in computor-types...")
    print(f"📂 Directory: {types_dir}")
    print()

    fixed_files = []

    for py_file in types_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            if fix_file(py_file):
                fixed_files.append(py_file.relative_to(types_dir))
                print(f"✅ Fixed: {py_file.relative_to(types_dir)}")
        except Exception as e:
            print(f"❌ Error fixing {py_file.relative_to(types_dir)}: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("="*60)
    print(f"✅ Processed {len(fixed_files)} files")
    if fixed_files:
        print("\nFixed files:")
        for f in sorted(fixed_files):
            print(f"  - {f}")
    print("="*60)


if __name__ == "__main__":
    main()

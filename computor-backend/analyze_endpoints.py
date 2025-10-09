#!/usr/bin/env python3
"""
Analyze POST/PATCH/PUT/DELETE endpoints to find direct database operations.
"""
import re
from pathlib import Path

API_DIR = Path("src/computor_backend/api")

# Patterns that indicate direct database writes (not through crud.py)
DB_WRITE_PATTERNS = [
    r'db\.add\(',
    r'db\.delete\(',
    r'db\.query\(.*\)\.update\(',
    r'db\.execute\(',
    r'db\.commit\(',
]

# Patterns that indicate using business logic (already has set_db_user)
CRUD_PATTERNS = [
    r'create_entity\(',
    r'update_entity\(',
    r'delete_entity\(',
    r'create_db\(',
    r'update_db\(',
]

def extract_function_body(content: str, start_line: int) -> tuple[str, int, int]:
    """Extract function body starting from line number."""
    lines = content.split('\n')

    # Find function definition
    func_start = start_line - 1

    # Find the end of function (next function def or end of file)
    indent_level = None
    func_end = len(lines)

    for i in range(func_start + 1, len(lines)):
        line = lines[i]

        # Skip empty lines
        if not line.strip():
            continue

        # Detect base indentation (first non-empty line after def)
        if indent_level is None:
            indent_level = len(line) - len(line.lstrip())
            continue

        # Check if we've reached a new function or class at same/lower indent
        current_indent = len(line) - len(line.lstrip())
        if current_indent < indent_level and (line.strip().startswith('def ') or
                                               line.strip().startswith('class ') or
                                               line.strip().startswith('@')):
            func_end = i
            break

    return '\n'.join(lines[func_start:func_end]), func_start + 1, func_end + 1

def analyze_endpoint(filepath: Path, line_num: int, decorator: str) -> dict:
    """Analyze a single endpoint."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Extract function body
    func_body, start, end = extract_function_body(content, line_num + 1)

    # Check for direct DB writes
    has_direct_writes = any(re.search(pattern, func_body) for pattern in DB_WRITE_PATTERNS)

    # Check for CRUD usage
    uses_crud = any(re.search(pattern, func_body) for pattern in CRUD_PATTERNS)

    # Check if already has set_db_user
    has_set_db_user = 'set_db_user(' in func_body

    # Extract function name
    func_match = re.search(r'async def (\w+)\(', func_body)
    func_name = func_match.group(1) if func_match else "unknown"

    return {
        'file': filepath.name,
        'line': line_num,
        'decorator': decorator,
        'function': func_name,
        'has_direct_writes': has_direct_writes,
        'uses_crud': uses_crud,
        'has_set_db_user': has_set_db_user,
        'needs_fix': has_direct_writes and not has_set_db_user and not uses_crud
    }

def main():
    """Main analysis."""
    print("=" * 80)
    print("Analyzing POST/PATCH/PUT/DELETE endpoints for database operations")
    print("=" * 80)
    print()

    # Find all endpoints
    endpoints_needing_fix = []
    endpoints_already_ok = []

    for py_file in sorted(API_DIR.glob("*.py")):
        if py_file.name == '__init__.py':
            continue

        with open(py_file, 'r') as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            # Match @router.post/patch/put/delete decorators
            if re.search(r'@\w+_router\.(post|patch|put|delete)\(', line, re.IGNORECASE):
                decorator = line.strip()
                result = analyze_endpoint(py_file, i + 1, decorator)

                if result['needs_fix']:
                    endpoints_needing_fix.append(result)
                else:
                    endpoints_already_ok.append(result)

    # Print results
    print(f"Total endpoints analyzed: {len(endpoints_needing_fix) + len(endpoints_already_ok)}")
    print(f"Endpoints needing fix: {len(endpoints_needing_fix)}")
    print(f"Endpoints already OK: {len(endpoints_already_ok)}")
    print()

    if endpoints_needing_fix:
        print("=" * 80)
        print("ENDPOINTS NEEDING set_db_user:")
        print("=" * 80)
        print()

        by_file = {}
        for ep in endpoints_needing_fix:
            if ep['file'] not in by_file:
                by_file[ep['file']] = []
            by_file[ep['file']].append(ep)

        for filename in sorted(by_file.keys()):
            print(f"\n{filename}:")
            print("-" * 80)
            for ep in by_file[filename]:
                print(f"  Line {ep['line']:4d}: {ep['function']:40s} {ep['decorator'][:60]}")
        print()

    # Show statistics
    print("=" * 80)
    print("STATISTICS:")
    print("=" * 80)
    print(f"  Uses CRUD (already protected): {sum(1 for ep in endpoints_already_ok if ep['uses_crud'])}")
    print(f"  Has set_db_user already: {sum(1 for ep in endpoints_already_ok if ep['has_set_db_user'])}")
    print(f"  No DB writes: {sum(1 for ep in endpoints_already_ok if not ep['has_direct_writes'])}")
    print(f"  Needs set_db_user: {len(endpoints_needing_fix)}")
    print()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Check for forbidden imports in packages to maintain clean architecture.

This script ensures that:
- computor-types remains pure (no web framework dependencies)
- computor-cli doesn't depend on backend
- computor-client doesn't depend on backend

Usage:
    python scripts/check_forbidden_imports.py
    python scripts/check_forbidden_imports.py --package computor-types
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


# Define forbidden imports for each package
FORBIDDEN_IMPORTS = {
    'computor-types': {
        'fastapi': 'Web framework - types should be framework-agnostic',
        'starlette': 'ASGI framework - types should be framework-agnostic',
        'sqlalchemy': 'Database ORM - types should not depend on ORM',
        'sqlalchemy_utils': 'SQLAlchemy utilities - types should not depend on ORM',
        'flask': 'Web framework - types should be framework-agnostic',
        'django': 'Web framework - types should be framework-agnostic',
        'computor_backend': 'Backend code - creates circular dependency',
    },
    'computor-cli': {
        'computor_backend': 'Backend code - CLI should use computor-client instead',
        'fastapi': 'Web framework - CLI should use httpx/computor-client',
        'starlette': 'ASGI framework - CLI should use httpx/computor-client',
        'sqlalchemy': 'Database ORM - CLI should use HTTP API',
        'flask': 'Web framework - CLI should use httpx/computor-client',
        'django': 'Web framework - CLI should use httpx/computor-client',
    },
    'computor-client': {
        'computor_backend': 'Backend code - client should be independent',
        'fastapi': 'Web framework - client should only use httpx',
        'starlette': 'ASGI framework - client should only use httpx',
        'sqlalchemy': 'Database ORM - client should use HTTP API',
        'flask': 'Web framework - client should only use httpx',
        'django': 'Web framework - client should only use httpx',
    },
    'computor-utils': {
        'computor_backend': 'Backend code - utils should be independent',
        'fastapi': 'Web framework - utils should be framework-agnostic',
        'starlette': 'ASGI framework - utils should be framework-agnostic',
    },
}


# Patterns to detect imports
IMPORT_PATTERNS = [
    re.compile(r'^\s*import\s+([\w\.]+)'),
    re.compile(r'^\s*from\s+([\w\.]+)\s+import'),
]


def find_python_files(package_path: Path) -> List[Path]:
    """Find all Python files in a package."""
    src_path = package_path / 'src'
    if not src_path.exists():
        return []

    return list(src_path.rglob('*.py'))


def extract_imports(file_path: Path) -> Set[str]:
    """Extract all import statements from a Python file."""
    imports = set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Skip comments
                if line.strip().startswith('#'):
                    continue

                # Check each import pattern
                for pattern in IMPORT_PATTERNS:
                    match = pattern.match(line)
                    if match:
                        module = match.group(1).split('.')[0]  # Get root module
                        imports.add(module)
    except Exception as e:
        print(f"  ⚠️  Error reading {file_path}: {e}", file=sys.stderr)

    return imports


def check_package(package_name: str, project_root: Path) -> Tuple[bool, List[Dict]]:
    """
    Check a package for forbidden imports.

    Returns:
        (is_clean, violations) - True if no violations found
    """
    package_path = project_root / package_name

    if not package_path.exists():
        print(f"  ⚠️  Package {package_name} not found at {package_path}")
        return True, []

    forbidden = FORBIDDEN_IMPORTS.get(package_name, {})
    if not forbidden:
        print(f"  ℹ️  No forbidden imports defined for {package_name}")
        return True, []

    python_files = find_python_files(package_path)
    if not python_files:
        print(f"  ⚠️  No Python files found in {package_name}")
        return True, []

    violations = []

    for file_path in python_files:
        imports = extract_imports(file_path)

        for imported_module in imports:
            if imported_module in forbidden:
                relative_path = file_path.relative_to(project_root)
                violations.append({
                    'file': str(relative_path),
                    'module': imported_module,
                    'reason': forbidden[imported_module],
                })

    return len(violations) == 0, violations


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Check for forbidden imports in packages'
    )
    parser.add_argument(
        '--package',
        help='Specific package to check (default: check all)'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Suggest fixes for violations (not implemented yet)'
    )

    args = parser.parse_args()

    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    print("🔍 Checking for forbidden imports...\n")

    # Determine which packages to check
    packages_to_check = [args.package] if args.package else FORBIDDEN_IMPORTS.keys()

    all_clean = True
    total_violations = 0

    for package_name in packages_to_check:
        print(f"📦 Checking {package_name}...")

        is_clean, violations = check_package(package_name, project_root)

        if is_clean:
            print(f"  ✅ No forbidden imports found\n")
        else:
            all_clean = False
            print(f"  ❌ Found {len(violations)} violation(s):\n")

            for violation in violations:
                print(f"     File: {violation['file']}")
                print(f"     Import: {violation['module']}")
                print(f"     Reason: {violation['reason']}")
                print()

            total_violations += len(violations)

    # Print summary
    print("=" * 60)
    if all_clean:
        print("✅ All checks passed! No forbidden imports found.")
        return 0
    else:
        print(f"❌ Found {total_violations} forbidden import(s) across packages.")
        print("\nPlease remove these imports to maintain clean architecture.")
        print("See the output above for details.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

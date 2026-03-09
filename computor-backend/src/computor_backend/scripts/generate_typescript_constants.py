#!/usr/bin/env python3
"""
Generate TypeScript constants from Python constants defined in computor-types.

This script extracts constants (e.g., EXAMPLE_EXCLUDE_PATTERNS) from
computor-types and generates a TypeScript constants file for use in
the web frontend and VS Code extension.
"""

import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, List

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "computor-types" / "src"))


def collect_constants() -> Dict[str, Any]:
    """Collect exportable constants from computor-types."""
    from computor_types.example import EXAMPLE_EXCLUDE_PATTERNS

    return {
        'EXAMPLE_EXCLUDE_PATTERNS': EXAMPLE_EXCLUDE_PATTERNS,
    }


def generate_typescript(constants: Dict[str, Any]) -> str:
    """Generate TypeScript source from constants dict."""
    lines = [
        '/**',
        ' * Auto-generated constants from computor-types Python package.',
        ' * DO NOT EDIT — regenerate with: bash generate.sh constants',
        ' */',
        '',
    ]

    for name, value in constants.items():
        if isinstance(value, list):
            items = ', '.join(json.dumps(v) for v in value)
            lines.append(f'export const {name}: readonly string[] = [{items}] as const;')
        elif isinstance(value, str):
            lines.append(f'export const {name} = {json.dumps(value)} as const;')
        elif isinstance(value, (int, float, bool)):
            lines.append(f'export const {name} = {json.dumps(value)} as const;')
        elif isinstance(value, dict):
            lines.append(f'export const {name} = {json.dumps(value, indent=2)} as const;')
        lines.append('')

    return '\n'.join(lines)


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent.parent.parent.parent

    # Output locations
    outputs = [
        project_root / "computor-web" / "src" / "generated" / "types" / "constants.ts",
    ]

    constants = collect_constants()
    ts_content = generate_typescript(constants)

    for output_path in outputs:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(ts_content, encoding='utf-8')
        print(f"✅ Generated {output_path}")

    print(f"\n📦 Exported {len(constants)} constant(s)")


if __name__ == "__main__":
    main()

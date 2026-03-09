#!/usr/bin/env python3
"""
Generate JSON Schema from Pydantic models for VS Code YAML validation.

Generates schemas for:
  - meta.yaml  (CodeAbilityMeta)
  - test.yaml  (ComputorTestSuite)
"""

import json
import sys
import os
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from computor_types.codeability_meta import CodeAbilityMeta
from computor_types.testing import ComputorTestSuite


def generate_schema(model_class, title: str, description: str) -> dict:
    """Generate JSON Schema from a Pydantic model."""
    schema = model_class.model_json_schema()
    schema['$schema'] = 'http://json-schema.org/draft-07/schema#'
    schema['title'] = title
    schema['description'] = description
    return schema


def write_schema(schema: dict, output_path: Path):
    """Write schema to file, creating directories as needed."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(schema, f, indent=2, sort_keys=False)

    prop_count = len(schema.get('properties', {}))
    print(f"  Generated: {output_path} ({prop_count} top-level properties)")


def main():
    """Generate all JSON schemas."""
    # Determine output directory
    backend_dir = Path(__file__).parent.parent  # computor_backend
    src_dir = backend_dir.parent  # src
    backend_root = src_dir.parent  # computor-backend
    project_root = backend_root.parent  # computor-fullstack
    schema_dir = project_root / 'computor-web' / 'src' / 'generated' / 'schemas'

    schemas = [
        (
            CodeAbilityMeta,
            'meta-yaml-schema.json',
            'CodeAbility Meta Schema',
            'Schema for meta.yaml files in Computor examples (auto-generated from codeability_meta.py)',
        ),
        (
            ComputorTestSuite,
            'test-yaml-schema.json',
            'Computor Test Suite Schema',
            'Schema for test.yaml files in Computor examples (auto-generated from testing.py)',
        ),
    ]

    print("JSON Schema Generator")
    print("=" * 50)

    for model_class, filename, title, description in schemas:
        schema = generate_schema(model_class, title, description)
        write_schema(schema, schema_dir / filename)

    print("=" * 50)
    print(f"Done. {len(schemas)} schemas generated in {schema_dir}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Generate JSON Schema from Pydantic models for VS Code YAML validation.
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from computor_types.codeability_meta import CodeAbilityMeta


def generate_schema(include_timestamp: bool = False):
    """Generate JSON Schema from CodeAbilityMeta Pydantic model."""
    
    # Get the JSON schema from the Pydantic model
    schema = CodeAbilityMeta.model_json_schema()
    
    # Add some VS Code specific enhancements
    schema['$schema'] = 'http://json-schema.org/draft-07/schema#'
    schema['title'] = 'CodeAbility Meta Schema'
    schema['description'] = 'Schema for meta.yaml files in Computor examples (auto-generated from codeability_meta.py)'

    if include_timestamp:
        schema['x-generated-on'] = datetime.utcnow().isoformat()
    
    return schema


def main(include_timestamp: bool = False):
    """Main function to generate and save the schema."""

    # Generate the schema
    schema = generate_schema(include_timestamp=include_timestamp)

    # Determine output path - use generated/schemas directory
    # Path: scripts -> computor_backend -> src -> computor-backend -> computor-fullstack
    backend_dir = Path(__file__).parent.parent  # computor_backend
    src_dir = backend_dir.parent  # src
    backend_root = src_dir.parent  # computor-backend
    project_root = backend_root.parent  # computor-fullstack

    # Output to generated/schemas directory
    schema_path = project_root / 'generated' / 'schemas' / 'meta-yaml-schema.json'

    # Create schemas directory if it doesn't exist
    schema_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the schema to file
    with open(schema_path, 'w') as f:
        json.dump(schema, f, indent=2, sort_keys=False)

    print(f"✅ Generated JSON Schema: {schema_path}")
    print(f"📝 Schema has {len(schema.get('properties', {}))} properties")

    # Print the top-level properties for verification
    if 'properties' in schema:
        print("\nTop-level properties:")
        for prop in schema['properties'].keys():
            print(f"  - {prop}")


if __name__ == '__main__':
    main()

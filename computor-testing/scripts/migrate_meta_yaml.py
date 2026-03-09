#!/usr/bin/env python3
"""
Meta.yaml Migration Script

Migrates meta.yaml files from old schema to new schema.

Changes applied:
1. Rename 'slug' -> 'identifier'
2. Rename 'links' -> 'courseMaterials'
3. Rename 'supportingMaterial' -> 'supportingMaterials'
4. Rename 'description' -> 'name' in material entries
5. Move 'keywords' -> 'content.tags' (then remove keywords)
6. Remove 'language' field (derived from content/index_*.md files)
7. Remove 'type' and 'kind' fields (deprecated)
8. Add empty 'content' structure if not present

Usage:
    # Dry run (preview changes)
    python migrate_meta_yaml.py /path/to/examples

    # Apply changes
    python migrate_meta_yaml.py /path/to/examples --apply

    # Migrate single file
    python migrate_meta_yaml.py /path/to/meta.yaml --apply

    # Show verbose output
    python migrate_meta_yaml.py /path/to/examples --verbose
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from ruamel.yaml import YAML

# Use ruamel.yaml to preserve formatting and comments
yaml = YAML()
yaml.preserve_quotes = True
yaml.default_flow_style = False
yaml.indent(mapping=2, sequence=4, offset=2)


def migrate_material_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate a single material entry (link or supportingMaterial).

    Renames 'description' -> 'name'
    """
    if isinstance(entry, dict):
        new_entry = {}
        for key, value in entry.items():
            if key == 'description':
                new_entry['name'] = value
            else:
                new_entry[key] = value
        return new_entry
    return entry


def migrate_materials_list(materials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Migrate a list of material entries."""
    if not materials:
        return []
    return [migrate_material_entry(m) for m in materials]


def infer_tools_from_identifier(identifier: str) -> List[str]:
    """
    Infer tools from the identifier pattern.

    Examples:
        itpcp.pgph.mat.* -> ['matlab', 'octave']
        itpcp.pgph.oct.* -> ['octave']
        itpcp.pgph.py.* -> ['python']
        itpcp.pgph.r.* -> ['r']
        itpcp.pgph.jl.* -> ['julia']
        itpcp.pgph.c.* -> ['c']
        itpcp.pgph.f.* -> ['fortran']
    """
    if not identifier:
        return []

    tools_map = {
        '.mat.': ['matlab', 'octave'],
        '.oct.': ['octave'],
        '.py.': ['python'],
        '.r.': ['r'],
        '.jl.': ['julia'],
        '.c.': ['c'],
        '.f.': ['fortran'],
        '.f90.': ['fortran'],
        '.doc.': [],
    }

    for pattern, tools in tools_map.items():
        if pattern in identifier:
            return tools

    return []


def migrate_meta_yaml(data: Dict[str, Any], filepath: Path = None) -> Tuple[Dict[str, Any], List[str]]:
    """
    Migrate a meta.yaml data dictionary to new schema.

    Returns:
        Tuple of (migrated_data, list_of_changes_made)
    """
    changes = []

    # Work with a copy to track changes
    result = dict(data)

    # 1. Rename 'slug' -> 'identifier'
    if 'slug' in result:
        result['identifier'] = result.pop('slug')
        changes.append("Renamed 'slug' -> 'identifier'")

    # Get identifier for inferring tools
    identifier = result.get('identifier', '')

    # 2. Rename 'links' -> 'courseMaterials' and migrate entries
    if 'links' in result:
        migrated_links = migrate_materials_list(result.pop('links'))
        result['courseMaterials'] = migrated_links
        changes.append("Renamed 'links' -> 'courseMaterials' (with 'description' -> 'name')")

    # 3. Rename 'supportingMaterial' -> 'supportingMaterials' and migrate entries
    if 'supportingMaterial' in result:
        migrated_materials = migrate_materials_list(result.pop('supportingMaterial'))
        result['supportingMaterials'] = migrated_materials
        changes.append("Renamed 'supportingMaterial' -> 'supportingMaterials' (with 'description' -> 'name')")
    elif 'supportingMaterials' in result:
        # Already plural, but still need to migrate 'description' -> 'name'
        result['supportingMaterials'] = migrate_materials_list(result['supportingMaterials'])
        if any('description' in m for m in data.get('supportingMaterials', []) if isinstance(m, dict)):
            changes.append("Migrated 'description' -> 'name' in supportingMaterials")

    # 4. Handle 'keywords' -> 'content.tags'
    keywords = result.pop('keywords', None)

    # 5. Remove 'language' field
    if 'language' in result:
        result.pop('language')
        changes.append("Removed 'language' (now derived from content/index_*.md)")

    # 6. Remove 'type' and 'kind' fields
    if 'type' in result:
        result.pop('type')
        changes.append("Removed deprecated 'type' field")
    if 'kind' in result:
        result.pop('kind')
        changes.append("Removed deprecated 'kind' field")

    # 7. Create/update 'content' structure
    content = result.get('content', {})
    if not isinstance(content, dict):
        content = {}

    # Initialize content fields if not present
    if 'types' not in content:
        content['types'] = []
    if 'disciplines' not in content:
        content['disciplines'] = []
    if 'topics' not in content:
        content['topics'] = []
    if 'tools' not in content:
        # Try to infer tools from identifier
        inferred_tools = infer_tools_from_identifier(identifier)
        content['tools'] = inferred_tools
        if inferred_tools:
            changes.append(f"Inferred tools from identifier: {inferred_tools}")
    if 'tags' not in content:
        # Move keywords to tags
        if keywords and isinstance(keywords, list) and len(keywords) > 0:
            content['tags'] = keywords
            changes.append(f"Moved 'keywords' -> 'content.tags': {keywords}")
        else:
            content['tags'] = []

    result['content'] = content
    if 'content' not in data:
        changes.append("Added 'content' structure")

    return result, changes


def reorder_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reorder keys to match the preferred schema order.
    """
    preferred_order = [
        'identifier',
        'version',
        'title',
        'description',
        'authors',
        'maintainers',
        'courseMaterials',
        'supportingMaterials',
        'license',
        'content',
        'properties',
    ]

    result = {}

    # Add keys in preferred order
    for key in preferred_order:
        if key in data:
            result[key] = data[key]

    # Add any remaining keys
    for key in data:
        if key not in result:
            result[key] = data[key]

    return result


def process_file(filepath: Path, apply: bool = False, verbose: bool = False) -> Tuple[bool, List[str]]:
    """
    Process a single meta.yaml file.

    Returns:
        Tuple of (was_modified, list_of_changes)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.load(f)

        if data is None:
            return False, ["Empty file"]

        migrated, changes = migrate_meta_yaml(data, filepath)

        if not changes:
            return False, ["No changes needed"]

        # Reorder keys
        migrated = reorder_keys(migrated)

        if apply:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(migrated, f)

        return True, changes

    except Exception as e:
        return False, [f"ERROR: {str(e)}"]


def find_meta_yaml_files(base_path: Path) -> List[Path]:
    """Find all meta.yaml files in directory tree."""
    if base_path.is_file():
        return [base_path]

    patterns = [
        'itpcp.progphys*/**/meta.yaml',
        '**/meta.yaml',
    ]

    files = set()
    for pattern in patterns:
        for f in base_path.glob(pattern):
            files.add(f)

    return sorted(files)


def main():
    parser = argparse.ArgumentParser(
        description='Migrate meta.yaml files to new schema',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'path',
        type=Path,
        help='Path to meta.yaml file or directory containing examples'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply changes (without this flag, only shows what would change)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output for each file'
    )
    parser.add_argument(
        '--pattern',
        type=str,
        default='**/meta.yaml',
        help='Glob pattern for finding meta.yaml files (default: **/meta.yaml)'
    )

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)

    # Find files
    if args.path.is_file():
        files = [args.path]
    else:
        files = list(args.path.glob(args.pattern))

    if not files:
        print(f"No meta.yaml files found in {args.path}")
        sys.exit(0)

    # Print mode
    if args.apply:
        print("=" * 60)
        print("APPLYING CHANGES")
        print("=" * 60)
    else:
        print("=" * 60)
        print("DRY RUN - Use --apply to make changes")
        print("=" * 60)
    print()

    # Process files
    stats = {
        'total': 0,
        'modified': 0,
        'unchanged': 0,
        'errors': 0,
    }

    for filepath in sorted(files):
        stats['total'] += 1

        modified, changes = process_file(filepath, apply=args.apply, verbose=args.verbose)

        if any('ERROR' in c for c in changes):
            stats['errors'] += 1
            print(f"ERROR: {filepath}")
            for change in changes:
                print(f"  {change}")
        elif modified:
            stats['modified'] += 1
            if args.verbose or not args.apply:
                print(f"{'Modified' if args.apply else 'Would modify'}: {filepath}")
                for change in changes:
                    print(f"  - {change}")
        else:
            stats['unchanged'] += 1
            if args.verbose:
                print(f"Unchanged: {filepath}")

    # Print summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total files:    {stats['total']}")
    print(f"Modified:       {stats['modified']}")
    print(f"Unchanged:      {stats['unchanged']}")
    print(f"Errors:         {stats['errors']}")

    if not args.apply and stats['modified'] > 0:
        print()
        print("Run with --apply to make changes")


if __name__ == '__main__':
    main()

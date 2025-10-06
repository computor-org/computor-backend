#!/usr/bin/env python3
"""
Export JSON schemas from all Pydantic models for TypeScript validation class generation.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Type, Any
from datetime import datetime
import importlib.util
import ast
import inspect
from enum import Enum

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from pydantic import BaseModel


class SchemaExporter:
    """Export JSON schemas from Pydantic models."""

    def __init__(self, include_timestamp: bool = False):
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.enum_schemas: Dict[str, Dict[str, Any]] = {}
        self.processed_models: Set[str] = set()
        self.processed_enums: Set[str] = set()
        self.include_timestamp = include_timestamp
        self._timestamp_value: str | None = None

    def _current_timestamp(self) -> str:
        """Get current timestamp for this generation run."""
        if not self.include_timestamp:
            raise RuntimeError("Timestamp requested but include_timestamp is False")
        if self._timestamp_value is None:
            self._timestamp_value = datetime.now().isoformat()
        return self._timestamp_value

    def scan_directory(self, directory: Path, pattern: str = "*.py") -> tuple[List[Type[BaseModel]], List[Type[Enum]]]:
        """Scan directory for Pydantic models and Enum definitions."""
        models: List[Type[BaseModel]] = []
        enums: List[Type[Enum]] = []
        model_names: Set[str] = set()
        enum_names: Set[str] = set()

        for py_file in directory.rglob(pattern):
            # Skip test files and __pycache__
            if '__pycache__' in str(py_file) or 'test_' in py_file.name:
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                tree = ast.parse(content)
            except Exception as e:
                print(f"Warning: Could not parse {py_file}: {e}")
                continue

            # Import the module to access classes
            module = None
            try:
                relative_path = py_file.relative_to(Path(__file__).parent.parent.parent)
                module_path = str(relative_path).replace('/', '.').replace('.py', '')
                spec = importlib.util.spec_from_file_location(module_path, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
            except Exception as e:
                print(f"Warning: Could not import module {py_file}: {e}")

            if module is None:
                continue

            def process_class(node: ast.ClassDef, parent_chain: List[str]):
                current_chain = parent_chain + [node.name]

                attr = module
                for name in current_chain:
                    if not hasattr(attr, name):
                        attr = None
                        break
                    attr = getattr(attr, name)

                if attr and inspect.isclass(attr):
                    try:
                        if issubclass(attr, BaseModel):
                            if attr.__name__ not in model_names:
                                models.append(attr)
                                model_names.add(attr.__name__)
                        elif issubclass(attr, Enum):
                            if attr.__name__ not in enum_names:
                                enums.append(attr)
                                enum_names.add(attr.__name__)
                    except TypeError:
                        pass

                for child in node.body:
                    if isinstance(child, ast.ClassDef):
                        process_class(child, current_chain)

            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    process_class(node, [])

        return models, enums

    def export_model_schema(self, model: Type[BaseModel]) -> Dict[str, Any]:
        """Export JSON schema for a single Pydantic model."""
        model_name = model.__name__

        if model_name in self.processed_models:
            return self.schemas[model_name]

        self.processed_models.add(model_name)

        # Try to rebuild model if it has forward references
        try:
            model.model_rebuild()
        except Exception:
            pass  # Model might already be built or doesn't need rebuilding

        # Get Pydantic JSON schema
        try:
            schema = model.model_json_schema(mode='serialization')
        except Exception as e:
            print(f"Warning: Could not generate schema for {model_name}: {e}")
            # Return a basic schema as fallback
            return {
                'type': 'object',
                'x-model-name': model_name,
                'x-schema-error': str(e),
            }

        # Add metadata
        schema['x-model-name'] = model_name
        if self.include_timestamp:
            schema['x-generated-on'] = self._current_timestamp()

        # Store documentation if available
        if model.__doc__:
            schema['description'] = model.__doc__.strip()

        self.schemas[model_name] = schema
        return schema

    def export_enum_schema(self, enum_class: Type[Enum]) -> Dict[str, Any]:
        """Export JSON schema for a Python Enum."""
        enum_name = enum_class.__name__

        if enum_name in self.processed_enums:
            return self.enum_schemas[enum_name]

        self.processed_enums.add(enum_name)

        # Create schema for enum
        values = [member.value for member in enum_class]

        schema = {
            'type': 'string' if all(isinstance(v, str) for v in values) else 'any',
            'enum': values,
            'x-enum-name': enum_name,
            'x-is-enum': True,
        }

        if self.include_timestamp:
            schema['x-generated-on'] = self._current_timestamp()

        self.enum_schemas[enum_name] = schema
        return schema

    def export_all(self, scan_dirs: List[Path], output_dir: Path) -> Dict[str, Path]:
        """Export all schemas to JSON files."""
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.include_timestamp:
            self._timestamp_value = None

        # Scan for models and enums
        all_models = []
        all_enums = []
        for scan_dir in scan_dirs:
            if scan_dir.exists():
                models, enums = self.scan_directory(scan_dir)
                all_models.extend(models)
                all_enums.extend(enums)

        print(f"📦 Found {len(all_models)} Pydantic models")
        print(f"📦 Found {len(all_enums)} Enum types")

        # Export schemas
        for model in all_models:
            self.export_model_schema(model)

        for enum in all_enums:
            self.export_enum_schema(enum)

        # Group schemas by category (similar to interface generation)
        categories = self._categorize_schemas()

        # Write schema files by category
        generated_files = {}

        for category, category_schemas in categories.items():
            if not category_schemas['models'] and not category_schemas['enums']:
                continue

            output_file = output_dir / f"{category}.schema.json"

            schema_bundle = {
                '$schema': 'http://json-schema.org/draft-07/schema#',
                'title': f'{category.title()} Schemas',
                'description': f'Auto-generated JSON schemas for {category} models',
                'category': category,
                'models': category_schemas['models'],
                'enums': category_schemas['enums'],
            }

            if self.include_timestamp:
                schema_bundle['x-generated-on'] = self._current_timestamp()

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(schema_bundle, f, indent=2, sort_keys=False)

            generated_files[category] = output_file
            print(f"✅ Generated schema: {output_file}")

        # Write master index
        index_file = output_dir / "index.json"
        index_data = {
            '$schema': 'http://json-schema.org/draft-07/schema#',
            'title': 'Schema Index',
            'description': 'Index of all exported Pydantic schemas',
            'categories': list(categories.keys()),
            'total_models': len(self.processed_models),
            'total_enums': len(self.processed_enums),
        }

        if self.include_timestamp:
            index_data['x-generated-on'] = self._current_timestamp()

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2)

        generated_files['index'] = index_file
        print(f"✅ Generated index: {index_file}")

        return generated_files

    def _categorize_schemas(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Categorize schemas by domain (auth, users, courses, etc.)."""
        categories = {
            'auth': {'models': {}, 'enums': {}},
            'users': {'models': {}, 'enums': {}},
            'courses': {'models': {}, 'enums': {}},
            'organizations': {'models': {}, 'enums': {}},
            'roles': {'models': {}, 'enums': {}},
            'sso': {'models': {}, 'enums': {}},
            'tasks': {'models': {}, 'enums': {}},
            'examples': {'models': {}, 'enums': {}},
            'messages': {'models': {}, 'enums': {}},
            'common': {'models': {}, 'enums': {}},
        }

        # Categorize model schemas
        for model_name, schema in self.schemas.items():
            category = self._determine_category(model_name)
            categories[category]['models'][model_name] = schema

        # Categorize enum schemas
        for enum_name, schema in self.enum_schemas.items():
            category = self._determine_category(enum_name)
            categories[category]['enums'][enum_name] = schema

        return categories

    def _determine_category(self, name: str) -> str:
        """Determine the category for a model or enum based on its name."""
        name_lower = name.lower()

        if 'gitlab' in name_lower or 'deployment' in name_lower:
            return 'common'
        elif 'auth' in name_lower or 'login' in name_lower or 'token' in name_lower:
            return 'auth'
        elif 'user' in name_lower or 'account' in name_lower:
            return 'users'
        elif 'course' in name_lower:
            return 'courses'
        elif 'organization' in name_lower:
            return 'organizations'
        elif 'role' in name_lower or 'permission' in name_lower:
            return 'roles'
        elif 'sso' in name_lower or 'provider' in name_lower:
            return 'sso'
        elif 'task' in name_lower or 'job' in name_lower:
            return 'tasks'
        elif 'example' in name_lower:
            return 'examples'
        elif 'message' in name_lower:
            return 'messages'
        else:
            return 'common'


def main(output_dir: Path | None = None, include_timestamp: bool = False) -> Dict[str, Path]:
    """Main entry point for schema export."""
    backend_dir = Path(__file__).parent.parent
    src_dir = backend_dir.parent
    project_root = src_dir.parent

    if output_dir is None:
        output_dir = project_root / "frontend" / "src" / "types" / "schemas"

    scan_dirs = [
        backend_dir / "interface",
        backend_dir / "api",
        backend_dir / "tasks",
    ]

    print("🚀 Pydantic Schema Exporter")
    print("=" * 50)
    print(f"📂 Scanning directories:")
    for scan_dir in scan_dirs:
        print(f"  - {scan_dir}")
    print(f"📁 Output directory: {output_dir}")
    print("=" * 50)

    exporter = SchemaExporter(include_timestamp=include_timestamp)
    generated_files = exporter.export_all(scan_dirs, output_dir)

    print("=" * 50)
    print(f"✅ Exported {len(generated_files)} schema files")
    return generated_files


if __name__ == "__main__":
    main()
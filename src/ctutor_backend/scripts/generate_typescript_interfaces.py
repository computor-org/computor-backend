#!/usr/bin/env python3
"""
Generate TypeScript interfaces from Pydantic models.

This script scans Pydantic models in the backend and generates corresponding
TypeScript interfaces for use in the React frontend.
"""

import os
import sys
import ast
import importlib.util
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Union
from datetime import datetime
import json
import re

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # ctutor_backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))  # src

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from typing import get_origin, get_args
import inspect


class TypeScriptGenerator:
    """Generates TypeScript interfaces from Pydantic models."""
    
    def __init__(self):
        self.interfaces: Dict[str, str] = {}
        self.imports: Set[str] = set()
        self.processed_models: Set[str] = set()
        
        # Python to TypeScript type mappings
        self.type_map = {
            'str': 'string',
            'int': 'number',
            'float': 'number',
            'bool': 'boolean',
            'datetime': 'string',  # ISO string
            'date': 'string',      # ISO string
            'UUID': 'string',
            'Any': 'any',
            'None': 'null',
            'NoneType': 'null',
        }
    
    def python_type_to_typescript(self, py_type: Any) -> str:
        """Convert Python type annotation to TypeScript type."""
        # Handle None type
        if py_type is None or py_type is type(None):
            return 'null'
        
        # Get the origin type for generics
        origin = get_origin(py_type)
        
        # Handle Optional types
        if origin is Union:
            args = get_args(py_type)
            # Check if it's Optional (Union with None)
            if type(None) in args:
                non_none_args = [arg for arg in args if arg is not type(None)]
                if len(non_none_args) == 1:
                    return f"{self.python_type_to_typescript(non_none_args[0])} | null"
                else:
                    # Multiple non-None types
                    types = [self.python_type_to_typescript(arg) for arg in non_none_args]
                    return f"({' | '.join(types)}) | null"
            else:
                # Regular Union
                types = [self.python_type_to_typescript(arg) for arg in args]
                # Remove duplicate types
                unique_types = list(dict.fromkeys(types))
                if len(unique_types) == 1:
                    return unique_types[0]
                return ' | '.join(unique_types)
        
        # Handle List/list types
        if origin in (list, List):
            args = get_args(py_type)
            if args:
                item_type = self.python_type_to_typescript(args[0])
                return f"{item_type}[]"
            return 'any[]'
        
        # Handle Dict/dict types
        if origin in (dict, Dict):
            args = get_args(py_type)
            if args and len(args) >= 2:
                key_type = self.python_type_to_typescript(args[0])
                value_type = self.python_type_to_typescript(args[1])
                if key_type == 'string':
                    return f"Record<string, {value_type}>"
                else:
                    return f"{{ [key: {key_type}]: {value_type} }}"
            return 'Record<string, any>'
        
        # Handle literal types
        if hasattr(py_type, '__name__'):
            type_name = py_type.__name__
            
            # Check if it's a Pydantic model
            if inspect.isclass(py_type) and issubclass(py_type, BaseModel):
                # Add to imports if not already processed
                if type_name not in self.processed_models:
                    self.imports.add(type_name)
                return type_name
            
            # Map basic Python types
            if type_name in self.type_map:
                return self.type_map[type_name]
            
            # Default for unknown types
            return 'any'
        
        # Handle string representation of types
        if isinstance(py_type, str):
            if py_type in self.type_map:
                return self.type_map[py_type]
            # Assume it's a reference to another model
            self.imports.add(py_type)
            return py_type
        
        # Default fallback
        return 'any'
    
    def generate_interface(self, model_class: type[BaseModel]) -> str:
        """Generate TypeScript interface from a Pydantic model."""
        model_name = model_class.__name__
        
        # Skip if already processed
        if model_name in self.processed_models:
            return ""
        
        self.processed_models.add(model_name)
        
        # Start interface
        lines = []
        
        # Add JSDoc comment if model has docstring
        if model_class.__doc__:
            lines.append("/**")
            for line in model_class.__doc__.strip().split('\n'):
                lines.append(f" * {line.strip()}")
            lines.append(" */")
        
        lines.append(f"export interface {model_name} {{")
        
        # Process fields
        for field_name, field_info in model_class.model_fields.items():
            # Get field type
            field_type = field_info.annotation
            ts_type = self.python_type_to_typescript(field_type)
            
            # Check if field is optional
            is_optional = not field_info.is_required()
            
            # Add JSDoc for field description
            if field_info.description:
                lines.append(f"  /** {field_info.description} */")
            
            # Add field
            optional_marker = "?" if is_optional else ""
            lines.append(f"  {field_name}{optional_marker}: {ts_type};")
        
        lines.append("}")
        
        return '\n'.join(lines)
    
    def scan_directory(self, directory: Path, pattern: str = "*.py") -> List[type[BaseModel]]:
        """Scan directory for Pydantic models."""
        models = []
        
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

            # Try to import the module once so we can inspect classes (including nested)
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

            base_class_names = {
                'BaseModel', 'BaseDeployment', 'RepositoryConfig', 'GitLabConfigGet',
                'BaseEntityList', 'BaseEntityGet', 'BaseEntityCreate', 'BaseEntityUpdate',
                'OrganizationConfig', 'CourseFamilyConfig', 'CourseConfig',
                'HierarchicalOrganizationConfig', 'HierarchicalCourseFamilyConfig',
                'HierarchicalCourseConfig', 'ListQuery'
            }

            def process_class(node: ast.ClassDef, parent_chain: List[str]):
                current_chain = parent_chain + [node.name]

                inherits_base = False
                for base in node.bases:
                    base_name = ''
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr

                    if base_name in base_class_names:
                        inherits_base = True
                        break

                if inherits_base:
                    try:
                        attr = module
                        for name in current_chain:
                            if not hasattr(attr, name):
                                attr = None
                                break
                            attr = getattr(attr, name)

                        if attr and inspect.isclass(attr) and issubclass(attr, BaseModel):
                            models.append(attr)
                    except Exception as e:
                        print(f"Warning: Could not resolve {'.'.join(current_chain)} in {py_file}: {e}")

                for child in node.body:
                    if isinstance(child, ast.ClassDef):
                        process_class(child, current_chain)

            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    process_class(node, [])

        return models
    
    def generate_index_file(self, models: List[type[BaseModel]], module_name: str) -> str:
        """Generate index.ts file that exports all interfaces."""
        lines = []
        
        # Group models by their source file
        model_groups: Dict[str, List[str]] = {}
        
        for model in models:
            model_name = model.__name__
            # Use module name as group key
            group = module_name.lower()
            if group not in model_groups:
                model_groups[group] = []
            model_groups[group].append(model_name)
        
        # Generate exports
        for group, model_names in sorted(model_groups.items()):
            lines.append(f"// {group.title()} models")
            for model_name in sorted(model_names):
                lines.append(f"export type {{ {model_name} }} from './{group}';")
            lines.append("")
        
        return '\n'.join(lines).strip()
    
    def generate_all(self, scan_dirs: List[Path], output_dir: Path):
        """Generate TypeScript interfaces for all models found."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Dictionary to group models by category
        model_categories: Dict[str, List[type[BaseModel]]] = {
            'auth': [],
            'users': [],
            'courses': [],
            'organizations': [],
            'roles': [],
            'sso': [],
            'tasks': [],
            'examples': [],
            'messages': [],
            'common': [],
        }
        
        # Map model names to categories for import resolution
        model_to_category: Dict[str, str] = {}
        
        # Scan for models
        all_models = []
        for scan_dir in scan_dirs:
            if scan_dir.exists():
                models = self.scan_directory(scan_dir)
                all_models.extend(models)
        
        # Categorize models based on module name or class name
        for model in all_models:
            model_name = model.__name__.lower()
            module_name = model.__module__.lower() if hasattr(model, '__module__') else ''
            
            # Determine category
            category = 'common'  # default
            
            # Special handling for GitLab and deployment configs
            if 'gitlab' in model_name or 'deployment' in model_name or 'deployment' in module_name:
                category = 'common'
            elif 'auth' in module_name or 'auth' in model_name or 'login' in model_name or 'token' in model_name:
                category = 'auth'
            elif 'user' in module_name or 'user' in model_name or 'account' in model_name:
                category = 'users'
            elif 'course' in module_name or 'course' in model_name:
                category = 'courses'
            elif 'organization' in module_name or 'organization' in model_name:
                category = 'organizations'
            elif 'role' in module_name or 'role' in model_name or 'permission' in model_name:
                category = 'roles'
            elif 'sso' in module_name or 'provider' in model_name:
                category = 'sso'
            elif 'task' in module_name or 'task' in model_name or 'job' in model_name:
                category = 'tasks'
            elif 'example' in module_name or 'example' in model_name:
                category = 'examples'
            elif 'message' in module_name or 'message' in model_name:
                category = 'messages'
            
            model_categories[category].append(model)
            model_to_category[model.__name__] = category
        
        # Generate interfaces for each category
        generated_files = []
        
        for category, models in model_categories.items():
            if not models:
                continue
            
            # Reset for each category
            self.interfaces.clear()
            self.imports.clear()
            self.processed_models.clear()
            
            # Generate interfaces
            interfaces = []
            for model in models:
                interface = self.generate_interface(model)
                if interface:
                    interfaces.append(interface)
            
            if interfaces:
                # Create category file
                file_content = []
                
                # Add header
                file_content.append("/**")
                file_content.append(f" * Auto-generated TypeScript interfaces from Pydantic models")
                file_content.append(f" * Generated on: {datetime.now().isoformat()}")
                file_content.append(f" * Category: {category.title()}")
                file_content.append(" */")
                file_content.append("")
                
                # Add imports if needed
                if self.imports:
                    other_imports = []
                    for imp in sorted(self.imports):
                        # Check if this import is in our model mapping
                        if imp in model_to_category:
                            imp_category = model_to_category[imp]
                            if imp_category != category:
                                other_imports.append((imp, imp_category))
                        else:
                            # If not found in model mapping, try to find it
                            for other_cat, other_models in model_categories.items():
                                if other_cat != category and any(m.__name__ == imp for m in other_models):
                                    other_imports.append((imp, other_cat))
                                    break
                    
                    if other_imports:
                        # Group imports by category
                        imports_by_category: Dict[str, List[str]] = {}
                        for imp, cat in other_imports:
                            if cat not in imports_by_category:
                                imports_by_category[cat] = []
                            if imp not in imports_by_category[cat]:
                                imports_by_category[cat].append(imp)
                        
                        # Generate import statements
                        for cat in sorted(imports_by_category.keys()):
                            imports = sorted(imports_by_category[cat])
                            file_content.append(f"import type {{ {', '.join(imports)} }} from './{cat}';")
                        file_content.append("")
                
                # Add interfaces
                file_content.extend(interfaces)
                
                # Write file
                output_file = output_dir / f"{category}.ts"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write('\n\n'.join(file_content))
                
                generated_files.append(output_file)
                print(f"✅ Generated {output_file}")
        
        # Generate index file
        if generated_files:
            index_content = []
            index_content.append("/**")
            index_content.append(" * Auto-generated TypeScript interfaces from Pydantic models")
            index_content.append(f" * Generated on: {datetime.now().isoformat()}")
            index_content.append(" */")
            index_content.append("")
            
            for category in sorted(model_categories.keys()):
                if model_categories[category]:
                    index_content.append(f"export * from './{category}';")
            
            index_file = output_dir / "index.ts"
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(index_content))
            
            print(f"✅ Generated {index_file}")
        
        return generated_files


def main():
    """Main entry point."""
    # Determine paths
    backend_dir = Path(__file__).parent.parent  # ctutor_backend
    src_dir = backend_dir.parent  # src
    project_root = src_dir.parent  # computor-fullstack
    frontend_dir = project_root / "frontend"
    
    # Directories to scan for models
    scan_dirs = [
        backend_dir / "interface",  # Pydantic DTOs
        backend_dir / "api",        # API models
    ]
    
    # Output directory
    output_dir = frontend_dir / "src" / "types" / "generated"
    
    print("🚀 TypeScript Interface Generator")
    print("=" * 50)
    print(f"Scanning directories:")
    for scan_dir in scan_dirs:
        print(f"  - {scan_dir}")
    print(f"Output directory: {output_dir}")
    print("=" * 50)
    
    # Generate interfaces
    generator = TypeScriptGenerator()
    generated_files = generator.generate_all(scan_dirs, output_dir)
    
    print("=" * 50)
    print(f"✅ Generated {len(generated_files)} TypeScript files")
    
    # Generate a README for the generated files
    readme_content = f"""# Generated TypeScript Interfaces

This directory contains auto-generated TypeScript interfaces from Python Pydantic models.

**DO NOT EDIT THESE FILES MANUALLY** - They will be overwritten on the next generation.

## Generation

To regenerate these interfaces, run:

```bash
cd src
python ctutor_backend/scripts/generate_typescript_interfaces.py
```

## Categories

- **auth.ts** - Authentication related interfaces (login, tokens, etc.)
- **users.ts** - User and account interfaces
- **courses.ts** - Course related interfaces
- **organizations.ts** - Organization interfaces
- **roles.ts** - Roles and permissions interfaces
- **sso.ts** - SSO provider interfaces
- **tasks.ts** - Task and job interfaces
- **messages.ts** - Messaging and discussion interfaces
- **examples.ts** - Example and template interfaces
- **common.ts** - Common/shared interfaces

## Usage

Import the interfaces in your TypeScript code:

```typescript
import {{ User, Account }} from '@/types/generated/users';
import {{ LoginRequest, AuthResponse }} from '@/types/generated/auth';
```

Generated on: {datetime.now().isoformat()}
"""
    
    readme_file = output_dir / "README.md"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ Generated {readme_file}")
    print("\n🎯 You can now use these interfaces in your React app!")


if __name__ == "__main__":
    main()

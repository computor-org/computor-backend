#!/usr/bin/env python3
"""
Generate Python HTTP clients from EntityInterface definitions.
Similar to TypeScript client generator but for Python.
"""

import inspect
import pkgutil
from pathlib import Path
from typing import Type, List, Set, Optional
from datetime import datetime


def discover_interfaces() -> List[tuple[str, Type]]:
    """Discover all EntityInterface subclasses from computor_backend.interfaces."""
    try:
        import computor_backend.interfaces as backend_interfaces
        from computor_backend.interfaces.base import BackendEntityInterface
    except ImportError as e:
        print(f"Error: Could not import backend interfaces: {e}")
        print("Make sure you're running from the src directory")
        return []

    interfaces = []
    seen_names = set()

    # Get all interface classes from the backend.interfaces module
    for name, obj in inspect.getmembers(backend_interfaces, inspect.isclass):
        try:
            if (
                issubclass(obj, BackendEntityInterface) and
                obj is not BackendEntityInterface and
                hasattr(obj, 'endpoint') and
                obj.endpoint and
                name not in seen_names
            ):
                # Map back to types module for DTO imports
                # e.g., UserInterface -> computor_types.users
                interface_base_name = name.replace("Interface", "").lower()
                # Convert CamelCase to snake_case
                import re
                snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', interface_base_name).lower()
                module_name = f"computor_types.{snake_case}s" if not snake_case.endswith('s') else f"computor_types.{snake_case}"

                interfaces.append((module_name, obj))
                seen_names.add(name)

        except Exception as e:
            print(f"Warning: Could not process {name}: {e}")
            continue

    # Sort by interface name for deterministic output
    interfaces.sort(key=lambda x: x[1].__name__)
    return interfaces


def generate_client_class(module_name: str, interface: Type) -> str:
    """Generate a client class for an EntityInterface."""

    class_name = interface.__name__.replace("Interface", "Client")
    endpoint = interface.endpoint
    module_base_name = module_name.split('.')[-1]

    # Determine what operations are supported
    has_create = interface.create is not None
    has_get = interface.get is not None
    has_list = getattr(interface, 'list', None) is not None
    has_update = interface.update is not None
    has_query = interface.query is not None

    # Collect imports
    imports = set()
    if has_get:
        imports.add(interface.get.__name__)
    if has_create:
        imports.add(interface.create.__name__)
    if has_update:
        imports.add(interface.update.__name__)
    if has_query:
        imports.add(interface.query.__name__)

    # Build the client class code
    lines = [
        '"""Auto-generated client for ' + interface.__name__ + '."""',
        '',
        'from typing import Optional, List',
        'import httpx',
        '',
        f'from computor_types.{module_base_name} import (',
    ]

    # Add imports
    for imp in sorted(imports):
        lines.append(f'    {imp},')
    lines.append(')')

    lines.extend([
        'from computor_client.base import BaseEndpointClient',
        '',
        '',
        f'class {class_name}(BaseEndpointClient):',
        f'    """Client for {endpoint} endpoint."""',
        '',
        '    def __init__(self, client: httpx.AsyncClient):',
        '        super().__init__(',
        '            client=client,',
        f'            base_path="/{endpoint}",',
        f'            response_model={interface.get.__name__ if has_get else "None"},',
    ])

    if has_create:
        lines.append(f'            create_model={interface.create.__name__},')
    if has_update:
        lines.append(f'            update_model={interface.update.__name__},')
    if has_query:
        lines.append(f'            query_model={interface.query.__name__},')

    lines.append('        )')

    return '\n'.join(lines)


def generate_init_file(interfaces: List[tuple[str, Type]]) -> str:
    """Generate __init__.py for generated clients."""

    lines = [
        '"""Auto-generated client imports."""',
        '',
        '# This file is auto-generated. Do not edit manually.',
        '',
    ]

    # Import all generated clients
    for module_name, interface in interfaces:
        class_name = interface.__name__.replace("Interface", "Client")
        module_base_name = module_name.split('.')[-1]
        lines.append(f'from .{module_base_name} import {class_name}')

    lines.append('')
    lines.append('__all__ = [')

    for _, interface in interfaces:
        class_name = interface.__name__.replace("Interface", "Client")
        lines.append(f'    "{class_name}",')

    lines.append(']')

    return '\n'.join(lines)


def main(output_dir: Optional[Path] = None, clean: bool = False, include_timestamp: bool = False):
    """Main generator entry point."""

    if output_dir is None:
        # Default output directory
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent.parent.parent
        output_dir = project_root / "computor-client" / "src" / "computor_client" / "generated"

    # Verify output directory is writable
    print("🐍 Generating Python API clients...")
    print(f"📂 Output directory: {output_dir}")
    print(f"📂 Output directory (absolute): {output_dir.absolute()}")
    print(f"📂 Output directory exists: {output_dir.exists()}")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Output directory created/verified")
    except Exception as e:
        print(f"❌ Failed to create output directory: {e}")
        return []

    # Test write permissions
    test_file = output_dir / ".write_test"
    try:
        test_file.write_text("test")
        test_file.unlink()
        print(f"✅ Output directory is writable")
    except Exception as e:
        print(f"❌ Output directory is not writable: {e}")
        return []

    print()

    # Clean existing files if requested
    if clean:
        for file in output_dir.glob("*.py"):
            if file.name != "__init__.py":
                try:
                    file.unlink()
                    print(f"🧹 Removed {file.name}")
                except Exception as e:
                    print(f"❌ Failed to remove {file.name}: {e}")

    # Discover interfaces
    interfaces = discover_interfaces()

    if not interfaces:
        print("❌ No interfaces found!")
        return []

    print(f"📋 Found {len(interfaces)} interfaces")
    print()

    generated_files = []
    failed_files = []

    # Group interfaces by module name to handle multiple interfaces per file
    from collections import defaultdict
    interfaces_by_module = defaultdict(list)
    for module_name, interface in interfaces:
        module_base_name = module_name.split('.')[-1]
        interfaces_by_module[module_base_name].append((module_name, interface))

    print(f"📦 Grouped into {len(interfaces_by_module)} modules")
    print()

    # Generate client for each module (may contain multiple interfaces)
    for module_base_name, module_interfaces in sorted(interfaces_by_module.items()):
        output_file = output_dir / f"{module_base_name}.py"

        try:
            # Generate all client classes for this module
            client_classes = []
            for module_name, interface in module_interfaces:
                try:
                    client_code = generate_client_class(module_name, interface)
                    client_classes.append(client_code)
                except Exception as e:
                    print(f"⚠️  Failed to generate class for {interface.__name__}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            if not client_classes:
                print(f"⚠️  No classes generated for {module_base_name}, skipping")
                continue

            # Combine all classes for this module
            full_code = '\n\n'.join(client_classes)

            # Write the file
            print(f"📝 Writing {output_file} ({len(full_code)} bytes)...")
            output_file.write_text(full_code + '\n')

            # Immediately verify the file exists and has content
            if not output_file.exists():
                print(f"❌ ERROR: File {output_file} does not exist after write!")
                failed_files.append(module_base_name)
                continue

            file_size = output_file.stat().st_size
            if file_size == 0:
                print(f"❌ ERROR: File {output_file} exists but is empty!")
                failed_files.append(module_base_name)
                continue

            # Read back to verify content
            read_back = output_file.read_text()
            if len(read_back) != len(full_code) + 1:  # +1 for trailing newline
                print(f"⚠️  WARNING: File size mismatch! Expected {len(full_code) + 1}, got {len(read_back)}")

            generated_files.append(output_file)

            if len(module_interfaces) > 1:
                print(f"✅ Generated {output_file.name} ({len(module_interfaces)} clients, {file_size} bytes)")
            else:
                print(f"✅ Generated {output_file.name} ({file_size} bytes)")

        except Exception as e:
            print(f"❌ Failed to generate {module_base_name}: {e}")
            import traceback
            traceback.print_exc()
            failed_files.append(module_base_name)

    print()

    # Generate __init__.py
    try:
        init_code = generate_init_file(interfaces)
        init_file = output_dir / "__init__.py"
        print(f"📝 Writing {init_file}...")
        init_file.write_text(init_code + '\n')

        if init_file.exists():
            init_size = init_file.stat().st_size
            print(f"✅ Generated {init_file.name} ({init_size} bytes)")
        else:
            print(f"❌ ERROR: {init_file} does not exist after write!")
    except Exception as e:
        print(f"❌ Failed to generate __init__.py: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("="*60)
    print(f"📊 Generation Summary:")
    print(f"   Total interfaces: {len(interfaces)}")
    print(f"   Modules: {len(interfaces_by_module)}")
    print(f"   Successfully generated: {len(generated_files)}")
    print(f"   Failed: {len(failed_files)}")
    if failed_files:
        print(f"   Failed modules: {', '.join(failed_files)}")
    print("="*60)

    # Final verification - list all files in output directory
    print()
    print("📂 Final directory contents:")
    all_files = sorted(output_dir.glob("*.py"))
    for f in all_files:
        size = f.stat().st_size
        print(f"   {f.name} ({size} bytes)")
    print(f"   Total files: {len(all_files)}")
    print("="*60)

    return generated_files


if __name__ == "__main__":
    main()

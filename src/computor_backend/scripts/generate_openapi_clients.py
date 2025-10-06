#!/usr/bin/env python3
"""
Generate Python HTTP clients from FastAPI OpenAPI specification.
This captures ALL endpoints including custom non-CRUD operations.
"""

import json
import httpx
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict
import re


class OpenAPIClientGenerator:
    """Generate Python clients from OpenAPI spec."""

    def __init__(self, openapi_spec: Dict[str, Any]):
        self.spec = openapi_spec
        self.paths = openapi_spec.get('paths', {})
        self.components = openapi_spec.get('components', {})
        self.schemas = self.components.get('schemas', {})

    def _normalize_path(self, path: str) -> str:
        """Convert OpenAPI path to Python-safe name."""
        # Remove leading slash
        path = path.lstrip('/')
        # Replace path parameters with placeholder
        path = re.sub(r'\{[^}]+\}', 'id', path)
        # Replace slashes and hyphens with underscores
        path = path.replace('/', '_').replace('-', '_')
        return path

    def _extract_base_path(self, path: str) -> str:
        """Extract base path (first segment) from endpoint path."""
        parts = path.lstrip('/').split('/')
        return parts[0] if parts else ""

    def _get_method_name(self, method: str, path: str, operation: Dict) -> str:
        """Generate method name from HTTP method and path."""
        operation_id = operation.get('operationId', '')

        if operation_id:
            # Use operation ID if available
            parts = operation_id.split('_')
            # Remove common prefixes
            if parts and parts[0] in ['get', 'post', 'put', 'patch', 'delete']:
                parts = parts[1:]
            return '_'.join(parts)

        # Generate from path
        path_parts = [p for p in path.split('/') if p and not p.startswith('{')]

        if method.lower() == 'get':
            if '{' in path:
                return 'get_' + '_'.join(path_parts[-2:]) if len(path_parts) > 1 else 'get'
            return 'list_' + '_'.join(path_parts[-1:]) if path_parts else 'list'
        elif method.lower() == 'post':
            return 'create_' + '_'.join(path_parts[-1:]) if path_parts else 'create'
        elif method.lower() == 'put':
            return 'replace_' + '_'.join(path_parts[-2:]) if len(path_parts) > 1 else 'replace'
        elif method.lower() == 'patch':
            return 'update_' + '_'.join(path_parts[-2:]) if len(path_parts) > 1 else 'update'
        elif method.lower() == 'delete':
            return 'delete_' + '_'.join(path_parts[-2:]) if len(path_parts) > 1 else 'delete'

        return method.lower() + '_' + '_'.join(path_parts)

    def _extract_path_params(self, path: str) -> List[str]:
        """Extract path parameter names from path."""
        return re.findall(r'\{([^}]+)\}', path)

    def _get_response_type(self, operation: Dict) -> Optional[str]:
        """Extract response type from operation."""
        responses = operation.get('responses', {})
        success_response = responses.get('200') or responses.get('201')

        if not success_response:
            return None

        content = success_response.get('content', {})
        json_content = content.get('application/json', {})
        schema = json_content.get('schema', {})

        # Handle array responses
        if schema.get('type') == 'array':
            items = schema.get('items', {})
            ref = items.get('$ref', '')
            if ref:
                return f"List[{ref.split('/')[-1]}]"
            return "List[Dict[str, Any]]"

        # Handle object responses
        ref = schema.get('$ref', '')
        if ref:
            return ref.split('/')[-1]

        return "Dict[str, Any]"

    def _get_request_body_type(self, operation: Dict) -> Optional[str]:
        """Extract request body type from operation."""
        request_body = operation.get('requestBody', {})
        content = request_body.get('content', {})
        json_content = content.get('application/json', {})
        schema = json_content.get('schema', {})

        ref = schema.get('$ref', '')
        if ref:
            return ref.split('/')[-1]

        return None

    def _determine_client_type(self, base_path: str, endpoints: List[Dict]) -> str:
        """Determine which base class to use for this client."""
        # Check for role-based views
        if base_path in ['students', 'tutors', 'lecturers']:
            return 'RoleBasedViewClient'

        # Check for file operations
        has_upload = any('upload' in e['path'].lower() for e in endpoints)
        has_download = any('download' in e['path'].lower() for e in endpoints)
        if has_upload or has_download:
            return 'FileOperationClient'

        # Check for task operations
        has_submit = any('submit' in e['path'].lower() for e in endpoints)
        has_status = any('status' in e['path'].lower() for e in endpoints)
        has_cancel = any('cancel' in e['path'].lower() for e in endpoints)
        if (has_submit or has_status or has_cancel) and base_path == 'tasks':
            return 'TaskClient'

        # Check for auth operations
        if base_path == 'auth':
            return 'AuthenticationClient'

        # Check for standard CRUD
        methods = set()
        for endpoint in endpoints:
            methods.add(endpoint['method'])

        has_crud = 'GET' in methods or 'POST' in methods
        if has_crud and len(methods) <= 5:
            return 'BaseEndpointClient'

        # Default to custom action client
        return 'CustomActionClient'

    def group_endpoints_by_base_path(self) -> Dict[str, List[Dict]]:
        """Group endpoints by their base path."""
        groups = defaultdict(list)

        for path, methods in self.paths.items():
            base_path = self._extract_base_path(path)

            for method, operation in methods.items():
                if method.lower() not in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
                    continue

                endpoint_info = {
                    'path': path,
                    'method': method.upper(),
                    'operation': operation,
                    'method_name': self._get_method_name(method, path, operation),
                    'path_params': self._extract_path_params(path),
                    'response_type': self._get_response_type(operation),
                    'request_body_type': self._get_request_body_type(operation),
                }

                groups[base_path].append(endpoint_info)

        return dict(groups)

    def generate_method(self, endpoint: Dict) -> str:
        """Generate a single method for an endpoint."""
        method_name = endpoint['method_name']
        http_method = endpoint['method']
        path = endpoint['path']
        path_params = endpoint['path_params']
        response_type = endpoint['response_type'] or 'Any'
        request_body = endpoint['request_body_type']
        operation = endpoint['operation']

        # Build method signature
        params = []
        for param in path_params:
            params.append(f"{param}: str")

        if request_body:
            params.append(f"payload: {request_body}")

        # Add query parameters from operation
        for param in operation.get('parameters', []):
            if param.get('in') == 'query':
                param_name = param.get('name')
                param_required = param.get('required', False)
                param_type = 'str'  # Simplified
                if param_required:
                    params.append(f"{param_name}: {param_type}")
                else:
                    params.append(f"{param_name}: Optional[{param_type}] = None")

        params_str = ', '.join(params)

        # Build docstring
        summary = operation.get('summary', '')
        description = operation.get('description', '')
        doc = summary or description or f"{http_method} {path}"

        # Build method body
        lines = [
            f'    async def {method_name}(self, {params_str}) -> {response_type}:',
            f'        """{doc}"""',
        ]

        # Build path with parameters
        path_with_params = path
        for param in path_params:
            path_with_params = path_with_params.replace(f'{{{param}}}', f'{{{param}}}')

        # Determine the request type
        if http_method == 'GET':
            query_params = [p.get('name') for p in operation.get('parameters', []) if p.get('in') == 'query']
            if query_params:
                lines.append(f'        params = {{k: v for k, v in locals().items() if k in {query_params} and v is not None}}')
                lines.append(f'        return await self._request("GET", "{path_with_params}", params=params)')
            else:
                lines.append(f'        return await self._request("GET", "{path_with_params}")')

        elif http_method == 'POST':
            if request_body:
                lines.append(f'        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload')
                lines.append(f'        return await self._request("POST", "{path_with_params}", json=json_data)')
            else:
                lines.append(f'        return await self._request("POST", "{path_with_params}")')

        elif http_method in ['PUT', 'PATCH']:
            if request_body:
                lines.append(f'        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload')
                lines.append(f'        return await self._request("{http_method}", "{path_with_params}", json=json_data)')
            else:
                lines.append(f'        return await self._request("{http_method}", "{path_with_params}")')

        elif http_method == 'DELETE':
            lines.append(f'        return await self._request("DELETE", "{path_with_params}")')

        return '\n'.join(lines)

    def generate_client_class(self, base_path: str, endpoints: List[Dict]) -> str:
        """Generate a complete client class for a base path."""
        class_name = ''.join(word.capitalize() for word in base_path.split('-')) + 'Client'
        base_class = self._determine_client_type(base_path, endpoints)

        # Collect unique types needed
        types_needed = set()
        for endpoint in endpoints:
            if endpoint['response_type']:
                # Extract base type name (remove List[])
                type_name = endpoint['response_type'].replace('List[', '').replace(']', '')
                if type_name not in ['Any', 'Dict[str, Any]', 'None']:
                    types_needed.add(type_name)
            if endpoint['request_body_type']:
                types_needed.add(endpoint['request_body_type'])

        # Build imports
        lines = [
            f'"""Auto-generated client for /{base_path} endpoints."""',
            '',
            'from typing import Optional, List, Dict, Any',
            'import httpx',
            '',
        ]

        # Add type imports if needed
        if types_needed:
            # Group by module (simplified - assumes types are in computor_types)
            lines.append('# Import Pydantic models (adjust module paths as needed)')
            for type_name in sorted(types_needed):
                lines.append(f'# from computor_types import {type_name}')
            lines.append('')

        lines.extend([
            f'from computor_client.advanced_base import {base_class}',
            '',
            '',
            f'class {class_name}({base_class}):',
            f'    """Client for /{base_path} endpoints."""',
            '',
            '    def __init__(self, client: httpx.AsyncClient):',
            '        super().__init__(',
            '            client=client,',
            f'            base_path="/{base_path}",',
            '        )',
            '',
        ])

        # Generate methods
        for endpoint in endpoints:
            try:
                method_code = self.generate_method(endpoint)
                lines.append(method_code)
                lines.append('')
            except Exception as e:
                print(f"⚠️  Failed to generate method {endpoint['method_name']}: {e}")
                continue

        return '\n'.join(lines)


def fetch_openapi_spec(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Fetch OpenAPI specification from running server."""
    try:
        response = httpx.get(f"{base_url}/openapi.json", timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Failed to fetch OpenAPI spec from {base_url}: {e}")
        print(f"💡 Make sure the backend server is running at {base_url}")
        raise


def main(
    output_dir: Optional[Path] = None,
    base_url: str = "http://localhost:8000",
    save_spec: bool = True,
):
    """Main generator entry point."""

    if output_dir is None:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent.parent
        output_dir = project_root / "computor-client" / "src" / "computor_client" / "openapi_generated"

    print("🌐 Generating Python API clients from OpenAPI spec...")
    print(f"📂 Output directory: {output_dir}")
    print(f"🔗 API base URL: {base_url}")
    print()

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch OpenAPI spec
    print("📥 Fetching OpenAPI specification...")
    spec = fetch_openapi_spec(base_url)
    print(f"✅ Fetched spec: {spec.get('info', {}).get('title', 'Unknown')} v{spec.get('info', {}).get('version', 'Unknown')}")
    print()

    # Save spec for reference
    if save_spec:
        spec_file = output_dir / "openapi_spec.json"
        spec_file.write_text(json.dumps(spec, indent=2))
        print(f"💾 Saved OpenAPI spec to {spec_file}")
        print()

    # Initialize generator
    generator = OpenAPIClientGenerator(spec)

    # Group endpoints
    print("📊 Analyzing endpoints...")
    endpoint_groups = generator.group_endpoints_by_base_path()
    print(f"✅ Found {len(endpoint_groups)} endpoint groups")
    print()

    # Generate clients
    generated_files = []
    failed = []

    for base_path, endpoints in sorted(endpoint_groups.items()):
        if not base_path:
            continue

        try:
            print(f"📝 Generating client for /{base_path} ({len(endpoints)} endpoints)...")

            client_code = generator.generate_client_class(base_path, endpoints)

            # Write file
            filename = base_path.replace('-', '_') + '_client.py'
            output_file = output_dir / filename
            output_file.write_text(client_code)

            generated_files.append(filename)
            print(f"✅ Generated {filename}")

        except Exception as e:
            print(f"❌ Failed to generate client for /{base_path}: {e}")
            import traceback
            traceback.print_exc()
            failed.append(base_path)

    print()

    # Generate __init__.py
    print("📝 Generating __init__.py...")
    init_lines = [
        '"""Auto-generated clients from OpenAPI specification."""',
        '',
        '# This file is auto-generated from FastAPI OpenAPI spec',
        '',
    ]

    for filename in sorted(generated_files):
        module_name = filename.replace('.py', '')
        class_name = ''.join(word.capitalize() for word in module_name.replace('_client', '').split('_')) + 'Client'
        init_lines.append(f'from .{module_name} import {class_name}')

    init_lines.append('')
    init_lines.append('__all__ = [')
    for filename in sorted(generated_files):
        module_name = filename.replace('.py', '')
        class_name = ''.join(word.capitalize() for word in module_name.replace('_client', '').split('_')) + 'Client'
        init_lines.append(f'    "{class_name}",')
    init_lines.append(']')

    init_file = output_dir / '__init__.py'
    init_file.write_text('\n'.join(init_lines))
    print(f"✅ Generated __init__.py")
    print()

    # Summary
    print("="*60)
    print(f"📊 Generation Summary:")
    print(f"   Total endpoint groups: {len(endpoint_groups)}")
    print(f"   Successfully generated: {len(generated_files)}")
    print(f"   Failed: {len(failed)}")
    if failed:
        print(f"   Failed groups: {', '.join(failed)}")
    print("="*60)

    return generated_files


if __name__ == "__main__":
    import sys

    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    main(base_url=base_url)

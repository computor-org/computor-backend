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
        """Generate clean Pythonic method name from HTTP method and path."""
        http_method = method.lower()

        # Remove leading slash
        path = path.lstrip('/')

        # Split by slash
        segments = path.split('/')

        # Process each segment
        clean_segments = []
        for i, segment in enumerate(segments):
            # Skip empty segments
            if not segment:
                continue

            # Handle path parameters like {id}, {course_id}, etc.
            if segment.startswith('{') and segment.endswith('}'):
                param_name = segment[1:-1]
                # Only add "by_{param}" for the main resource ID, not for nested IDs
                if param_name == 'id':
                    clean_segments.append('by_id')
                elif i == len(segments) - 1:  # Last segment is a path param
                    clean_segments.append(f'by_{param_name}')
                # Skip intermediate path params, they're implied
                continue

            # Convert kebab-case to snake_case
            segment = segment.replace('-', '_')

            # Skip plural 's' at the end for single resource operations (GET/PATCH/DELETE with ID)
            if segment.endswith('s') and ('{' in path or http_method in ['patch', 'delete']):
                # This is a specific resource operation, use singular
                if segment.endswith('ies'):
                    # families -> family, repositories -> repository
                    segment = segment[:-3] + 'y'
                elif segment.endswith('ses'):
                    # courses -> course (but 'ses' -> 'se')
                    segment = segment[:-2]
                else:
                    segment = segment[:-1]  # Remove trailing 's'

            clean_segments.append(segment)

        # Join segments
        method_name = '_'.join(clean_segments)

        # Add HTTP method prefix
        return f"{http_method}_{method_name}"

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

    def generate_method(self, endpoint: Dict, base_path: str) -> str:
        """Generate a single method for an endpoint."""
        method_name = endpoint['method_name']
        http_method = endpoint['method']
        full_path = endpoint['path']
        path_params = endpoint['path_params']
        response_type = endpoint['response_type'] or 'Any'
        request_body = endpoint['request_body_type']
        operation = endpoint['operation']

        # Extract relative path by removing base_path prefix
        # If path is /course-groups/123, and base_path is /course-groups, we want just /123
        # If path is /course-groups, and base_path is /course-groups, we want empty string
        base_path_normalized = f"/{base_path}"
        if full_path == base_path_normalized:
            path = ""  # Root path of the resource
        elif full_path.startswith(base_path_normalized + "/"):
            path = full_path[len(base_path_normalized):]  # Remove base_path, keep the /
        else:
            path = full_path  # Fallback to full path

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
        doc = summary or description or f"{http_method} {full_path}"

        # Build method body
        lines = [
            f'    async def {method_name}(self, {params_str}) -> {response_type}:',
            f'        """{doc}"""',
        ]

        # Build path with parameters - use f-string if there are path params
        path_with_params = path
        if path_params:
            # Use f-string for path interpolation
            path_str = f'f"{path}"'
        else:
            # Regular string
            path_str = f'"{path}"'

        # Helper to parse response
        def add_response_parsing(lines, response_type):
            """Add response parsing logic."""
            if not response_type or response_type == 'Any':
                return

            # Check if it's a List type
            if response_type.startswith('List['):
                inner_type = response_type[5:-1]  # Extract type from List[Type]
                lines.append(f'        if isinstance(data, list):')
                lines.append(f'            return [{inner_type}.model_validate(item) for item in data]')
                lines.append(f'        return data')
            else:
                lines.append(f'        if data:')
                lines.append(f'            return {response_type}.model_validate(data)')
                lines.append(f'        return data')

        # Determine the request type
        if http_method == 'GET':
            query_params = [p.get('name') for p in operation.get('parameters', []) if p.get('in') == 'query']
            if query_params:
                lines.append(f'        params = {{k: v for k, v in locals().items() if k in {query_params} and v is not None}}')
                lines.append(f'        data = await self._request("GET", {path_str}, params=params)')
            else:
                lines.append(f'        data = await self._request("GET", {path_str})')
            add_response_parsing(lines, response_type)

        elif http_method == 'POST':
            if request_body:
                lines.append(f'        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload')
                lines.append(f'        data = await self._request("POST", {path_str}, json=json_data)')
            else:
                lines.append(f'        data = await self._request("POST", {path_str})')
            add_response_parsing(lines, response_type)

        elif http_method in ['PUT', 'PATCH']:
            if request_body:
                lines.append(f'        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload')
                lines.append(f'        data = await self._request("{http_method}", {path_str}, json=json_data)')
            else:
                lines.append(f'        data = await self._request("{http_method}", {path_str})')
            add_response_parsing(lines, response_type)

        elif http_method == 'DELETE':
            lines.append(f'        data = await self._request("DELETE", {path_str})')
            add_response_parsing(lines, response_type)

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
            # Group types by module
            module_types = {}
            for type_name in sorted(types_needed):
                module = SCHEMA_TO_MODULE_MAP.get(type_name, 'unknown')
                if module != 'unknown':
                    if module not in module_types:
                        module_types[module] = []
                    module_types[module].append(type_name)
            
            # Generate grouped imports
            for module in sorted(module_types.keys()):
                types = sorted(set(module_types[module]))
                if len(types) == 1:
                    lines.append(f'from computor_types.{module} import {types[0]}')
                else:
                    lines.append(f'from computor_types.{module} import (')
                    for t in types:
                        lines.append(f'    {t},')
                    lines.append(')')
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

        # Add CRUD method overrides that delegate to generated methods
        # Find the generated method names for standard CRUD operations
        post_method = None
        get_list_method = None
        get_by_id_method = None
        patch_method = None
        delete_method = None

        for endpoint in endpoints:
            method_name = endpoint['method_name']
            http_method = endpoint['method']
            path = endpoint['path']
            base_path_normalized = f"/{base_path}"

            # POST to root = create
            if http_method == 'POST' and path == base_path_normalized:
                post_method = method_name
            # GET to root = list
            elif http_method == 'GET' and path == base_path_normalized:
                get_list_method = method_name
            # GET to /{id} = get by id
            elif http_method == 'GET' and '/{' in path and path.count('/') == path.count('{'):
                get_by_id_method = method_name
            # PATCH to /{id} = update
            elif http_method == 'PATCH' and '/{' in path:
                patch_method = method_name
            # DELETE to /{id} = delete
            elif http_method == 'DELETE' and '/{' in path:
                delete_method = method_name

        # Generate CRUD override methods
        if post_method:
            lines.extend([
                '    async def create(self, payload):'  ,
                '        """Create a new entity (delegates to generated POST method)."""',
                f'        return await self.{post_method}(payload)',
                '',
            ])

        if get_list_method:
            lines.extend([
                '    async def list(self, query=None):',
                '        """List entities (delegates to generated GET method)."""',
                f'        if query:',
                f'            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query',
                f'            return await self.{get_list_method}(**params)',
                f'        return await self.{get_list_method}()',
                '',
            ])

        if get_by_id_method:
            lines.extend([
                '    async def get(self, id: str):',
                '        """Get entity by ID (delegates to generated GET method)."""',
                f'        return await self.{get_by_id_method}(id)',
                '',
            ])

        if patch_method:
            lines.extend([
                '    async def update(self, id: str, payload):',
                '        """Update entity (delegates to generated PATCH method)."""',
                f'        return await self.{patch_method}(id, payload)',
                '',
            ])

        if delete_method:
            lines.extend([
                '    async def delete(self, id: str):',
                '        """Delete entity (delegates to generated DELETE method)."""',
                f'        return await self.{delete_method}(id)',
                '',
            ])

        # Generate methods
        for endpoint in endpoints:
            try:
                method_code = self.generate_method(endpoint, base_path)
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
        project_root = script_dir.parent.parent.parent.parent
        output_dir = project_root / "computor-client" / "src" / "computor_client" / "generated"

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


# Valid SCHEMA_TO_MODULE_MAP - only types that exist in computor-types
# Auto-generated from OpenAPI spec and computor-types index
SCHEMA_TO_MODULE_MAP = {
    'AccountCreate': 'accounts',
    'AccountGet': 'accounts',
    'AccountList': 'accounts',
    'AccountUpdate': 'accounts',
    'AssignExampleRequest': 'deployment',
    'BucketCreate': 'storage',
    'BucketInfo': 'storage',
    'CourseContentCreate': 'course_contents',
    'CourseContentDeploymentGet': 'deployment',
    'CourseContentDeploymentList': 'deployment',
    'CourseContentGet': 'course_contents',
    'CourseContentKindCreate': 'course_content_kind',
    'CourseContentKindGet': 'course_content_kind',
    'CourseContentKindList': 'course_content_kind',
    'CourseContentKindUpdate': 'course_content_kind',
    'CourseContentLecturerGet': 'lecturer_course_contents',
    'CourseContentLecturerList': 'lecturer_course_contents',
    'CourseContentList': 'course_contents',
    'CourseContentProperties': 'course_contents',
    'CourseContentPropertiesGet': 'course_contents',
    'CourseContentRepositoryLecturerGet': 'lecturer_course_contents',
    'CourseContentStudentGet': 'student_course_contents',
    'CourseContentStudentList': 'student_course_contents',
    'CourseContentTypeCreate': 'course_content_types',
    'CourseContentTypeGet': 'course_content_types',
    'CourseContentTypeList': 'course_content_types',
    'CourseContentTypeUpdate': 'course_content_types',
    'CourseContentUpdate': 'course_contents',
    'CourseCreate': 'courses',
    'CourseExecutionBackendCreate': 'course_execution_backends',
    'CourseExecutionBackendGet': 'course_execution_backends',
    'CourseExecutionBackendList': 'course_execution_backends',
    'CourseFamilyCreate': 'course_families',
    'CourseFamilyGet': 'course_families',
    'CourseFamilyList': 'course_families',
    'CourseFamilyProperties': 'course_families',
    'CourseFamilyPropertiesGet': 'course_families',
    'CourseFamilyTaskRequest': 'system',
    'CourseFamilyUpdate': 'course_families',
    'CourseGet': 'courses',
    'CourseGroupCreate': 'course_groups',
    'CourseGroupGet': 'course_groups',
    'CourseGroupList': 'course_groups',
    'CourseGroupUpdate': 'course_groups',
    'CourseList': 'courses',
    'CommentCreate': 'course_member_comments',
    'CommentUpdate': 'course_member_comments',
    'CourseMemberCommentList': 'course_member_comments',
    'CourseMemberCreate': 'course_members',
    'CourseMemberGet': 'course_members',
    'CourseMemberGitLabConfig': 'course_members',
    'CourseMemberList': 'course_members',
    'CourseMemberProperties': 'course_members',
    'CourseMemberProviderAccountUpdate': 'course_member_accounts',
    'CourseMemberReadinessStatus': 'course_member_accounts',
    'CourseMemberUpdate': 'course_members',
    'CourseMemberValidationRequest': 'course_member_accounts',
    'CourseProperties': 'courses',
    'CoursePropertiesGet': 'courses',
    'CourseRoleGet': 'course_roles',
    'CourseRoleList': 'course_roles',
    'CourseStudentGet': 'student_courses',
    'CourseStudentList': 'student_courses',
    'CourseStudentRepository': 'student_courses',
    'CourseTaskRequest': 'system',
    'CourseTutorGet': 'tutor_courses',
    'CourseTutorList': 'tutor_courses',
    'CourseTutorRepository': 'tutor_courses',
    'CourseUpdate': 'courses',
    'DeploymentHistoryGet': 'deployment',
    'DeploymentSummary': 'deployment',
    'DeploymentWithHistory': 'deployment',
    'ExampleDependencyCreate': 'example',
    'ExampleDependencyGet': 'example',
    'ExampleDownloadResponse': 'example',
    'ExampleFileSet': 'example',
    'ExampleGet': 'example',
    'ExampleList': 'example',
    'ExampleRepositoryCreate': 'example',
    'ExampleRepositoryGet': 'example',
    'ExampleRepositoryList': 'example',
    'ExampleRepositoryUpdate': 'example',
    'ExampleUploadRequest': 'example',
    'ExampleVersionCreate': 'example',
    'ExampleVersionGet': 'example',
    'ExampleVersionList': 'example',
    'ExecutionBackendCreate': 'execution_backends',
    'ExecutionBackendGet': 'execution_backends',
    'ExecutionBackendList': 'execution_backends',
    'ExecutionBackendUpdate': 'execution_backends',
    'ExtensionMetadata': 'extensions',
    'ExtensionPublishResponse': 'extensions',
    'ExtensionVersionDetail': 'extensions',
    'ExtensionVersionListItem': 'extensions',
    'ExtensionVersionListResponse': 'extensions',
    'ExtensionVersionYankRequest': 'extensions',
    'GenerateAssignmentsRequest': 'system',
    'GenerateAssignmentsResponse': 'system',
    'GenerateTemplateRequest': 'system',
    'GenerateTemplateResponse': 'system',
    'GitLabConfig': 'deployments',
    'GitLabConfigGet': 'deployments',
    'GitLabCredentials': 'system',
    'GradedArtifactInfo': 'tutor_grading',
    'GradedByCourseMember': 'grading',
    'GradingAuthor': 'grading',
    'GradingStatus': 'grading',
    'GroupCreate': 'groups',
    'GroupGet': 'groups',
    'GroupList': 'groups',
    'GroupType': 'groups',
    'GroupUpdate': 'groups',
    'LanguageGet': 'languages',
    'LanguageList': 'languages',
    'LocalLoginRequest': 'auth',
    'LocalLoginResponse': 'auth',
    'LocalTokenRefreshRequest': 'auth',
    'LocalTokenRefreshResponse': 'auth',
    'LogoutResponse': 'auth',
    'ProviderInfo': 'auth',
    'LoginRequest': 'auth',
    'UserRegistrationRequest': 'auth',
    'UserRegistrationResponse': 'auth',
    'TokenRefreshRequest': 'auth',
    'TokenRefreshResponse': 'auth',
    'MessageAuthor': 'messages',
    'MessageCreate': 'messages',
    'MessageGet': 'messages',
    'MessageList': 'messages',
    'MessageUpdate': 'messages',
    'OrganizationCreate': 'organizations',
    'OrganizationGet': 'organizations',
    'OrganizationList': 'organizations',
    'OrganizationProperties': 'organizations',
    'OrganizationPropertiesGet': 'organizations',
    'OrganizationTaskRequest': 'system',
    'OrganizationType': 'organizations',
    'OrganizationUpdate': 'organizations',
    'OrganizationUpdateTokenQuery': 'organizations',
    'OrganizationUpdateTokenUpdate': 'organizations',
    'PresignedUrlRequest': 'storage',
    'PresignedUrlResponse': 'storage',
    'ProfileCreate': 'profiles',
    'ProfileGet': 'profiles',
    'ProfileList': 'profiles',
    'ProfileUpdate': 'profiles',
    'ReleaseOverride': 'system',
    'ReleaseSelection': 'system',
    'ResultCreate': 'results',
    'ResultGet': 'results',
    'ResultList': 'results',
    'ResultStudentList': 'student_course_contents',
    'ResultUpdate': 'results',
    'RoleClaimList': 'roles_claims',
    'RoleGet': 'roles',
    'RoleList': 'roles',
    'SessionCreate': 'sessions',
    'SessionGet': 'sessions',
    'SessionList': 'sessions',
    'SessionUpdate': 'sessions',
    'StorageObjectGet': 'storage',
    'StorageObjectList': 'storage',
    'StorageUsageStats': 'storage',
    'StudentProfileCreate': 'student_profile',
    'StudentProfileGet': 'student_profile',
    'StudentProfileList': 'student_profile',
    'StudentProfileUpdate': 'student_profile',
    'SubmissionArtifactGet': 'artifacts',
    'SubmissionArtifactList': 'artifacts',
    'SubmissionArtifactUpdate': 'artifacts',
    'SubmissionGradeCreate': 'artifacts',
    'SubmissionGradeDetail': 'artifacts',
    'SubmissionGradeListItem': 'artifacts',
    'SubmissionGradeUpdate': 'artifacts',
    'SubmissionGroupCreate': 'submission_groups',
    'SubmissionGroupGet': 'submission_groups',
    'SubmissionGroupGradingList': 'grading',
    'SubmissionGroupList': 'submission_groups',
    'SubmissionGroupMemberBasic': 'student_course_contents',
    'SubmissionGroupMemberCreate': 'submission_group_members',
    'SubmissionGroupMemberGet': 'submission_group_members',
    'SubmissionGroupMemberList': 'submission_group_members',
    'SubmissionGroupMemberProperties': 'submission_group_members',
    'SubmissionGroupMemberUpdate': 'submission_group_members',
    'SubmissionGroupProperties': 'submission_groups',
    'SubmissionGroupRepository': 'student_course_contents',
    'SubmissionGroupStudentGet': 'student_course_contents',
    'SubmissionGroupStudentList': 'student_course_contents',
    'SubmissionGroupUpdate': 'submission_groups',
    'SubmissionReviewCreate': 'artifacts',
    'SubmissionReviewListItem': 'artifacts',
    'SubmissionReviewUpdate': 'artifacts',
    'SubmissionUploadResponseModel': 'submissions',
    'TaskResponse': 'system',
    'TaskStatus': 'tasks',
    'TaskResult': 'tasks',
    'TaskSubmission': 'tasks',
    'TaskInfo': 'tasks',
    'TestCreate': 'tests',
    'TutorCourseMemberCourseContent': 'tutor_course_members',
    'TutorCourseMemberGet': 'tutor_course_members',
    'TutorCourseMemberList': 'tutor_course_members',
    'TutorGradeCreate': 'tutor_grading',
    'TutorGradeResponse': 'tutor_grading',
    'UserCreate': 'users',
    'UserGet': 'users',
    'UserList': 'users',
    'UserPassword': 'users',
    'UserRoleCreate': 'user_roles',
    'UserRoleGet': 'user_roles',
    'UserRoleList': 'user_roles',
    'UserTypeEnum': 'users',
    'UserUpdate': 'users',
}


if __name__ == "__main__":
    import sys
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    main(base_url=base_url)

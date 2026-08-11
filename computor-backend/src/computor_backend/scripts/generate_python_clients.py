#!/usr/bin/env python3
"""
Generate Python HTTP clients from OpenAPI specification.

This script generates typed endpoint clients for the computor-client package
by parsing the OpenAPI specification from the running API server.

Output structure:
    computor-client/src/computor_client/endpoints/
    ├── __init__.py          # Re-exports all clients
    ├── auth.py              # AuthClient (login, logout, refresh, etc.)
    ├── organizations.py     # OrganizationClient (CRUD + custom endpoints)
    ├── lecturers.py         # LecturerClient (role-specific endpoints)
    └── ...
"""

import importlib
import inspect
import json
import pkgutil
import re
import urllib.request
from collections import defaultdict
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel


def load_openapi_spec_offline() -> Dict[str, Any]:
    """Build the OpenAPI spec in-process from the FastAPI app (no server needed).

    This is the default: it imports ``computor_backend.server`` and calls
    ``app.openapi()``, so codegen works offline and always matches the current
    routers. Note that env-gated routers (e.g. the Coder API, mounted only when
    ``CODER_ENABLED=true``) follow the process env, exactly as the served spec
    would.
    """
    from computor_backend.server import app

    return app.openapi()


def fetch_openapi_spec_from_url(url: str = "http://localhost:8000/openapi.json") -> Dict[str, Any]:
    """Fetch the OpenAPI spec from a running server (fallback mode)."""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching OpenAPI spec from {url}: {e}")
        print("Make sure the API server is running.")
        return {}


def load_openapi_spec(url: Optional[str] = None) -> Dict[str, Any]:
    """Load the OpenAPI spec offline by default, or over HTTP when ``url`` is set."""
    if url:
        print(f"Fetching OpenAPI spec from {url}")
        return fetch_openapi_spec_from_url(url)
    print("Building OpenAPI spec offline from computor_backend.server:app")
    try:
        return load_openapi_spec_offline()
    except Exception as e:
        print(f"Error building OpenAPI spec offline: {e}")
        import traceback
        traceback.print_exc()
        return {}


# Backwards-compatible alias (older callers imported this name).
def fetch_openapi_spec(url: str = "http://localhost:8000/openapi.json") -> Dict[str, Any]:
    """Deprecated: use ``load_openapi_spec``. Kept for import compatibility."""
    return fetch_openapi_spec_from_url(url)


def snake_to_pascal(name: str) -> str:
    """Convert snake_case or kebab-case to PascalCase."""
    name = name.replace("-", "_")
    return "".join(word.capitalize() for word in name.split("_"))


def extract_path_params(path: str) -> List[str]:
    """Extract path parameters from a route path."""
    return re.findall(r"\{(\w+)\}", path)


def sanitize_method_name(name: str) -> str:
    """Sanitize a string to be a valid Python identifier."""
    # Replace hyphens and other invalid chars with underscores
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Remove leading numbers
    name = re.sub(r'^[0-9]+', '', name)
    # Collapse multiple underscores
    name = re.sub(r'_+', '_', name)
    # Remove leading/trailing underscores
    name = name.strip('_')
    return name


def path_to_method_name(path: str, method: str, operation_id: str, base_segments: List[str]) -> str:
    """Generate a method name from path and operation."""
    segments = [s for s in path.split("/") if s and not s.startswith("{")]

    # Normalize base segments - also create the joined version for hyphenated paths
    normalized_base = [b.replace("-", "_").lower() for b in base_segments]
    joined_base = "_".join(normalized_base)  # e.g., "course_families"

    # Remove base segments from path
    remaining = []
    for seg in segments:
        seg_normalized = seg.replace("-", "_").lower()
        # Check if segment matches either individual base segments or the joined base
        if seg_normalized not in normalized_base and seg_normalized != joined_base:
            remaining.append(seg)

    if not remaining:
        # Standard CRUD
        if method == "GET" and not path.endswith("}"):
            return "list"
        elif method == "GET" and path.endswith("}"):
            return "get"
        elif method == "POST" and not any(s.startswith("{") for s in path.split("/")[-2:]):
            return "create"
        elif method == "PATCH" and path.count("{") == 1:
            return "update"
        elif method == "PUT" and path.count("{") == 1:
            return "replace"
        elif method == "DELETE" and path.count("{") == 1:
            return "delete"
        return method.lower()

    # Use remaining segments for method name
    name_parts = []
    for seg in remaining:
        seg_clean = sanitize_method_name(seg)
        if seg_clean:
            name_parts.append(seg_clean)

    method_name = "_".join(name_parts)

    # Add method prefix for non-standard operations
    if method == "POST" and "upload" not in method_name and "submit" not in method_name:
        if method_name not in ["login", "logout", "register", "refresh", "validate", "join", "sync"]:
            method_name = method_name
    elif method == "DELETE" and path.count("{") > 1:
        if not method_name.startswith("delete"):
            method_name = f"delete_{method_name}" if method_name else "delete"
    elif method == "GET" and path.count("{") > 1:
        if not method_name.startswith("get"):
            method_name = f"get_{method_name}" if method_name else "get"

    # Ensure final name is valid
    method_name = sanitize_method_name(method_name)
    return method_name if method_name else method.lower()


def find_schema_ref(schema: Dict[str, Any]) -> Optional[str]:
    """Extract schema reference name from a schema definition."""
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if "items" in schema and "$ref" in schema.get("items", {}):
        return schema["items"]["$ref"].split("/")[-1]
    if "anyOf" in schema:
        for item in schema["anyOf"]:
            if "$ref" in item:
                return item["$ref"].split("/")[-1]
    return None


def get_response_schema(operation: Dict[str, Any]) -> Tuple[Optional[str], bool, bool]:
    """Get the response schema name, whether it's a list, and whether it's binary.

    Returns:
        Tuple of (schema_name, is_list, is_binary)
    """
    responses = operation.get("responses", {})
    for status in ["200", "201"]:
        if status in responses:
            content = responses[status].get("content", {})
            # Check for binary responses (ZIP, octet-stream, etc.)
            binary_types = ["application/octet-stream", "application/zip", "application/x-zip-compressed"]
            for binary_type in binary_types:
                if binary_type in content:
                    return None, False, True  # Binary response
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                is_list = schema.get("type") == "array"
                ref = find_schema_ref(schema)
                return ref, is_list, False
    return None, False, False


def get_request_schema(operation: Dict[str, Any]) -> Optional[str]:
    """Get the request body schema name for an operation."""
    body = operation.get("requestBody", {})
    content = body.get("content", {})
    if "application/json" in content:
        schema = content["application/json"].get("schema", {})
        return find_schema_ref(schema)
    return None


# ---------------------------------------------------------------------------
# Schema resolution
# ---------------------------------------------------------------------------
#
# Schema names in the OpenAPI spec are bare class names ("CourseGet"); to emit an
# import for one, the generator needs the module that defines it. That mapping
# used to be a hand-maintained literal dict, and it rotted quietly: a schema
# missing from it produced an untyped `Dict[str, Any]` return and — far worse —
# a request body with no `data` parameter at all, i.e. a method that could never
# send its payload. The index is now derived by importing computor_types and
# reading each class's own `__module__`, so it cannot fall behind the DTOs.


class SchemaIndex:
    """DTO class name -> the computor_types module that defines it."""

    def __init__(
        self,
        by_name: Dict[str, str],
        ambiguous: Dict[str, List[str]],
        enums: Set[str],
    ):
        self.by_name = by_name
        self.ambiguous = ambiguous
        self.enums = enums

    def module_for(self, schema_name: str) -> Optional[str]:
        return self.by_name.get(schema_name)

    def is_enum(self, schema_name: str) -> bool:
        return schema_name in self.enums


@lru_cache(maxsize=1)
def build_schema_index() -> SchemaIndex:
    """Index every pydantic model and enum exported by ``computor_types``.

    Walks the package, imports each module and records ``cls.__module__`` — the
    *defining* module, so a class re-exported through a deprecation shim still
    resolves to its real home. A name defined in two different modules is left
    unresolved rather than guessed at.

    Raises:
        RuntimeError: If any computor_types module fails to import. A partial
            index would silently drop schemas, which is the exact failure mode
            this replaced.
    """
    import computor_types

    found: Dict[str, Set[str]] = defaultdict(set)
    enums: Set[str] = set()
    failed: List[Tuple[str, str]] = []

    for mod_info in pkgutil.walk_packages(computor_types.__path__, prefix="computor_types."):
        try:
            module = importlib.import_module(mod_info.name)
        except Exception as e:
            failed.append((mod_info.name, f"{type(e).__name__}: {e}"))
            continue

        for obj in vars(module).values():
            if not inspect.isclass(obj) or not issubclass(obj, (BaseModel, Enum)):
                continue
            # Skip pydantic's own bases and anything re-exported from outside.
            if not obj.__module__.startswith("computor_types."):
                continue
            found[obj.__name__].add(obj.__module__)
            if issubclass(obj, Enum):
                enums.add(obj.__name__)

    if failed:
        raise RuntimeError(
            "Could not import these computor_types modules, so the schema index "
            "would be incomplete:\n"
            + "\n".join(f"  {name}: {err}" for name, err in failed)
        )

    by_name = {name: next(iter(mods)) for name, mods in found.items() if len(mods) == 1}
    ambiguous = {name: sorted(mods) for name, mods in found.items() if len(mods) > 1}
    return SchemaIndex(by_name, ambiguous, enums)


# Schemas the generator deliberately never imports: FastAPI's own error envelope
# and the `Body_*` wrappers it synthesises for multipart form endpoints.
_INTERNAL_SCHEMA_NAMES = frozenset({"HTTPValidationError", "ValidationError"})


def is_internal_schema(schema_name: str) -> bool:
    """True for FastAPI-internal schemas that have no computor_types counterpart."""
    return schema_name in _INTERNAL_SCHEMA_NAMES or schema_name.startswith("Body_")


def is_enum_type(schema_name: str) -> bool:
    """Enums are constructed (``Status(value)``), not ``model_validate``d."""
    return build_schema_index().is_enum(schema_name)


def map_schema_to_import(schema_name: str) -> Optional[Tuple[str, str]]:
    """Map a schema name to ``(module, class_name)``, or None if not importable."""
    if not schema_name or is_internal_schema(schema_name):
        return None
    module = build_schema_index().module_for(schema_name)
    if module is None:
        return None
    return (module, schema_name)


def group_operations_by_tag(spec: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Group all operations by their primary tag."""
    by_tag = defaultdict(list)

    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method not in ["get", "post", "put", "patch", "delete"]:
                continue

            tags = operation.get("tags", ["default"])
            primary_tag = tags[0] if tags else "default"
            primary_tag = primary_tag.replace("-", "_").replace(" ", "_").lower()

            by_tag[primary_tag].append({
                "path": path,
                "method": method.upper(),
                "operation": operation,
                "operation_id": operation.get("operationId", ""),
            })

    return dict(by_tag)


def generate_method(
    path: str,
    method: str,
    operation: Dict[str, Any],
    operation_id: str,
    tag: str,
) -> Tuple[str, Set[Tuple[str, str]]]:
    """Generate a single method for an endpoint."""
    imports = set()

    # Determine base segments from tag
    base_segments = tag.replace("_", "-").split("-")
    method_name = path_to_method_name(path, method, operation_id, base_segments)

    # Avoid duplicate method names
    path_params = extract_path_params(path)

    # Get schemas
    request_schema = get_request_schema(operation)
    response_schema, is_list_response, is_binary_response = get_response_schema(operation)

    # Collect imports
    if request_schema:
        import_info = map_schema_to_import(request_schema)
        if import_info:
            imports.add(import_info)

    if response_schema:
        import_info = map_schema_to_import(response_schema)
        if import_info:
            imports.add(import_info)

    # Build parameters
    params = ["self"]
    for pp in path_params:
        params.append(f"{pp}: str")

    # Only add data parameter for methods that use request body (not GET/DELETE)
    if request_schema and map_schema_to_import(request_schema) and method in ["POST", "PUT", "PATCH"]:
        params.append(f"data: Union[{request_schema}, Dict[str, Any]]")

    # Query params (skip user_id as it's auto-injected)
    query_params = []
    for param in operation.get("parameters", []):
        if param.get("in") == "query" and param.get("name") != "user_id":
            pname = param["name"]
            required = param.get("required", False)
            if pname not in ["skip", "limit"]:
                query_params.append(pname)

    # Add query parameter for list endpoints to accept Query objects
    if method_name == "list":
        params.append("query: Optional[BaseModel] = None")

    # Return type
    if is_binary_response:
        return_type = "bytes"
    elif response_schema and map_schema_to_import(response_schema):
        if is_list_response:
            return_type = f"List[{response_schema}]"
        else:
            return_type = response_schema
    elif method == "DELETE" or operation.get("responses", {}).get("204"):
        return_type = "None"
    else:
        return_type = "Dict[str, Any]"

    # Build method
    docstring = operation.get("summary", f"{method} {path}")
    path_formatted = path
    for pp in path_params:
        path_formatted = path_formatted.replace(f"{{{pp}}}", "{" + pp + "}")

    lines = [
        f"    async def {method_name}(",
    ]
    for p in params:
        lines.append(f"        {p},")
    lines.extend([
        "        **kwargs: Any,",
        f"    ) -> {return_type}:",
        f'        """{docstring}"""',
    ])

    # HTTP call
    http_method = method.lower()
    if http_method == "get":
        if method_name == "list":
            lines.append(f'        params = query.model_dump(exclude_none=True) if query else {{}}'  )
            lines.append(f'        params.update(kwargs)')
            lines.append(f'        response = await self._http.get(')
            lines.append(f'            f"{path_formatted}",')
            lines.append(f'            params=params,')
            lines.append('        )')
        else:
            lines.append(f'        response = await self._http.get(f"{path_formatted}", params=kwargs)')
    elif http_method in ["post", "patch", "put"]:
        if request_schema and map_schema_to_import(request_schema):
            lines.append(f'        response = await self._http.{http_method}(f"{path_formatted}", json_data=data, params=kwargs)')
        else:
            lines.append(f'        response = await self._http.{http_method}(f"{path_formatted}", params=kwargs)')
    elif http_method == "delete":
        lines.append(f'        await self._http.delete(f"{path_formatted}", params=kwargs)')
        lines.append('        return')
        return "\n".join(lines), imports

    # Parse response
    if is_binary_response:
        lines.append('        return response.content')
    elif response_schema and map_schema_to_import(response_schema):
        if is_list_response:
            lines.append('        data = response.json()')
            lines.append('        if isinstance(data, list):')
            if is_enum_type(response_schema):
                lines.append(f'            return [{response_schema}(item) for item in data]')
            else:
                lines.append(f'            return [{response_schema}.model_validate(item) for item in data]')
            lines.append('        return []')
        else:
            if is_enum_type(response_schema):
                # Enums use constructor, not model_validate
                lines.append(f'        return {response_schema}(response.json())')
            else:
                lines.append(f'        return {response_schema}.model_validate(response.json())')
    else:
        if return_type == "None":
            lines.append('        return')
        else:
            lines.append('        return response.json()')

    return "\n".join(lines), imports


def generate_client_class(
    tag: str,
    operations: List[Dict[str, Any]],
) -> Tuple[str, Set[Tuple[str, str]], str]:
    """Generate a complete client class for a tag."""
    class_name = snake_to_pascal(tag) + "Client"

    all_imports = set()
    methods = []
    seen_method_names = set()

    for op in operations:
        method_code, imports = generate_method(
            op["path"],
            op["method"],
            op["operation"],
            op["operation_id"],
            tag,
        )

        # Extract method name to check for duplicates
        match = re.search(r"async def (\w+)\(", method_code)
        if match:
            method_name = match.group(1)
            if method_name in seen_method_names:
                # Add HTTP method and path hint to make unique
                http_method = op["method"].lower()
                path_hint = sanitize_method_name(op["path"].replace("/", "_").replace("{", "").replace("}", ""))
                # Use HTTP method as prefix to disambiguate
                new_name = f"{http_method}_{method_name}"
                if new_name in seen_method_names:
                    # Also add path hint
                    new_name = f"{http_method}_{path_hint[-30:]}" if len(path_hint) > 30 else f"{http_method}_{path_hint}"
                new_name = sanitize_method_name(new_name)
                method_code = method_code.replace(f"async def {method_name}(", f"async def {new_name}(")
                method_name = new_name
            seen_method_names.add(method_name)

        methods.append(method_code)
        all_imports.update(imports)

    lines = [
        f'class {class_name}:',
        f'    """',
        f'    Client for {tag.replace("_", " ")} endpoints.',
        f'    """',
        '',
        '    def __init__(self, http_client: AsyncHTTPClient) -> None:',
        '        self._http = http_client',
        '',
    ]

    for m in methods:
        lines.append(m)
        lines.append('')

    return "\n".join(lines), all_imports, class_name


def generate_file(tag: str, operations: List[Dict[str, Any]]) -> Tuple[str, str]:
    """Generate a complete Python file for a tag."""
    class_code, imports, class_name = generate_client_class(tag, operations)

    imports_by_module = defaultdict(set)
    for module, name in imports:
        imports_by_module[module].add(name)

    lines = [
        '"""',
        'Auto-generated endpoint client.',
        '',
        'DO NOT EDIT: this module is auto-generated from the OpenAPI specification.',
        'Hand edits are silently overwritten on the next regeneration.',
        'Run `bash generate.sh python-client` to regenerate.',
        '"""',
        '',
        'from typing import Any, Dict, List, Optional, Union',
        '',
        'from pydantic import BaseModel',
        '',
    ]

    for module in sorted(imports_by_module.keys()):
        names = sorted(imports_by_module[module])
        if len(names) == 1:
            lines.append(f'from {module} import {names[0]}')
        else:
            lines.append(f'from {module} import (')
            for name in names:
                lines.append(f'    {name},')
            lines.append(')')

    lines.extend([
        '',
        'from computor_client.http import AsyncHTTPClient',
        '',
        '',
        class_code,
    ])

    return "\n".join(lines), class_name


def collect_unresolvable_schemas(spec: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """Find *named* schemas with no importable computor_types counterpart.

    These are the dangerous ones: the spec says "this is a `FooCreate`" but the
    generator cannot import ``FooCreate``, so it degrades the type. Bodies that
    were never named at all (inline objects, multipart forms) are a different,
    milder case — see :func:`collect_untyped_bodies`.

    Returns ``(schema_name, "METHOD /path", "request"|"response")`` tuples,
    sorted and de-duplicated.
    """
    found: Set[Tuple[str, str, str]] = set()

    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method not in ["get", "post", "put", "patch", "delete"]:
                continue
            where = f"{method.upper()} {path}"

            request_schema = get_request_schema(operation)
            if request_schema and not is_internal_schema(request_schema):
                if not map_schema_to_import(request_schema):
                    found.add((request_schema, where, "request"))

            response_schema, _, _ = get_response_schema(operation)
            if response_schema and not is_internal_schema(response_schema):
                if not map_schema_to_import(response_schema):
                    found.add((response_schema, where, "response"))

    return sorted(found)


def collect_untyped_bodies(spec: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Find request bodies that carry no named schema to type them with.

    Two shapes land here: an endpoint declaring a bare ``dict`` (FastAPI emits
    an anonymous ``{"type": "object"}``), and multipart/form endpoints (FastAPI
    synthesises a ``Body_*`` wrapper). Both are generatable — the body is
    emitted untyped — but they lose compile-time checking, so they are always
    reported rather than passing silently.

    Returns sorted ``("METHOD /path", content_type)`` tuples.
    """
    found: Set[Tuple[str, str]] = set()

    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method not in ["post", "put", "patch"]:
                continue
            content = operation.get("requestBody", {}).get("content", {})
            if not content or get_request_schema(operation):
                continue
            found.add((f"{method.upper()} {path}", ", ".join(sorted(content))))

    return sorted(found)


def format_unresolvable_report(unresolvable: List[Tuple[str, str, str]]) -> str:
    """Build the abort message for named schemas the generator cannot import."""
    index = build_schema_index()
    lines = [
        f"{len(unresolvable)} schema reference(s) could not be resolved to a "
        "computor_types import:",
        "",
    ]
    for name, where, kind in unresolvable:
        note = ""
        if name in index.ambiguous:
            note = f"  (defined in more than one module: {', '.join(index.ambiguous[name])})"
        lines.append(f"  {name}  <- {kind} of {where}{note}")
    lines += [
        "",
        "Generating anyway would silently degrade these: a response falls back to",
        "Dict[str, Any], and a *request* body loses its declared type.",
        "",
        "Usual causes:",
        "  - the DTO lives in computor-backend instead of computor-types",
        "    (see scripts/check_dto_location.py)",
        "  - the same class name is defined in two computor_types modules",
        "",
        "Pass --allow-unresolved-schemas to generate regardless.",
    ]
    return "\n".join(lines)


def main(
    output_dir: Optional[Path] = None,
    spec_url: Optional[str] = None,
    allow_unresolved_schemas: bool = False,
):
    """Main generator entry point.

    ``spec_url=None`` (default) builds the spec offline from the FastAPI app;
    pass a URL to fetch it from a running server instead.

    Raises:
        SystemExit: If any referenced schema cannot be resolved to a
            computor_types import, unless ``allow_unresolved_schemas`` is set.
    """
    if output_dir is None:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent.parent.parent
        output_dir = project_root / "computor-client" / "src" / "computor_client" / "endpoints"

    print("Generating Python API clients from OpenAPI spec...")
    print(f"Output directory: {output_dir}")
    print()

    spec = load_openapi_spec(spec_url)
    if not spec:
        print("Failed to load OpenAPI spec.")
        return []

    unresolvable = collect_unresolvable_schemas(spec)
    if unresolvable:
        report = format_unresolvable_report(unresolvable)
        if not allow_unresolved_schemas:
            raise SystemExit(f"Aborting: {report}")
        print(f"WARNING: {report}")
        print()

    untyped_bodies = collect_untyped_bodies(spec)
    if untyped_bodies:
        print(f"{len(untyped_bodies)} request body/bodies have no named schema and "
              "will be generated untyped:")
        for where, content_types in untyped_bodies:
            print(f"  {where}  [{content_types}]")
        print()

    output_dir.mkdir(parents=True, exist_ok=True)

    for file in output_dir.glob("*.py"):
        file.unlink()
    print("Cleaned output directory")
    print()

    operations_by_tag = group_operations_by_tag(spec)
    print(f"Found {len(operations_by_tag)} API tags")
    print()

    generated_files = []
    all_clients = []

    for tag in sorted(operations_by_tag.keys()):
        operations = operations_by_tag[tag]
        if tag in ["default"]:
            continue

        filename = tag + ".py"
        output_file = output_dir / filename

        try:
            file_content, class_name = generate_file(tag, operations)
            output_file.write_text(file_content + "\n")
            generated_files.append(output_file)
            all_clients.append((tag, class_name))
            print(f"Generated {filename} ({len(operations)} endpoints)")
        except Exception as e:
            print(f"Failed to generate {filename}: {e}")
            import traceback
            traceback.print_exc()

    print()

    # Generate __init__.py
    init_lines = [
        '"""',
        'Auto-generated endpoint clients.',
        '',
        'DO NOT EDIT: this module is auto-generated from the OpenAPI specification.',
        'Hand edits are silently overwritten on the next regeneration.',
        'Run `bash generate.sh python-client` to regenerate.',
        '"""',
        '',
    ]

    for tag, class_name in sorted(all_clients):
        init_lines.append(f'from computor_client.endpoints.{tag} import {class_name}')

    init_lines.extend(['', '__all__ = ['])
    for _, class_name in sorted(all_clients, key=lambda x: x[1]):
        init_lines.append(f'    "{class_name}",')
    init_lines.append(']')

    init_file = output_dir / "__init__.py"
    init_file.write_text("\n".join(init_lines) + "\n")
    print("Generated __init__.py")

    print()
    print("=" * 60)
    print(f"Generation Summary:")
    print(f"   Total tags: {len(operations_by_tag)}")
    print(f"   Generated files: {len(generated_files)}")
    print(f"   Total clients: {len(all_clients)}")
    print("=" * 60)

    return generated_files


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Python HTTP clients from the OpenAPI spec (offline by default)."
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Fetch the spec from a running server at this URL instead of "
             "building it offline (e.g. http://localhost:8000/openapi.json).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override the endpoints output directory.",
    )
    parser.add_argument(
        "--allow-unresolved-schemas",
        action="store_true",
        help="Generate even when a schema cannot be resolved to a computor_types "
             "import. Off by default: an unresolved request schema produces a "
             "method with no body parameter, which can never send its payload.",
    )
    args = parser.parse_args()
    main(
        output_dir=Path(args.output_dir) if args.output_dir else None,
        spec_url=args.url,
        allow_unresolved_schemas=args.allow_unresolved_schemas,
    )

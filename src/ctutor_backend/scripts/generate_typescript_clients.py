#!/usr/bin/env python3
"""Generate TypeScript API clients from backend interface definitions."""

from __future__ import annotations

import inspect
import json
import re
import os
import pkgutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Type

# Ensure the backend package is importable when running as a script
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
SRC_DIR = BACKEND_DIR.parent
PROJECT_ROOT = SRC_DIR.parent

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(SRC_DIR))

from pydantic import BaseModel  # noqa: E402

from ctutor_backend.interface import base as interface_base  # noqa: E402


RESERVED_IDENTIFIERS = {
    'default',
    'class',
    'function',
    'return',
    'delete',
    'export',
    'import',
    'new',
    'switch',
    'case',
    'for',
    'while',
    'break',
    'continue',
    'const',
    'let',
    'var',
    'extends',
    'implements',
    'package',
    'interface',
    'this',
    'await',
}


@dataclass
class InterfaceMetadata:
    """Metadata collected for generating a TypeScript client."""

    name: str
    endpoint: str
    create: Optional[Type[BaseModel]]
    get: Optional[Type[BaseModel]]
    list_model: Optional[Type[BaseModel]]
    update: Optional[Type[BaseModel]]
    query: Optional[Type[BaseModel]]
    has_archive: bool
    extra_operations: List['OperationMethod'] = field(default_factory=list)
    is_custom: bool = False

    @property
    def client_class_name(self) -> str:
        return self.name.replace("Interface", "Client")

    @property
    def base_path(self) -> str:
        return f"/{self.endpoint.strip('/')}"


@dataclass
class OperationParameter:
    """Represents a path or query parameter for an operation."""

    name: str
    var_name: str
    ts_type: str
    required: bool


@dataclass
class PathSegment:
    """Represents a single segment of an endpoint path."""

    literal: Optional[str] = None
    parameter: Optional[OperationParameter] = None


@dataclass
class OperationMethod:
    """Metadata for generating an additional client method from OpenAPI."""

    method_name: str
    http_method: str
    path_segments: List[PathSegment]
    path_params: List[OperationParameter]
    query_params: List[OperationParameter]
    summary: Optional[str]
    description: Optional[str]
    body_type: Optional[str]
    body_required: bool
    response_type: Optional[str]
    success_status: str
    type_dependencies: Set[str] = field(default_factory=set)


@dataclass
class EndpointDocEntry:
    """Represents a single endpoint entry for documentation purposes."""

    method_name: str
    http_method: str
    path: str
    request_type: str
    response_type: str


class TypeScriptClientGenerator:
    """Generate TypeScript API client classes from interface metadata."""

    def __init__(self, output_dir: Path, include_timestamp: bool = False):
        self.output_dir = output_dir
        self.generated_files: Set[Path] = set()
        self.include_timestamp = include_timestamp
        self._timestamp_value: Optional[str] = None

    def _current_timestamp(self) -> str:
        if not self.include_timestamp:
            raise RuntimeError("Timestamp requested but include_timestamp is False")
        if self._timestamp_value is None:
            self._timestamp_value = datetime.utcnow().isoformat()
        return self._timestamp_value

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------
    def discover_interfaces(self) -> list[InterfaceMetadata]:
        """Discover ``EntityInterface`` subclasses with configured endpoints."""

        interfaces: list[InterfaceMetadata] = []
        seen: Set[type] = set()

        for module in self._iter_interface_modules():
            for attr in module.__dict__.values():
                if not inspect.isclass(attr):
                    continue

                if attr in seen:
                    continue

                if not issubclass(attr, interface_base.EntityInterface):
                    continue

                # Skip the abstract base itself
                if attr is interface_base.EntityInterface:
                    continue

                endpoint = getattr(attr, "endpoint", None)
                if not endpoint:
                    continue

                seen.add(attr)

                interfaces.append(
                    InterfaceMetadata(
                        name=attr.__name__,
                        endpoint=endpoint,
                        create=self._ensure_model(getattr(attr, "create", None)),
                        get=self._ensure_model(getattr(attr, "get", None)),
                        list_model=self._ensure_model(getattr(attr, "list", None)),
                        update=self._ensure_model(getattr(attr, "update", None)),
                        query=self._ensure_model(getattr(attr, "query", None)),
                        has_archive=self._detect_archive(attr),
                    )
                )

        # Sort for deterministic output (by class name)
        interfaces.sort(key=lambda meta: meta.name)
        return interfaces

    def _iter_interface_modules(self) -> Iterable[object]:
        import ctutor_backend.interface  # noqa: WPS433, E402

        package = ctutor_backend.interface

        for module_info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            try:
                module = __import__(module_info.name, fromlist=["__name__"])
            except Exception as exc:  # pragma: no cover - defensive logging
                print(f"Warning: unable to import {module_info.name}: {exc}")
                continue
            yield module

    @staticmethod
    def _ensure_model(model: Optional[object]) -> Optional[Type[BaseModel]]:
        if inspect.isclass(model) and issubclass(model, BaseModel):
            return model
        return None

    @staticmethod
    def _detect_archive(interface_cls: Type[interface_base.EntityInterface]) -> bool:
        model = getattr(interface_cls, "model", None)
        if model is None:
            return False

        try:
            return hasattr(model, "archived_at")
        except Exception:  # pragma: no cover - defensive
            return False

    # ------------------------------------------------------------------
    # Generation helpers
    # ------------------------------------------------------------------
    def generate(self, clean: bool = False) -> list[Path]:
        """Generate all client files."""

        self.output_dir.mkdir(parents=True, exist_ok=True)

        if clean:
            self._clean_output_dir()

        if self.include_timestamp:
            self._timestamp_value = None

        interface_clients = self.discover_interfaces()
        custom_clients = self._attach_openapi_operations(interface_clients)

        all_clients = interface_clients + custom_clients

        generated_paths: list[Path] = []

        # Write shared base class before individual clients
        generated_paths.append(self._write_base_client())

        for meta in all_clients:
            client_file = self._write_client(meta)
            if client_file:
                generated_paths.append(client_file)

        generated_paths.append(self._write_index(all_clients))

        self._write_markdown_summary(all_clients)

        self._remove_stale_files(generated_paths)

        return generated_paths

    # ------------------------------------------------------------------
    # File writers
    # ------------------------------------------------------------------
    def _write_base_client(self) -> Path:
        header = [
            "/**",
            " * Auto-generated helper utilities for API endpoint clients.",
        ]
        if self.include_timestamp:
            header.append(f" * Generated on: {self._current_timestamp()}")
        header.append(" */")
        header.append("")

        body = [
            "import { APIClient, apiClient } from 'api/client';",
            "",
            "export class BaseEndpointClient {",
            "  protected readonly client: APIClient;",
            "  protected readonly basePath: string;",
            "",
            "  constructor(client: APIClient = apiClient, basePath: string) {",
            "    this.client = client;",
            "    if (!basePath) {",
            "      this.basePath = '/';",
            "      return;",
            "    }",
            "",
            "    const normalized = basePath.startsWith('/') ? basePath : `/${basePath}`;",
            "    this.basePath = normalized !== '/' && normalized.endsWith('/') ? normalized.slice(0, -1) : normalized;",
            "  }",
            "",
            "  protected buildPath(...segments: (string | number)[]): string {",
            "    if (!segments.length) {",
            "      return this.basePath;",
            "    }",
            "",
            "    const encoded = segments.map((segment) => encodeURIComponent(String(segment)));",
            "    const joined = encoded.join('/');",
            "    if (this.basePath === '/') {",
            "      return `/${joined}`;",
            "    }",
            "",
            "    return `${this.basePath}/${joined}`;",
            "  }",
            "}",
        ]

        content = "\n".join(header + body)
        return self._write_file("baseClient.ts", content)

    def _write_client(self, meta: InterfaceMetadata) -> Optional[Path]:
        crud_lines, crud_types = self._generate_crud_methods(meta)
        extra_lines, extra_types = self._generate_extra_methods(meta)

        method_lines = crud_lines + extra_lines
        if not method_lines:
            return None

        type_names = crud_types | extra_types
        imports: list[str] = []

        if type_names:
            imports.append(f"import type {{ {', '.join(sorted(type_names))} }} from 'types/generated';")

        imports.append("import { APIClient, apiClient } from 'api/client';")
        imports.append("import { BaseEndpointClient } from './baseClient';")

        header = [
            "/**",
            f" * Auto-generated client for {meta.name}.",
            f" * Endpoint: {meta.base_path}",
        ]
        if self.include_timestamp:
            header.append(f" * Generated on: {self._current_timestamp()}")
        header.append(" */")

        body_lines = [
            *header,
            "",
            *imports,
            "",
            f"export class {meta.client_class_name} extends BaseEndpointClient {{",
            f"  constructor(client: APIClient = apiClient) {{",
            f"    super(client, '{meta.base_path}');",
            "  }",
        ]

        body_lines.extend(method_lines)
        body_lines.append("}")

        content = "\n".join(body_lines)

        filename = f"{meta.client_class_name}.ts"
        return self._write_file(filename, content)

    def _write_index(self, interfaces: list[InterfaceMetadata]) -> Path:
        exports = [
            "/**",
            " * Auto-generated barrel file for API clients.",
        ]
        if self.include_timestamp:
            exports.append(f" * Generated on: {self._current_timestamp()}")
        exports.append(" */")
        exports.append("")
        exports.append("export * from './baseClient';")

        for meta in interfaces:
            exports.append(f"export * from './{meta.client_class_name}';")

        content = "\n".join(exports)
        return self._write_file("index.ts", content)

    def _write_markdown_summary(self, interfaces: list[InterfaceMetadata]) -> Path:
        """Write a markdown summary of generated endpoints."""

        summary_lines: List[str] = ["# API Client Endpoint Summary"]
        if self.include_timestamp:
            summary_lines.append(f"_Generated on: {self._current_timestamp()}_")
        summary_lines.append("")

        wrote_section = False

        for meta in interfaces:
            entries = self._collect_endpoint_entries(meta)
            if not entries:
                continue

            wrote_section = True

            summary_lines.append(f"## {meta.client_class_name}")
            summary_lines.append(f"- Base path: `{self._normalize_path(meta.base_path)}`")
            if meta.is_custom:
                summary_lines.append("- Note: custom operations discovered from OpenAPI schema")
            summary_lines.append("")
            summary_lines.append("| TS Method | HTTP | Path | Request | Response |")
            summary_lines.append("| --- | --- | --- | --- | --- |")

            for entry in entries:
                summary_lines.append(
                    f"| `{entry.method_name}` | {entry.http_method} | `{entry.path}` | {entry.request_type} | {entry.response_type} |"
                )

            summary_lines.append("")

        if not wrote_section:
            summary_lines.append("_No endpoints discovered._")

        content = "\n".join(summary_lines).rstrip() + "\n"
        path = self.output_dir / "client-endpoints.md"
        path.write_text(content, encoding="utf-8")
        print(f"📝 Wrote endpoint summary {path.relative_to(PROJECT_ROOT)}")
        return path

    def _collect_endpoint_entries(self, meta: InterfaceMetadata) -> List[EndpointDocEntry]:
        entries: List[EndpointDocEntry] = []
        base_path = self._normalize_path(meta.base_path)

        if not meta.is_custom:
            entries.extend(self._standard_operation_entries(meta, base_path))

        seen: Set[Tuple[str, str]] = {(entry.http_method, entry.path) for entry in entries}

        for operation in meta.extra_operations:
            path = self._compose_path(base_path, *self._operation_segments(operation))
            request_type = self._format_request_type(operation.body_type, optional=not operation.body_required)
            response_type = self._format_type(operation.response_type)
            key = (operation.http_method.upper(), path)
            if key in seen:
                continue

            entries.append(
                EndpointDocEntry(
                    method_name=operation.method_name,
                    http_method=operation.http_method.upper(),
                    path=path,
                    request_type=request_type,
                    response_type=response_type,
                )
            )
            seen.add(key)

        return entries

    def _standard_operation_entries(self, meta: InterfaceMetadata, base_path: str) -> List[EndpointDocEntry]:
        entries: List[EndpointDocEntry] = []

        if meta.create is not None:
            request_type = self._format_type(meta.create.__name__)
            response_model = (meta.get or meta.create)
            response_type = self._format_type(response_model.__name__ if response_model else None)
            entries.append(
                EndpointDocEntry(
                    method_name="create",
                    http_method="POST",
                    path=base_path,
                    request_type=request_type,
                    response_type=response_type,
                )
            )

        if meta.get is not None:
            response_type = self._format_type(meta.get.__name__)
            entries.append(
                EndpointDocEntry(
                    method_name="get",
                    http_method="GET",
                    path=self._compose_path(base_path, "{id}"),
                    request_type=self._format_type(None),
                    response_type=response_type,
                )
            )

        if meta.list_model is not None:
            request_type = self._format_type(meta.query.__name__ if meta.query is not None else None)
            response_type = self._format_type(f"{meta.list_model.__name__}[]")
            entries.append(
                EndpointDocEntry(
                    method_name="list",
                    http_method="GET",
                    path=base_path,
                    request_type=request_type,
                    response_type=response_type,
                )
            )

        if meta.update is not None:
            request_type = self._format_type(meta.update.__name__)
            response_model = (meta.get or meta.update)
            response_type = self._format_type(response_model.__name__ if response_model else None)
            entries.append(
                EndpointDocEntry(
                    method_name="update",
                    http_method="PATCH",
                    path=self._compose_path(base_path, "{id}"),
                    request_type=request_type,
                    response_type=response_type,
                )
            )

        if meta.create is not None or meta.update is not None:
            entries.append(
                EndpointDocEntry(
                    method_name="delete",
                    http_method="DELETE",
                    path=self._compose_path(base_path, "{id}"),
                    request_type=self._format_type(None),
                    response_type=self._format_type("void"),
                )
            )

        if meta.has_archive:
            entries.append(
                EndpointDocEntry(
                    method_name="archive",
                    http_method="PATCH",
                    path=self._compose_path(base_path, "{id}", "archive"),
                    request_type=self._format_type(None),
                    response_type=self._format_type("void"),
                )
            )

        return entries

    def _operation_segments(self, operation: OperationMethod) -> List[str]:
        segments: List[str] = []
        for segment in operation.path_segments:
            if segment.literal is not None:
                segments.append(segment.literal)
            elif segment.parameter is not None:
                segments.append(f"{{{segment.parameter.name}}}")
        return segments

    @staticmethod
    def _normalize_path(path: str) -> str:
        parts = [part for part in path.strip('/').split('/') if part]
        if not parts:
            return '/'
        return '/' + '/'.join(parts)

    def _compose_path(self, base_path: str, *segments: str) -> str:
        base_parts = [part for part in base_path.strip('/').split('/') if part]
        segment_parts = [segment.strip('/') for segment in segments if segment]
        parts = base_parts + segment_parts
        if not parts:
            return '/'
        return '/' + '/'.join(parts)

    @staticmethod
    def _format_request_type(value: Optional[str], optional: bool = False) -> str:
        if not value:
            return '—'
        suffix = ' (optional)' if optional else ''
        return f"`{value}`{suffix}"

    @staticmethod
    def _format_type(value: Optional[str]) -> str:
        if not value:
            return '—'
        return f"`{value}`"

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _attach_openapi_operations(self, descriptors: List[InterfaceMetadata]) -> List[InterfaceMetadata]:
        """Augment interface descriptors with operations discovered from OpenAPI."""

        schema = self._load_openapi_schema()
        if not schema:
            return []

        paths = schema.get('paths', {})
        custom_clients: Dict[str, InterfaceMetadata] = {}

        for raw_path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            path_parameters = path_item.get('parameters', [])

            for http_method, operation in path_item.items():
                method = http_method.lower()
                if method == 'parameters':
                    continue
                if method not in {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}:
                    continue
                if not isinstance(operation, dict):
                    continue

                descriptor = self._match_descriptor(descriptors, raw_path)
                if descriptor and self._is_standard_crud_operation(descriptor, raw_path, method):
                    continue

                if descriptor is None:
                    descriptor = self._get_or_create_custom_descriptor(custom_clients, raw_path, operation)

                op_metadata = self._create_operation_metadata(raw_path, method, operation, path_parameters, descriptor)
                if op_metadata:
                    descriptor.extra_operations.append(op_metadata)

        return list(custom_clients.values())

    def _load_openapi_schema(self) -> Dict[str, Any]:
        try:
            from ctutor_backend.server import app  # noqa: WPS433

            return app.openapi()
        except Exception as exc:  # pragma: no cover - defensive log
            print(f"Warning: Unable to load OpenAPI schema: {exc}")
            return {}

    def _match_descriptor(self, descriptors: List[InterfaceMetadata], path: str) -> Optional[InterfaceMetadata]:
        """Find the interface descriptor whose base path matches the given path."""

        normalized_path = '/' + path.strip('/')
        best_match: Optional[InterfaceMetadata] = None
        best_length = -1

        for descriptor in descriptors:
            base = descriptor.base_path.rstrip('/')
            if not base:
                base = '/'

            if normalized_path == base or normalized_path.startswith(base + '/'):
                if len(base) > best_length:
                    best_match = descriptor
                    best_length = len(base)

        return best_match

    def _is_standard_crud_operation(self, descriptor: InterfaceMetadata, path: str, method: str) -> bool:
        if descriptor.is_custom:
            return False

        base = descriptor.base_path.rstrip('/')
        normalized_path = '/' + path.strip('/')

        if not base:
            base = '/'

        if method == 'post' and descriptor.create is not None and normalized_path == base:
            return True

        if method == 'get':
            if descriptor.list_model is not None and normalized_path == base:
                return True
            if descriptor.get is not None and self._is_single_resource_path(base, normalized_path):
                return True

        if method in {'patch', 'put'} and descriptor.update is not None and self._is_single_resource_path(base, normalized_path):
            return True

        if method == 'delete' and self._is_single_resource_path(base, normalized_path):
            return True

        return False

    @staticmethod
    def _is_single_resource_path(base: str, path: str) -> bool:
        if not path.startswith(base):
            return False

        suffix = path[len(base):]
        if not suffix.startswith('/'):
            return False

        remainder = suffix.strip('/')
        return remainder.startswith('{') and remainder.endswith('}') and '/' not in remainder

    def _get_or_create_custom_descriptor(
        self,
        cache: Dict[str, InterfaceMetadata],
        path: str,
        operation: Dict[str, Any],
    ) -> InterfaceMetadata:
        endpoint = self._derive_endpoint_from_path(path)
        key = endpoint or '/'

        if key not in cache:
            class_name = self._derive_custom_class_name(operation, path)
            metadata = InterfaceMetadata(
                name=class_name,
                endpoint=endpoint or '/',
                create=None,
                get=None,
                list_model=None,
                update=None,
                query=None,
                has_archive=False,
                is_custom=True,
            )
            cache[key] = metadata

        return cache[key]

    def _derive_custom_class_name(self, operation: Dict[str, Any], path: str) -> str:
        tags = operation.get('tags') or []
        if tags:
            base = tags[0]
        else:
            base = self._derive_endpoint_from_path(path) or 'misc'
        return f"{self._pascal_case(base)}Client"

    @staticmethod
    def _derive_endpoint_from_path(path: str) -> str:
        parts = [segment for segment in path.strip('/').split('/') if segment]
        for segment in parts:
            if not segment.startswith('{'):
                return segment
        return ''

    def _create_operation_metadata(
        self,
        path: str,
        method: str,
        operation: Dict[str, Any],
        path_parameters: List[Dict[str, Any]],
        descriptor: InterfaceMetadata,
    ) -> Optional[OperationMethod]:
        combined_params = self._combine_parameters(path_parameters, operation.get('parameters', []))

        dependencies: Set[str] = set()
        path_params: List[OperationParameter] = []
        query_params: List[OperationParameter] = []
        param_lookup: Dict[str, OperationParameter] = {}

        for param in combined_params:
            location = param.get('in')
            name = param.get('name')
            if not location or not name:
                continue

            schema = param.get('schema', {})
            ts_type, type_deps = self._schema_to_ts(schema)
            dependencies |= type_deps

            if ts_type == 'unknown' and location == 'path':
                ts_type = 'string | number'
            elif ts_type == 'unknown':
                ts_type = 'string | number | boolean'

            var_name = self._sanitize_identifier(name)
            parameter = OperationParameter(
                name=name,
                var_name=var_name,
                ts_type=ts_type,
                required=param.get('required', location == 'path'),
            )

            if location == 'path':
                path_params.append(parameter)
                param_lookup[name] = parameter
            elif location == 'query':
                query_params.append(parameter)
                param_lookup.setdefault(name, parameter)

        path_segments = self._relative_path_segments(descriptor, path, param_lookup)

        body_type: Optional[str] = None
        body_required = False
        request_body = operation.get('requestBody')
        if isinstance(request_body, dict):
            body_required = request_body.get('required', False)
            schema = self._extract_json_schema(request_body.get('content', {}))
            if schema:
                body_type, body_deps = self._schema_to_ts(schema)
                dependencies |= body_deps

        if body_type and method.lower() in {'get', 'head'}:
            body_type = None
            body_required = False

        response_type: Optional[str] = 'void'
        success_status = 'default'
        responses = operation.get('responses', {})
        success_codes = ['200', '201', '202', '203', '204', 'default']

        for status in success_codes:
            if status in responses:
                success_status = status
                response = responses[status]
                schema = None
                if isinstance(response, dict):
                    schema = self._extract_json_schema(response.get('content', {}))

                if schema:
                    response_type, resp_deps = self._schema_to_ts(schema)
                    dependencies |= resp_deps
                else:
                    response_type = 'void'
                break

        if response_type is None:
            response_type = 'void'

        base_name = operation.get('operationId') or self._fallback_operation_name(method, path)
        method_name = self._ensure_unique_method_name(descriptor, base_name)

        return OperationMethod(
            method_name=method_name,
            http_method=method,
            path_segments=path_segments,
            path_params=path_params,
            query_params=query_params,
            summary=operation.get('summary'),
            description=operation.get('description'),
            body_type=body_type,
            body_required=body_required,
            response_type=response_type,
            success_status=success_status,
            type_dependencies=dependencies,
        )

    @staticmethod
    def _combine_parameters(
        path_level: List[Dict[str, Any]],
        operation_level: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        combined: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for param in path_level or []:
            key = (param.get('name'), param.get('in'))
            combined[key] = param

        for param in operation_level or []:
            key = (param.get('name'), param.get('in'))
            combined[key] = param

        return list(combined.values())

    def _relative_path_segments(
        self,
        descriptor: InterfaceMetadata,
        path: str,
        param_lookup: Dict[str, OperationParameter],
    ) -> List[PathSegment]:
        segments = [segment for segment in path.strip('/').split('/') if segment]
        base_segments = [segment for segment in descriptor.base_path.strip('/').split('/') if segment]

        index = 0
        while index < len(base_segments) and index < len(segments) and base_segments[index] == segments[index]:
            index += 1

        relative_segments = segments[index:]
        result: List[PathSegment] = []

        for segment in relative_segments:
            if segment.startswith('{') and segment.endswith('}'):
                name = segment[1:-1]
                parameter = param_lookup.get(name)
                if parameter is None:
                    var_name = self._sanitize_identifier(name)
                    parameter = OperationParameter(
                        name=name,
                        var_name=var_name,
                        ts_type='string | number',
                        required=True,
                    )
                    param_lookup[name] = parameter
                result.append(PathSegment(parameter=parameter))
            else:
                result.append(PathSegment(literal=segment))

        return result

    def _fallback_operation_name(self, method: str, path: str) -> str:
        parts = []
        params: List[str] = []

        for segment in path.strip('/').split('/'):
            if not segment:
                continue
            if segment.startswith('{') and segment.endswith('}'):
                params.append(self._pascal_case(segment[1:-1]))
            else:
                parts.append(self._pascal_case(segment))

        base = method.lower() + ''.join(parts)
        if params:
            base += 'By' + 'And'.join(params)

        return base

    def _ensure_unique_method_name(self, descriptor: InterfaceMetadata, base_name: str) -> str:
        candidate = self._camel_case(base_name or 'operation')

        existing = {
            'create',
            'get',
            'list',
            'update',
            'delete',
            'archive',
        }
        existing.update(method.method_name for method in descriptor.extra_operations)

        name = candidate
        index = 2
        while name in existing:
            name = f"{candidate}{index}"
            index += 1

        return name

    def _extract_json_schema(self, content: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(content, dict):
            return None

        for media_type in ('application/json', 'application/*+json', 'text/json', '*/*'):
            if media_type in content:
                media = content[media_type]
                if isinstance(media, dict):
                    schema = media.get('schema')
                    if isinstance(schema, dict):
                        return schema
        return None

    def _schema_to_ts(self, schema: Optional[Dict[str, Any]]) -> Tuple[str, Set[str]]:
        if not schema:
            return 'unknown', set()

        if '$ref' in schema:
            ref = schema['$ref']
            type_name = ref.split('/')[-1]
            return type_name, {type_name}

        if 'enum' in schema:
            enum_values = []
            for value in schema['enum']:
                if isinstance(value, str):
                    enum_values.append(f"'{value}'")
                else:
                    enum_values.append(json.dumps(value))
            if enum_values:
                return ' | '.join(enum_values), set()

        for composition in ('oneOf', 'anyOf'):
            if composition in schema:
                union_parts: List[str] = []
                deps: Set[str] = set()
                for item in schema[composition]:
                    part, part_deps = self._schema_to_ts(item)
                    union_parts.append(part)
                    deps |= part_deps
                union = ' | '.join(union_parts)
                if schema.get('nullable') and 'null' not in union:
                    union += ' | null'
                return union, deps

        if 'allOf' in schema:
            intersection_parts: List[str] = []
            deps: Set[str] = set()
            for item in schema['allOf']:
                part, part_deps = self._schema_to_ts(item)
                intersection_parts.append(part)
                deps |= part_deps
            intersection = ' & '.join(intersection_parts)
            if schema.get('nullable') and 'null' not in intersection:
                intersection += ' | null'
            return intersection, deps

        schema_type = schema.get('type')

        if schema_type == 'array':
            item_type, deps = self._schema_to_ts(schema.get('items'))
            result = f"{item_type}[]"
            if schema.get('nullable'):
                result += ' | null'
            return result, deps

        if schema_type == 'object' or 'properties' in schema or 'additionalProperties' in schema:
            properties = schema.get('properties') or {}
            required = set(schema.get('required', []))
            deps: Set[str] = set()

            if properties:
                parts: List[str] = []
                for name, prop_schema in properties.items():
                    prop_type, prop_deps = self._schema_to_ts(prop_schema)
                    deps |= prop_deps
                    optional = '?' if name not in required else ''
                    property_name = self._format_property_name(name)
                    parts.append(f"{property_name}{optional}: {prop_type};")
                type_str = '{ ' + ' '.join(parts) + ' }'
            else:
                type_str = 'Record<string, unknown>'

            additional = schema.get('additionalProperties')
            if additional:
                additional_type, additional_deps = self._schema_to_ts(additional if isinstance(additional, dict) else {})
                deps |= additional_deps
                type_str = f"{type_str} & Record<string, {additional_type}>"

            if schema.get('nullable'):
                type_str += ' | null'

            return type_str, deps

        if schema_type == 'integer' or schema_type == 'number':
            base = 'number'
        elif schema_type == 'string':
            base = 'string'
        elif schema_type == 'boolean':
            base = 'boolean'
        elif schema_type == 'null':
            base = 'null'
        else:
            base = 'unknown'

        if schema.get('nullable') and base != 'null':
            base = f"{base} | null"

        return base, set()

    def _build_operation_method(
        self,
        descriptor: InterfaceMetadata,
        operation: OperationMethod,
    ) -> Tuple[List[str], Set[str]]:
        lines: List[str] = []

        comment_lines: List[str] = []
        if operation.summary:
            comment_lines.append(operation.summary.strip())
        if operation.description:
            for line in operation.description.strip().splitlines():
                if line:
                    comment_lines.append(line.strip())

        lines.append("")
        if comment_lines:
            lines.append("  /**")
            for comment in comment_lines:
                lines.append(f"   * {comment}")
            lines.append("   */")

        return_type = operation.response_type or 'void'

        destruct_names: List[str] = []
        type_fields: List[str] = []

        for param in operation.path_params + operation.query_params:
            optional = '' if param.required else '?'
            destruct_names.append(param.var_name)
            type_fields.append(f"{param.var_name}{optional}: {param.ts_type}")

        if operation.body_type:
            optional = '' if operation.body_required else '?'
            destruct_names.append('body')
            type_fields.append(f"body{optional}: {operation.body_type}")

        if type_fields:
            destruct_decl = ', '.join(destruct_names)
            type_decl = '; '.join(type_fields)
            signature = f"({{ {destruct_decl} }}: {{ {type_decl} }})"
        else:
            signature = "()"

        lines.append(f"  async {operation.method_name}{signature}: Promise<{return_type}> {{")

        if operation.query_params:
            lines.append("    const queryParams: Record<string, unknown> = {")
            for param in operation.query_params:
                property_name = self._format_property_name(param.name)
                if property_name == param.var_name:
                    lines.append(f"      {property_name},")
                else:
                    lines.append(f"      {property_name}: {param.var_name},")
            lines.append("    };")

        if operation.path_segments:
            segments_expr = ', '.join(
                [
                    self._quote_literal(segment.literal)
                    if segment.literal is not None
                    else segment.parameter.var_name
                    for segment in operation.path_segments
                ]
            )
            url_expr = f"this.buildPath({segments_expr})"
        else:
            url_expr = 'this.basePath'

        call_line = self._build_client_call(operation, return_type, url_expr)
        lines.append(f"    {call_line}")
        lines.append("  }")

        return lines, set(operation.type_dependencies)

    def _build_client_call(self, operation: OperationMethod, return_type: str, url_expr: str) -> str:
        method = operation.http_method.lower()
        client_method = self._client_method_name(method)
        generic = return_type or 'void'

        has_query = bool(operation.query_params)
        has_body = bool(operation.body_type)
        include_body = has_body and client_method in {'post', 'put', 'patch', 'delete'}

        if client_method != 'request':
            args: List[str] = [url_expr]
            if include_body:
                args.append('body')
            if has_query:
                options = '{ params: queryParams }'
                args.append(options)
            return f"return this.client.{client_method}<{generic}>({', '.join(args)});"

        options_parts = [f"method: '{method.upper()}'"]
        if include_body:
            options_parts.append("body: body")
        if has_query:
            options_parts.append("params: queryParams")
        options = '{ ' + ', '.join(options_parts) + ' }'
        return f"return this.client.request<{generic}>({url_expr}, {options});"

    @staticmethod
    def _client_method_name(method: str) -> str:
        mapping = {
            'get': 'get',
            'post': 'post',
            'put': 'put',
            'patch': 'patch',
            'delete': 'delete',
        }
        return mapping.get(method, 'request')

    @staticmethod
    def _format_property_name(name: str) -> str:
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
            return name
        escaped = name.replace("'", "\\'")
        return f"'{escaped}'"

    def _sanitize_identifier(self, name: str) -> str:
        cleaned = re.sub(r'[^0-9a-zA-Z]+', ' ', name)
        parts = [part for part in cleaned.strip().split(' ') if part]
        if not parts:
            return 'param'

        first = parts[0].lower()
        rest = ''.join(part.capitalize() for part in parts[1:])
        candidate = first + rest

        if candidate[0].isdigit():
            candidate = f"_{candidate}"

        if candidate in RESERVED_IDENTIFIERS:
            candidate += '_value'

        return candidate

    def _camel_case(self, value: str) -> str:
        cleaned = re.sub(r'[^0-9a-zA-Z]+', ' ', value)
        parts = [part for part in cleaned.strip().split(' ') if part]
        if not parts:
            return 'operation'
        first = parts[0].lower()
        rest = ''.join(part.capitalize() for part in parts[1:])
        candidate = first + rest
        if candidate in RESERVED_IDENTIFIERS:
            candidate += 'Op'
        return candidate

    def _pascal_case(self, value: str) -> str:
        cleaned = re.sub(r'[^0-9a-zA-Z]+', ' ', value)
        parts = [part.capitalize() for part in cleaned.strip().split(' ') if part]
        candidate = ''.join(parts) or 'Client'
        if candidate in RESERVED_IDENTIFIERS:
            candidate += 'Client'
        return candidate

    @staticmethod
    def _quote_literal(value: str) -> str:
        escaped = value.replace("'", "\\'")
        return f"'{escaped}'"

    def _generate_crud_methods(self, meta: InterfaceMetadata) -> tuple[list[str], Set[str]]:
        lines: list[str] = []
        type_names: Set[str] = set()

        if meta.is_custom:
            return lines, type_names

        if meta.create is not None:
            payload_type = meta.create.__name__
            return_type = (meta.get or meta.create).__name__
            type_names.update({payload_type, return_type})
            lines.extend(
                [
                    "",
                    f"  async create(payload: {payload_type}): Promise<{return_type}> {{",
                    f"    return this.client.post<{return_type}>(this.basePath, payload);",
                    "  }",
                ]
            )

        if meta.get is not None:
            return_type = meta.get.__name__
            type_names.add(return_type)
            lines.extend(
                [
                    "",
                    f"  async get(id: string | number): Promise<{return_type}> {{",
                    f"    return this.client.get<{return_type}>(this.buildPath(id));",
                    "  }",
                ]
            )

        if meta.list_model is not None:
            item_type = meta.list_model.__name__
            params_type = meta.query.__name__ if meta.query is not None else "Record<string, unknown>"
            type_names.add(item_type)
            if meta.query is not None:
                type_names.add(params_type)
            lines.extend(
                [
                    "",
                    f"  async list(params?: {params_type}): Promise<{item_type}[]> {{",
                    f"    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;",
                    f"    return this.client.get<{item_type}[]>(this.basePath, queryParams ? {{ params: queryParams }} : undefined);",
                    "  }",
                ]
            )

        if meta.update is not None:
            payload_type = meta.update.__name__
            return_type = (meta.get or meta.update).__name__
            type_names.update({payload_type, return_type})
            lines.extend(
                [
                    "",
                    f"  async update(id: string | number, payload: {payload_type}): Promise<{return_type}> {{",
                    f"    return this.client.patch<{return_type}>(this.buildPath(id), payload);",
                    "  }",
                ]
            )

        if meta.create is not None or meta.update is not None:
            lines.extend(
                [
                    "",
                    "  async delete(id: string | number): Promise<void> {",
                    "    await this.client.delete<void>(this.buildPath(id));",
                    "  }",
                ]
            )

        if meta.has_archive:
            lines.extend(
                [
                    "",
                    "  async archive(id: string | number): Promise<void> {",
                    "    await this.client.patch<void>(this.buildPath(id, 'archive'));",
                    "  }",
                ]
            )

        return lines, type_names

    def _generate_extra_methods(self, meta: InterfaceMetadata) -> tuple[list[str], Set[str]]:
        lines: list[str] = []
        type_names: Set[str] = set()

        for operation in meta.extra_operations:
            method_lines, method_types = self._build_operation_method(meta, operation)
            lines.extend(method_lines)
            type_names |= method_types

        return lines, type_names

    def _write_file(self, filename: str, content: str) -> Path:
        path = self.output_dir / filename
        path.write_text(content + "\n", encoding="utf-8")
        self.generated_files.add(path)
        print(f"✅ Generated {path.relative_to(PROJECT_ROOT)}")
        return path

    def _clean_output_dir(self) -> None:
        for item in self.output_dir.glob("*.ts"):
            try:
                item.unlink()
            except FileNotFoundError:
                continue

    def _remove_stale_files(self, generated: Iterable[Path]) -> None:
        keep = {path.resolve() for path in generated}

        for file in self.output_dir.glob("*.ts"):
            if file.resolve() not in keep:
                try:
                    file.unlink()
                    print(f"🧹 Removed stale client file {file.relative_to(PROJECT_ROOT)}")
                except FileNotFoundError:
                    continue


def main(output_dir: Optional[Path] = None, clean: bool = False, include_timestamp: bool = False) -> list[Path]:
    if output_dir is None:
        output_dir = PROJECT_ROOT / "frontend" / "src" / "api" / "generated"

    generator = TypeScriptClientGenerator(output_dir, include_timestamp=include_timestamp)
    return generator.generate(clean=clean)


if __name__ == "__main__":
    main()

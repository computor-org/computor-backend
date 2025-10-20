#!/usr/bin/env python3
"""
Generate error code definitions for TypeScript, JSON, and Markdown documentation.

This script reads error_registry.yaml and generates:
1. TypeScript interfaces and constants for frontend
2. JSON error catalog for VSCode extension
3. Markdown documentation for developers
"""

import yaml
import json
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime


def load_error_registry(registry_path: Path) -> Dict[str, Any]:
    """Load error registry YAML file."""
    with open(registry_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_typescript(errors: List[Dict], output_path: Path) -> None:
    """
    Generate TypeScript interfaces and constants.

    Generates:
    - Error code constants
    - ErrorResponse interface
    - Error category and severity enums
    - Utility functions for error handling
    """
    ts_content = f'''/**
 * Auto-generated error code definitions
 *
 * DO NOT EDIT MANUALLY
 * Generated at: {datetime.now().isoformat()}
 *
 * To regenerate: bash generate_error_codes.sh
 */

// ============================================================================
// Error Categories and Severities
// ============================================================================

export enum ErrorCategory {{
  AUTHENTICATION = "authentication",
  AUTHORIZATION = "authorization",
  VALIDATION = "validation",
  NOT_FOUND = "not_found",
  CONFLICT = "conflict",
  RATE_LIMIT = "rate_limit",
  EXTERNAL_SERVICE = "external_service",
  DATABASE = "database",
  INTERNAL = "internal",
  NOT_IMPLEMENTED = "not_implemented",
}}

export enum ErrorSeverity {{
  INFO = "info",
  WARNING = "warning",
  ERROR = "error",
  CRITICAL = "critical",
}}

// ============================================================================
// Error Response Interface
// ============================================================================

export interface ErrorDebugInfo {{
  timestamp: string;
  request_id?: string;
  function?: string;
  file?: string;
  line?: number;
  user_id?: string;
  additional_context?: Record<string, any>;
}}

export interface ErrorResponse {{
  error_code: string;
  message: string;
  details?: any;
  severity: ErrorSeverity;
  category: ErrorCategory;
  retry_after?: number;
  documentation_url?: string;
  debug?: ErrorDebugInfo;
}}

// ============================================================================
// Error Code Constants
// ============================================================================

export const ErrorCodes = {{
'''

    # Generate error code constants
    for error in errors:
        code = error["code"]
        title = error["title"]
        ts_content += f'  {code}: "{code}", // {title}\n'

    ts_content += '''} as const;

export type ErrorCode = typeof ErrorCodes[keyof typeof ErrorCodes];

// ============================================================================
// Error Definitions
// ============================================================================

export interface ErrorDefinition {
  code: string;
  httpStatus: number;
  category: ErrorCategory;
  severity: ErrorSeverity;
  title: string;
  message: {
    plain: string;
    markdown?: string;
    html?: string;
  };
  retryAfter?: number;
  documentationUrl?: string;
}

export const ERROR_DEFINITIONS: Record<string, ErrorDefinition> = {
'''

    # Generate error definitions
    for i, error in enumerate(errors):
        code = error["code"]
        ts_content += f'''  {code}: {{
    code: "{code}",
    httpStatus: {error["http_status"]},
    category: ErrorCategory.{error["category"].upper()},
    severity: ErrorSeverity.{error["severity"].upper()},
    title: "{error["title"]}",
    message: {{
      plain: {json.dumps(error["message"]["plain"])},
      markdown: {json.dumps(error["message"].get("markdown"))},
      html: {json.dumps(error["message"].get("html"))},
    }},
    retryAfter: {error.get("retry_after") or "undefined"},
    documentationUrl: {json.dumps(error.get("documentation_url"))},
  }}{',' if i < len(errors) - 1 else ''}
'''

    ts_content += '''};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Get error definition by code
 */
export function getErrorDefinition(code: string): ErrorDefinition | undefined {
  return ERROR_DEFINITIONS[code];
}

/**
 * Get user-friendly error message
 */
export function getErrorMessage(error: ErrorResponse, format: "plain" | "markdown" | "html" = "plain"): string {
  const definition = getErrorDefinition(error.error_code);

  if (!definition) {
    return error.message;
  }

  // Use custom message if provided, otherwise use definition
  if (error.message) {
    return error.message;
  }

  const formatMessage = definition.message[format];
  return formatMessage || definition.message.plain;
}

/**
 * Check if error is retryable
 */
export function isRetryableError(error: ErrorResponse): boolean {
  const retryableCategories = [
    ErrorCategory.RATE_LIMIT,
    ErrorCategory.EXTERNAL_SERVICE,
    ErrorCategory.DATABASE,
  ];

  return retryableCategories.includes(error.category);
}

/**
 * Get retry delay in milliseconds
 */
export function getRetryDelay(error: ErrorResponse): number | undefined {
  if (!isRetryableError(error)) {
    return undefined;
  }

  if (error.retry_after) {
    return error.retry_after * 1000; // Convert seconds to milliseconds
  }

  // Default retry delays by category
  const defaultDelays: Record<ErrorCategory, number> = {
    [ErrorCategory.RATE_LIMIT]: 60000, // 1 minute
    [ErrorCategory.EXTERNAL_SERVICE]: 30000, // 30 seconds
    [ErrorCategory.DATABASE]: 5000, // 5 seconds
    [ErrorCategory.AUTHENTICATION]: 0,
    [ErrorCategory.AUTHORIZATION]: 0,
    [ErrorCategory.VALIDATION]: 0,
    [ErrorCategory.NOT_FOUND]: 0,
    [ErrorCategory.CONFLICT]: 0,
    [ErrorCategory.INTERNAL]: 0,
    [ErrorCategory.NOT_IMPLEMENTED]: 0,
  };

  return defaultDelays[error.category] || 0;
}

/**
 * Format error for display in UI
 */
export interface FormattedError {
  title: string;
  message: string;
  severity: ErrorSeverity;
  canRetry: boolean;
  retryDelay?: number;
  documentationUrl?: string;
}

export function formatErrorForDisplay(error: ErrorResponse): FormattedError {
  const definition = getErrorDefinition(error.error_code);

  return {
    title: definition?.title || "Error",
    message: getErrorMessage(error, "markdown"),
    severity: error.severity,
    canRetry: isRetryableError(error),
    retryDelay: getRetryDelay(error),
    documentationUrl: error.documentation_url || definition?.documentationUrl,
  };
}

/**
 * Get all errors by category
 */
export function getErrorsByCategory(category: ErrorCategory): ErrorDefinition[] {
  return Object.values(ERROR_DEFINITIONS).filter(
    (def) => def.category === category
  );
}

/**
 * Get all errors by HTTP status
 */
export function getErrorsByHttpStatus(httpStatus: number): ErrorDefinition[] {
  return Object.values(ERROR_DEFINITIONS).filter(
    (def) => def.httpStatus === httpStatus
  );
}
'''

    # Write TypeScript file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ts_content)

    print(f"✓ Generated TypeScript definitions: {output_path}")


def generate_json_catalog(errors: List[Dict], output_path: Path) -> None:
    """
    Generate full JSON error catalog for internal use (includes all metadata).
    """
    catalog = {
        "version": "1.0.0",
        "generated_at": datetime.now().isoformat(),
        "error_count": len(errors),
        "errors": {}
    }

    for error in errors:
        catalog["errors"][error["code"]] = {
            "code": error["code"],
            "http_status": error["http_status"],
            "category": error["category"],
            "severity": error["severity"],
            "title": error["title"],
            "message": error["message"],
            "retry_after": error.get("retry_after"),
            "documentation_url": error.get("documentation_url"),
            "internal_description": error.get("internal_description", ""),
            "affected_functions": error.get("affected_functions", []),
            "common_causes": error.get("common_causes", []),
            "resolution_steps": error.get("resolution_steps", []),
        }

    # Write JSON file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

    print(f"✓ Generated JSON catalog (full): {output_path}")


def generate_vscode_catalog(errors: List[Dict], output_path: Path) -> None:
    """
    Generate lightweight JSON catalog for VSCode extension distribution.

    This version contains only user-facing information and is safe to bundle
    in the .vsix file. It excludes internal/developer metadata like:
    - documentation_url (may be internal)
    - internal_description
    - affected_functions
    - common_causes (developer-focused)
    - resolution_steps (developer-focused)
    """
    catalog = {
        "version": "1.0.0",
        "generated_at": datetime.now().isoformat(),
        "error_count": len(errors),
        "errors": {}
    }

    for error in errors:
        catalog["errors"][error["code"]] = {
            "code": error["code"],
            "http_status": error["http_status"],
            "category": error["category"],
            "severity": error["severity"],
            "title": error["title"],
            "message": {
                "plain": error["message"]["plain"],
                "markdown": error["message"].get("markdown"),
                "html": error["message"].get("html"),
            },
            "retry_after": error.get("retry_after"),
        }

    # Write JSON file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

    print(f"✓ Generated JSON catalog (VSCode): {output_path}")


def generate_markdown_docs(errors: List[Dict], output_path: Path) -> None:
    """
    Generate Markdown documentation for developers.
    """
    md_content = f'''# Error Code Reference

**Auto-generated documentation**
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Total errors:** {len(errors)}

To regenerate: `bash generate_error_codes.sh`

---

## Table of Contents

'''

    # Group errors by category
    categories = {}
    for error in errors:
        category = error["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append(error)

    # Generate TOC
    for category in sorted(categories.keys()):
        category_title = category.replace("_", " ").title()
        md_content += f"- [{category_title}](#{category.replace('_', '-')})\n"

    md_content += "\n---\n\n"

    # Generate sections by category
    for category in sorted(categories.keys()):
        category_title = category.replace("_", " ").title()
        category_errors = categories[category]

        md_content += f"## {category_title}\n\n"

        for error in category_errors:
            md_content += f"### {error['code']} - {error['title']}\n\n"
            md_content += f"**HTTP Status:** `{error['http_status']}`  \n"
            md_content += f"**Severity:** `{error['severity']}`  \n"
            md_content += f"**Category:** `{error['category']}`  \n"

            if error.get("retry_after"):
                md_content += f"**Retry After:** {error['retry_after']} seconds  \n"

            if error.get("documentation_url"):
                md_content += f"**Documentation:** [{error['documentation_url']}]({error['documentation_url']})  \n"

            md_content += "\n"

            # Description
            md_content += "**Description:**  \n"
            md_content += f"{error.get('internal_description', 'No description available')}\n\n"

            # Message
            md_content += "**User Message:**  \n"
            md_content += f"> {error['message']['plain']}\n\n"

            # Affected functions
            if error.get("affected_functions"):
                md_content += "**Affected Functions:**\n"
                for func in error["affected_functions"]:
                    md_content += f"- `{func}`\n"
                md_content += "\n"

            # Common causes
            if error.get("common_causes"):
                md_content += "**Common Causes:**\n"
                for cause in error["common_causes"]:
                    md_content += f"- {cause}\n"
                md_content += "\n"

            # Resolution steps
            if error.get("resolution_steps"):
                md_content += "**Resolution Steps:**\n"
                for i, step in enumerate(error["resolution_steps"], 1):
                    md_content += f"{i}. {step}\n"
                md_content += "\n"

            md_content += "---\n\n"

    # Write Markdown file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"✓ Generated Markdown documentation: {output_path}")


def generate_python_constants(errors: List[Dict], output_path: Path) -> None:
    """
    Generate Python constants file for backend usage.
    """
    py_content = f'''"""
Auto-generated error code constants

DO NOT EDIT MANUALLY
Generated at: {datetime.now().isoformat()}

To regenerate: bash generate_error_codes.sh
"""

from enum import Enum


class ErrorCode(str, Enum):
    """Error code constants."""
'''

    for error in errors:
        code = error["code"]
        title = error["title"]
        py_content += f'    {code} = "{code}"  # {title}\n'

    py_content += '''

# Mapping of HTTP status codes to default error codes
HTTP_STATUS_TO_ERROR_CODE = {
'''

    # Group by HTTP status
    status_map = {}
    for error in errors:
        status = error["http_status"]
        if status not in status_map:
            status_map[status] = error["code"]

    for status, code in sorted(status_map.items()):
        py_content += f'    {status}: ErrorCode.{code},\n'

    py_content += '''}

# Mapping of error categories
ERROR_CATEGORIES = {
'''

    for error in errors:
        code = error["code"]
        category = error["category"]
        py_content += f'    ErrorCode.{code}: "{category}",\n'

    py_content += '''}
'''

    # Write Python file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(py_content)

    print(f"✓ Generated Python constants: {output_path}")


def main():
    """Main generator function."""
    # Paths
    script_dir = Path(__file__).parent
    registry_path = script_dir / "computor-backend" / "error_registry.yaml"

    # Output paths - following project structure conventions
    # TypeScript goes to generated/types/ (shared by frontend projects)
    ts_output = script_dir / "generated" / "types" / "error-codes.ts"

    # JSON catalog and docs go to generated/errors/
    errors_dir = script_dir / "generated" / "errors"
    json_output = errors_dir / "error-catalog.json"
    json_vscode_output = errors_dir / "error-catalog.vscode.json"
    md_output = errors_dir / "ERROR_CODES.md"

    # Python constants for computor-types
    py_output = script_dir / "computor-types" / "src" / "computor_types" / "generated" / "error_codes.py"

    # Load registry
    print(f"Loading error registry from: {registry_path}")
    data = load_error_registry(registry_path)
    errors = data.get("errors", [])
    print(f"Found {len(errors)} error definitions")

    # Generate outputs
    print("\nGenerating output files...")
    generate_typescript(errors, ts_output)
    generate_json_catalog(errors, json_output)
    generate_vscode_catalog(errors, json_vscode_output)
    generate_markdown_docs(errors, md_output)
    generate_python_constants(errors, py_output)

    print("\n✓ All error code files generated successfully!")
    print(f"\nGenerated files:")
    print(f"  - TypeScript: {ts_output}")
    print(f"  - JSON catalog (full): {json_output}")
    print(f"  - JSON catalog (VSCode): {json_vscode_output}")
    print(f"  - Documentation: {md_output}")
    print(f"  - Python constants: {py_output}")


if __name__ == "__main__":
    main()

"""
Error registry management for loading and accessing error definitions.

This module loads the error_registry.yaml file and provides utilities
to access error definitions by code.
"""

import yaml
from pathlib import Path
from typing import Dict, Optional
from functools import lru_cache

from computor_types.errors import ErrorDefinition, ErrorMessageFormat


# Cache for error registry
_error_registry: Optional[Dict[str, ErrorDefinition]] = None


def load_error_registry() -> Dict[str, ErrorDefinition]:
    """
    Load error registry from YAML file.

    Returns:
        Dictionary mapping error codes to ErrorDefinition objects

    Raises:
        FileNotFoundError: If error_registry.yaml is not found
        ValueError: If YAML is malformed or validation fails
    """
    global _error_registry

    if _error_registry is not None:
        return _error_registry

    # Find error_registry.yaml in project root
    # Go up from computor-backend/src/computor_backend/error_handling/error_registry.py
    # to the project root
    current_file = Path(__file__)
    # Up to error_handling -> computor_backend -> src -> computor-backend -> project root
    project_root = current_file.parent.parent.parent.parent.parent
    registry_path = project_root / "error_registry.yaml"

    if not registry_path.exists():
        raise FileNotFoundError(
            f"Error registry not found at {registry_path}. "
            "Please ensure error_registry.yaml exists in project root."
        )

    # Load YAML
    with open(registry_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "errors" not in data:
        raise ValueError("Invalid error registry format: missing 'errors' key")

    # Parse errors into ErrorDefinition objects
    _error_registry = {}
    for error_dict in data["errors"]:
        try:
            # Parse message format
            message_data = error_dict.get("message", {})
            message = ErrorMessageFormat(
                plain=message_data.get("plain", ""),
                markdown=message_data.get("markdown"),
                html=message_data.get("html"),
            )

            # Create ErrorDefinition
            error_def = ErrorDefinition(
                code=error_dict["code"],
                http_status=error_dict["http_status"],
                category=error_dict["category"],
                severity=error_dict["severity"],
                title=error_dict["title"],
                message=message,
                retry_after=error_dict.get("retry_after"),
                documentation_url=error_dict.get("documentation_url"),
                internal_description=error_dict.get("internal_description", ""),
                affected_functions=error_dict.get("affected_functions", []),
                common_causes=error_dict.get("common_causes", []),
                resolution_steps=error_dict.get("resolution_steps", []),
            )

            _error_registry[error_def.code] = error_def

        except Exception as e:
            raise ValueError(
                f"Failed to parse error definition for {error_dict.get('code', 'unknown')}: {e}"
            )

    return _error_registry


def get_error_definition(error_code: str) -> ErrorDefinition:
    """
    Get error definition by code.

    Args:
        error_code: Error code (e.g., "AUTH_001")

    Returns:
        ErrorDefinition for the given code

    Raises:
        KeyError: If error code not found in registry
    """
    registry = load_error_registry()

    if error_code not in registry:
        # Return a default error definition for unknown codes
        return ErrorDefinition(
            code="UNKNOWN",
            http_status=500,
            category="internal",
            severity="error",
            title="Unknown Error",
            message=ErrorMessageFormat(
                plain=f"An error occurred (code: {error_code})",
                markdown=f"**Unknown Error**\n\nAn error occurred with code: `{error_code}`",
                html=f"<strong>Unknown Error</strong><p>An error occurred with code: <code>{error_code}</code></p>",
            ),
            internal_description=f"Unknown error code: {error_code}",
            affected_functions=[],
            common_causes=[],
            resolution_steps=["Contact support"],
        )

    return registry[error_code]


def get_all_error_codes() -> list[str]:
    """
    Get list of all registered error codes.

    Returns:
        List of error codes
    """
    registry = load_error_registry()
    return list(registry.keys())


def get_errors_by_category(category: str) -> list[ErrorDefinition]:
    """
    Get all errors for a specific category.

    Args:
        category: Error category (e.g., "authentication", "validation")

    Returns:
        List of ErrorDefinition objects in the category
    """
    registry = load_error_registry()
    return [
        error_def
        for error_def in registry.values()
        if error_def.category == category
    ]


def get_errors_by_http_status(http_status: int) -> list[ErrorDefinition]:
    """
    Get all errors for a specific HTTP status code.

    Args:
        http_status: HTTP status code (e.g., 404, 500)

    Returns:
        List of ErrorDefinition objects with that status code
    """
    registry = load_error_registry()
    return [
        error_def
        for error_def in registry.values()
        if error_def.http_status == http_status
    ]


@lru_cache(maxsize=1)
def get_registry_version() -> str:
    """
    Get error registry version.

    Returns:
        Registry version string
    """
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent.parent
    registry_path = project_root / "error_registry.yaml"

    with open(registry_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data.get("version", "unknown")


def validate_error_registry() -> tuple[bool, list[str]]:
    """
    Validate error registry for completeness and consistency.

    Returns:
        Tuple of (is_valid, list of validation errors)
    """
    errors = []

    try:
        registry = load_error_registry()
    except Exception as e:
        return False, [f"Failed to load registry: {e}"]

    # Check for duplicate codes
    codes = [error_def.code for error_def in registry.values()]
    duplicates = [code for code in codes if codes.count(code) > 1]
    if duplicates:
        errors.append(f"Duplicate error codes found: {set(duplicates)}")

    # Check each error definition
    for code, error_def in registry.items():
        # Validate message formats
        if not error_def.message.plain:
            errors.append(f"{code}: Missing plain text message")

        # Validate HTTP status codes
        if error_def.http_status < 100 or error_def.http_status > 599:
            errors.append(f"{code}: Invalid HTTP status code {error_def.http_status}")

        # Validate internal documentation
        if not error_def.internal_description:
            errors.append(f"{code}: Missing internal description")

    return len(errors) == 0, errors

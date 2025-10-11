"""
Field transformation utilities for deployment mapping.

Provides functions to transform raw table values into deployment-ready values.
"""

import re
from typing import Any, Dict, List, Optional, Union


class FieldTransformer:
    """Handles field value transformations during mapping."""

    @staticmethod
    def extract_username(email: str) -> str:
        """
        Extract username from email address.

        Example: "john.doe@example.com" -> "john.doe"
        """
        if not email or "@" not in email:
            return email
        return email.split("@")[0]

    @staticmethod
    def to_lower(value: str) -> str:
        """Convert string to lowercase."""
        if value is None:
            return None
        return str(value).lower()

    @staticmethod
    def to_upper(value: str) -> str:
        """Convert string to uppercase."""
        if value is None:
            return None
        return str(value).upper()

    @staticmethod
    def strip(value: str) -> str:
        """Strip whitespace from string."""
        if value is None:
            return None
        return str(value).strip()

    @staticmethod
    def to_bool(
        value: Any,
        true_values: Optional[List[str]] = None,
        false_values: Optional[List[str]] = None
    ) -> bool:
        """
        Convert value to boolean.

        Args:
            value: Value to convert
            true_values: List of strings that represent True
            false_values: List of strings that represent False

        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value

        if true_values is None:
            true_values = ["true", "yes", "y", "1", "on"]
        if false_values is None:
            false_values = ["false", "no", "n", "0", "off", ""]

        str_value = str(value).lower().strip()

        if str_value in true_values:
            return True
        if str_value in false_values:
            return False

        # Default: try Python's bool conversion
        return bool(value)

    @staticmethod
    def to_int(value: Any) -> Optional[int]:
        """
        Convert value to integer.

        Returns None if conversion fails.
        """
        if value is None or value == "":
            return None
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def to_float(value: Any) -> Optional[float]:
        """
        Convert value to float.

        Returns None if conversion fails.
        """
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def split(value: str, separator: str = ",") -> List[str]:
        """
        Split string into list.

        Args:
            value: String to split
            separator: Separator character (default: comma)

        Returns:
            List of stripped strings
        """
        if not value:
            return []
        return [item.strip() for item in str(value).split(separator)]

    @staticmethod
    def join(value: List[Any], separator: str = ",") -> str:
        """
        Join list into string.

        Args:
            value: List to join
            separator: Separator character (default: comma)

        Returns:
            Joined string
        """
        if not value:
            return ""
        return separator.join(str(item) for item in value)

    @staticmethod
    def normalize_path(path: str) -> str:
        """
        Normalize path string.

        Removes leading/trailing slashes, collapses multiple slashes.
        """
        if not path:
            return ""
        # Remove leading/trailing slashes
        path = path.strip("/").strip()
        # Collapse multiple slashes
        path = re.sub(r"/+", "/", path)
        return path

    @staticmethod
    def extract_path_parts(path: str, separator: str = "/") -> List[str]:
        """
        Extract parts from a path string.

        Example: "kit/prog/prog1" -> ["kit", "prog", "prog1"]

        Args:
            path: Path string
            separator: Path separator (default: /)

        Returns:
            List of path components
        """
        if not path:
            return []
        normalized = FieldTransformer.normalize_path(path)
        return [part.strip() for part in normalized.split(separator) if part.strip()]

    @staticmethod
    def substitute_template(template: str, context: Dict[str, Any]) -> str:
        """
        Substitute template variables with context values.

        Template syntax: {variable_name}

        Args:
            template: Template string with {var} placeholders
            context: Dictionary of variable values

        Returns:
            Substituted string

        Example:
            >>> substitute_template("{first}_{last}", {"first": "john", "last": "doe"})
            "john_doe"
        """
        if not template or "{" not in template:
            return template

        result = template
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value) if value is not None else "")

        return result

    @staticmethod
    def apply_transformation(
        value: Any,
        transform_name: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Apply a named transformation to a value.

        Args:
            value: Value to transform
            transform_name: Name of transformation function
            context: Context dictionary for template substitution
            **kwargs: Additional arguments for the transformation

        Returns:
            Transformed value

        Raises:
            ValueError: If transformation name is unknown
        """
        transformer = FieldTransformer()

        # Map transformation names to methods
        transformations = {
            "extract_username": transformer.extract_username,
            "to_lower": transformer.to_lower,
            "to_upper": transformer.to_upper,
            "strip": transformer.strip,
            "to_bool": transformer.to_bool,
            "to_int": transformer.to_int,
            "to_float": transformer.to_float,
            "split": transformer.split,
            "join": transformer.join,
            "normalize_path": transformer.normalize_path,
            "extract_path_parts": transformer.extract_path_parts,
        }

        if transform_name not in transformations:
            raise ValueError(f"Unknown transformation: {transform_name}")

        transform_func = transformations[transform_name]

        # Apply transformation with kwargs if provided
        try:
            if kwargs:
                return transform_func(value, **kwargs)
            else:
                return transform_func(value)
        except TypeError:
            # Function doesn't accept kwargs, try without
            return transform_func(value)

    @staticmethod
    def is_null_value(value: Any, null_values: Optional[List[str]] = None) -> bool:
        """
        Check if value should be treated as null/empty.

        Args:
            value: Value to check
            null_values: List of strings to treat as null

        Returns:
            True if value is null/empty
        """
        if value is None:
            return True

        if null_values is None:
            null_values = ["", "null", "NULL", "None", "N/A", "-", "n/a"]

        str_value = str(value).strip()
        return str_value in null_values

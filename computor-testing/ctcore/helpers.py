"""
Computor Testing Core - Shared Helper Functions

Language-agnostic helper functions for testing frameworks.
"""

import re
from typing import Any, List, Union


def get_property_as_list(prop: Any) -> List[str]:
    """
    Convert a property to a list.

    Args:
        prop: Property value (can be None, str, or list)

    Returns:
        List of strings (empty strings and None values filtered out)
    """
    if prop is None:
        return []
    if isinstance(prop, str):
        # MATLAB/R use "" for null values
        if prop == "":
            return []
        return [prop]
    if isinstance(prop, list):
        # Filter out empty strings and None values from list
        return [item for item in prop if item is not None and item != ""]
    return [str(prop)]


def get_abbr(value: Any, max_len: int = 50) -> str:
    """
    Get abbreviated string representation of a value.

    Args:
        value: Value to abbreviate
        max_len: Maximum length of output

    Returns:
        Abbreviated string representation
    """
    s = str(value)
    if len(s) > max_len:
        return s[:max_len - 3] + "..."
    return s


def normalize_name(name: str) -> str:
    """
    Normalize a variable name to a valid Python identifier.

    Args:
        name: Original variable name

    Returns:
        Normalized name safe for use as Python identifier
    """
    # Replace invalid characters with underscores
    result = ""
    for char in name:
        if char.isalnum() or char == '_':
            result += char
        else:
            result += '_'

    # Ensure it doesn't start with a digit
    if result and result[0].isdigit():
        result = '_' + result

    return result


def token_exchange(text: Union[str, List[str]], file_list: List[str],
                   command_list: List[str]) -> Union[str, List[str]]:
    """
    Replace tokens in text with actual file/command names.

    Tokens like #file_1# or #command_1# are replaced with actual values
    from the provided lists.

    Args:
        text: Text or list of texts to process
        file_list: List of file names for #file_N# tokens
        command_list: List of command names for #command_N# tokens

    Returns:
        Text with tokens replaced
    """
    was_string = isinstance(text, str)
    if was_string:
        texts = [text]
    else:
        texts = list(text)

    result = []
    for t in texts:
        # Replace #command_N# tokens
        def replace_command(match):
            idx = int(match.group(1)) - 1  # 1-indexed
            if 0 <= idx < len(command_list):
                return command_list[idx]
            return match.group(0)

        t = re.sub(r'#command_(\d+)#', replace_command, t)

        # Replace #file_N# tokens
        def replace_file(match):
            idx = int(match.group(1)) - 1  # 1-indexed
            if 0 <= idx < len(file_list):
                return file_list[idx]
            return match.group(0)

        t = re.sub(r'#file_(\d+)#', replace_file, t)
        result.append(t)

    return result[0] if was_string else result


def compare_values(actual: Any, expected: Any,
                   relative_tolerance: float = 1e-12,
                   absolute_tolerance: float = 0.0001,
                   type_check: bool = True,
                   shape_check: bool = True) -> tuple[bool, str]:
    """
    Compare two values with tolerance for numeric types.

    Args:
        actual: Actual value from student code
        expected: Expected value from reference
        relative_tolerance: Relative tolerance for numeric comparison
        absolute_tolerance: Absolute tolerance for numeric comparison
        type_check: Whether to check type equality
        shape_check: Whether to check shape/dimensions

    Returns:
        Tuple of (is_equal, message)
    """
    import numpy as np

    # Handle None
    if expected is None:
        if actual is None:
            return True, "Both values are None"
        return False, f"Expected None, got {type(actual).__name__}"

    if actual is None:
        return False, f"Expected {type(expected).__name__}, got None"

    # Type check
    if type_check and type(actual) != type(expected):
        # Allow numeric type coercion
        if not (isinstance(actual, (int, float, np.number)) and
                isinstance(expected, (int, float, np.number))):
            return False, f"Type mismatch: {type(actual).__name__} vs {type(expected).__name__}"

    # Handle numpy arrays
    if isinstance(expected, np.ndarray):
        if not isinstance(actual, np.ndarray):
            return False, f"Expected ndarray, got {type(actual).__name__}"

        if shape_check and actual.shape != expected.shape:
            return False, f"Shape mismatch: {actual.shape} vs {expected.shape}"

        if np.issubdtype(expected.dtype, np.number):
            if np.allclose(actual, expected, rtol=relative_tolerance, atol=absolute_tolerance, equal_nan=True):
                return True, "Arrays are equal within tolerance"
            return False, "Array values differ"
        else:
            if np.array_equal(actual, expected):
                return True, "Arrays are equal"
            return False, "Array values differ"

    # Handle numeric scalars
    if isinstance(expected, (int, float, np.number)):
        if not isinstance(actual, (int, float, np.number)):
            return False, f"Expected numeric, got {type(actual).__name__}"

        # Explicit NaN handling
        actual_nan = np.isnan(actual) if isinstance(actual, (float, np.floating)) else False
        expected_nan = np.isnan(expected) if isinstance(expected, (float, np.floating)) else False
        if actual_nan or expected_nan:
            if actual_nan and expected_nan:
                return True, "Both values are NaN"
            return False, f"NaN mismatch: actual={'NaN' if actual_nan else actual}, expected={'NaN' if expected_nan else expected}"

        if abs(expected) > 0:
            rel_diff = abs(actual - expected) / abs(expected)
            if rel_diff <= relative_tolerance:
                return True, "Values are equal within relative tolerance"

        abs_diff = abs(actual - expected)
        if abs_diff <= absolute_tolerance:
            return True, "Values are equal within absolute tolerance"

        return False, f"Values differ: {actual} vs {expected}"

    # Handle strings
    if isinstance(expected, str):
        if actual == expected:
            return True, "Strings are equal"
        return False, f"String mismatch: '{actual}' vs '{expected}'"

    # Handle lists
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False, f"Expected list, got {type(actual).__name__}"

        if shape_check and len(actual) != len(expected):
            return False, f"Length mismatch: {len(actual)} vs {len(expected)}"

        for i, (a, e) in enumerate(zip(actual, expected)):
            is_equal, msg = compare_values(a, e, relative_tolerance, absolute_tolerance,
                                          type_check, shape_check)
            if not is_equal:
                return False, f"Element {i}: {msg}"

        return True, "Lists are equal"

    # Default comparison
    if actual == expected:
        return True, "Values are equal"
    return False, f"Values differ: {actual} vs {expected}"

"""
Computor Testing Core - Standard I/O Testing Utilities

Helper functions for comparing stdout/stderr output with various
matching strategies (exact, regex, fuzzy, numeric extraction, etc.)
"""

import re
from typing import Any, List, Optional, Tuple, Union
from enum import Enum


class MatchResult:
    """Result of a stdio match operation"""

    def __init__(self, success: bool, message: str = "",
                 actual: str = "", expected: str = "", details: dict = None):
        self.success = success
        self.message = message
        self.actual = actual
        self.expected = expected
        self.details = details or {}

    def __bool__(self):
        return self.success

    def __repr__(self):
        return f"MatchResult(success={self.success}, message={self.message!r})"


def normalize_output(text: str,
                     trim: bool = True,
                     normalize_newlines: bool = True,
                     ignore_whitespace: bool = False,
                     ignore_case: bool = False) -> str:
    """
    Normalize output text for comparison.

    Args:
        text: The text to normalize
        trim: Remove leading/trailing whitespace
        normalize_newlines: Convert \\r\\n to \\n
        ignore_whitespace: Collapse all whitespace to single space
        ignore_case: Convert to lowercase

    Returns:
        Normalized text
    """
    if text is None:
        return ""

    result = str(text)

    if normalize_newlines:
        result = result.replace('\r\n', '\n').replace('\r', '\n')

    if trim:
        result = result.strip()

    if ignore_whitespace:
        # Collapse multiple whitespace to single space
        result = re.sub(r'\s+', ' ', result)

    if ignore_case:
        result = result.lower()

    return result


def get_lines(text: str, normalize: bool = True) -> List[str]:
    """
    Split text into lines.

    Args:
        text: Text to split
        normalize: Whether to normalize newlines first

    Returns:
        List of lines
    """
    if normalize:
        text = text.replace('\r\n', '\n').replace('\r', '\n')

    lines = text.split('\n')

    # Remove trailing empty line if present (common from trailing newline)
    if lines and lines[-1] == '':
        lines = lines[:-1]

    return lines


def match_exact(actual: str, expected: str,
                trim: bool = True,
                normalize_newlines: bool = True,
                ignore_case: bool = False) -> MatchResult:
    """
    Exact string match.

    Args:
        actual: Actual output
        expected: Expected output
        trim: Trim whitespace
        normalize_newlines: Normalize line endings
        ignore_case: Case-insensitive comparison

    Returns:
        MatchResult indicating success/failure
    """
    actual_norm = normalize_output(actual, trim, normalize_newlines, False, ignore_case)
    expected_norm = normalize_output(expected, trim, normalize_newlines, False, ignore_case)

    if actual_norm == expected_norm:
        return MatchResult(True, "Output matches exactly")

    return MatchResult(
        False,
        "Output does not match",
        actual=actual_norm,
        expected=expected_norm
    )


def match_contains(actual: str, pattern: str,
                   ignore_case: bool = False) -> MatchResult:
    """
    Check if actual output contains the pattern.

    Args:
        actual: Actual output
        pattern: Pattern to search for
        ignore_case: Case-insensitive search

    Returns:
        MatchResult indicating success/failure
    """
    actual_search = actual.lower() if ignore_case else actual
    pattern_search = pattern.lower() if ignore_case else pattern

    if pattern_search in actual_search:
        return MatchResult(True, f"Output contains '{pattern}'")

    return MatchResult(
        False,
        f"Output does not contain '{pattern}'",
        actual=actual,
        expected=f"Contains: {pattern}"
    )


def match_starts_with(actual: str, prefix: str,
                      trim: bool = True,
                      ignore_case: bool = False) -> MatchResult:
    """
    Check if actual output starts with prefix.
    """
    actual_norm = normalize_output(actual, trim, True, False, ignore_case)
    prefix_norm = prefix.lower() if ignore_case else prefix

    if actual_norm.startswith(prefix_norm):
        return MatchResult(True, f"Output starts with '{prefix}'")

    return MatchResult(
        False,
        f"Output does not start with '{prefix}'",
        actual=actual_norm[:len(prefix_norm) + 20] + "...",
        expected=prefix
    )


def match_ends_with(actual: str, suffix: str,
                    trim: bool = True,
                    ignore_case: bool = False) -> MatchResult:
    """
    Check if actual output ends with suffix.
    """
    actual_norm = normalize_output(actual, trim, True, False, ignore_case)
    suffix_norm = suffix.lower() if ignore_case else suffix

    if actual_norm.endswith(suffix_norm):
        return MatchResult(True, f"Output ends with '{suffix}'")

    return MatchResult(
        False,
        f"Output does not end with '{suffix}'",
        actual="..." + actual_norm[-(len(suffix_norm) + 20):],
        expected=suffix
    )


def match_regexp(actual: str, pattern: str,
                 multiline: bool = False,
                 ignore_case: bool = False,
                 full_match: bool = False) -> MatchResult:
    """
    Match actual output against a regular expression.

    Args:
        actual: Actual output
        pattern: Regex pattern
        multiline: Enable multiline mode (^ and $ match line boundaries)
        ignore_case: Case-insensitive matching
        full_match: Require full string match (not just search)

    Returns:
        MatchResult with match details
    """
    flags = 0
    if multiline:
        flags |= re.MULTILINE | re.DOTALL
    if ignore_case:
        flags |= re.IGNORECASE

    try:
        if full_match:
            match = re.fullmatch(pattern, actual, flags)
        else:
            match = re.search(pattern, actual, flags)

        if match:
            return MatchResult(
                True,
                f"Output matches pattern '{pattern}'",
                details={"match": match.group(), "groups": match.groups()}
            )

        return MatchResult(
            False,
            f"Output does not match pattern '{pattern}'",
            actual=actual,
            expected=f"Pattern: {pattern}"
        )

    except re.error as e:
        return MatchResult(
            False,
            f"Invalid regex pattern: {e}",
            expected=pattern
        )


def match_line(actual: str, expected_line: str,
               line_number: Optional[int] = None,
               ignore_case: bool = False,
               trim: bool = True) -> MatchResult:
    """
    Match a specific line in the output.

    Args:
        actual: Actual output
        expected_line: Expected line content
        line_number: Specific line number to check (1-indexed), None to search all
        ignore_case: Case-insensitive comparison
        trim: Trim whitespace from lines

    Returns:
        MatchResult
    """
    lines = get_lines(actual)

    if line_number is not None:
        # Check specific line (1-indexed)
        idx = line_number - 1
        if idx < 0 or idx >= len(lines):
            return MatchResult(
                False,
                f"Line {line_number} does not exist (output has {len(lines)} lines)",
                actual=f"Total lines: {len(lines)}",
                expected=f"Line {line_number}: {expected_line}"
            )

        actual_line = lines[idx]
        if trim:
            actual_line = actual_line.strip()
            expected_line = expected_line.strip()
        if ignore_case:
            actual_line = actual_line.lower()
            expected_line = expected_line.lower()

        if actual_line == expected_line:
            return MatchResult(True, f"Line {line_number} matches")

        return MatchResult(
            False,
            f"Line {line_number} does not match",
            actual=actual_line,
            expected=expected_line
        )

    # Search for line in any position
    for i, line in enumerate(lines):
        check_line = line.strip() if trim else line
        check_expected = expected_line.strip() if trim else expected_line
        if ignore_case:
            check_line = check_line.lower()
            check_expected = check_expected.lower()

        if check_line == check_expected:
            return MatchResult(
                True,
                f"Found matching line at line {i + 1}",
                details={"line_number": i + 1}
            )

    return MatchResult(
        False,
        f"Line not found in output",
        actual=f"Total lines: {len(lines)}",
        expected=expected_line
    )


def match_line_count(actual: str, expected_count: int,
                     min_count: Optional[int] = None,
                     max_count: Optional[int] = None) -> MatchResult:
    """
    Check the number of lines in output.

    Args:
        actual: Actual output
        expected_count: Exact expected line count (ignored if min/max set)
        min_count: Minimum line count (optional)
        max_count: Maximum line count (optional)

    Returns:
        MatchResult
    """
    lines = get_lines(actual)
    count = len(lines)

    if min_count is not None and max_count is not None:
        if min_count <= count <= max_count:
            return MatchResult(
                True,
                f"Line count {count} is within range [{min_count}, {max_count}]"
            )
        return MatchResult(
            False,
            f"Line count {count} is not within range [{min_count}, {max_count}]",
            actual=str(count),
            expected=f"[{min_count}, {max_count}]"
        )

    if min_count is not None:
        if count >= min_count:
            return MatchResult(True, f"Line count {count} >= {min_count}")
        return MatchResult(
            False,
            f"Line count {count} < {min_count}",
            actual=str(count),
            expected=f">= {min_count}"
        )

    if max_count is not None:
        if count <= max_count:
            return MatchResult(True, f"Line count {count} <= {max_count}")
        return MatchResult(
            False,
            f"Line count {count} > {max_count}",
            actual=str(count),
            expected=f"<= {max_count}"
        )

    if count == expected_count:
        return MatchResult(True, f"Line count is {expected_count}")

    return MatchResult(
        False,
        f"Line count mismatch",
        actual=str(count),
        expected=str(expected_count)
    )


def extract_numbers(text: str) -> List[float]:
    """
    Extract all numbers from text.

    Args:
        text: Text to extract numbers from

    Returns:
        List of extracted float values
    """
    # Match integers, decimals, scientific notation
    pattern = r'-?\d+\.?\d*(?:[eE][+-]?\d+)?'
    matches = re.findall(pattern, text)

    numbers = []
    for m in matches:
        try:
            numbers.append(float(m))
        except ValueError:
            pass

    return numbers


def match_numeric_output(actual: str, expected: Union[float, List[float]],
                         tolerance: float = 1e-6,
                         relative_tolerance: Optional[float] = None) -> MatchResult:
    """
    Extract numbers from output and compare with expected values.

    Args:
        actual: Actual output
        expected: Expected number(s)
        tolerance: Absolute tolerance
        relative_tolerance: Relative tolerance (optional)

    Returns:
        MatchResult
    """
    actual_numbers = extract_numbers(actual)

    if isinstance(expected, (int, float)):
        expected = [float(expected)]
    else:
        expected = [float(x) for x in expected]

    if len(actual_numbers) < len(expected):
        return MatchResult(
            False,
            f"Found {len(actual_numbers)} numbers, expected at least {len(expected)}",
            actual=str(actual_numbers),
            expected=str(expected)
        )

    # Try to match expected numbers in order
    for i, exp_val in enumerate(expected):
        if i >= len(actual_numbers):
            return MatchResult(
                False,
                f"Missing expected value at index {i}",
                actual=str(actual_numbers),
                expected=str(expected)
            )

        act_val = actual_numbers[i]
        diff = abs(act_val - exp_val)

        # Check absolute tolerance
        if diff > tolerance:
            # Check relative tolerance if specified
            if relative_tolerance is not None and exp_val != 0:
                rel_diff = diff / abs(exp_val)
                if rel_diff > relative_tolerance:
                    return MatchResult(
                        False,
                        f"Value at index {i} differs: {act_val} vs {exp_val}",
                        actual=str(act_val),
                        expected=str(exp_val),
                        details={"absolute_diff": diff, "relative_diff": rel_diff}
                    )
            else:
                return MatchResult(
                    False,
                    f"Value at index {i} differs: {act_val} vs {exp_val}",
                    actual=str(act_val),
                    expected=str(exp_val),
                    details={"absolute_diff": diff}
                )

    return MatchResult(
        True,
        f"All {len(expected)} numeric values match within tolerance",
        details={"actual_numbers": actual_numbers, "expected_numbers": expected}
    )


def match_exit_code(actual: int, expected: int) -> MatchResult:
    """
    Check program exit code.

    Args:
        actual: Actual exit code
        expected: Expected exit code

    Returns:
        MatchResult
    """
    if actual == expected:
        return MatchResult(True, f"Exit code is {expected}")

    return MatchResult(
        False,
        f"Exit code mismatch",
        actual=str(actual),
        expected=str(expected)
    )


def match_lines_subset(actual: str, expected_lines: List[str],
                       ordered: bool = True,
                       ignore_case: bool = False,
                       trim: bool = True) -> MatchResult:
    """
    Check if expected lines appear in actual output.

    Args:
        actual: Actual output
        expected_lines: Lines that should appear
        ordered: Whether lines must appear in order
        ignore_case: Case-insensitive comparison
        trim: Trim whitespace

    Returns:
        MatchResult
    """
    actual_lines = get_lines(actual)

    # Normalize lines
    if trim:
        actual_lines = [l.strip() for l in actual_lines]
        expected_lines = [l.strip() for l in expected_lines]
    if ignore_case:
        actual_lines = [l.lower() for l in actual_lines]
        expected_lines = [l.lower() for l in expected_lines]

    if ordered:
        # Lines must appear in order (but not necessarily consecutive)
        actual_idx = 0
        for exp_line in expected_lines:
            found = False
            while actual_idx < len(actual_lines):
                if actual_lines[actual_idx] == exp_line:
                    found = True
                    actual_idx += 1
                    break
                actual_idx += 1

            if not found:
                return MatchResult(
                    False,
                    f"Expected line not found (in order): '{exp_line}'",
                    expected=exp_line
                )

        return MatchResult(True, "All expected lines found in order")

    else:
        # Lines can appear in any order
        missing = []
        for exp_line in expected_lines:
            if exp_line not in actual_lines:
                missing.append(exp_line)

        if missing:
            return MatchResult(
                False,
                f"Missing {len(missing)} expected line(s)",
                expected=str(missing)
            )

        return MatchResult(True, "All expected lines found")


def compare_outputs(actual: str, expected: str,
                    qualification: str,
                    pattern: Optional[str] = None,
                    **options) -> MatchResult:
    """
    Compare actual output with expected using the specified qualification.

    This is the main entry point for stdio comparison.

    Args:
        actual: Actual output
        expected: Expected output (may be unused depending on qualification)
        qualification: Comparison type (matches, contains, regexp, etc.)
        pattern: Pattern for pattern-based qualifications
        **options: Additional options (ignore_case, trim, etc.)

    Returns:
        MatchResult
    """
    # Extract common options
    ignore_case = options.get('ignore_case', False)
    trim = options.get('trim', True)
    normalize_newlines = options.get('normalize_newlines', True)

    if qualification in ('matches', 'verifyEqual'):
        return match_exact(actual, expected, trim, normalize_newlines, ignore_case)

    elif qualification == 'contains':
        search_pattern = pattern if pattern else expected
        return match_contains(actual, search_pattern, ignore_case)

    elif qualification == 'startsWith':
        prefix = pattern if pattern else expected
        return match_starts_with(actual, prefix, trim, ignore_case)

    elif qualification == 'endsWith':
        suffix = pattern if pattern else expected
        return match_ends_with(actual, suffix, trim, ignore_case)

    elif qualification == 'regexp':
        regex = pattern if pattern else expected
        return match_regexp(actual, regex, multiline=False, ignore_case=ignore_case)

    elif qualification == 'regexpMultiline':
        regex = pattern if pattern else expected
        return match_regexp(actual, regex, multiline=True, ignore_case=ignore_case)

    elif qualification == 'matchesLine':
        line_number = options.get('line_number')
        return match_line(actual, expected, line_number, ignore_case, trim)

    elif qualification == 'containsLine':
        return match_line(actual, expected, None, ignore_case, trim)

    elif qualification == 'lineCount':
        count = int(expected) if expected else options.get('count', 0)
        min_count = options.get('min_count')
        max_count = options.get('max_count')
        return match_line_count(actual, count, min_count, max_count)

    elif qualification == 'numericOutput':
        tolerance = options.get('tolerance', 1e-6)
        rel_tol = options.get('relative_tolerance')
        # Parse expected as number(s)
        if isinstance(expected, str):
            expected_nums = extract_numbers(expected)
        else:
            expected_nums = expected
        return match_numeric_output(actual, expected_nums, tolerance, rel_tol)

    elif qualification == 'exitCode':
        actual_code = options.get('exit_code', 0)
        expected_code = int(expected) if expected else 0
        return match_exit_code(actual_code, expected_code)

    else:
        return MatchResult(
            False,
            f"Unknown qualification type: {qualification}"
        )

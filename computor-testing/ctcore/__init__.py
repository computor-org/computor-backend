"""
Computor Testing Core (catcore)

Shared models and utilities for language-specific testing frameworks.
Supports: Octave, Python, R, Julia, C/C++, Fortran, Document/Text testing.
"""

from .models import (
    # Enums
    QualificationEnum,
    TypeEnum,
    StatusEnum,
    ResultEnum,
    # Test Models
    ComputorTest,
    ComputorTestCollection,
    ComputorTestProperty,
    ComputorTestSuite,
    # Configuration Models
    ComputorSpecification,
    ComputorMeta,
    ComputorMetaProperty,
    ComputorPerson,
    ComputorMaterial,
    ContentMetadata,
    # Execution Backend Models
    ExecutionBackend,
    ExecutionBackendSettings,
    # Report Models
    ComputorReport,
    ComputorReportMain,
    ComputorReportSub,
    ComputorReportSummary,
    ComputorReportProperties,
    # Utilities
    load_config,
    read_ca_file,
    get_schema,
    DEFAULTS,
    DIRECTORIES,
)

from .helpers import (
    get_property_as_list,
    get_abbr,
    normalize_name,
    token_exchange,
)

from .security import (
    PathValidationError,
    RegexTimeoutError,
    validate_path_in_root,
    validate_filename,
    validate_absolute_path,
    safe_join,
    safe_regex_findall,
    safe_regex_search,
)

from .stdio import (
    MatchResult,
    normalize_output,
    compare_outputs,
    match_exact,
    match_contains,
    match_regexp,
    match_line,
    match_line_count,
    match_numeric_output,
    match_exit_code,
    extract_numbers,
)

__version__ = "0.1.0"
__all__ = [
    # Enums
    "QualificationEnum",
    "TypeEnum",
    "StatusEnum",
    "ResultEnum",
    # Test Models
    "ComputorTest",
    "ComputorTestCollection",
    "ComputorTestProperty",
    "ComputorTestSuite",
    # Configuration Models
    "ComputorSpecification",
    "ComputorMeta",
    "ComputorMetaProperty",
    "ComputorPerson",
    "ComputorMaterial",
    "ContentMetadata",
    # Execution Backend Models
    "ExecutionBackend",
    "ExecutionBackendSettings",
    # Report Models
    "ComputorReport",
    "ComputorReportMain",
    "ComputorReportSub",
    "ComputorReportSummary",
    "ComputorReportProperties",
    # Utilities
    "load_config",
    "read_ca_file",
    "get_schema",
    "DEFAULTS",
    "DIRECTORIES",
    "get_property_as_list",
    "get_abbr",
    "normalize_name",
    "token_exchange",
    # Security
    "PathValidationError",
    "validate_path_in_root",
    "validate_filename",
    "safe_join",
    # Stdio
    "MatchResult",
    "normalize_output",
    "compare_outputs",
    "match_exact",
    "match_contains",
    "match_regexp",
    "match_line",
    "match_line_count",
    "match_numeric_output",
    "match_exit_code",
    "extract_numbers",
]

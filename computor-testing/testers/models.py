"""
Computor Testing Framework - Unified Models

Re-exports all models from ctcore and provides language-specific
defaults through a factory function.
"""

from typing import Optional

# Re-export everything from ctcore
from ctcore.models import (
    # Enums
    QualificationEnum,
    TypeEnum,
    StatusEnum,
    ResultEnum,
    # Base classes
    ComputorBase,
    ComputorTestCommon,
    ComputorTestCollectionCommon,
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
    VERSION_REGEX,
    empty_list_to_none,
    empty_string_to_none,
)

# Language-specific names
LANGUAGE_NAMES = {
    "python": "Python Test Suite",
    "octave": "Octave Test Suite",
    "r": "R Test Suite",
    "julia": "Julia Test Suite",
    "c": "C/C++ Test Suite",
    "fortran": "Fortran Test Suite",
    "document": "Document Test Suite",
}


def get_defaults(language: str) -> dict:
    """
    Get defaults with language-specific values.

    Args:
        language: Language identifier (python, octave, r, julia, c, fortran, document)

    Returns:
        Copy of DEFAULTS with language-specific values set
    """
    import copy
    defaults = copy.deepcopy(DEFAULTS)

    lang_lower = language.lower()
    defaults["testsuite"]["type"] = lang_lower
    defaults["testsuite"]["name"] = LANGUAGE_NAMES.get(lang_lower, f"{language.title()} Test Suite")

    return defaults


__all__ = [
    # Enums
    "QualificationEnum",
    "TypeEnum",
    "StatusEnum",
    "ResultEnum",
    # Base classes
    "ComputorBase",
    "ComputorTestCommon",
    "ComputorTestCollectionCommon",
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
    "VERSION_REGEX",
    "empty_list_to_none",
    "empty_string_to_none",
    # New utilities
    "LANGUAGE_NAMES",
    "get_defaults",
]

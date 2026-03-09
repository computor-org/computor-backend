"""
Julia Testing Framework - Pytest Configuration

Defines fixtures and hooks for jltester using the object-oriented approach.
"""

import pytest

from ..conftest_base import (
    Solution,
    metadata_key,
    report_key,
    SimpleTesterConfig,
    create_conftest_hooks,
)


# Re-export for test_class.py
__all__ = ["Solution", "report_key", "metadata_key"]


class JuliaTesterConfig(SimpleTesterConfig):
    """Configuration for Julia tester."""
    language = "julia"
    has_metadata = True
    has_property_inheritance = True


# Create and register all hooks from the config class
_config = JuliaTesterConfig()
_hooks = create_conftest_hooks(type(_config))

# Export hooks to module level so pytest can discover them
pytest_addoption = _hooks["pytest_addoption"]
pytest_configure = _hooks["pytest_configure"]
pytest_generate_tests = _hooks["pytest_generate_tests"]
pytest_runtest_makereport = _hooks["pytest_runtest_makereport"]
pytest_sessionstart = _hooks["pytest_sessionstart"]
pytest_sessionfinish = _hooks["pytest_sessionfinish"]

# Optional hooks
if "pytest_metadata" in _hooks:
    pytest_metadata = _hooks["pytest_metadata"]

if "pytest_report_header" in _hooks:
    pytest_report_header = _hooks["pytest_report_header"]

if "pytest_terminal_summary" in _hooks:
    pytest_terminal_summary = _hooks["pytest_terminal_summary"]

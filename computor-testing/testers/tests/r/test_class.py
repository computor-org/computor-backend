"""
R Testing Framework - Test Class

Main test execution logic for R code testing.
Uses InterpretedSolutionManager and InterpretedTestClass base classes.
"""

from .conftest import report_key
from testers.executors.r import RExecutor, RExecutionError
from ..test_base import InterpretedSolutionManager, InterpretedTestClass


class RSolutionManager(InterpretedSolutionManager):
    """Solution manager for R scripts."""
    executor_class = RExecutor
    execution_error_class = RExecutionError
    file_extensions = ["*.R", "*.r"]
    language_name = "R"


_solution_manager_cache = {}


class TestComputorR(InterpretedTestClass):
    """Main test class for R code testing."""

    file_extensions = ["*.R", "*.r"]

    def get_report_key(self):
        return report_key

    def get_solution_manager(self, pytestconfig):
        if id(pytestconfig) not in _solution_manager_cache:
            _solution_manager_cache[id(pytestconfig)] = RSolutionManager(
                pytestconfig, report_key
            )
        return _solution_manager_cache[id(pytestconfig)]

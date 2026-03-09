"""
Julia Testing Framework - Test Class

Main test execution logic for Julia code testing.
Uses InterpretedSolutionManager and InterpretedTestClass base classes.
"""

from .conftest import report_key
from testers.executors.julia import JuliaExecutor, JuliaExecutionError
from ..test_base import InterpretedSolutionManager, InterpretedTestClass


class JuliaSolutionManager(InterpretedSolutionManager):
    """Solution manager for Julia scripts."""
    executor_class = JuliaExecutor
    execution_error_class = JuliaExecutionError
    file_extensions = ["*.jl"]
    language_name = "Julia"


_solution_manager_cache = {}


class TestComputorJulia(InterpretedTestClass):
    """Main test class for Julia code testing."""

    file_extensions = ["*.jl"]

    def get_report_key(self):
        return report_key

    def get_solution_manager(self, pytestconfig):
        if id(pytestconfig) not in _solution_manager_cache:
            _solution_manager_cache[id(pytestconfig)] = JuliaSolutionManager(
                pytestconfig, report_key
            )
        return _solution_manager_cache[id(pytestconfig)]

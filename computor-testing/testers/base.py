"""
Base Tester Class

Provides common functionality for all language testers, including:
- Test execution via pytest
- Configuration loading
- Result reporting
"""

import os
import sys
import tempfile
from abc import ABC
from typing import Optional, List, Dict, Any, Type

import yaml
import pytest

from .models import ComputorSpecification, ComputorTestSuite, load_config, get_defaults
from .executors import get_executor


class BaseTester(ABC):
    """
    Abstract base class for all language testers.

    Subclasses should:
    - Set the `language` class attribute
    """

    language: str = ""  # Override in subclass
    verbosity_flag: str = "--ctverbosity"  # pytest flag for tester verbosity

    def __init__(
        self,
        testroot: Optional[str] = None,
        testsuite: Optional[str] = None,
        specification: Optional[str] = None,
    ):
        """
        Initialize the tester.

        Args:
            testroot: Root directory for tests
            testsuite: Path to test.yaml file
            specification: Path to specification.yaml file
        """
        self.testroot = testroot or os.getcwd()
        self.testsuite_path = testsuite
        self.specification_path = specification
        self._spec: Optional[ComputorSpecification] = None
        self._suite: Optional[ComputorTestSuite] = None

    @property
    def executor_class(self):
        """Get the executor class for this language."""
        return get_executor(self.language)

    def check_installed(self) -> tuple:
        """Check if the language runtime is installed."""
        if self.executor_class:
            return self.executor_class.check_installed()
        return False, f"No executor for language: {self.language}"

    def load_specification(self, path: Optional[str] = None) -> ComputorSpecification:
        """
        Load or create a specification.

        Args:
            path: Path to specification.yaml

        Returns:
            ComputorSpecification instance
        """
        path = path or self.specification_path
        if path and os.path.exists(path):
            self._spec = load_config(ComputorSpecification, path)
        else:
            self._spec = ComputorSpecification()
        return self._spec

    def load_testsuite(self, path: Optional[str] = None) -> ComputorTestSuite:
        """
        Load a test suite configuration.

        Args:
            path: Path to test.yaml

        Returns:
            ComputorTestSuite instance
        """
        path = path or self.testsuite_path
        if path and os.path.exists(path):
            self._suite = load_config(ComputorTestSuite, path)
        else:
            raise FileNotFoundError(f"Test suite not found: {path}")
        return self._suite

    def get_test_file(self) -> str:
        """
        Get the path to the pytest test file.

        Returns:
            Path to test_class.py for this language
        """
        return os.path.join(
            os.path.dirname(__file__),
            "tests", self.language, "test_class.py"
        )

    def run(
        self,
        target: Optional[str] = None,
        testsuite: Optional[str] = None,
        specification: Optional[str] = None,
        pytestflags: str = "",
        verbosity: int = 0,
    ) -> int:
        """
        Run tests using pytest.

        Args:
            target: Target directory for student code
            testsuite: Path to test.yaml file
            specification: Path to specification.yaml
            pytestflags: Additional pytest flags
            verbosity: Verbosity level (0-3)

        Returns:
            Exit code from pytest
        """
        # Use provided paths or fall back to instance attributes
        testsuite = testsuite or self.testsuite_path
        specification = specification or self.specification_path

        # Resolve paths
        if testsuite and not os.path.isabs(testsuite):
            testsuite = os.path.join(self.testroot, testsuite)

        if not testsuite or not os.path.exists(testsuite):
            print(f"Error: Test suite not found: {testsuite}", file=sys.stderr)
            return 1

        # Update testroot based on testsuite location
        testroot = os.path.dirname(os.path.abspath(testsuite))

        # Load or create specification
        spec = self.load_specification(specification)

        # Override student directory if target provided
        if target:
            spec.studentDirectory = os.path.abspath(target)

        # Write temporary specification file
        spec_data = spec.model_dump()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(spec_data, f)
            temp_spec = f.name

        try:
            # Build pytest arguments
            test_file = self.get_test_file()

            pytest_args = [
                test_file,
                f"--testroot={testroot}",
                f"--testsuite={testsuite}",
                f"--specification={temp_spec}",
                f"{self.verbosity_flag}={verbosity}",
            ]

            if pytestflags:
                pytest_args.extend(pytestflags.split())

            # Add verbosity
            if verbosity >= 2:
                pytest_args.append("-v")
            if verbosity >= 3:
                pytest_args.append("-vv")

            # Print header
            self._print_header(testroot, testsuite, temp_spec, pytestflags, verbosity)

            # Run pytest
            return pytest.main(pytest_args)

        finally:
            # Clean up temp file
            if os.path.exists(temp_spec):
                os.unlink(temp_spec)

    def _print_header(
        self,
        testroot: str,
        testsuite: str,
        specification: str,
        pytestflags: str,
        verbosity: int,
    ):
        """Print test run header."""
        import click

        click.echo("=" * 80)
        click.secho(f"Computor {self.language.title()} Testing Engine", fg="cyan")
        click.echo("=" * 80)
        click.secho("testroot:      ", fg="cyan", nl=False)
        click.echo(testroot)
        click.secho("testsuite:     ", fg="cyan", nl=False)
        click.echo(testsuite)
        click.secho("specification: ", fg="cyan", nl=False)
        click.echo(specification)
        click.secho("pytestflags:   ", fg="cyan", nl=False)
        click.echo(pytestflags)
        click.secho("verbosity:     ", fg="cyan", nl=False)
        click.echo(str(verbosity))
        click.echo("=" * 80)

    def local(self, directory: str, verbosity: int = 1) -> int:
        """
        Run local tests in a directory.

        Args:
            directory: Directory containing solution and test.yaml nearby
            verbosity: Verbosity level

        Returns:
            Exit code from pytest
        """
        directory = os.path.abspath(directory)

        # Look for test.yaml in parent directory first
        test_yaml = os.path.join(os.path.dirname(directory), "test.yaml")
        if not os.path.exists(test_yaml):
            test_yaml = os.path.join(directory, "test.yaml")
            if not os.path.exists(test_yaml):
                print(f"Error: test.yaml not found", file=sys.stderr)
                return 1

        return self.run(
            target=directory,
            testsuite=test_yaml,
            verbosity=verbosity,
        )


# Registry of tester classes
TESTERS: Dict[str, Type[BaseTester]] = {}


def register_tester(cls: Type[BaseTester]) -> Type[BaseTester]:
    """Decorator to register a tester class."""
    if cls.language:
        TESTERS[cls.language] = cls
    return cls


def get_tester(language: str) -> Optional[Type[BaseTester]]:
    """
    Get the tester class for a language.

    Args:
        language: Language identifier

    Returns:
        Tester class or None if not found
    """
    return TESTERS.get(language.lower())


__all__ = [
    "BaseTester",
    "TESTERS",
    "register_tester",
    "get_tester",
]

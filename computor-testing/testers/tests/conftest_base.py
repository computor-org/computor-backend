"""
Shared Pytest Configuration Base for All Language Testers.

This module provides common pytest hooks and fixtures used by all
language-specific test configurations. It supports both:
1. Object-oriented approach via BaseTesterConfig classes
2. Functional approach via standalone functions (for backward compatibility)

Individual language conftest.py files should either:
- Create a TesterConfig class inheriting from BaseTesterConfig
- Import and use the standalone functions directly
"""

import json
import os
import datetime
from datetime import timezone
import shutil
import time
import logging
import platform
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Any, Type, Callable

import pytest
from _pytest.terminal import TerminalReporter
from _pytest._code.code import ExceptionChainRepr
from colorama import Fore, Style

from ctcore.models import (
    DIRECTORIES,
    ComputorTestSuite,
    ComputorSpecification,
    ComputorReport,
    ComputorReportMain,
    ComputorReportSub,
    ComputorReportSummary,
    StatusEnum,
    ResultEnum,
    load_config,
    read_ca_file,
)
from ctcore.helpers import get_property_as_list
from ctcore.security import validate_path_in_root, validate_filename, validate_absolute_path, PathValidationError

logger = logging.getLogger(__name__)


class Solution(str, Enum):
    """Which solution to test."""
    student = "student"
    reference = "reference"


# Pytest stash keys
metadata_key = pytest.StashKey[dict]()
report_key = pytest.StashKey[dict]()


# =============================================================================
# Object-Oriented Configuration Classes
# =============================================================================

class BaseTesterConfig(ABC):
    """
    Base configuration class for pytest hooks.

    Subclass this to create language-specific configurations.
    Override methods as needed for custom behavior.

    Feature flags control which hooks/fixtures are enabled:
    - has_metadata: Store pytest-metadata in stash (default True)
    - has_monkeypatch: Provide monkeymodule fixture (default False)
    - has_property_inheritance: Inherit properties from parent to child (default False)
    - has_custom_session_finish: Use custom session finish logic (default False)
    - has_custom_terminal_summary: Use custom detailed terminal summary (default False)
    - has_report_header: Display custom report header (default True)

    Example:
        class PythonTesterConfig(BaseTesterConfig):
            language = "python"
            has_monkeypatch = True
    """

    # Required: Override in subclass
    language: str = ""

    # Feature flags - override in subclass as needed
    has_metadata: bool = True
    has_monkeypatch: bool = False
    has_property_inheritance: bool = False
    has_custom_session_finish: bool = False
    has_custom_terminal_summary: bool = False
    has_report_header: bool = True

    # Property inheritance fields (used when has_property_inheritance=True)
    sub_fields: List[str] = [
        "qualification",
        "relativeTolerance",
        "absoluteTolerance",
        "allowedOccuranceRange",
        "occuranceType",
        "typeCheck",
        "shapeCheck",
        "ignoreClass",
        "verbosity",
    ]
    main_fields: List[str] = sub_fields + [
        "storeGraphicsArtifacts",
        "competency",
        "timeout",
    ]

    def __init__(self):
        """Initialize the configuration."""
        if not self.language:
            raise ValueError("language must be set in subclass")

    # -------------------------------------------------------------------------
    # Hook implementations - override as needed
    # -------------------------------------------------------------------------

    def add_options(self, parser: pytest.Parser) -> None:
        """Add command-line options. Override to add custom options."""
        add_common_options(parser)

    def store_metadata(self, metadata: dict, config: pytest.Config) -> None:
        """Store pytest-metadata. Override for custom metadata handling."""
        if self.has_metadata:
            config.stash[metadata_key] = metadata

    def configure(self, config: pytest.Config) -> None:
        """
        Configure pytest session.

        Override for custom configuration logic.
        Default uses configure_test_session() with property inheritance if enabled.
        """
        if self.has_property_inheritance:
            self._configure_with_inheritance(config)
        else:
            configure_test_session(config, language=self.language)

    def generate_tests(self, metafunc: pytest.Metafunc) -> None:
        """Generate test cases. Override for custom test generation."""
        generate_test_cases(metafunc)

    def make_report(self, item: pytest.Item, call: pytest.CallInfo) -> None:
        """Update report after test. Override for custom report handling."""
        update_report_on_test_result(item, call)

    def session_start(self, session: pytest.Session) -> None:
        """Handle session start. Override for custom startup logic."""
        _report = session.config.stash[report_key]
        _report["started"] = _report.get("created", time.time())

    def session_finish(self, session: pytest.Session, exitstatus: int) -> None:
        """
        Handle session finish.

        Override for custom finalization logic.
        Default uses finalize_session() unless has_custom_session_finish is True.
        """
        if self.has_custom_session_finish:
            self._custom_session_finish(session, exitstatus)
        else:
            finalize_session(session, exitstatus)

    def get_report_header(self, config: pytest.Config) -> List[str]:
        """Get report header lines. Override for custom header."""
        if self.has_report_header:
            return get_report_header(config)
        return []

    def terminal_summary(
        self,
        terminalreporter: TerminalReporter,
        exitstatus: pytest.ExitCode,
        config: pytest.Config
    ) -> None:
        """Add terminal summary. Override for custom summary."""
        if self.has_custom_terminal_summary:
            self._custom_terminal_summary(terminalreporter, exitstatus, config)
        else:
            add_terminal_summary(terminalreporter, exitstatus, config)

    # -------------------------------------------------------------------------
    # Property inheritance implementation
    # -------------------------------------------------------------------------

    def _configure_with_inheritance(self, config: pytest.Config) -> None:
        """Configure with property inheritance (for Octave-style testers)."""
        now = datetime.datetime.now(timezone.utc)
        timestamp = now.isoformat()

        testroot = config.getoption("--testroot")
        specyamlfile = config.getoption("--specification")
        testyamlfile = config.getoption("--testsuite")
        indent = int(config.getoption("--indent"))
        verbosity_level = int(config.getoption("--ctverbosity") or 0)
        pytestflags = config.getoption("--pytestflags")

        specification: ComputorSpecification = read_ca_file(
            ComputorSpecification, specyamlfile
        )
        testsuite: ComputorTestSuite = read_ca_file(
            ComputorTestSuite, testyamlfile
        )

        # Root directory
        root = os.path.abspath(testroot) if testroot and testroot != "." else os.path.abspath(os.path.dirname(testyamlfile))

        # Validate and create directories
        for directory in DIRECTORIES:
            dir_path = getattr(specification, directory)
            if dir_path is not None:
                try:
                    if not os.path.isabs(dir_path):
                        # Relative paths: validate they stay within testroot (security)
                        dir_path = validate_path_in_root(dir_path, root, f"{directory}")
                    else:
                        # Absolute paths: used by automated testing systems
                        # Validate basic safety (no traversal, no sensitive dirs)
                        dir_path = validate_absolute_path(dir_path, f"{directory}")
                    setattr(specification, directory, dir_path)
                    os.makedirs(dir_path, exist_ok=True)
                except PathValidationError as e:
                    logger.error(f"Path validation failed for {directory}: {e}")
                    raise ValueError(f"Security error: {e}") from e

        # Validate output file name
        try:
            validate_filename(specification.outputName, allow_path_separators=False)
        except PathValidationError as e:
            logger.error(f"Output filename validation failed: {e}")
            raise ValueError(f"Security error: {e}") from e

        reportfile = specification.outputName
        if not os.path.isabs(reportfile):
            reportfile = os.path.join(specification.outputDirectory, reportfile)

        # Validate output file path
        try:
            if not os.path.isabs(reportfile):
                reportfile = validate_path_in_root(reportfile, root, "output file")
            else:
                reportfile = validate_absolute_path(reportfile, "output file")
        except PathValidationError as e:
            logger.error(f"Output file path validation failed: {e}")
            raise ValueError(f"Security error: {e}") from e

        os.makedirs(os.path.dirname(reportfile), exist_ok=True)

        # Build test case indices with property inheritance
        testcases = []
        main_tests: List[ComputorReportMain] = []

        def inherit_properties(properties: List[str], child: Any, parent: Any) -> None:
            """Inherit None properties from parent."""
            for prop in properties:
                if getattr(child, prop, None) is None:
                    setattr(child, prop, getattr(parent, prop, None))

        for idx_main, main in enumerate(testsuite.properties.tests):
            inherit_properties(self.main_fields, main, testsuite.properties)
            sub_tests: List[ComputorReportSub] = []
            for idx_sub, sub in enumerate(main.tests):
                inherit_properties(self.sub_fields, sub, main)
                testcases.append((idx_main, idx_sub))
                sub_tests.append(ComputorReportSub(name=sub.name))

            setup = None if main.setUpCode is None else "\n".join(
                get_property_as_list(main.setUpCode)
            )
            teardown = None if main.tearDownCode is None else "\n".join(
                get_property_as_list(main.tearDownCode)
            )
            main_tests.append(ComputorReportMain(
                type=main.type,
                name=main.name,
                description=main.description,
                setup=setup,
                teardown=teardown,
                status=StatusEnum.scheduled,
                summary=ComputorReportSummary(total=len(main.tests)),
                tests=sub_tests,
                timestamp=0,
            ))

        report = ComputorReport(
            timestamp=timestamp,
            type=testsuite.type,
            version=testsuite.version,
            name=testsuite.name,
            description=testsuite.description,
            status=StatusEnum.scheduled,
            summary=ComputorReportSummary(total=len(testsuite.properties.tests)),
            tests=main_tests,
        )

        report_data = {
            "report": report,
            "testcases": testcases,
            "testsuite": testsuite,
            "specification": specification,
            "reportfile": reportfile,
            "indent": indent,
            "created": time.time(),
            "started": 0,
            "solutions": {},
            "root": root,
            "testyamlfile": testyamlfile,
            "specyamlfile": specyamlfile,
            "verbosity": verbosity_level,
            "pytestflags": pytestflags,
            "language": self.language,
            "student_file_list": [],
            "reference_file_list": [],
            "student_command_list": [],
            "reference_command_list": [],
        }
        config.stash[report_key] = report_data

    def _custom_session_finish(self, session: pytest.Session, exitstatus: int) -> None:
        """
        Custom session finish with detailed execution tracking.

        Override in subclass for language-specific behavior.
        This is the Octave-style detailed session finish.
        """
        environment = session.config.stash.get(metadata_key, {})
        _report = session.config.stash[report_key]
        testyamlfile = _report["testyamlfile"]
        specyamlfile = _report["specyamlfile"]
        pytestflags = _report["pytestflags"]
        report: ComputorReport = _report["report"]
        reportfile = _report["reportfile"]
        indent = _report["indent"]
        started = _report["started"]
        solutions = _report["solutions"]
        testsuite: ComputorTestSuite = _report["testsuite"]
        duration = time.time() - started

        total = report.summary.total
        passed = 0
        failed = 0
        skipped = 0
        time_s = 0.0
        time_r = 0.0

        _teststarted = started
        for idx_main, main in enumerate(report.tests):
            _testended = float(main.timestamp) if main.timestamp else time.time()
            # Clear timestamp after use (set to None rather than delete for Pydantic)
            main.timestamp = None
            _testduration = _testended - _teststarted
            _teststarted = _testended

            test_main = testsuite.properties.tests[idx_main]
            sub_time_s = 0
            sub_time_r = 0
            status = StatusEnum.completed
            idx = str(idx_main)
            errs = []

            if idx in solutions:
                solution_s = solutions[idx].get(Solution.student, {})
                solution_r = solutions[idx].get(Solution.reference, {})
                errs = solution_s.get("errors", [])
                sub_time_s = solution_s.get("exectime", 0)
                sub_time_r = solution_r.get("exectime", 0)
                status = solution_s.get("status", StatusEnum.completed)

            sub_total = main.summary.total
            sub_passed = 0
            sub_failed = 0
            sub_skipped = 0

            for idx_sub, sub in enumerate(main.tests):
                if sub.result == ResultEnum.passed:
                    sub_passed += 1
                elif sub.result == ResultEnum.failed:
                    sub_failed += 1
                elif sub.result == ResultEnum.skipped:
                    sub_skipped += 1

            time_s += sub_time_s
            time_r += sub_time_r

            main.debug = {
                "executionDurationStudent": sub_time_s,
                "executionDurationReference": sub_time_r,
                "lintingErrors": errs,
            }
            main.duration = _testduration
            main.executionDuration = sub_time_s
            main.summary.passed = sub_passed
            main.summary.failed = sub_failed
            main.summary.skipped = sub_skipped
            main.status = status

            if sub_passed == sub_total:
                passed += 1
                main.result = ResultEnum.passed
                result_message = getattr(test_main, 'successMessage', None)
            elif sub_skipped > 0:
                skipped += 1
                main.result = ResultEnum.skipped
                result_message = "Tests skipped"
            else:
                failed += 1
                main.result = ResultEnum.failed
                result_message = getattr(test_main, 'failureMessage', None)
            main.resultMessage = result_message

        report.summary.passed = passed
        report.summary.skipped = skipped
        report.summary.failed = failed

        if exitstatus == pytest.ExitCode.INTERRUPTED:
            report.status = StatusEnum.cancelled
        else:
            report.status = StatusEnum.completed

        if total == 0:
            report.result = ResultEnum.skipped
            result_message = "No Tests specified"
        elif passed == total:
            report.result = ResultEnum.passed
            result_message = getattr(testsuite.properties, 'successMessage', "All tests passed")
        elif skipped == total:
            report.result = ResultEnum.skipped
            result_message = "Tests skipped"
        else:
            report.result = ResultEnum.failed
            result_message = getattr(testsuite.properties, 'failureMessage', "Some tests failed")

        report.resultMessage = result_message
        report.environment = environment
        report.duration = duration
        report.executionDuration = time_s
        report.debug = {
            "executionDurationStudent": time_s,
            "executionDurationReference": time_r,
        }
        report.properties = {
            "test": testyamlfile,
            "specification": specyamlfile,
            "pytestflags": pytestflags,
            "exitcode": str(exitstatus),
        }

        with open(reportfile, "w", encoding="utf-8") as file:
            json.dump(
                report.model_dump(exclude_none=True),
                file, default=str, indent=indent
            )

    def _custom_terminal_summary(
        self,
        terminalreporter: TerminalReporter,
        exitstatus: pytest.ExitCode,
        config: pytest.Config
    ) -> None:
        """
        Custom detailed terminal summary.

        Override in subclass for language-specific behavior.
        This is the Octave-style detailed terminal summary.
        """
        _report = config.stash[report_key]
        verbosity_level = _report["verbosity"]

        if verbosity_level > 0:
            report: ComputorReport = _report["report"]
            testsuite: ComputorTestSuite = _report["testsuite"]

            total = report.summary.total
            passed = report.summary.passed
            failed = report.summary.failed
            skipped = report.summary.skipped

            terminalreporter.ensure_newline()
            terminalreporter.section(
                f"{testsuite.name} - Summary", sep="~", purple=True, bold=True
            )
            terminalreporter.line(f"Total Test Collections: {total}")
            terminalreporter.line(f"PASSED: {passed} ", green=True)
            terminalreporter.line(f"FAILED: {failed} ", red=True)
            terminalreporter.line(f"SKIPPED: {skipped} ", yellow=True)

            for idx_main, main in enumerate(report.tests):
                test_main = testsuite.properties.tests[idx_main]
                sub_total = main.summary.total
                sub_passed = main.summary.passed
                sub_failed = main.summary.failed
                sub_skipped = main.summary.skipped
                testtext = "Test" if sub_total == 1 else "Tests"

                terminalreporter.write_sep("*", f"Testcollection {idx_main + 1}")
                terminalreporter.line(f"{test_main.name} ({sub_total} {testtext})")

                if sub_passed > 0:
                    terminalreporter.line(f"PASSED: {sub_passed} ", green=True)
                if sub_failed > 0:
                    terminalreporter.line(f"FAILED: {sub_failed} ", red=True)
                if sub_skipped > 0:
                    terminalreporter.line(f"SKIPPED: {sub_skipped} ", yellow=True)

                for idx_sub, sub in enumerate(main.tests):
                    test_sub = test_main.tests[idx_sub]
                    outcome = sub.result
                    terminalreporter.line(
                        f"Test {idx_sub + 1} ({test_sub.name}): {outcome} ",
                        green=outcome == ResultEnum.passed,
                        red=outcome == ResultEnum.failed,
                        yellow=outcome == ResultEnum.skipped,
                    )


# =============================================================================
# Pre-built Configuration Classes for Common Patterns
# =============================================================================

class SimpleTesterConfig(BaseTesterConfig):
    """
    Simple tester configuration.

    Use for languages that just need basic configuration:
    C, Fortran, Julia, R, Document.

    Example:
        class CTesterConfig(SimpleTesterConfig):
            language = "c"
    """
    pass


class InterpretedTesterConfig(BaseTesterConfig):
    """
    Configuration for interpreted language testers with monkeypatch.

    Use for Python and similar languages.

    Example:
        class PythonTesterConfig(InterpretedTesterConfig):
            language = "python"
    """
    has_monkeypatch = True
    has_custom_session_finish = True


class OctaveTesterConfig(BaseTesterConfig):
    """
    Full-featured configuration with property inheritance.

    Use for Octave/MATLAB testers that need:
    - Property inheritance from parent to child tests
    - Custom session finish with detailed timing
    - Custom terminal summary with per-test breakdown
    - Custom report handling with hook wrapper

    Example:
        class MyOctaveConfig(OctaveTesterConfig):
            language = "octave"
    """
    has_property_inheritance = True
    has_custom_session_finish = True
    has_custom_terminal_summary = True

    def make_report(self, item: pytest.Item, call: pytest.CallInfo) -> None:
        """
        Custom report handling for Octave.

        Note: This needs to be called from a hookwrapper in conftest.py
        because we need access to the report object.
        """
        # Default implementation - override in conftest.py using hookwrapper
        pass


# =============================================================================
# Factory Function to Create Hook Functions
# =============================================================================

def create_conftest_hooks(config_class: Type[BaseTesterConfig]) -> Dict[str, Callable]:
    """
    Create pytest hook functions from a config class.

    Returns a dictionary of hook functions that can be added to globals()
    in a conftest.py file.

    Example:
        from testers.tests.conftest_base import (
            create_conftest_hooks, SimpleTesterConfig
        )

        class CTesterConfig(SimpleTesterConfig):
            language = "c"

        # Add hooks to module
        _config = CTesterConfig()
        globals().update(create_conftest_hooks(type(_config)))

    Args:
        config_class: A BaseTesterConfig subclass

    Returns:
        Dictionary of hook functions
    """
    tester_config = config_class()

    # Note: Parameter names must match pytest's hook specifications exactly
    def pytest_addoption(parser: pytest.Parser):
        tester_config.add_options(parser)

    def pytest_configure(config: pytest.Config):
        tester_config.configure(config)

    def pytest_generate_tests(metafunc: pytest.Metafunc):
        tester_config.generate_tests(metafunc)

    def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
        tester_config.make_report(item, call)

    def pytest_sessionstart(session: pytest.Session):
        tester_config.session_start(session)

    def pytest_sessionfinish(session: pytest.Session, exitstatus: int):
        tester_config.session_finish(session, exitstatus)

    hooks = {
        "pytest_addoption": pytest_addoption,
        "pytest_configure": pytest_configure,
        "pytest_generate_tests": pytest_generate_tests,
        "pytest_runtest_makereport": pytest_runtest_makereport,
        "pytest_sessionstart": pytest_sessionstart,
        "pytest_sessionfinish": pytest_sessionfinish,
    }

    # Add optional hooks
    if tester_config.has_metadata:
        def pytest_metadata(metadata, config):
            tester_config.store_metadata(metadata, config)
        hooks["pytest_metadata"] = pytest_metadata

    if tester_config.has_report_header:
        @pytest.hookimpl(trylast=True)
        def pytest_report_header(config):
            return tester_config.get_report_header(config)
        hooks["pytest_report_header"] = pytest_report_header

    def pytest_terminal_summary(terminalreporter, exitstatus, config):
        tester_config.terminal_summary(terminalreporter, exitstatus, config)
    hooks["pytest_terminal_summary"] = pytest_terminal_summary

    return hooks


# =============================================================================
# Functional API (Backward Compatibility)
# =============================================================================

def add_common_options(parser: pytest.Parser) -> None:
    """
    Add common command-line options for all testers.

    Args:
        parser: pytest argument parser
    """
    parser.addoption(
        "--testroot",
        default=".",
        help="root directory for tests",
    )
    parser.addoption(
        "--testsuite",
        default="test.yaml",
        help="test yaml input file",
    )
    parser.addoption(
        "--specification",
        default="",
        help="specification yaml input file",
    )
    parser.addoption(
        "--ctverbosity",
        default="0",
        help="tester verbosity level",
    )
    parser.addoption(
        "--indent",
        default=2,
        help="json report output indentation in spaces",
    )
    parser.addoption(
        "--pytestflags",
        default="",
        help="additional pytest flags",
    )


def configure_test_session(
    config: pytest.Config,
    language: str,
    extra_stash: Optional[Dict[str, Any]] = None
) -> None:
    """
    Configure pytest session with test suite data.

    This is the main configuration function that loads the test suite
    and specification, validates paths, and initializes the report structure.

    Args:
        config: pytest config object
        language: language name (e.g., "octave", "python")
        extra_stash: additional data to store in the stash
    """
    now = datetime.datetime.now(timezone.utc)
    timestamp = now.isoformat()

    testroot = config.getoption("--testroot")
    testyamlfile = config.getoption("--testsuite")
    specyamlfile = config.getoption("--specification")
    indent = int(config.getoption("--indent"))
    verbosity_level = int(config.getoption("--ctverbosity") or 0)
    pytestflags = config.getoption("--pytestflags")

    # Load test suite and specification
    specification: ComputorSpecification = read_ca_file(
        ComputorSpecification, specyamlfile
    )
    testsuite: ComputorTestSuite = read_ca_file(
        ComputorTestSuite, testyamlfile
    )

    # Determine root directory
    root = os.path.abspath(testroot) if testroot and testroot != "." else os.path.abspath(os.path.dirname(testyamlfile))

    # Validate and create directories
    for directory in DIRECTORIES:
        dir_path = getattr(specification, directory)
        if dir_path is not None:
            try:
                if not os.path.isabs(dir_path):
                    # Relative paths: validate they stay within testroot (security)
                    dir_path = validate_path_in_root(dir_path, root, f"{directory}")
                else:
                    # Absolute paths: trust them (used by automated testing systems)
                    # No validation needed - absolute paths indicate deliberate configuration
                    dir_path = os.path.abspath(dir_path)
                setattr(specification, directory, dir_path)
                os.makedirs(dir_path, exist_ok=True)
                logger.debug(f"Validated and created directory {directory}: {dir_path}")
            except PathValidationError as e:
                logger.error(f"Path validation failed for {directory}: {e}")
                raise ValueError(f"Security error: {e}") from e

    # Validate output file name
    try:
        validate_filename(specification.outputName, allow_path_separators=False)
    except PathValidationError as e:
        logger.error(f"Output filename validation failed: {e}")
        raise ValueError(f"Security error: {e}") from e

    # Resolve report file path
    reportfile = specification.outputName
    if not os.path.isabs(reportfile):
        reportfile = os.path.join(specification.outputDirectory, reportfile)

    # Validate output file path
    try:
        if not os.path.isabs(reportfile):
            reportfile = validate_path_in_root(reportfile, root, "output file")
        else:
            reportfile = os.path.abspath(reportfile)
    except PathValidationError as e:
        logger.error(f"Output file path validation failed: {e}")
        raise ValueError(f"Security error: {e}") from e

    # Generate test case indices
    testcases = []
    for idx, main in enumerate(testsuite.properties.tests):
        for sub_idx, sub in enumerate(main.tests):
            testcases.append((idx, sub_idx))

    # Initialize report structure
    report = ComputorReport(
        name=testsuite.name,
        description=testsuite.description,
        version=testsuite.version,
        status=StatusEnum.scheduled,
        timestamp=timestamp,
        type=language,
        tests=[],
        summary=ComputorReportSummary(total=len(testsuite.properties.tests)),
    )

    # Create report structure for each test collection
    for main in testsuite.properties.tests:
        main_report = ComputorReportMain(
            name=main.name,
            description=main.description,
            type=main.type,
            status=StatusEnum.scheduled,
            tests=[],
            summary=ComputorReportSummary(),
        )

        for sub in main.tests:
            sub_report = ComputorReportSub(
                name=sub.name,
                status=StatusEnum.scheduled,
            )
            main_report.tests.append(sub_report)

        main_report.summary.total = len(main.tests)
        report.tests.append(main_report)

    # Store in pytest stash
    stash_data = {
        "report": report,
        "testsuite": testsuite,
        "specification": specification,
        "reportfile": reportfile,
        "indent": indent,
        "timestamp": timestamp,
        "testcases": testcases,
        "solutions": {},
        "root": root,
        "testyamlfile": testyamlfile,
        "specyamlfile": specyamlfile,
        "verbosity": verbosity_level,
        "pytestflags": pytestflags,
        "language": language,
        "started": 0,
        "created": time.time(),
        # For exist tests - track found files
        "student_file_list": [],
        "reference_file_list": [],
        # For compiled languages
        "student_command_list": [],
        "reference_command_list": [],
    }

    # Add any extra stash data
    if extra_stash:
        stash_data.update(extra_stash)

    config.stash[report_key] = stash_data


def generate_test_cases(metafunc: pytest.Metafunc) -> None:
    """
    Generate test cases from test suite.

    Parametrizes tests with (main_idx, sub_idx) tuples.

    Args:
        metafunc: pytest metafunc object
    """
    if "testcases" in metafunc.fixturenames:
        _report = metafunc.config.stash[report_key]
        testsuite = _report["testsuite"]

        test_ids = []
        test_params = []

        for main_idx, main in enumerate(testsuite.properties.tests):
            for sub_idx, sub in enumerate(main.tests):
                test_ids.append(f"{main.name}\\{sub.name}")
                test_params.append((main_idx, sub_idx))

        metafunc.parametrize("testcases", test_params, ids=test_ids)


def update_report_on_test_result(item: pytest.Item, call: pytest.CallInfo) -> None:
    """
    Update report after each test execution.

    Args:
        item: pytest test item
        call: pytest call info
    """
    if call.when != "call":
        return

    _report = item.config.stash.get(report_key, None)
    if not _report:
        return

    report = _report["report"]

    try:
        if hasattr(item, "callspec"):
            main_idx, sub_idx = item.callspec.params["testcases"]

            sub_report = report.tests[main_idx].tests[sub_idx]
            main_report = report.tests[main_idx]

            if call.excinfo is None:
                sub_report.status = StatusEnum.completed
                sub_report.result = ResultEnum.passed
                main_report.summary.passed += 1
            elif call.excinfo.typename == "Skipped":
                sub_report.status = StatusEnum.skipped
                sub_report.result = ResultEnum.skipped
                main_report.summary.skipped += 1
            else:
                sub_report.status = StatusEnum.failed
                sub_report.result = ResultEnum.failed
                sub_report.statusMessage = str(call.excinfo.value)
                main_report.summary.failed += 1

            # Track timestamp for duration calculation in session finish
            main_report.timestamp = time.time()

    except (KeyError, IndexError, AttributeError):
        pass


def finalize_session(session: pytest.Session, exitstatus: int) -> None:
    """
    Finalize report at end of session.

    Calculates summary statistics and writes the report file.

    Args:
        session: pytest session
        exitstatus: exit status code
    """
    _report = session.config.stash.get(report_key, None)
    if not _report:
        return

    report: ComputorReport = _report["report"]
    specification: ComputorSpecification = _report["specification"]
    reportfile = _report["reportfile"]
    indent = _report["indent"]
    start_time = _report.get("created", time.time())

    # Calculate duration
    duration = time.time() - start_time

    # Calculate overall summary
    total = sum(m.summary.total for m in report.tests)
    passed = sum(m.summary.passed for m in report.tests)
    failed = sum(m.summary.failed for m in report.tests)
    skipped = sum(m.summary.skipped for m in report.tests)

    report.summary = ComputorReportSummary(
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
    )

    report.duration = duration

    # Set overall result
    if failed > 0:
        report.status = StatusEnum.completed
        report.result = ResultEnum.failed
        report.resultMessage = "Some or all tests failed"
    elif passed == total and total > 0:
        report.status = StatusEnum.completed
        report.result = ResultEnum.passed
        report.resultMessage = "Congratulations! All tests passed"
    else:
        report.status = StatusEnum.completed
        report.result = ResultEnum.passed if skipped == 0 else ResultEnum.skipped
        report.resultMessage = "Some tests were skipped"

    # Add environment info
    report.environment = {
        "Python": platform.python_version(),
        "Platform": platform.platform(),
        "Packages": {
            "pytest": pytest.__version__,
        },
    }

    # Write report to file
    if reportfile:
        output_dir = os.path.dirname(reportfile)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(reportfile, "w") as f:
            json.dump(report.model_dump(), f, indent=indent)


def get_report_header(config: pytest.Config) -> List[str]:
    """
    Generate report header lines.

    Args:
        config: pytest config object

    Returns:
        List of header lines
    """
    _report = config.stash[report_key]
    root = _report["root"]
    testyamlfile = _report["testyamlfile"]
    specyamlfile = _report["specyamlfile"]
    pytestflags = _report["pytestflags"]
    verbosity_level = _report["verbosity"]

    if specyamlfile == "":
        specyamlfile = "not set"

    tw, _ = shutil.get_terminal_size(fallback=(80, 24))
    full = "=" * tw

    return [
        f"{full}",
        f"{Fore.CYAN}Computor Testing Engine{Style.RESET_ALL}",
        f"{full}",
        f"{Fore.CYAN}testroot:      {Style.RESET_ALL} {root}",
        f"{Fore.CYAN}testsuite:     {Style.RESET_ALL} {testyamlfile}",
        f"{Fore.CYAN}specification: {Style.RESET_ALL} {specyamlfile}",
        f"{Fore.CYAN}pytestflags:   {Style.RESET_ALL} {pytestflags}",
        f"{Fore.CYAN}verbosity:     {Style.RESET_ALL} {verbosity_level}",
        f"{full}",
    ]


def add_terminal_summary(
    terminalreporter: TerminalReporter,
    exitstatus: pytest.ExitCode,
    config: pytest.Config,
) -> None:
    """
    Add custom summary to pytest output.

    Args:
        terminalreporter: pytest terminal reporter
        exitstatus: exit status code
        config: pytest config object
    """
    _report = config.stash[report_key]
    verbosity_level = _report["verbosity"]

    if verbosity_level > 0:
        report: ComputorReport = _report["report"]
        testsuite: ComputorTestSuite = _report["testsuite"]

        total = report.summary.total
        passed = report.summary.passed
        failed = report.summary.failed
        skipped = report.summary.skipped

        terminalreporter.ensure_newline()
        terminalreporter.section(
            f"{testsuite.name} - Summary", sep="~", purple=True, bold=True
        )
        terminalreporter.line(f"Total Test Collections: {total}")
        terminalreporter.line(f"Passed: {passed}")
        terminalreporter.line(f"Failed: {failed}")
        terminalreporter.line(f"Skipped: {skipped}")


# Utility functions for test implementations

def main_idx_by_dependency(testsuite: ComputorTestSuite, dependency: str) -> Optional[int]:
    """
    Find main test index by dependency name.

    Args:
        testsuite: test suite object
        dependency: dependency name to find

    Returns:
        Index of the test collection or None if not found
    """
    for idx, main in enumerate(testsuite.properties.tests):
        if main.name == dependency:
            return idx
    return None


__all__ = [
    # Enums and keys
    "Solution",
    "metadata_key",
    "report_key",
    # OO Configuration classes
    "BaseTesterConfig",
    "SimpleTesterConfig",
    "InterpretedTesterConfig",
    "OctaveTesterConfig",
    "create_conftest_hooks",
    # Configuration functions (functional API)
    "add_common_options",
    "configure_test_session",
    "generate_test_cases",
    # Report functions
    "update_report_on_test_result",
    "finalize_session",
    "get_report_header",
    "add_terminal_summary",
    # Utilities
    "main_idx_by_dependency",
    "get_property_as_list",
]

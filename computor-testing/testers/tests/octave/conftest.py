"""
Pytest configuration and hooks for OATester.

This module configures pytest for running Octave code tests,
including test parametrization, reporting, and result collection.
"""

import json
import os
import datetime
from datetime import timezone
import shutil
import time
import logging
import pytest
from _pytest.terminal import TerminalReporter
from _pytest._code.code import ExceptionChainRepr
from colorama import Fore, Style
from typing import List

from ctcore.models import (
    DIRECTORIES,
    ComputorTestSuite, ComputorSpecification,
    StatusEnum, ResultEnum,
    ComputorReport, ComputorReportMain,
    ComputorReportSub, ComputorReportSummary,
    read_ca_file,
)
from ctcore.helpers import get_property_as_list
from ctcore.security import validate_path_in_root, validate_filename, PathValidationError

from ..conftest_base import (
    Solution,
    metadata_key,
    report_key,
    add_common_options,
    get_report_header,
    add_terminal_summary,
)


logger = logging.getLogger(__name__)


# Re-export for test_class.py
__all__ = ["Solution", "report_key", "metadata_key"]


def pytest_addoption(parser: pytest.Parser):
    """Add custom command line options."""
    add_common_options(parser)


def pytest_metadata(metadata, config):
    """Store environment metadata."""
    config.stash[metadata_key] = metadata


def pytest_configure(config: pytest.Config) -> None:
    """
    Configure test execution.

    Generates test case indices and initializes the report structure.
    Note: Octave tester has custom property inheritance logic that differs
    from the base implementation.
    """
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

    # Root directory from option or fallback to testsuite location
    root = os.path.abspath(testroot) if testroot and testroot != "." else os.path.abspath(os.path.dirname(testyamlfile))

    # Validate and create directories
    for directory in DIRECTORIES:
        dir_path = getattr(specification, directory)
        if dir_path is not None:
            try:
                if not os.path.isabs(dir_path):
                    dir_path = validate_path_in_root(dir_path, root, f"{directory}")
                else:
                    dir_path = validate_path_in_root(dir_path, root, f"{directory}")
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

    reportfile = specification.outputName
    if not os.path.isabs(reportfile):
        reportfile = os.path.join(specification.outputDirectory, reportfile)

    try:
        reportfile = validate_path_in_root(reportfile, root, "output file")
    except PathValidationError as e:
        logger.error(f"Output file path validation failed: {e}")
        raise ValueError(f"Security error: {e}") from e

    os.makedirs(os.path.dirname(reportfile), exist_ok=True)

    # Build test case indices with property inheritance
    testcases = []
    main_tests: List[ComputorReportMain] = []

    subfields = [
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
    mainfields = subfields.copy()
    mainfields.extend([
        "storeGraphicsArtifacts",
        "competency",
        "timeout",
    ])

    def parent_property(properties, this, parent):
        """Inherit None properties from parent."""
        for prop in properties:
            if getattr(this, prop) is None:
                setattr(this, prop, getattr(parent, prop))

    for idx_main, main in enumerate(testsuite.properties.tests):
        parent_property(mainfields, main, testsuite.properties)
        sub_tests: List[ComputorReportSub] = []
        for idx_sub, sub in enumerate(main.tests):
            parent_property(subfields, sub, main)
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
        "language": "octave",
        # For exist tests - track found files
        "student_file_list": [],
        "reference_file_list": [],
        "student_command_list": [],
        "reference_command_list": [],
    }
    config.stash[report_key] = report_data


def pytest_generate_tests(metafunc: pytest.Metafunc):
    """Generate parametrized test cases."""
    report = metafunc.config.stash[report_key]
    metafunc.parametrize("testcases", report["testcases"])


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Process test results."""
    out = yield
    _report: pytest.TestReport = out.get_result()

    if _report.when == "call":
        idx_main, idx_sub = item.callspec.params["testcases"]
        rep = item.config.stash[report_key]
        testsuite: ComputorTestSuite = rep["testsuite"]
        main = testsuite.properties.tests[idx_main]
        sub = main.tests[idx_sub]
        _report.nodeid = f"{main.name}\\{sub.name}"

        report: ComputorReport = rep["report"]
        testmain: ComputorReportMain = report.tests[idx_main]
        testsub: ComputorReportSub = testmain.tests[idx_sub]

        testsub.result = _report.outcome.upper()

        if _report.longrepr is not None:
            if testsub.result == ResultEnum.skipped:
                try:
                    testsub.resultMessage = str(_report.longrepr[2])
                except:
                    testsub.resultMessage = str(_report.longrepr)
            else:
                longrepr: ExceptionChainRepr = _report.longrepr
                chain = longrepr.chain[-1][1]
                if chain is not None:
                    testsub.resultMessage = chain.message

        testmain.timestamp = time.time()


def pytest_sessionstart(session: pytest.Session):
    """Record session start time."""
    _report = session.config.stash[report_key]
    _report["started"] = time.time()


def pytest_sessionfinish(session: pytest.Session):
    """Generate final report on session finish."""
    exitcode = session.exitstatus
    environment = session.config.stash[metadata_key]
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
        _testended = float(main.timestamp)
        del main.timestamp
        _testduration = _testended - _teststarted
        _teststarted = _testended

        test_main = testsuite.properties.tests[idx_main]
        sub_time_s = 0
        sub_time_r = 0
        status = StatusEnum.completed
        idx = str(idx_main)
        errs = []

        if idx in solutions:
            solution_s = solutions[idx][Solution.student]
            solution_r = solutions[idx][Solution.reference]
            errs = solution_s.get("errors", [])
            sub_time_s = solution_s.get("exectime", 0)
            sub_time_r = solution_r.get("exectime", 0)
            status = solution_s.get("status", StatusEnum.completed)

        sub_total = main.summary.total
        sub_passed = 0
        sub_failed = 0
        sub_skipped = 0

        for idx_sub, sub in enumerate(main.tests):
            test_sub = test_main.tests[idx_sub]
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
            result_message = test_main.successMessage
        elif sub_skipped > 0:
            skipped += 1
            main.result = ResultEnum.skipped
            result_message = "Tests skipped"
        else:
            failed += 1
            main.result = ResultEnum.failed
            result_message = test_main.failureMessage
        main.resultMessage = result_message

    report.summary.passed = passed
    report.summary.skipped = skipped
    report.summary.failed = failed

    if exitcode == pytest.ExitCode.INTERRUPTED:
        report.status = StatusEnum.cancelled
    else:
        report.status = StatusEnum.completed

    if total == 0:
        report.result = ResultEnum.skipped
        result_message = "No Tests specified"
    elif passed == total:
        report.result = ResultEnum.passed
        result_message = testsuite.properties.successMessage
    elif skipped == total:
        report.result = ResultEnum.skipped
        result_message = "Tests skipped"
    else:
        report.result = ResultEnum.failed
        result_message = testsuite.properties.failureMessage

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
        "exitcode": str(exitcode),
    }

    with open(reportfile, "w", encoding="utf-8") as file:
        json.dump(
            report.model_dump(exclude_none=True),
            file, default=str, indent=indent
        )


@pytest.hookimpl(trylast=True)
def pytest_report_header(config):
    """Add custom header to pytest output."""
    return get_report_header(config)


def pytest_terminal_summary(
    terminalreporter: TerminalReporter,
    exitstatus: pytest.ExitCode,
    config: pytest.Config
):
    """Add custom summary to pytest output."""
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

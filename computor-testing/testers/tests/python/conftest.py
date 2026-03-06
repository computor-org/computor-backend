"""
Python Testing Framework - Pytest Configuration

Defines fixtures and hooks for pytester using the object-oriented approach.
"""

import time
import pytest
from _pytest.monkeypatch import MonkeyPatch
from _pytest._code.code import ExceptionChainRepr

from ctcore.models import (
    ComputorTestSuite,
    StatusEnum, ResultEnum,
    ComputorReport, ComputorReportMain, ComputorReportSub,
)

from ..conftest_base import (
    Solution,
    metadata_key,
    report_key,
    InterpretedTesterConfig,
    create_conftest_hooks,
)


# Re-export for test_class.py
__all__ = ["Solution", "report_key", "metadata_key"]


class PythonTesterConfig(InterpretedTesterConfig):
    """Configuration for Python tester."""
    language = "python"
    has_metadata = True
    has_monkeypatch = True
    has_property_inheritance = True


# Create and register all hooks from the config class
_config = PythonTesterConfig()
_hooks = create_conftest_hooks(type(_config))

# Export hooks to module level so pytest can discover them
pytest_addoption = _hooks["pytest_addoption"]
pytest_configure = _hooks["pytest_configure"]
pytest_generate_tests = _hooks["pytest_generate_tests"]
pytest_sessionstart = _hooks["pytest_sessionstart"]
pytest_sessionfinish = _hooks["pytest_sessionfinish"]


# Override pytest_runtest_makereport with hookwrapper to capture detailed error messages
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Process test results and extract detailed error messages."""
    out = yield
    _report: pytest.TestReport = out.get_result()

    if _report.when == "call":
        try:
            idx_main, idx_sub = item.callspec.params["testcases"]
            rep = item.config.stash[report_key]
            testsuite: ComputorTestSuite = rep["testsuite"]
            main = testsuite.properties.tests[idx_main]
            sub = main.tests[idx_sub]
            _report.nodeid = f"{main.name}\\{sub.name}"

            report: ComputorReport = rep["report"]
            testmain: ComputorReportMain = report.tests[idx_main]
            testsub: ComputorReportSub = testmain.tests[idx_sub]

            # Update status based on outcome
            if _report.outcome == "passed":
                testsub.status = StatusEnum.completed
                testsub.result = ResultEnum.passed
                testmain.summary.passed += 1
            elif _report.outcome == "skipped":
                testsub.status = StatusEnum.skipped
                testsub.result = ResultEnum.skipped
                testmain.summary.skipped += 1
            else:  # failed
                testsub.status = StatusEnum.failed
                testsub.result = ResultEnum.failed
                testmain.summary.failed += 1

            # Extract detailed error message from longrepr
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
        except (KeyError, IndexError, AttributeError):
            pass

# Optional hooks
if "pytest_metadata" in _hooks:
    pytest_metadata = _hooks["pytest_metadata"]

if "pytest_report_header" in _hooks:
    pytest_report_header = _hooks["pytest_report_header"]

if "pytest_terminal_summary" in _hooks:
    pytest_terminal_summary = _hooks["pytest_terminal_summary"]


# Python-specific fixture for monkeypatching
@pytest.fixture(scope="function")
def monkeymodule():
    """Provide a monkeypatch fixture scoped to function."""
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()

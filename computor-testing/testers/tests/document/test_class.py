"""
Document Testing Framework - Test Class

Main test execution logic for document/text testing.
"""

import os
import re
import pytest

from ctcore.security import safe_regex_findall, RegexTimeoutError

from ctcore.models import (
    ComputorTestSuite,
    ComputorTestCollection,
    ComputorTest,
    ComputorSpecification,
    TypeEnum,
    StatusEnum,
    QualificationEnum,
)
from .conftest import report_key, Solution
from testers.executors.document import TextAnalyzer, TextMetrics
from ctcore.helpers import get_property_as_list
from ..test_base import (
    main_idx_by_dependency,
    check_file_exists,
    check_success_dependencies,
    check_exist,
)


def get_analyzer(pytestconfig, file_path: str) -> TextAnalyzer:
    """
    Get or create a TextAnalyzer for a file.

    Caches analyzers in the pytest stash for reuse.
    """
    _report = pytestconfig.stash[report_key]
    analyzed_files = _report.get("analyzed_files", {})

    if file_path in analyzed_files:
        return analyzed_files[file_path]

    if not os.path.exists(file_path):
        return None

    analyzer = TextAnalyzer.from_file(file_path)
    analyzer.analyze()  # Pre-compute metrics
    analyzed_files[file_path] = analyzer
    _report["analyzed_files"] = analyzed_files

    return analyzer


class TestComputorDocument:
    """Main test class for document/text testing."""

    def test_entrypoint(self, pytestconfig, testcases):
        """
        Execute a single test case.

        Args:
            pytestconfig: Pytest configuration
            testcases: Tuple of (main_idx, sub_idx)
        """
        idx_main, idx_sub = testcases

        _report = pytestconfig.stash[report_key]
        testsuite: ComputorTestSuite = _report["testsuite"]
        specification: ComputorSpecification = _report["specification"]
        main: ComputorTestCollection = testsuite.properties.tests[idx_main]
        sub: ComputorTest = main.tests[idx_sub]
        root = _report["root"]

        dir_student = specification.studentDirectory
        if not os.path.isabs(dir_student):
            dir_student = os.path.join(root, dir_student)

        testtype = main.type
        file = main.file or main.entryPoint

        name = sub.name
        value = sub.value
        pattern = sub.pattern
        qualification = sub.qualification or QualificationEnum.verifyEqual

        # Get test options
        ignore_case = sub.ignoreCase or False
        allowed_range = sub.allowedOccuranceRange

        # Check success dependencies
        report_obj = _report["report"]
        error, errormsg, dep_status = check_success_dependencies(testsuite, report_obj, main)
        if error:
            if dep_status == StatusEnum.skipped:
                pytest.skip(errormsg)
            else:
                pytest.fail(errormsg)

        # Exist tests (check file exists)
        if testtype == TypeEnum.exist:
            check_exist(name, file, dir_student, sub, _report)

        # Word count test
        elif testtype == "wordcount":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for wordcount test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            metrics = analyzer.analyze()
            actual = metrics.word_count

            self._check_count(name, actual, value, allowed_range, qualification, "word count")

        # Line count test
        elif testtype == "linecount":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for linecount test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            metrics = analyzer.analyze()
            actual = metrics.line_count

            self._check_count(name, actual, value, allowed_range, qualification, "line count")

        # Character count test
        elif testtype == "charcount":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for charcount test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            metrics = analyzer.analyze()
            # Use char_count_no_spaces by default unless specified
            actual = metrics.char_count_no_spaces if name == "no_spaces" else metrics.char_count

            self._check_count(name, actual, value, allowed_range, qualification, "character count")

        # Paragraph count test
        elif testtype == "paragraphcount":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for paragraphcount test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            metrics = analyzer.analyze()
            actual = metrics.paragraph_count

            self._check_count(name, actual, value, allowed_range, qualification, "paragraph count")

        # Sentence count test
        elif testtype == "sentencecount":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for sentencecount test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            metrics = analyzer.analyze()
            actual = metrics.sentence_count

            self._check_count(name, actual, value, allowed_range, qualification, "sentence count")

        # Heading count test (markdown)
        elif testtype == "headingcount":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for headingcount test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            metrics = analyzer.analyze()
            actual = metrics.heading_count

            self._check_count(name, actual, value, allowed_range, qualification, "heading count")

        # Section/heading existence test (markdown)
        elif testtype == "section":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for section test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            # value can be a heading level (1-6)
            level = int(value) if value is not None else None

            if not analyzer.has_section(name, level=level):
                level_str = f" (level {level})" if level else ""
                pytest.fail(f"Section `{name}`{level_str} not found")

        # Keyword presence test
        elif testtype == "keyword":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for keyword test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            # name is the keyword to search for
            keyword = name

            if qualification == QualificationEnum.count or value is not None or allowed_range:
                # Count occurrences
                actual = analyzer.count_keyword(keyword, case_sensitive=not ignore_case)
                self._check_count(keyword, actual, value, allowed_range, qualification, "keyword occurrences")
            else:
                # Just check presence
                if not analyzer.has_keyword(keyword, case_sensitive=not ignore_case):
                    pytest.fail(f"Keyword `{keyword}` not found")

        # Pattern/regex test
        elif testtype == "pattern":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for pattern test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            # pattern is the regex to search for
            regex = pattern or name
            flags = re.IGNORECASE if ignore_case else 0

            matches = analyzer.matches_pattern(regex, flags=flags)

            if qualification == QualificationEnum.count or value is not None or allowed_range:
                # Count matches
                actual = len(matches)
                self._check_count(regex, actual, value, allowed_range, qualification, "pattern matches")
            else:
                # Just check presence
                if not matches:
                    pytest.fail(f"Pattern `{regex}` not found")

        # Structural test (reuse from other testers)
        elif testtype == TypeEnum.structural:
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for structural test")

            if not os.path.exists(file_path):
                pytest.fail(f"File `{file}` not found")

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if pattern:
                flags = re.IGNORECASE if ignore_case else 0
                try:
                    matches = safe_regex_findall(pattern, content, flags)
                except RegexTimeoutError:
                    pytest.fail(f"Pattern `{pattern}` timed out (possible ReDoS)")
                count = len(matches)

                if allowed_range:
                    c_min, c_max = allowed_range
                    if c_max == 0:
                        c_max = float('inf')
                    if not (c_min <= count <= c_max):
                        pytest.fail(f"Pattern `{pattern}` found {count} times, expected {c_min}-{c_max}")
                elif value is not None:
                    if count != int(value):
                        pytest.fail(f"Pattern `{pattern}` found {count} times, expected {value}")
            else:
                search_str = name
                if ignore_case:
                    found = search_str.lower() in content.lower()
                else:
                    found = search_str in content

                if not found:
                    pytest.fail(f"`{name}` not found in file")

        # Unique word count test
        elif testtype == "uniquewords":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for uniquewords test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            metrics = analyzer.analyze()
            actual = metrics.unique_word_count

            self._check_count(name, actual, value, allowed_range, qualification, "unique word count")

        # Average word length test
        elif testtype == "avgwordlength":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for avgwordlength test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            metrics = analyzer.analyze()
            actual = metrics.avg_word_length

            if value is not None:
                expected = float(value)
                tolerance = sub.absoluteTolerance or 0.1
                if abs(actual - expected) > tolerance:
                    pytest.fail(f"Average word length is {actual:.2f}, expected {expected:.2f} (±{tolerance})")

        # Average sentence length test
        elif testtype == "avgsentencelength":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for avgsentencelength test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            metrics = analyzer.analyze()
            actual = metrics.avg_sentence_length

            if value is not None:
                expected = float(value)
                tolerance = sub.absoluteTolerance or 1.0
                if abs(actual - expected) > tolerance:
                    pytest.fail(f"Average sentence length is {actual:.2f}, expected {expected:.2f} (±{tolerance})")

        # Link count test (markdown)
        elif testtype == "linkcount":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for linkcount test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            metrics = analyzer.analyze()
            actual = metrics.link_count

            self._check_count(name, actual, value, allowed_range, qualification, "link count")

        # Image count test (markdown)
        elif testtype == "imagecount":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for imagecount test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            metrics = analyzer.analyze()
            actual = metrics.image_count

            self._check_count(name, actual, value, allowed_range, qualification, "image count")

        # Code block count test (markdown)
        elif testtype == "codeblockcount":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for codeblockcount test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            metrics = analyzer.analyze()
            actual = metrics.code_block_count

            self._check_count(name, actual, value, allowed_range, qualification, "code block count")

        # List item count test (markdown)
        elif testtype == "listitemcount":
            file_path = os.path.join(dir_student, file) if file else None
            if not file_path:
                pytest.fail("No file specified for listitemcount test")

            analyzer = get_analyzer(pytestconfig, file_path)
            if analyzer is None:
                pytest.fail(f"File `{file}` not found")

            metrics = analyzer.analyze()
            actual = metrics.list_item_count

            self._check_count(name, actual, value, allowed_range, qualification, "list item count")

        else:
            pytest.skip(f"Unknown test type: {testtype}")

    def _check_count(self, name: str, actual: int, value, allowed_range, qualification, metric_name: str):
        """
        Check a count against expected value or range.

        Args:
            name: Test/item name
            actual: Actual count
            value: Expected value (if any)
            allowed_range: [min, max] range (if any)
            qualification: Test qualification type
            metric_name: Human-readable metric name for error messages
        """
        if allowed_range:
            c_min, c_max = allowed_range
            if c_max == 0:
                c_max = float('inf')
            if not (c_min <= actual <= c_max):
                if c_max == float('inf'):
                    pytest.fail(f"{metric_name.capitalize()} is {actual}, expected at least {c_min}")
                else:
                    pytest.fail(f"{metric_name.capitalize()} is {actual}, expected {c_min}-{c_max}")
        elif value is not None:
            expected = int(value)
            if qualification == QualificationEnum.verifyEqual:
                if actual != expected:
                    pytest.fail(f"{metric_name.capitalize()} is {actual}, expected {expected}")
            elif qualification == QualificationEnum.contains:
                # Contains means at least this many
                if actual < expected:
                    pytest.fail(f"{metric_name.capitalize()} is {actual}, expected at least {expected}")

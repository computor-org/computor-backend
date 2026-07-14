"""Authoring + release (golden-path phase 3).

`lena` creates a group, enrols the students, builds a unit + six assignments,
assigns the examples, and releases — pushing the student template into Forgejo.
"""

from __future__ import annotations

import httpx
import pytest

from fixtures.authoring import example_label, template_folder

pytestmark = pytest.mark.release


def test_students_enrolled_with_group(enrolled_students: dict, target_course_group: dict) -> None:
    assert set(enrolled_students) == {"s_correct", "s_empty", "s_mixed"}
    for member in enrolled_students.values():
        assert member["course_role_id"] == "_student"
        assert member["course_group_id"] == target_course_group["id"]


def test_unit_and_assignments_created(course_contents: dict, python_examples: tuple) -> None:
    assert course_contents["unit"]["path"] == "unit"
    assert len(course_contents["assignments"]) == 6
    for ex in python_examples:
        cc = course_contents["assignments"][ex.directory]
        assert cc["path"] == f"unit.{example_label(ex.directory)}"


def test_examples_assigned(assigned_examples: dict, python_examples: tuple) -> None:
    assert len(assigned_examples) == 6


def test_template_populated_with_all_assignments(
    released_template: dict, python_examples: tuple
) -> None:
    present = {p.split("/", 1)[0] for p in released_template["paths"] if "/" in p}
    for ex in python_examples:
        folder = template_folder(ex.directory)
        assert folder in present, f"{folder} missing from template"


def test_template_has_student_files_but_no_solutions(
    released_template: dict, python_examples: tuple
) -> None:
    paths = set(released_template["paths"])
    # datentypen: student stub present, master solution + test spec absent.
    assert "itpcp.pgph.py.datentypen/datentypen.py" in paths
    leaked = [
        p for p in paths
        if p.endswith("_master.py") or p.endswith("test.yaml") or "localTests/" in p
    ]
    assert not leaked, f"solution/test files leaked into student template: {leaked}"

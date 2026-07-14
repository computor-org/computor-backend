"""Permission matrix — the `student` persona column (s_correct, _student)."""
from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import MATRIX, check_matrix_row

pytestmark = pytest.mark.permissions


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.id())
def test_student(row, student_correct_client: httpx.Client, matrix_ids: dict, record_property) -> None:
    check_matrix_row(row, student_correct_client, matrix_ids, "student", record_property)

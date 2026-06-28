"""Permission matrix — course ``_student`` column."""

from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import MATRIX, check_matrix_row

pytestmark = pytest.mark.permissions


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.id())
def test_student(
    row,
    student_client: httpx.Client,
    matrix_ids: dict[str, str],
    record_property,
) -> None:
    check_matrix_row(row, student_client, matrix_ids, "student", record_property)

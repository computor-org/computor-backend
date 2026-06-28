"""Permission matrix — course ``_lecturer`` column."""

from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import MATRIX, check_matrix_row

pytestmark = pytest.mark.permissions


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.id())
def test_lecturer(
    row,
    lecturer_client: httpx.Client,
    matrix_ids: dict[str, str],
    record_property,
) -> None:
    check_matrix_row(row, lecturer_client, matrix_ids, "lecturer", record_property)

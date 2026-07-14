"""Permission matrix — the `uma` persona column."""
from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import MATRIX, check_matrix_row

pytestmark = pytest.mark.permissions


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.id())
def test_uma(row, uma_client: httpx.Client, matrix_ids: dict, record_property) -> None:
    check_matrix_row(row, uma_client, matrix_ids, "uma", record_property)

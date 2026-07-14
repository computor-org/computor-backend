"""Permission matrix — the `lena` persona column."""
from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import MATRIX, check_matrix_row

pytestmark = pytest.mark.permissions


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.id())
def test_lena(row, lena_client: httpx.Client, matrix_ids: dict, record_property) -> None:
    check_matrix_row(row, lena_client, matrix_ids, "lena", record_property)

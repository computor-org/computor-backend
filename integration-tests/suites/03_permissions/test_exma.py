"""Permission matrix — the `exma` persona column."""
from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import MATRIX, check_matrix_row

pytestmark = pytest.mark.permissions


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.id())
def test_exma(row, exma_client: httpx.Client, matrix_ids: dict, record_property) -> None:
    check_matrix_row(row, exma_client, matrix_ids, "exma", record_property)

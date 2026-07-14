"""Permission matrix — the `orga` persona column."""
from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import MATRIX, check_matrix_row

pytestmark = pytest.mark.permissions


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.id())
def test_orga(row, orga_client: httpx.Client, matrix_ids: dict, record_property) -> None:
    check_matrix_row(row, orga_client, matrix_ids, "orga", record_property)

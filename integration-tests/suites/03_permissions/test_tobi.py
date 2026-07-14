"""Permission matrix — the `tobi` persona column."""
from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import MATRIX, check_matrix_row

pytestmark = pytest.mark.permissions


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.id())
def test_tobi(row, tobi_client: httpx.Client, matrix_ids: dict, record_property) -> None:
    check_matrix_row(row, tobi_client, matrix_ids, "tobi", record_property)

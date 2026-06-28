"""Permission matrix — unauthenticated column."""

from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import MATRIX, check_matrix_row

pytestmark = pytest.mark.permissions


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.id())
def test_unauthenticated(
    row,
    anonymous_client: httpx.Client,
    matrix_ids: dict[str, str],
    record_property,
) -> None:
    check_matrix_row(row, anonymous_client, matrix_ids, "anon", record_property)

"""Permission matrix — course ``_maintainer`` column."""

from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import MATRIX, check_matrix_row

pytestmark = pytest.mark.permissions


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.id())
def test_maintainer(
    row,
    maintainer_client: httpx.Client,
    matrix_ids: dict[str, str],
    record_property,
) -> None:
    check_matrix_row(row, maintainer_client, matrix_ids, "maintainer", record_property)

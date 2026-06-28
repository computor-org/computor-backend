"""Permission matrix — admin (``_admin``) column.

Admin bypasses every permission check (see
``computor_backend/permissions/principal.py``), so every asserted cell
should be a 2xx.
"""

from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import MATRIX, check_matrix_row

pytestmark = pytest.mark.permissions


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.id())
def test_admin(
    row,
    admin_client: httpx.Client,
    matrix_ids: dict[str, str],
    record_property,
) -> None:
    check_matrix_row(row, admin_client, matrix_ids, "admin", record_property)

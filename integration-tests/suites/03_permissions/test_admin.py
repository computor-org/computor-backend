"""Permission matrix — admin (`_admin`) column.

Admin bypasses every permission check (see
``computor_backend/permissions/principal.py``), so every asserted cell
should be a 2xx. If a test here 403s, either the admin claims haven't been
applied at seed time or an endpoint is gating on something other than the
admin flag.
"""

from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import MATRIX, UNSET, call

pytestmark = pytest.mark.permissions


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.id())
def test_admin(
    row, admin_client: httpx.Client, matrix_ids: dict[str, str]
) -> None:
    expected = row.expected_for("admin")
    if expected == UNSET:
        pytest.skip("matrix cell not asserted for admin")
    r = call(admin_client, row, matrix_ids)
    assert r.status_code == expected, (
        f"{row.method} {r.request.url}: expected {expected}, got "
        f"{r.status_code} — body={r.text[:200]}"
    )

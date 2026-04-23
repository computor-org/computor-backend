"""Permission matrix — unauthenticated column.

Every row in the matrix is called against a client with no credentials; the
observed status code must match ``row.expected["anon"]``. Rows marked UNSET
are skipped (the matrix isn't asserting that cell yet).
"""

from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import MATRIX, UNSET, call

pytestmark = pytest.mark.permissions


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.id())
def test_unauthenticated(
    row, anonymous_client: httpx.Client, matrix_ids: dict[str, str]
) -> None:
    expected = row.expected_for("anon")
    if expected == UNSET:
        pytest.skip("matrix cell not asserted for anon")
    r = call(anonymous_client, row, matrix_ids)
    assert r.status_code == expected, (
        f"{row.method} {r.request.url}: expected {expected}, got "
        f"{r.status_code} — body={r.text[:200]}"
    )

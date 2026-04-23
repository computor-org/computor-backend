"""Permission matrix — course ``_lecturer`` column."""

from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import MATRIX, UNSET, call

pytestmark = pytest.mark.permissions


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.id())
def test_lecturer(
    row, lecturer_client: httpx.Client, matrix_ids: dict[str, str]
) -> None:
    expected = row.expected_for("lecturer")
    if expected == UNSET:
        pytest.skip("matrix cell not asserted for lecturer")
    r = call(lecturer_client, row, matrix_ids)
    assert r.status_code == expected, (
        f"{row.method} {r.request.url}: expected {expected}, got "
        f"{r.status_code} — body={r.text[:200]}"
    )

"""P3.1 — OpenAPI coverage guard for the permission matrix.

Flags any endpoint the live backend exposes that is in neither the permission
``MATRIX`` nor the curated exclusions (``EXCLUDED`` / ``EXCLUDED_PREFIXES`` in
``fixtures/permission_matrix.py``). This forces a matrix-or-exclude decision on
every new endpoint, so authorization coverage cannot silently rot.

Landed ``xfail(strict=False)`` (informational): the exclusions are not yet
curated against the full live surface, so it reports the uncovered set without
failing the suite. Once ``EXCLUDED`` is triaged to empty-uncovered, drop the
``xfail`` to make the guard enforcing (it will then xpass → fail-on-regression).
"""
from __future__ import annotations

import httpx
import pytest

from fixtures.permission_matrix import is_excluded, matrix_coverage

pytestmark = pytest.mark.permissions


@pytest.mark.xfail(
    reason="P3.1: exclusions not yet fully curated against the live surface — "
    "informational until the uncovered set is triaged, then drop this xfail.",
    strict=False,
)
def test_every_endpoint_is_matrixed_or_excluded(
    openapi_inventory: set[tuple[str, str]],
    record_property,
) -> None:
    covered = matrix_coverage()
    uncovered = sorted(
        (method, path)
        for (method, path) in openapi_inventory
        if (method, path) not in covered and not is_excluded(method, path)
    )
    record_property("uncovered_endpoint_count", len(uncovered))
    assert not uncovered, (
        f"{len(uncovered)} endpoint(s) are in neither MATRIX nor EXCLUDED — "
        "add a matrix row or an exclusion for each:\n"
        + "\n".join(f"  {method} {path}" for method, path in uncovered)
    )

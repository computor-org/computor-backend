"""Temporarily skip the legacy permission-matrix suite.

These per-role tests are built on the removed local-login role clients
(owner/maintainer/lecturer/tutor/student) and a course pre-seeded with
course-role memberships. They are reworked in P3 (permission matrix) on the new
persona axis, after course setup lands — see testing-strategy/BACKLOG.md.

Until then they are skipped (visibly), not deleted, so the reference matrix in
fixtures/permission_matrix.py stays intact.
"""
import pytest

_SKIP = pytest.mark.skip(
    reason="legacy permission suite — reworked in P3 on the persona axis (needs course memberships)"
)


def pytest_collection_modifyitems(items):
    for item in items:
        if "03_permissions" in str(item.fspath):
            item.add_marker(_SKIP)

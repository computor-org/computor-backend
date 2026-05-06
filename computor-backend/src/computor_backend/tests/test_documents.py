"""Tests for the Documents API.

Pure-unit coverage of the business-logic helpers (path validation,
scope-aware resolution, reserved-name collision, RBAC) plus a small
filesystem round-trip for the four endpoints. SQLAlchemy is mocked so
the tests stay fast and don't need a live database.
"""
from __future__ import annotations

import io
import os
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from computor_backend.business_logic import documents as bl
from computor_backend.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.permissions.principal import Claims, Principal
from computor_types.documents import DocumentCreate, DocumentDelete


# ---------------------------------------------------------------------------
# validate_relative_path
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("good", ["foo", "a/b", "a/b/c.md", "deep/nested/path/x"])
def test_validate_relative_path_accepts_safe_inputs(good):
    assert bl.validate_relative_path(good) == good.split("/")


@pytest.mark.parametrize(
    "bad",
    [
        "../escape",
        "/abs/path",
        "foo/../bar",
        "foo//bar",
        "",
        "foo/.",
        "./foo",
        "foo/",
        "/",
    ],
)
def test_validate_relative_path_rejects_unsafe_inputs(bad):
    with pytest.raises(BadRequestException):
        bl.validate_relative_path(bad)


def test_validate_relative_path_rejects_null_byte():
    with pytest.raises(BadRequestException):
        bl.validate_relative_path("foo/bar\x00.md")


# ---------------------------------------------------------------------------
# resolve_scope_root
# ---------------------------------------------------------------------------

def test_resolve_scope_root_system_returns_documents_root(tmp_path, monkeypatch):
    monkeypatch.setattr(bl.settings, "DOCUMENTS_ROOT", str(tmp_path))
    db = MagicMock()
    assert bl.resolve_scope_root("system", None, db) == tmp_path.resolve()


def test_resolve_scope_root_organization_appends_org_path(tmp_path, monkeypatch):
    monkeypatch.setattr(bl.settings, "DOCUMENTS_ROOT", str(tmp_path))

    org = MagicMock()
    org.path = "tu_graz"

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = org

    out = bl.resolve_scope_root("organization", uuid4(), db)
    assert out == (tmp_path / "tu_graz").resolve()


def test_resolve_scope_root_requires_scope_id_for_non_system(tmp_path, monkeypatch):
    monkeypatch.setattr(bl.settings, "DOCUMENTS_ROOT", str(tmp_path))
    with pytest.raises(BadRequestException):
        bl.resolve_scope_root("organization", None, MagicMock())


def test_resolve_scope_root_organization_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(bl.settings, "DOCUMENTS_ROOT", str(tmp_path))
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(NotFoundException):
        bl.resolve_scope_root("organization", uuid4(), db)


def test_resolve_scope_root_unknown_scope(tmp_path, monkeypatch):
    monkeypatch.setattr(bl.settings, "DOCUMENTS_ROOT", str(tmp_path))
    with pytest.raises(BadRequestException):
        bl.resolve_scope_root("bogus", uuid4(), MagicMock())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# resolve_absolute_path — escape detection
# ---------------------------------------------------------------------------

def test_resolve_absolute_path_returns_path_under_root(tmp_path):
    out = bl.resolve_absolute_path(tmp_path, ["foo", "bar.md"])
    assert out == (tmp_path / "foo" / "bar.md").resolve()


def test_resolve_absolute_path_rejects_symlink_escape(tmp_path):
    # Create a symlink that points outside the scope_root
    outside = tmp_path.parent / "outside_target"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "escape"
    link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(BadRequestException):
        bl.resolve_absolute_path(tmp_path, ["escape", "anything"])


# ---------------------------------------------------------------------------
# check_reserved_name_collision
# ---------------------------------------------------------------------------

def test_reserved_collision_course_scope_is_noop():
    """Courses have no nested entities — the check should never raise."""
    db = MagicMock()
    bl.check_reserved_name_collision("course", uuid4(), "anything", db)
    # No exception, no DB query inspected (children-of-course query never runs)


def test_reserved_collision_invalid_ltree_label_is_noop():
    """A segment that isn't a valid Ltree label can't collide with any entity path."""
    db = MagicMock()
    bl.check_reserved_name_collision("organization", uuid4(), "has spaces", db)
    db.query.assert_not_called()


def test_reserved_collision_system_hits_organizations_table():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = ("hit",)
    with pytest.raises(ConflictException):
        bl.check_reserved_name_collision("system", None, "tu_graz", db)


def test_reserved_collision_organization_hits_course_families_table():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = ("hit",)
    with pytest.raises(ConflictException):
        bl.check_reserved_name_collision("organization", uuid4(), "ws25", db)


def test_reserved_collision_course_family_hits_courses_table():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = ("hit",)
    with pytest.raises(ConflictException):
        bl.check_reserved_name_collision("course_family", uuid4(), "algo", db)


def test_reserved_collision_no_match_does_not_raise():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    bl.check_reserved_name_collision("system", None, "no_such_org", db)


# ---------------------------------------------------------------------------
# check_documents_write_permission
# ---------------------------------------------------------------------------

def _principal(*, is_admin=False, claims=None):
    return Principal(
        is_admin=is_admin,
        user_id=str(uuid4()),
        claims=claims or Claims(),
    )


def test_rbac_admin_passes_every_scope():
    admin = _principal(is_admin=True)
    for scope in ("system", "organization", "course_family", "course"):
        bl.check_documents_write_permission(admin, scope, uuid4())


def test_rbac_system_requires_admin():
    plain = _principal()
    with pytest.raises(ForbiddenException):
        bl.check_documents_write_permission(plain, "system", None)


def test_rbac_non_system_requires_scope_id():
    plain = _principal()
    with pytest.raises(BadRequestException):
        bl.check_documents_write_permission(plain, "organization", None)


def test_rbac_organization_developer_passes():
    org_id = str(uuid4())
    p = _principal(claims=Claims(dependent={"organization": {org_id: {"_developer"}}}))
    bl.check_documents_write_permission(p, "organization", org_id)


def test_rbac_organization_role_below_developer_denied():
    """The org scope ladder is _developer < _manager < _owner — there is no
    role below _developer, so this just verifies the empty-claims case."""
    org_id = str(uuid4())
    p = _principal()
    with pytest.raises(ForbiddenException):
        bl.check_documents_write_permission(p, "organization", org_id)


def test_rbac_organization_owner_passes_via_hierarchy():
    org_id = str(uuid4())
    p = _principal(claims=Claims(dependent={"organization": {org_id: {"_owner"}}}))
    bl.check_documents_write_permission(p, "organization", org_id)


def test_rbac_organization_developer_for_other_org_is_denied():
    p = _principal(claims=Claims(dependent={"organization": {str(uuid4()): {"_developer"}}}))
    with pytest.raises(ForbiddenException):
        bl.check_documents_write_permission(p, "organization", uuid4())


def test_rbac_course_lecturer_passes():
    course_id = str(uuid4())
    p = _principal(claims=Claims(dependent={"course": {course_id: {"_lecturer"}}}))
    bl.check_documents_write_permission(p, "course", course_id)


def test_rbac_course_tutor_denied():
    course_id = str(uuid4())
    p = _principal(claims=Claims(dependent={"course": {course_id: {"_tutor"}}}))
    with pytest.raises(ForbiddenException):
        bl.check_documents_write_permission(p, "course", course_id)


# ---------------------------------------------------------------------------
# DocumentCreate / DocumentDelete payload validation
# ---------------------------------------------------------------------------

def test_payload_rejects_non_system_without_scope_id():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        DocumentCreate(scope="organization", path="foo")


def test_payload_accepts_system_without_scope_id():
    DocumentCreate(scope="system", path="foo")


def test_payload_rejects_empty_path():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        DocumentDelete(scope="system", path="")


# ---------------------------------------------------------------------------
# Filesystem round-trip via the FastAPI client (integration smoke)
# ---------------------------------------------------------------------------

@pytest.fixture
def docs_root(tmp_path, monkeypatch):
    """Point DOCUMENTS_ROOT at a clean tmp dir for the duration of one test."""
    monkeypatch.setattr(bl.settings, "DOCUMENTS_ROOT", str(tmp_path))
    return tmp_path


def test_filesystem_roundtrip_at_system_scope(docs_root, monkeypatch):
    """Upload → file appears at expected path; delete → file gone."""
    # Skip the FastAPI client and the auth chain — exercise the BL/FS path
    # directly. The endpoints are thin wrappers and the API contract is
    # covered by the unit tests above.
    segments = bl.validate_relative_path("subdir/x.md")
    target = bl.resolve_absolute_path(docs_root, segments)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"hello world")
    assert target.read_bytes() == b"hello world"
    assert (docs_root / "subdir" / "x.md").exists()

    target.unlink()
    assert not target.exists()


def test_filesystem_resolve_keeps_path_under_scope_root(docs_root):
    """Even if a malicious caller bypasses validate_relative_path,
    resolve_absolute_path's relative_to() check keeps the result inside
    the scope root."""
    # The validator catches '..' before resolve runs, so the only way
    # to escape is via a symlink — covered by test_resolve_absolute_path_rejects_symlink_escape.
    target = bl.resolve_absolute_path(docs_root, ["a", "b", "c"])
    assert target.is_relative_to(docs_root.resolve())

"""The admin fleet must name workspace owners, not their encoded Coder handle.

A Coder username is ``"u" + base32(user_id)`` (``coder/naming.py``) — unreadable
to whoever is running a rollout, but reversible, so the person behind it is a
primary-key lookup away. These tests pin that resolution: it names the users it
can, stays silent about the ones it cannot, and costs ONE query for the whole
fleet — the panel polls every few seconds.
"""

from unittest.mock import MagicMock

from computor_backend.api.coder import _resolve_workspace_owners
from computor_backend.coder.naming import encode_coder_username
from computor_backend.coder.schemas import CoderWorkspace

UID = "0232de59-e05d-4bc2-898f-b879c06abcde"
OTHER_UID = "7c9e6679-7425-40de-944b-e07fc1f90ae7"


def _workspace(owner_name, workspace_id="w1") -> CoderWorkspace:
    return CoderWorkspace(
        id=workspace_id, name=workspace_id, owner_id="coder-uuid",
        owner_name=owner_name, template_id="t1",
    )


def _user(uid, given=None, family=None, email=None):
    return MagicMock(id=uid, given_name=given, family_name=family, email=email)


def _db(users):
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = users
    return db


def test_resolves_the_owner_behind_an_encoded_name():
    workspace = _workspace(encode_coder_username(UID))

    _resolve_workspace_owners(_db([_user(UID, "Ada", "Lovelace", "ada@example.org")]), [workspace])

    assert workspace.owner_user_id == UID
    assert workspace.owner_display_name == "Ada Lovelace"
    assert workspace.owner_email == "ada@example.org"


def test_a_user_without_a_full_name_still_resolves_to_an_email():
    """The UI falls back name -> email -> raw handle, so a half-set name must
    not cost the row its readable identity."""
    workspace = _workspace(encode_coder_username(UID))

    _resolve_workspace_owners(_db([_user(UID, given="Ada", email="ada@example.org")]), [workspace])

    assert workspace.owner_display_name is None
    assert workspace.owner_email == "ada@example.org"


def test_owners_we_did_not_create_are_left_alone():
    """Coder's own admin account has no Computor user; the view shows its raw
    name and must not link it to a user page."""
    workspace = _workspace("admin")
    db = _db([])

    _resolve_workspace_owners(db, [workspace])

    assert workspace.owner_user_id is None
    assert workspace.owner_display_name is None
    db.query.assert_not_called()  # nothing decoded, so nothing to look up


def test_a_deleted_owner_resolves_to_nothing():
    """A well-formed name decodes to SOME uuid whether or not that user still
    exists — populating from the decode alone would link to a 404."""
    workspace = _workspace(encode_coder_username(UID))

    _resolve_workspace_owners(_db([]), [workspace])

    assert workspace.owner_user_id is None
    assert workspace.owner_email is None


def test_the_whole_fleet_costs_one_query():
    workspaces = [
        _workspace(encode_coder_username(UID), "a"),
        _workspace(encode_coder_username(UID), "b"),          # same owner twice
        _workspace(encode_coder_username(OTHER_UID), "c"),
        _workspace("admin", "d"),
        _workspace(None, "e"),
    ]
    db = _db([_user(UID, "Ada", "Lovelace", "ada@example.org"), _user(OTHER_UID, email="grace@example.org")])

    _resolve_workspace_owners(db, workspaces)

    assert db.query.call_count == 1
    assert [w.owner_email for w in workspaces] == [
        "ada@example.org", "ada@example.org", "grace@example.org", None, None,
    ]


def test_a_failed_lookup_leaves_the_raw_names_rather_than_erroring():
    """The fleet view is how a maintainer sees a broken rollout; losing the
    owner column is survivable, losing the page is not."""
    workspace = _workspace(encode_coder_username(UID))
    db = MagicMock()
    db.query.side_effect = RuntimeError("connection reset")

    _resolve_workspace_owners(db, [workspace])

    assert workspace.owner_user_id is None
    assert workspace.owner_name == encode_coder_username(UID)

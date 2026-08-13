"""Deleting a user via the ORM must defer to the database's delete semantics.

Every user has a trigger-created ``profile`` row, so before ``passive_deletes``
was set on the User relationships, ``db.delete(user)`` — the generic CRUD
delete path — tried to null ``profile.user_id`` and every API user delete
failed with a NOT NULL violation. These tests pin the fixed behavior against
the live dev Postgres: CASCADE children go with the user, RESTRICT children
(grading data under a course membership) still block the delete.
"""

import uuid

import pytest
from sqlalchemy import exc

from computor_backend.model.auth import Account, StudentProfile, User
from computor_backend.model.course import CourseMember
from computor_backend.model.result import Result
from computor_backend.model.role import UserRole

from computor_backend.tests.test_user_connect import _Scaffold


@pytest.fixture
def world(session):
    w = _Scaffold(session)
    try:
        yield w
    finally:
        w.teardown()


def test_delete_user_with_profile_and_children_succeeds(world, session):
    """The everyday case that used to 400: a user with the usual attachments."""
    user = world.user(f"delete_me_{world.sfx}@example.test")
    user_id = str(user.id)
    world.member(user, group=world.group)
    world.profile(user, f"delete_me_{world.sfx}@example.test")
    session.add(UserRole(user_id=user.id, role_id="_user_manager"))
    session.add(
        Account(
            provider="keycloak",
            type="oidc",
            provider_account_id=f"sub-{world.sfx}",
            user_id=user.id,
            builtin=True,
        )
    )
    session.commit()

    fresh = session.query(User).filter(User.id == user_id).one()
    session.delete(fresh)
    session.commit()

    assert session.query(User).filter(User.id == user_id).first() is None
    assert session.query(StudentProfile).filter(StudentProfile.user_id == user_id).first() is None
    assert session.query(Account).filter(Account.user_id == user_id).first() is None
    assert session.query(UserRole).filter(UserRole.user_id == user_id).first() is None
    assert session.query(CourseMember).filter(CourseMember.user_id == user_id).first() is None


def test_delete_user_with_results_is_blocked_by_the_database(world, session):
    """RESTRICT children must keep protecting grading data."""
    user = world.user(f"graded_{world.sfx}@example.test")
    user_id = str(user.id)
    cm = world.member(user, group=world.group)
    content = world.content()
    session.add(
        Result(
            course_member_id=cm.id,
            course_content_id=content.id,
            course_content_type_id=content.course_content_type_id,
            version_identifier=f"v_{world.sfx}",
            status=0,
        )
    )
    session.commit()

    fresh = session.query(User).filter(User.id == user_id).one()
    session.delete(fresh)
    with pytest.raises(exc.IntegrityError):
        session.commit()
    session.rollback()

    assert session.query(User).filter(User.id == user_id).first() is not None

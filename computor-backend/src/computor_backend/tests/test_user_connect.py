"""Integration tests for connecting a pre-provisioned user to a real one.

The merge in ``business_logic/user_connect.py`` is mostly SQL choreography
around real constraints — the cross-table email-uniqueness trigger, the
``(user_id, course_id)`` membership key, RESTRICT children of course_member —
so these tests run against the live dev Postgres and clean up after
themselves. They skip when no database is reachable.
"""

import uuid

import pytest
from sqlalchemy_utils import Ltree

from computor_backend.business_logic.user_connect import connect_users
from computor_backend.exceptions import BadRequestException, ConflictException
from computor_backend.model.auth import Account, StudentProfile, User
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentKind,
    CourseContentType,
    CourseFamily,
    CourseGroup,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.organization import Organization
from computor_backend.model.result import Result


def _sfx() -> str:
    return uuid.uuid4().hex[:10]


class _Scaffold:
    """One org → family → course → group world, plus created users, torn down bottom-up."""

    def __init__(self, db):
        self.db = db
        self.sfx = _sfx()
        self.user_ids = []

        self.org = Organization(
            title=f"Connect Org {self.sfx}",
            organization_type="organization",
            path=Ltree(f"connectorg_{self.sfx}"),
            properties={},
        )
        db.add(self.org)
        db.flush()
        self.family = CourseFamily(
            title="Connect Family",
            path=Ltree(f"connectfam_{self.sfx}"),
            organization_id=self.org.id,
        )
        db.add(self.family)
        db.flush()
        self.course = Course(
            title=f"Connect Course {self.sfx}",
            path=Ltree(f"connectcourse_{self.sfx}"),
            course_family_id=self.family.id,
            organization_id=self.org.id,
        )
        db.add(self.course)
        db.flush()
        self.group = CourseGroup(course_id=self.course.id, title="G1")
        db.add(self.group)
        db.flush()

    def user(self, email: str) -> User:
        u = User(email=email, given_name="Connect", family_name="Test")
        self.db.add(u)
        self.db.flush()
        self.user_ids.append(str(u.id))
        return u

    def member(self, user: User, group=None, role="_student") -> CourseMember:
        cm = CourseMember(
            user_id=user.id,
            course_id=self.course.id,
            course_role_id=role,
            course_group_id=(group.id if group is not None else None),
        )
        self.db.add(cm)
        self.db.flush()
        return cm

    def profile(self, user: User, student_email: str) -> StudentProfile:
        sp = StudentProfile(
            user_id=user.id,
            organization_id=self.org.id,
            student_email=student_email,
        )
        self.db.add(sp)
        self.db.flush()
        return sp

    def content(self):
        """A submittable course content (needed for submission groups / results)."""
        kind = self.db.query(CourseContentKind).filter_by(submittable=True).first()
        assert kind is not None, "no submittable course_content_kind seeded"
        ctype = CourseContentType(
            slug=f"connect_{self.sfx}",
            course_content_kind_id=kind.id,
            course_id=self.course.id,
            title="Connect Type",
        )
        self.db.add(ctype)
        self.db.flush()
        content = CourseContent(
            title="A1",
            path=Ltree(f"a1_{self.sfx}"),
            course_id=self.course.id,
            course_content_type_id=ctype.id,
            course_content_kind_id=kind.id,
            position=1.0,
        )
        self.db.add(content)
        self.db.flush()
        return content

    def submission_group(self, content, member: CourseMember) -> SubmissionGroup:
        sg = SubmissionGroup(max_group_size=1, course_id=self.course.id, course_content_id=content.id)
        self.db.add(sg)
        self.db.flush()
        self.db.add(
            SubmissionGroupMember(
                course_id=self.course.id,
                submission_group_id=sg.id,
                course_member_id=member.id,
            )
        )
        self.db.flush()
        return sg

    def teardown(self):
        """Explicit bottom-up delete; RESTRICT FKs make cascades unreliable here."""
        db = self.db
        db.rollback()
        course_id = str(self.course.id)
        db.query(Result).filter(Result.course_member_id.in_(
            db.query(CourseMember.id).filter(CourseMember.course_id == course_id)
        )).delete(synchronize_session=False)
        db.query(SubmissionGroupMember).filter(
            SubmissionGroupMember.course_id == course_id
        ).delete(synchronize_session=False)
        db.query(SubmissionGroup).filter(
            SubmissionGroup.course_id == course_id
        ).delete(synchronize_session=False)
        db.query(CourseContent).filter(CourseContent.course_id == course_id).delete(
            synchronize_session=False
        )
        db.query(CourseContentType).filter(CourseContentType.course_id == course_id).delete(
            synchronize_session=False
        )
        db.query(CourseMember).filter(CourseMember.course_id == course_id).delete(
            synchronize_session=False
        )
        db.query(CourseGroup).filter(CourseGroup.course_id == course_id).delete(
            synchronize_session=False
        )
        db.query(Course).filter(Course.id == course_id).delete(synchronize_session=False)
        db.query(CourseFamily).filter(CourseFamily.id == str(self.family.id)).delete(
            synchronize_session=False
        )
        db.query(StudentProfile).filter(
            StudentProfile.organization_id == str(self.org.id)
        ).delete(synchronize_session=False)
        db.query(Organization).filter(Organization.id == str(self.org.id)).delete(
            synchronize_session=False
        )
        if self.user_ids:
            db.query(User).filter(User.id.in_(self.user_ids)).delete(synchronize_session=False)
        db.commit()


@pytest.fixture
def world(session):
    w = _Scaffold(session)
    try:
        yield w
    finally:
        w.teardown()


def test_connect_moves_membership_and_profile_and_deletes_source(world, session):
    """The plain case: imported user with membership + profile, keeper with nothing."""
    imported_email = f"imported_{world.sfx}@student.example"
    source = world.user(imported_email)
    target = world.user(f"real_{world.sfx}@example.org")
    sm = world.member(source, group=world.group)
    world.profile(source, imported_email)
    source_id, target_id, sm_id = str(source.id), str(target.id), str(sm.id)
    session.commit()

    result = connect_users(target_id, source_id, dry_run=False, db=session)

    assert result.source_deleted is True
    assert session.query(User).filter(User.id == source_id).first() is None
    moved = session.query(CourseMember).filter(CourseMember.id == sm_id).first()
    assert moved is not None and str(moved.user_id) == target_id
    profile = (
        session.query(StudentProfile)
        .filter(
            StudentProfile.user_id == target_id,
            StudentProfile.organization_id == str(world.org.id),
        )
        .first()
    )
    assert profile is not None
    assert profile.student_email == imported_email
    assert [m.action for m in result.course_memberships] == ["moved"]
    assert [p.action for p in result.student_profiles] == ["moved"]
    # Traceability breadcrumb on the keeper.
    keeper = session.query(User).filter(User.id == target_id).first()
    assert keeper.properties["connected_users"][0]["email"] == imported_email


def test_merged_profile_keeps_the_imported_email(world, session):
    """Keeper already has a profile in the org — the imported address must win.

    This is the trigger-ordering case: the imported email may only be written
    onto the keeper's profile after the source user row is gone.
    """
    imported_email = f"imported_{world.sfx}@student.example"
    keeper_email = f"real_{world.sfx}@example.org"
    source = world.user(imported_email)
    target = world.user(keeper_email)
    world.member(source, group=world.group)
    world.profile(source, imported_email)
    world.profile(target, keeper_email)
    source_id, target_id = str(source.id), str(target.id)
    session.commit()

    result = connect_users(target_id, source_id, dry_run=False, db=session)

    profiles = (
        session.query(StudentProfile)
        .filter(
            StudentProfile.user_id == target_id,
            StudentProfile.organization_id == str(world.org.id),
        )
        .all()
    )
    assert len(profiles) == 1
    assert profiles[0].student_email == imported_email
    assert [p.action for p in result.student_profiles] == ["merged"]


def test_duplicate_empty_membership_is_removed(world, session):
    """Both enrolled in the same course; the imported empty shell goes, debris and all."""
    source = world.user(f"imported_{world.sfx}@student.example")
    target = world.user(f"real_{world.sfx}@example.org")
    sm = world.member(source, group=world.group)
    tm = world.member(target, group=world.group)
    content = world.content()
    sg = world.submission_group(content, sm)
    source_id, target_id = str(source.id), str(target.id)
    sm_id, tm_id, sg_id = str(sm.id), str(tm.id), str(sg.id)
    session.commit()

    result = connect_users(target_id, source_id, dry_run=False, db=session)

    assert session.query(CourseMember).filter(CourseMember.id == sm_id).first() is None
    kept = session.query(CourseMember).filter(CourseMember.id == tm_id).first()
    assert kept is not None and str(kept.user_id) == target_id
    # The imported member's solo submission group is gone with it.
    assert session.query(SubmissionGroup).filter(SubmissionGroup.id == sg_id).first() is None
    assert [m.action for m in result.course_memberships] == ["duplicate_removed"]
    assert session.query(User).filter(User.id == source_id).first() is None


def test_duplicate_membership_with_results_refuses(world, session):
    """Real work on the imported side blocks the merge instead of deleting it."""
    source = world.user(f"imported_{world.sfx}@student.example")
    target = world.user(f"real_{world.sfx}@example.org")
    sm = world.member(source, group=world.group)
    world.member(target, group=world.group)
    content = world.content()
    session.add(
        Result(
            course_member_id=sm.id,
            course_content_id=content.id,
            course_content_type_id=content.course_content_type_id,
            version_identifier=f"v_{world.sfx}",
            status=0,
        )
    )
    session.commit()

    with pytest.raises(ConflictException):
        connect_users(str(target.id), str(source.id), dry_run=False, db=session)
    session.rollback()

    assert session.query(User).filter(User.id == str(source.id)).first() is not None


def test_source_with_a_login_is_refused(world, session):
    """A builtin account is proof of a real login — never absorb such a user."""
    source = world.user(f"imported_{world.sfx}@student.example")
    target = world.user(f"real_{world.sfx}@example.org")
    session.add(
        Account(
            provider="keycloak",
            type="oidc",
            provider_account_id=f"sub-{world.sfx}",
            user_id=source.id,
            builtin=True,
        )
    )
    session.commit()

    with pytest.raises(ConflictException):
        connect_users(str(target.id), str(source.id), dry_run=False, db=session)
    session.rollback()
    assert session.query(User).filter(User.id == str(source.id)).first() is not None


def test_dry_run_changes_nothing(world, session):
    imported_email = f"imported_{world.sfx}@student.example"
    source = world.user(imported_email)
    target = world.user(f"real_{world.sfx}@example.org")
    sm = world.member(source, group=world.group)
    world.profile(source, imported_email)
    session.commit()

    result = connect_users(str(target.id), str(source.id), dry_run=True, db=session)

    assert result.dry_run is True
    assert result.source_deleted is False
    assert [m.action for m in result.course_memberships] == ["moved"]
    assert session.query(User).filter(User.id == str(source.id)).first() is not None
    still = session.query(CourseMember).filter(CourseMember.id == str(sm.id)).first()
    assert still is not None and str(still.user_id) == str(source.id)


def test_self_connect_is_refused(world, session):
    target = world.user(f"real_{world.sfx}@example.org")
    session.commit()
    with pytest.raises(BadRequestException):
        connect_users(str(target.id), str(target.id), dry_run=True, db=session)
    session.rollback()


def test_non_user_manager_is_refused(world, session):
    """The endpoint gate: a plain user without _user_manager must get 403."""
    from computor_backend.api.user_connect import _require_user_manager
    from computor_backend.exceptions import ForbiddenException
    from computor_backend.permissions.principal import Principal

    plain = world.user(f"plain_{world.sfx}@example.org")
    session.commit()

    principal = Principal(user_id=str(plain.id), is_admin=False)
    with pytest.raises(ForbiddenException):
        _require_user_manager(principal, session)

    admin_principal = Principal(user_id=str(plain.id), is_admin=True)
    _require_user_manager(admin_principal, session)  # must not raise

"""Lecturer analytics against a real schema (synthetic rows only).

Checks what the pure-rule tests cannot: which rows the loaders pick up
(students only, this course only, group runs shared by the group), the
lecturer floor, and that feedback reaches the student history.

Rows live in a transaction that is rolled back after each test. Skips when
Postgres is unreachable; the object store is replaced by an in-memory dict.
"""

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.business_logic import course_analytics as ca
from computor_backend.exceptions import ForbiddenException
from computor_backend.model.artifact import SubmissionArtifact, SubmissionGrade
from computor_backend.model.auth import User
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentKind,
    CourseContentType,
    CourseFamily,
    CourseGroup,
    CourseMember,
    CourseRole,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.organization import Organization
from computor_backend.model.result import Result
from computor_backend.permissions.principal import Principal

T0 = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)


def _url() -> str:
    return (
        f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'postgres_secret')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'computor')}"
    )


@pytest.fixture
def db():
    try:
        engine = create_engine(_url())
        conn = engine.connect()
    except OperationalError as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Postgres unavailable: {exc}")
    trans = conn.begin()
    session = sessionmaker(bind=conn)()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()
        engine.dispose()


def _failing(test, message):
    return {
        "result": "FAILED",
        "tests": [{"name": "unit", "result": "FAILED", "tests": [
            {"name": test, "result": "FAILED", "resultMessage": message},
        ]}],
    }


@pytest.fixture
def world(db):
    suffix = uuid.uuid4().hex[:10]
    for role, title in [("_student", "Student"), ("_tutor", "Tutor"), ("_lecturer", "Lecturer")]:
        if db.get(CourseRole, role) is None:
            db.add(CourseRole(id=role, title=title, builtin=True))
    kind = CourseContentKind(
        id=f"analytics_{suffix}", title="Assignment",
        has_ascendants=False, has_descendants=False, submittable=True,
    )
    db.add(kind)
    db.flush()

    org = Organization(title="Analytics", organization_type="organization",
                       path=Ltree(f"analytics_{suffix}"), properties={})
    db.add(org)
    db.flush()
    family = CourseFamily(title="F", organization_id=org.id, path=Ltree(f"analytics_{suffix}.f"))
    db.add(family)
    db.flush()

    def course(slug):
        c = Course(title=slug, course_family_id=family.id, organization_id=org.id,
                   path=Ltree(f"analytics_{suffix}.f.{slug}"))
        db.add(c)
        db.flush()
        g = CourseGroup(title="G", course_id=c.id)
        db.add(g)
        ct = CourseContentType(slug=f"a-{slug}", course_id=c.id, course_content_kind_id=kind.id)
        db.add(ct)
        db.flush()
        return c, g, ct

    main, main_group, main_type = course("main")
    other, other_group, other_type = course("other")

    users = {}
    for name in ["lect", "tutor", "ada", "bob", "cyd", "eve"]:
        users[name] = User(given_name=name.title(), family_name="Synthetic",
                           email=f"{name}.{suffix}@test.local")
    db.add_all(users.values())
    db.flush()

    def member(user, c, role, group=None):
        m = CourseMember(user_id=user.id, course_id=c.id, course_role_id=role,
                         course_group_id=group.id if group else None)
        db.add(m)
        db.flush()
        return m

    m = {
        "lect": member(users["lect"], main, "_lecturer"),
        "tutor": member(users["tutor"], main, "_tutor"),
        "ada": member(users["ada"], main, "_student", main_group),
        "bob": member(users["bob"], main, "_student", main_group),
        "cyd": member(users["cyd"], main, "_student", main_group),
        "eve": member(users["eve"], other, "_student", other_group),
    }

    def content(c, ct, slug, title, pos):
        cc = CourseContent(course_id=c.id, course_content_type_id=ct.id, path=Ltree(slug),
                           position=pos, title=title, course_content_kind_id=kind.id,
                           max_group_size=2, is_submittable=True)
        db.add(cc)
        db.flush()
        return cc

    loops = content(main, main_type, "loops", "Loops", 1.0)
    lists = content(main, main_type, "lists", "Lists", 2.0)
    other_cc = content(other, other_type, "loops", "Other loops", 1.0)

    def group(c, cc, *members):
        sg = SubmissionGroup(max_group_size=2, course_id=c.id, course_content_id=cc.id)
        db.add(sg)
        db.flush()
        for mm in members:
            db.add(SubmissionGroupMember(course_id=c.id, submission_group_id=sg.id, course_member_id=mm.id))
        db.flush()
        return sg

    # Ada and Bob work as a team on Loops; Cyd alone; Eve in another course.
    team = group(main, loops, m["ada"], m["bob"])
    cyd_g = group(main, loops, m["cyd"])
    eve_g = group(other, other_cc, m["eve"])

    reports = {}

    def run(mm, sg, cc, ct, minutes, grade, report=None, artifact=None):
        r = Result(course_member_id=mm.id, submission_group_id=sg.id, course_content_id=cc.id,
                   course_content_type_id=ct.id, version_identifier=uuid.uuid4().hex,
                   status=0, grade=grade, result=grade,
                   created_at=T0 + timedelta(minutes=minutes),
                   submission_artifact_id=artifact.id if artifact else None)
        db.add(r)
        db.flush()
        if report is not None:
            reports[str(r.id)] = report
        return r

    def artifact(sg, mm, minutes, submit=True):
        a = SubmissionArtifact(submission_group_id=sg.id, uploaded_by_course_member_id=mm.id,
                               file_size=1, bucket_name="submissions",
                               object_key=f"{sg.id}/{uuid.uuid4().hex}", submit=submit,
                               created_at=T0 + timedelta(minutes=minutes))
        db.add(a)
        db.flush()
        return a

    run(m["ada"], team, loops, main_type, 0, 0.0, _failing("sum", "assert 1 == 2"))
    run(m["bob"], team, loops, main_type, 5, 0.2, _failing("sum", "assert 7 == 2"))
    sub_art = artifact(team, m["ada"], 9)
    run(m["ada"], team, loops, main_type, 10, 1.0, artifact=sub_art)
    run(m["cyd"], cyd_g, loops, main_type, 20, 0.5, _failing("sum", "assert 3 == 4"))
    run(m["cyd"], cyd_g, loops, main_type, 30, 0.5, _failing("mean", "ZeroDivisionError: division by zero"))
    # The lecturer's own trial run must not count as a student's error.
    run(m["lect"], cyd_g, loops, main_type, 40, 0.0, _failing("sum", "assert 0 == 1"))
    run(m["eve"], eve_g, other_cc, other_type, 0, 0.0, _failing("sum", "assert 1 == 2"))

    db.add(SubmissionGrade(artifact_id=sub_art.id, graded_by_course_member_id=m["tutor"].id,
                           grade=0.8, status=1, comment="Good, but name your variables.",
                           graded_at=T0 + timedelta(hours=2)))
    db.flush()

    async def fetch(result_id):
        return reports.get(result_id)

    return {"db": db, "users": users, "m": m, "main": main, "other": other,
            "loops": loops, "lists": lists, "fetch": fetch}


def _p(user=None, admin=False):
    return Principal(user_id=str(user.id) if user else None, is_admin=admin)


def test_typical_errors_count_students_of_this_course_only(world):
    out = asyncio.run(ca.get_typical_errors(
        str(world["main"].id), _p(world["users"]["lect"]), world["db"], fetch_report=world["fetch"]))
    top = out.errors[0]
    assert (top.test_name, top.message) == ("unit / sum", "assert <n> == <n>")
    # Ada, Bob and Cyd — not the lecturer's trial run, not Eve in the other course.
    assert top.affected_students == 3 and top.occurrences == 3
    assert {e.student_name for e in top.examples} == {"Ada Synthetic", "Bob Synthetic", "Cyd Synthetic"}
    assert out.results_scanned == 4 and out.results_without_report == 0
    assert not out.truncated


def test_typical_errors_can_be_limited_and_truncated(world):
    out = asyncio.run(ca.get_typical_errors(
        str(world["main"].id), _p(world["users"]["lect"]), world["db"],
        course_content_id=str(world["loops"].id), max_results=1, fetch_report=world["fetch"]))
    assert out.results_scanned == 1 and out.truncated
    assert [e.test_name for e in out.errors] == ["unit / mean"]


@pytest.mark.parametrize("who", ["tutor", "ada", "eve"])
def test_below_lecturer_is_refused(world, who):
    with pytest.raises(ForbiddenException):
        asyncio.run(ca.get_typical_errors(
            str(world["main"].id), _p(world["users"][who]), world["db"], fetch_report=world["fetch"]))
    with pytest.raises(ForbiddenException):
        asyncio.run(ca.get_course_flags(str(world["main"].id), _p(world["users"][who]), world["db"]))
    with pytest.raises(ForbiddenException):
        asyncio.run(ca.get_student_activity(str(world["m"]["ada"].id), _p(world["users"][who]), world["db"]))


def test_student_activity_merges_team_runs_submissions_and_feedback(world):
    out = asyncio.run(ca.get_student_activity(
        str(world["m"]["bob"].id), _p(world["users"]["lect"]), world["db"],
        due_at=T0 + timedelta(minutes=60), now=T0 + timedelta(hours=3)))
    kinds = [e.kind for e in out.events]
    assert kinds == ["grading", "test_run", "submission", "test_run", "test_run"]
    grading = out.events[0]
    assert grading.feedback == "Good, but name your variables."
    assert grading.graded_by == "Tutor Synthetic" and grading.status == "corrected"
    assert [e.is_submission for e in out.events if e.kind == "test_run"] == [True, False, False]

    (tl,) = out.timelines
    assert tl.course_content_title == "Loops"
    assert (tl.test_runs, tl.submissions) == (3, 1)
    assert tl.first_full_score_at == T0 + timedelta(minutes=10)
    assert tl.hours_before_due == pytest.approx(51 / 60, abs=0.01)
    assert tl.estimated_active_minutes == 10.0

    codes = sorted(f.code for f in out.flags)
    # Submitted 1 of 2 assignments (50%) — no low-progress flag; jump 20% -> 100%.
    assert codes == ["last_minute", "sudden_jump"]


def test_course_flags_list_only_flagged_students_with_reasons(world):
    out = asyncio.run(ca.get_course_flags(
        str(world["main"].id), _p(world["users"]["lect"]), world["db"],
        now=T0 + timedelta(days=30)))
    by_name = {s.student_name: sorted(f.code for f in s.flags) for s in out.students}
    assert by_name["Cyd Synthetic"] == ["inactive", "low_progress"]
    assert "Eve Synthetic" not in by_name
    assert all(f.reason for s in out.students for f in s.flags)
    assert {r.code for r in out.rules} >= {"inactive", "low_progress", "late_submission"}


@pytest.fixture
def left_learner(world):
    """Dan worked on Loops, submitted it and then left the course (issues#458).

    The membership stays with the role ``_inactive``; staff-facing reads must
    still show his work, and his submission must keep protecting the course.
    """
    db = world["db"]
    if db.get(CourseRole, "_inactive") is None:
        db.add(CourseRole(id="_inactive", title="Inactive", builtin=True))
        db.flush()
    main = world["main"]
    group_id = world["m"]["ada"].course_group_id
    dan = User(given_name="Dan", family_name="Synthetic", email=f"dan.{uuid.uuid4().hex[:10]}@test.local")
    db.add(dan)
    db.flush()
    member = CourseMember(user_id=dan.id, course_id=main.id, course_role_id="_inactive",
                          course_group_id=group_id)
    db.add(member)
    db.flush()
    sg = SubmissionGroup(max_group_size=2, course_id=main.id, course_content_id=world["loops"].id)
    db.add(sg)
    db.flush()
    db.add(SubmissionGroupMember(course_id=main.id, submission_group_id=sg.id, course_member_id=member.id))
    db.add(SubmissionArtifact(submission_group_id=sg.id, uploaded_by_course_member_id=member.id,
                              file_size=1, bucket_name="submissions",
                              object_key=f"{sg.id}/{uuid.uuid4().hex}", submit=True,
                              created_at=T0 + timedelta(minutes=50)))
    r = Result(course_member_id=member.id, submission_group_id=sg.id,
               course_content_id=world["loops"].id,
               course_content_type_id=world["loops"].course_content_type_id,
               version_identifier=uuid.uuid4().hex, status=0, grade=0.0, result=0.0,
               created_at=T0 + timedelta(minutes=45))
    db.add(r)
    db.flush()
    original_fetch = world["fetch"]

    async def fetch(result_id):
        if result_id == str(r.id):
            return _failing("sum", "assert 5 == 6")
        return await original_fetch(result_id)

    return {**world, "dan": member, "fetch": fetch}


def test_learner_who_left_stays_in_the_gradebook(left_learner):
    from computor_backend.repositories.course_member_gradings import CourseMemberGradingsRepository

    repo = CourseMemberGradingsRepository(left_learner["db"])
    course_id = str(left_learner["main"].id)
    dan_id = str(left_learner["dan"].id)
    members = {m["course_member_id"]: m for m in repo.get_all_course_members_with_students_role(course_id)}
    assert members[dan_id]["course_role_id"] == "_inactive"
    assert members[str(left_learner["m"]["ada"].id)]["course_role_id"] == "_student"
    assert str(left_learner["m"]["lect"].id) not in members

    stats = [r for r in repo.get_course_level_stats_for_all_members(course_id) if r["course_member_id"] == dan_id]
    assert stats and stats[0]["submitted_assignments"] == 1


def test_typical_errors_include_a_learner_who_left(left_learner):
    out = asyncio.run(ca.get_typical_errors(
        str(left_learner["main"].id), _p(left_learner["users"]["lect"]), left_learner["db"],
        fetch_report=left_learner["fetch"]))
    top = out.errors[0]
    assert top.test_name == "unit / sum"
    assert top.affected_students == 4
    assert "Dan Synthetic" in {e.student_name for e in top.examples}


def test_course_flags_skip_a_learner_who_left(left_learner):
    out = asyncio.run(ca.get_course_flags(
        str(left_learner["main"].id), _p(left_learner["users"]["lect"]), left_learner["db"],
        now=T0 + timedelta(days=30)))
    names = {s.student_name for s in out.students}
    assert "Cyd Synthetic" in names and "Dan Synthetic" not in names


def test_submission_of_a_learner_who_left_blocks_course_deletion(left_learner):
    from computor_backend.business_logic.cascade_deletion import (
        count_course_entities,
        course_delete_block_reason,
    )

    db = left_learner["db"]
    course_id = str(left_learner["main"].id)
    before = count_course_entities(db, course_id).student_submissions
    # Only Dan's submission is left once the active team's artifacts are gone,
    # so the count shows whether a learner who left is counted at all.
    db.query(SubmissionArtifact).filter(
        SubmissionArtifact.uploaded_by_course_member_id != left_learner["dan"].id,
        SubmissionArtifact.submission_group_id.in_(
            db.query(SubmissionGroup.id).filter(SubmissionGroup.course_id == course_id)
        ),
    ).delete(synchronize_session=False)
    db.flush()
    counts = count_course_entities(db, course_id)
    assert before == 2
    assert counts.student_submissions == 1
    assert course_delete_block_reason(counts, archived=False, is_admin=False) is not None

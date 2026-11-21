"""The course switch that enrols the AI tutor (Lena) as ``_tutor`` (issues#618).

The decisions are tested against a recording session: which membership is
added or removed, what is refused, and that asking for the current state
changes nothing. Permission filtering and the member-list delete guards are
the shared helpers the rest of the API uses, so they are stubbed here.
"""

from types import SimpleNamespace

import pytest

from computor_backend.business_logic import course_tutor_agent as logic
from computor_backend.exceptions import BadRequestException
from computor_backend.permissions.principal import Principal

pytestmark = pytest.mark.asyncio

COURSE = "11111111-1111-1111-1111-111111111111"
AGENT = "22222222-2222-2222-2222-222222222222"
LECTURER = "33333333-3333-3333-3333-333333333333"


class RecordingSession:
    def __init__(self):
        self.added = []
        self.deleted = []
        self.commits = 0

    def add(self, row):
        self.added.append(row)

    def delete(self, row):
        self.deleted.append(row)

    def commit(self):
        self.commits += 1


@pytest.fixture
def world(monkeypatch):
    state = SimpleNamespace(
        agent=SimpleNamespace(id=AGENT, given_name="Lena"),
        member=None,
        changes=[],
        post_created=[],
        guarded=[],
    )
    monkeypatch.setattr(
        logic, "_course_for_manager",
        lambda course_id, principal, db: SimpleNamespace(id=course_id),
    )
    monkeypatch.setattr(logic, "tutor_agent_user", lambda db: state.agent)
    monkeypatch.setattr(logic, "_membership", lambda user_id, course_id, db: state.member)
    monkeypatch.setattr(
        logic, "_after_change",
        lambda user_id, course_id: state.changes.append((user_id, course_id)),
    )

    async def post_create(member, db):
        state.post_created.append(member)

    monkeypatch.setattr(logic, "_run_post_create", post_create)
    monkeypatch.setattr(logic, "_guard_removal", lambda member, db: state.guarded.append(member))
    return state


def lecturer():
    return Principal(user_id=LECTURER)


def member(role):
    return SimpleNamespace(id="m-1", user_id=AGENT, course_id=COURSE, course_role_id=role)


async def test_enrolling_adds_the_agent_as_tutor(world):
    db = RecordingSession()

    status = await logic.set_course_tutor_agent(COURSE, True, lecturer(), db)

    assert [(m.user_id, m.course_id, m.course_role_id) for m in db.added] == [
        (AGENT, COURSE, "_tutor")
    ]
    assert db.added[0].created_by == LECTURER
    assert db.commits == 1
    assert world.changes == [(AGENT, COURSE)]
    assert world.post_created == db.added
    assert status.available and status.enrolled
    assert status.course_role_id == "_tutor"
    assert status.name == "Lena"


async def test_enrolling_twice_changes_nothing(world):
    world.member = member("_tutor")
    db = RecordingSession()

    status = await logic.set_course_tutor_agent(COURSE, True, lecturer(), db)

    assert db.added == [] and db.commits == 0 and world.changes == []
    assert status.enrolled


async def test_a_higher_role_from_the_member_list_counts_as_enrolled(world):
    world.member = member("_lecturer")
    db = RecordingSession()

    status = await logic.set_course_tutor_agent(COURSE, True, lecturer(), db)

    assert db.added == [] and db.commits == 0
    assert status.enrolled and status.course_role_id == "_lecturer"


async def test_a_student_membership_is_not_promoted_silently(world):
    world.member = member("_student")
    db = RecordingSession()

    with pytest.raises(BadRequestException, match="_student"):
        await logic.set_course_tutor_agent(COURSE, True, lecturer(), db)

    assert db.added == [] and db.commits == 0


async def test_removing_deletes_the_tutor_membership_behind_the_list_guards(world):
    world.member = member("_tutor")
    db = RecordingSession()

    status = await logic.set_course_tutor_agent(COURSE, False, lecturer(), db)

    assert world.guarded == [world.member]
    assert db.deleted == [world.member]
    assert db.commits == 1
    assert world.changes == [(AGENT, COURSE)]
    assert status.available and not status.enrolled
    assert status.course_role_id is None


async def test_removing_a_role_given_by_hand_is_refused(world):
    world.member = member("_lecturer")
    db = RecordingSession()

    with pytest.raises(BadRequestException, match="member list"):
        await logic.set_course_tutor_agent(COURSE, False, lecturer(), db)

    assert db.deleted == [] and db.commits == 0


async def test_removing_when_not_enrolled_changes_nothing(world):
    db = RecordingSession()

    status = await logic.set_course_tutor_agent(COURSE, False, lecturer(), db)

    assert db.deleted == [] and db.commits == 0 and world.changes == []
    assert not status.enrolled


async def test_a_deployment_without_a_tutor_agent_refuses_the_switch(world):
    world.agent = None
    db = RecordingSession()

    with pytest.raises(BadRequestException, match="TUTOR_AGENT_USER_ID"):
        await logic.set_course_tutor_agent(COURSE, True, lecturer(), db)

    assert db.added == [] and db.commits == 0


def test_status_reports_an_unavailable_agent(world):
    world.agent = None

    status = logic.get_course_tutor_agent(COURSE, lecturer(), RecordingSession())

    assert not status.available and not status.enrolled and status.name is None


def test_status_reports_the_current_membership(world):
    world.member = member("_tutor")

    status = logic.get_course_tutor_agent(COURSE, lecturer(), RecordingSession())

    assert status.available and status.enrolled and status.name == "Lena"


def test_the_switch_is_routed_under_the_course():
    from computor_backend.api.courses import course_router

    routes = {
        (route.path, method)
        for route in course_router.router.routes
        for method in getattr(route, "methods", ())
    }
    assert ("/{course_id}/tutor-agent", "GET") in routes
    assert ("/{course_id}/tutor-agent", "PUT") in routes

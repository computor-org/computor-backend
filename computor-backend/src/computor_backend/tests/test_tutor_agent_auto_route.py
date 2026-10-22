"""Courses with ``tutor_agent_auto_route`` address unmentioned student messages to Lena."""
from types import SimpleNamespace

import pytest

from computor_backend.business_logic.messages import auto_route, core
from computor_backend.permissions.principal import Principal
from computor_types.messages import MessageCreate


TUTOR = "12345678-1234-1234-1234-123456789abc"
STUDENT = "12345678-1234-1234-1234-123456789def"
OWNER = "12345678-1234-1234-1234-123456789aaa"
COURSE = "11111111-1111-1111-1111-111111111111"
GROUP = "22222222-2222-2222-2222-222222222222"
LENA = f"@[Lena]({TUTOR})"


@pytest.fixture
def course(monkeypatch):
    """One course with the flag on, a student, an owner and the tutor agent
    in the audience. Tests flip individual facts to exercise each gate."""
    state = SimpleNamespace(
        enabled=True,
        roles={STUDENT: "_student", OWNER: "_owner", TUTOR: "_tutor"},
        audience={STUDENT, OWNER, TUTOR},
        agent=SimpleNamespace(id=TUTOR, given_name="Luna", family_name="Tutor"),
    )
    monkeypatch.setattr(auto_route.settings, "TUTOR_AGENT_USER_ID", TUTOR)
    monkeypatch.setattr(auto_route, "_course_id_for_targets", lambda dump, db: COURSE)
    monkeypatch.setattr(auto_route, "_auto_route_enabled", lambda cid, db: state.enabled)
    monkeypatch.setattr(auto_route, "_course_role", lambda cid, uid, db: state.roles.get(str(uid)))
    monkeypatch.setattr(auto_route, "message_audience_user_ids", lambda m, db: state.audience)
    monkeypatch.setattr(auto_route, "_active_user", lambda uid, db: state.agent)
    return state


def route(content, author=STUDENT, parent=None):
    dump = {"content": content, "submission_group_id": GROUP}
    return auto_route.route_to_tutor_agent(None, dump, author, parent, db=None)


def test_unmentioned_student_message_gets_visible_lena_mention(course):
    assert route("Why does my loop never end?") == f"{LENA} Why does my loop never end?"


def test_disabled_course_is_unchanged(course):
    course.enabled = False
    assert route("help") == "help"


@pytest.mark.parametrize("content", [
    f"@[Max Owner]({OWNER}) can you check this?",
    f"{LENA} already asked",
])
def test_any_existing_mention_is_left_alone(course, content):
    assert route(content) == content


@pytest.mark.parametrize("author", [OWNER, TUTOR])
def test_only_student_authors_are_routed(course, author):
    assert route("note", author=author) == "note"


def test_replies_to_the_agent_are_its_follow_ups_already(course):
    assert route("thanks, and why?", parent=SimpleNamespace(author_id=TUTOR)) == "thanks, and why?"


def test_replies_in_a_human_thread_are_routed(course):
    assert route("still stuck", parent=SimpleNamespace(author_id=OWNER)) == f"{LENA} still stuck"


def test_agent_outside_the_audience_is_not_mentioned(course):
    course.audience = {STUDENT, OWNER}
    assert route("help") == "help"


@pytest.mark.parametrize("missing", ["setting", "agent"])
def test_unconfigured_or_inactive_agent_is_not_mentioned(course, monkeypatch, missing):
    if missing == "setting":
        monkeypatch.setattr(auto_route.settings, "TUTOR_AGENT_USER_ID", None)
    else:
        course.agent = None
    assert route("help") == "help"


def test_blank_content_is_unchanged(course):
    assert route("   ") == "   "


def test_messages_outside_a_course_are_unchanged(course, monkeypatch):
    monkeypatch.setattr(auto_route, "_course_id_for_targets", lambda dump, db: None)
    assert route("hello") == "hello"


def test_create_message_routes_before_validating_mentions(course, monkeypatch):
    validated = []
    monkeypatch.setattr(core, "_check_submission_group_write_permission", lambda *args: None)
    monkeypatch.setattr(core, "resolve_message_mentions", lambda m, content, db: content)
    monkeypatch.setattr(core, "validate_message_mentions", lambda m, content, db: validated.append(content))
    created = core.create_message_with_author(
        MessageCreate(content="my test fails", submission_group_id=GROUP),
        Principal(user_id=STUDENT),
        db=None,
    )
    assert created["content"] == f"{LENA} my test fails"
    assert validated == [f"{LENA} my test fails"]

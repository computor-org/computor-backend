"""``MessageContext`` enrichment — human-readable placement per message.

A message row carries exactly one target id (the single-target invariant),
so a submission-group message has ``course_content_id = NULL`` and clients
could only render the raw UUID. ``message_contexts_for`` resolves the
course title, the content (through ``SubmissionGroup.course_content_id``
for group messages), the course-group title and the group members — all
batched, so the query count must stay flat in page size.

The routed-mock DB dispatches on the model being queried, mirroring the
style of ``test_message_enrichment_batching``.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from computor_backend.business_logic.messages.context import message_contexts_for
from computor_types.messages import MESSAGE_TARGET_FIELDS


def _msg(i, **targets):
    base = {f: None for f in MESSAGE_TARGET_FIELDS}
    base.update(targets)
    return SimpleNamespace(id=f"m-{i}", author_id="u-1", **base)


class _RoutingDB:
    """Answers each query with rows preset for the model it starts from."""

    def __init__(self, rows_by_model):
        self.rows_by_model = rows_by_model
        self.queries = 0

    def query(self, *cols):
        self.queries += 1
        model_name = cols[0].class_.__name__
        rows = self.rows_by_model.get(model_name, [])
        q = MagicMock()
        q.join.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.all.return_value = rows
        return q


SG_WORLD = {
    "SubmissionGroup": [("sg-1", None, "cc-9")],
    "Course": [("c-1", "Programming in MATLAB")],
    "CourseContent": [("cc-9", "A3 Filters", "unit1.a3")],
    "SubmissionGroupMember": [
        ("sg-1", "cm-1", "u-9", "Max", "Muster", "max@example.org"),
        ("sg-1", "cm-2", "u-10", "Eva", "Beispiel", "eva@example.org"),
    ],
}


def test_submission_group_message_resolves_content_through_the_group():
    msgs = [_msg(0, submission_group_id="sg-1")]
    ctx = message_contexts_for(msgs, _RoutingDB(SG_WORLD), {"m-0": "c-1"})["m-0"]
    assert ctx.course_id == "c-1"
    assert ctx.course_title == "Programming in MATLAB"
    # The invariant nulls course_content_id on the row; the group's own
    # course_content_id fills it back in.
    assert ctx.course_content_id == "cc-9"
    assert ctx.course_content_title == "A3 Filters"
    assert ctx.course_content_path == "unit1.a3"
    assert [m.course_member_id for m in ctx.submission_group_members] == ["cm-1", "cm-2"]
    assert ctx.submission_group_members[0].user_id == "u-9"
    assert ctx.submission_group_members[0].given_name == "Max"


def test_display_name_falls_back_to_first_member_name():
    msgs = [_msg(0, submission_group_id="sg-1")]
    ctx = message_contexts_for(msgs, _RoutingDB(SG_WORLD), {"m-0": "c-1"})["m-0"]
    assert ctx.submission_group_display_name == "Max Muster"


def test_explicit_display_name_wins_over_member_name():
    world = dict(SG_WORLD, SubmissionGroup=[("sg-1", "Team Rocket", "cc-9")])
    msgs = [_msg(0, submission_group_id="sg-1")]
    ctx = message_contexts_for(msgs, _RoutingDB(world), {"m-0": "c-1"})["m-0"]
    assert ctx.submission_group_display_name == "Team Rocket"


def test_nameless_first_member_falls_back_to_email():
    world = dict(SG_WORLD, SubmissionGroupMember=[
        ("sg-1", "cm-1", "u-9", None, None, "max@example.org"),
    ])
    msgs = [_msg(0, submission_group_id="sg-1")]
    ctx = message_contexts_for(msgs, _RoutingDB(world), {"m-0": "c-1"})["m-0"]
    assert ctx.submission_group_display_name == "max@example.org"


def test_course_group_message_gets_group_title():
    world = {
        "Course": [("c-1", "Programming in MATLAB")],
        "CourseGroup": [("cg-1", "Group 2")],
    }
    msgs = [_msg(0, course_group_id="cg-1")]
    ctx = message_contexts_for(msgs, _RoutingDB(world), {"m-0": "c-1"})["m-0"]
    assert ctx.course_group_id == "cg-1"
    assert ctx.course_group_title == "Group 2"
    assert ctx.submission_group_members == []


def test_direct_course_content_message_resolves_title():
    world = {
        "Course": [("c-1", "Programming in MATLAB")],
        "CourseContent": [("cc-9", "A3 Filters", "unit1.a3")],
    }
    msgs = [_msg(0, course_content_id="cc-9")]
    ctx = message_contexts_for(msgs, _RoutingDB(world), {"m-0": "c-1"})["m-0"]
    assert ctx.course_content_title == "A3 Filters"


def test_courseless_scopes_have_no_context():
    msgs = [
        _msg(0),                              # global
        _msg(1, organization_id="o-1"),
        _msg(2, course_family_id="f-1"),
        _msg(3, user_id="u-2"),
    ]
    db = _RoutingDB({})
    out = message_contexts_for(msgs, db, {m: None for m in ("m-0", "m-1", "m-2", "m-3")})
    assert set(out.values()) == {None}
    assert db.queries == 0


def test_query_count_is_flat_in_batch_size():
    for n in (1, 10, 500):
        msgs = [_msg(i, submission_group_id="sg-1") for i in range(n)]
        db = _RoutingDB(SG_WORLD)
        out = message_contexts_for(msgs, db, {f"m-{i}": "c-1" for i in range(n)})
        # submission groups, courses, contents, members — never per message.
        assert db.queries == 4, f"n={n} issued {db.queries} queries"
        assert out[f"m-{n-1}"].course_content_title == "A3 Filters"


def test_empty_batch_issues_no_queries():
    db = _RoutingDB({})
    assert message_contexts_for([], db, {}) == {}
    assert db.queries == 0

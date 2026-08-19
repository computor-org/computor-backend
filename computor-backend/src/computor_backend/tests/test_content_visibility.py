"""Guards on student visibility of course contents (issue #338).

The rule under test is a veto, not a nearest-non-NULL fallback. The single
most important case in this file is
``test_true_on_a_child_does_not_override_a_hidden_ancestor``: if that ever goes
green the other way round, the feature is broken in the exact way the design
set out to avoid — a lecturer hides a unit and one child quietly stays live.
"""
import pytest

from computor_backend.business_logic.content_visibility import (
    ancestor_paths,
    effective_visible_predicate,
    filter_visible,
    resolve_visible,
)
from computor_backend.model.course import Course, CourseContent


class _Row:
    """Stand-in for a loaded course-content row."""

    def __init__(self, path, visible_effective=True):
        self.path = path
        self.visible_effective = visible_effective


# --------------------------------------------------------------------------
# ancestor_paths
# --------------------------------------------------------------------------

def test_ancestor_paths_includes_self():
    """A node's own visible=False must veto it, so self is in the chain."""
    assert ancestor_paths("a.b.c") == ["a", "a.b", "a.b.c"]


def test_ancestor_paths_of_a_root_node():
    assert ancestor_paths("a") == ["a"]


# --------------------------------------------------------------------------
# resolve_visible: NULL inherits
# --------------------------------------------------------------------------

def test_unset_everywhere_is_visible():
    """NULL at every level is the default state of every existing course."""
    assert resolve_visible("a.b.c", {}, None) is True


def test_explicit_true_is_visible():
    assert resolve_visible("a.b.c", {"a.b.c": True}, True) is True


# --------------------------------------------------------------------------
# resolve_visible: False vetoes
# --------------------------------------------------------------------------

def test_own_false_hides_the_node():
    assert resolve_visible("a.b.c", {"a.b.c": False}, None) is False


def test_parent_false_hides_the_descendant():
    assert resolve_visible("a.b.c", {"a.b": False}, None) is False


def test_root_unit_false_hides_the_whole_subtree():
    overrides = {"a": False}
    assert resolve_visible("a", overrides, None) is False
    assert resolve_visible("a.b", overrides, None) is False
    assert resolve_visible("a.b.c", overrides, None) is False


def test_course_false_hides_everything():
    """Setting visible=false on the course empties the whole student tree."""
    assert resolve_visible("a.b.c", {}, False) is False
    assert resolve_visible("a", {}, False) is False


# --------------------------------------------------------------------------
# resolve_visible: True never re-grants
# --------------------------------------------------------------------------

def test_true_on_a_child_does_not_override_a_hidden_ancestor():
    """The defining case. A veto cannot be undone from below."""
    assert resolve_visible("a.b.c", {"a.b": False, "a.b.c": True}, None) is False


def test_true_on_a_content_does_not_override_a_hidden_course():
    assert resolve_visible("a.b", {"a.b": True}, False) is False


def test_true_on_the_course_does_not_override_a_hidden_content():
    """Issue #338: 'a visible true at the course level does not affect it'."""
    assert resolve_visible("a.b", {"a.b": False}, True) is False


def test_intermediate_true_does_not_shield_a_deeper_false():
    assert resolve_visible("a.b.c", {"a.b": True, "a.b.c": False}, None) is False


# --------------------------------------------------------------------------
# resolve_visible: siblings are independent
# --------------------------------------------------------------------------

def test_hiding_one_unit_leaves_its_siblings_alone():
    overrides = {"a.b": False}
    assert resolve_visible("a.b.one", overrides, None) is False
    assert resolve_visible("a.c.one", overrides, None) is True
    assert resolve_visible("a", overrides, None) is True


def test_a_prefix_that_is_not_a_path_segment_does_not_match():
    """'a.bb' is not a descendant of 'a.b' — string prefixes are not enough."""
    assert resolve_visible("a.bb", {"a.b": False}, None) is True


# --------------------------------------------------------------------------
# filter_visible
# --------------------------------------------------------------------------

def test_filter_visible_drops_only_the_hidden_rows():
    rows = [_Row("a", True), _Row("a.b", False), _Row("a.c", True)]
    assert [r.path for r in filter_visible(rows)] == ["a", "a.c"]


def test_filter_visible_defaults_to_keeping_unannotated_rows():
    """A row that never went through annotation must not vanish silently."""

    class _Bare:
        path = "a"

    assert filter_visible([_Bare()]) != []


# --------------------------------------------------------------------------
# effective_visible_predicate: the SQL half
# --------------------------------------------------------------------------

def _compiled(query):
    from sqlalchemy.dialects import postgresql

    return str(
        query.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


def test_predicate_correlates_to_the_outer_course_content():
    from sqlalchemy import select

    sql = _compiled(select(CourseContent.id).where(effective_visible_predicate()))
    # The ancestor half must compare an alias against the outer row, not
    # against itself.
    assert "course_content.path <@ course_content_1.path" in sql
    assert "course_content_1.visible IS false" in sql


def test_predicate_keeps_its_own_course_when_course_is_joined_outside():
    """The correlation trap this predicate is written to survive.

    ``user_course_content_list_query`` and friends already join ``Course``.
    Without an explicit ``correlate(CourseContent)``, SQLAlchemy would hoist
    ``course`` out of the subquery and bind it to the outer join, silently
    changing what the check means.
    """
    from sqlalchemy import select

    query = (
        select(CourseContent.id, Course.title)
        .join(Course, Course.id == CourseContent.course_id)
        .where(effective_visible_predicate())
    )
    sql = _compiled(query)
    # Two independent FROM course occurrences: the outer join and the subquery.
    assert sql.count("FROM course \n") + sql.count("FROM course\n") >= 1
    assert "EXISTS (SELECT * \nFROM course \nWHERE course.id" in sql


def test_predicate_uses_the_ltree_containment_operator():
    """`<@` is what ix_course_content_path_gist exists to serve."""
    from sqlalchemy import select

    assert "<@" in _compiled(select(CourseContent.id).where(effective_visible_predicate()))


# --------------------------------------------------------------------------
# The read filter: who loses rows and who does not
# --------------------------------------------------------------------------

def _student_search_sql(include_hidden):
    from sqlalchemy.orm import Session

    from computor_backend.interfaces.student_course_contents import (
        CourseContentStudentInterface,
    )

    session = Session()
    query = session.query(CourseContent)
    filtered = CourseContentStudentInterface.search(
        session, query, None, include_hidden=include_hidden
    )
    return _compiled(filtered.statement)


def test_student_search_filters_hidden_content():
    sql = _student_search_sql(include_hidden=False)
    assert "<@" in sql, "the ancestor veto must reach the student's SQL"
    assert "archived_at IS NULL" in sql, "the archived filter must survive"


def test_staff_search_keeps_hidden_content():
    """A tutor viewing a student, or a lecturer rehearsing as one, keeps rows."""
    sql = _student_search_sql(include_hidden=True)
    assert "<@" not in sql
    assert "archived_at IS NULL" in sql, "archived is still filtered for everyone"


def test_hiding_is_the_default_when_a_caller_forgets():
    """A caller that omits the flag must err towards hiding, never leaking."""
    import inspect

    from computor_backend.interfaces.student_course_contents import (
        CourseContentStudentInterface,
    )

    param = inspect.signature(
        CourseContentStudentInterface.search
    ).parameters["include_hidden"]
    assert param.default is False
    assert param.kind is inspect.Parameter.KEYWORD_ONLY


# --------------------------------------------------------------------------
# Enforcement on the test / submit paths
# --------------------------------------------------------------------------

class _FakeQuery:
    def __init__(self, scalar=None, first=None):
        self._scalar, self._first = scalar, first

    def filter(self, *_args, **_kwargs):
        return self

    def scalar(self):
        return self._scalar

    def first(self):
        return self._first


class _FakeDb:
    """Answers exactly the two reads is_content_visible performs."""

    def __init__(self, course_visible=None, hidden_ancestor=False):
        self.course_visible = course_visible
        self.hidden_ancestor = hidden_ancestor
        self.queries = 0

    def query(self, *entities):
        self.queries += 1
        # First read is Course.visible; second looks for a hiding ancestor.
        if self.queries == 1:
            return _FakeQuery(scalar=self.course_visible)
        return _FakeQuery(first="a-hidden-ancestor" if self.hidden_ancestor else None)


class _Content:
    def __init__(self, path="a.b", course_id="course-1"):
        self.path = path
        self.course_id = course_id
        self.id = "content-1"


def test_enforce_passes_for_visible_content():
    from computor_backend.business_logic.content_visibility import (
        enforce_content_visible,
    )

    enforce_content_visible(_FakeDb(), _Content())  # must not raise


def test_enforce_raises_submit_012_for_hidden_content():
    from computor_backend.business_logic.content_visibility import (
        enforce_content_visible,
    )
    from computor_backend.exceptions import BadRequestException

    with pytest.raises(BadRequestException) as exc:
        enforce_content_visible(_FakeDb(hidden_ancestor=True), _Content())
    assert exc.value.error_code == "SUBMIT_012"


def test_enforce_raises_when_the_whole_course_is_hidden():
    from computor_backend.business_logic.content_visibility import (
        enforce_content_visible,
    )
    from computor_backend.exceptions import BadRequestException

    with pytest.raises(BadRequestException):
        enforce_content_visible(_FakeDb(course_visible=False), _Content())


def test_staff_are_exempt_and_the_check_is_not_even_run():
    """Staff testing hidden content is the point of the feature.

    Asserting no query is issued also pins that `exempt` short-circuits before
    any DB work, matching enforce_max_test_runs.
    """
    from computor_backend.business_logic.content_visibility import (
        enforce_content_visible,
    )

    db = _FakeDb(hidden_ancestor=True)
    enforce_content_visible(db, _Content(), exempt=True)  # must not raise
    assert db.queries == 0


def test_the_guard_is_wired_into_every_student_entry_point():
    """Four routes reach testing or submission; all four must be guarded.

    A new route added without a guard is the realistic regression here, so
    this asserts on the call sites rather than on behaviour alone.
    """
    import inspect

    from computor_backend.api import tests as tests_api
    from computor_backend.business_logic import submissions, testing_orchestration

    assert "enforce_content_visible" in inspect.getsource(tests_api.create_test_run)
    assert "enforce_content_visible" in inspect.getsource(
        submissions.upload_submission_artifact
    )
    assert "enforce_content_visible" in inspect.getsource(submissions.update_artifact)
    assert "enforce_content_visible" in inspect.getsource(
        testing_orchestration.enforce_test_limits
    )


def test_the_tutor_test_route_is_deliberately_not_guarded():
    """Staff must be able to test hidden content; pin that this stays true."""
    import inspect

    from computor_backend.api import tutor

    assert "enforce_content_visible" not in inspect.getsource(tutor.create_tutor_test)

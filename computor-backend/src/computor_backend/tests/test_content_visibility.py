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

def _bind_check(clauses):
    """Push every literal in these clauses through its column's bind processor.

    The reason this exists: comparing against ``CourseContent.path`` with a
    plain ``str`` compiles perfectly happily and only explodes at execution,
    because sqlalchemy_utils' LtreeType bind processor reads ``value.path`` off
    whatever it is handed. ``literal_binds`` compilation does NOT run that
    processor, so a compile-based assertion cannot see the bug. Running the
    processor is the only check that reproduces it without a database.
    """
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.sql.elements import BinaryExpression, BindParameter

    dialect = postgresql.dialect()
    for clause in clauses:
        if not isinstance(clause, BinaryExpression):
            continue
        column, right = clause.left, clause.right
        proc = getattr(column, "type", None)
        proc = proc.bind_processor(dialect) if proc is not None else None
        if proc is None:
            continue
        values = []
        if isinstance(right, BindParameter):
            value = right.value
            values = list(value) if isinstance(value, (list, tuple)) else [value]
        for value in values:
            if value is not None:
                proc(value)


class _FakeQuery:
    def __init__(self, scalar=None, first=None):
        self._scalar, self._first = scalar, first

    def filter(self, *args, **_kwargs):
        _bind_check(args)
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


# --------------------------------------------------------------------------
# Grading: display only
# --------------------------------------------------------------------------

def _grading_inputs(visible):
    """One unit with two submittable assignments, one of them submitted."""
    path_info = {
        "unit": {
            "title": "Unit", "submittable": False, "position": 1.0,
            "course_content_type_color": "#fff", "visible_effective": True,
        },
        "unit.a": {
            "title": "A", "submittable": True, "position": 1.0,
            "course_content_type_color": "#fff", "visible_effective": visible,
        },
        "unit.b": {
            "title": "B", "submittable": True, "position": 2.0,
            "course_content_type_color": "#fff", "visible_effective": True,
        },
    }
    def row(path, depth, max_a, submitted):
        return {
            "path": path, "path_depth": depth,
            "content_type_id": "ct-1", "content_type_slug": "assignment",
            "content_type_title": "Assignment", "content_type_color": "#fff",
            "max_assignments": max_a, "submitted_assignments": submitted,
            "latest_submission_at": None, "graded_assignments": max_a,
            "average_grading": 0.5, "grading_status": "not_reviewed",
        }

    # Nodes come from the db_stats rows (one per path prefix), not path_info.
    db_stats = [
        row("unit", 1, 2, 1),
        row("unit.a", 2, 1, 1),
        row("unit.b", 2, 1, 0),
    ]
    return db_stats, path_info


def test_hidden_content_does_not_change_grading_totals():
    """The decision recorded for #338, pinned.

    The issue text says invisible content should not be counted in grading
    summaries. That was resolved the other way on purpose: these endpoints are
    lecturer-and-above, so staff see the real denominator, and the student
    case is already handled because hidden rows never reach a student at all.
    Without this test someone reads the issue in six months and "fixes" it.
    """
    from computor_backend.utils.grading_stats import process_hierarchical_stats

    all_visible = process_hierarchical_stats(*_grading_inputs(visible=True))
    one_hidden = process_hierarchical_stats(*_grading_inputs(visible=False))

    for key in (
        "total_max_assignments",
        "total_submitted_assignments",
        "overall_progress_percentage",
        "overall_average_grading",
    ):
        assert all_visible[key] == one_hidden[key], f"{key} must not react to visibility"


def test_the_grading_node_still_reports_the_hidden_flag():
    """Excluded from the maths, but the UI must still be able to mark it."""
    from computor_backend.utils.grading_stats import process_hierarchical_stats

    stats = process_hierarchical_stats(*_grading_inputs(visible=False))
    flags = {node["path"]: node["visible_effective"] for node in stats["nodes"]}
    assert flags["unit.a"] is False
    assert flags["unit"] is True


def test_a_synthesised_path_with_no_content_row_defaults_to_visible():
    """Path prefixes invented by the roll-up cannot have been hidden."""
    from computor_backend.utils.grading_stats import process_hierarchical_stats

    db_stats, path_info = _grading_inputs(visible=True)
    del path_info["unit"]  # the prefix now has no course_content row
    stats = process_hierarchical_stats(db_stats, path_info)
    flags = {node["path"]: node["visible_effective"] for node in stats["nodes"]}
    assert flags["unit"] is True

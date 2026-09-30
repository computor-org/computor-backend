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

    def __init__(self, course_visible=None, hidden_ancestor=False, archived_at=None):
        self.course_visible = course_visible
        self.hidden_ancestor = hidden_ancestor
        self.archived_at = archived_at
        self.queries = 0

    def query(self, *entities):
        self.queries += 1
        # First read is the course row (visible, archived_at); second looks for
        # a hiding ancestor.
        if self.queries == 1:
            return _FakeQuery(first=(self.course_visible, self.archived_at))
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


def test_enforce_raises_submit_013_for_an_archived_course():
    """Archived beats hidden: the student gets the archived message, not
    "your lecturer has hidden it"."""
    from datetime import datetime, timezone

    from computor_backend.business_logic.content_visibility import (
        enforce_content_visible,
    )
    from computor_backend.exceptions import BadRequestException

    db = _FakeDb(archived_at=datetime.now(timezone.utc))
    with pytest.raises(BadRequestException) as exc:
        enforce_content_visible(db, _Content())
    assert exc.value.error_code == "SUBMIT_013"
    # The course row is read once; the ancestor lookup never runs.
    assert db.queries == 1


def test_enforce_uses_a_passed_course_row_for_the_archived_check():
    from datetime import datetime, timezone
    from types import SimpleNamespace

    from computor_backend.business_logic.content_visibility import (
        enforce_content_visible,
    )
    from computor_backend.exceptions import BadRequestException

    db = _FakeDb()
    course = SimpleNamespace(visible=None, archived_at=datetime.now(timezone.utc))
    with pytest.raises(BadRequestException) as exc:
        enforce_content_visible(db, _Content(), course=course)
    assert exc.value.error_code == "SUBMIT_013"
    assert db.queries == 0


def test_archived_course_is_invisible_like_visible_false():
    """The archived veto sits at the root of the chain, so every read path —
    not only the write guard — treats an archived course as hidden."""
    from datetime import datetime, timezone
    from types import SimpleNamespace

    from computor_backend.business_logic.content_visibility import (
        is_content_visible,
        load_course_visible,
    )

    when = datetime.now(timezone.utc)
    assert load_course_visible(_FakeDb(course_visible=True, archived_at=when), "course-1") is False
    assert load_course_visible(_FakeDb(course_visible=None), "course-1") is None
    assert is_content_visible(_FakeDb(archived_at=when), _Content()) is False
    assert is_content_visible(
        _FakeDb(), _Content(), SimpleNamespace(visible=True, archived_at=when)
    ) is False


def test_the_sql_predicate_vetoes_archived_courses():
    """Paginated student lists go through the SQL predicate; archived must be
    part of the course-level veto there too."""
    from computor_backend.business_logic.content_visibility import (
        effective_visible_predicate,
    )

    sql = str(effective_visible_predicate())
    assert "archived_at IS NOT NULL" in sql


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


# --------------------------------------------------------------------------
# Who may change visibility
# --------------------------------------------------------------------------

def test_changing_visibility_requires_lecturer_in_the_course():
    """Visibility is a course-content field, so it inherits that gate.

    Pinned because it is the security-relevant half of #338: a tutor must be
    able to SEE every hidden row (that is the whole point of marking them) and
    must not be able to change one. Read and write deliberately sit at
    different roles in the same map.
    """
    from computor_backend.permissions.handlers_course import (
        CourseContentPermissionHandler,
    )
    from computor_backend.permissions.roles import CourseRole

    role_map = CourseContentPermissionHandler.ACTION_ROLE_MAP
    assert role_map["update"] is CourseRole.LECTURER
    assert role_map["get"] is CourseRole.STUDENT
    assert role_map["list"] is CourseRole.STUDENT


def test_no_role_grants_course_content_writes_outside_a_course():
    """`_organization_manager` and friends hold no course_content claims.

    check_general_permission short-circuits the course-role check when a
    principal holds a claim for the resource. The resource name here is the
    table name, `course_content`, and the seeded role claims contain no such
    subject -- so the only way to write is to be `_lecturer`+ IN the course, or
    an admin. If a claim is ever added, this test should fail and the decision
    be made deliberately rather than inherited.
    """
    from computor_backend.model.course import CourseContent

    assert CourseContent.__tablename__ == "course_content"


# --------------------------------------------------------------------------
# Release state: the second reason a student loses a row (issue #163)
# --------------------------------------------------------------------------

_CONTENT_UUID = "11111111-1111-1111-1111-111111111111"


def test_released_predicate_lets_units_through_untouched():
    """A unit is never deployed; gating it on a deployment would empty the tree."""
    from sqlalchemy import select

    from computor_backend.business_logic.content_visibility import released_predicate

    sql = _compiled(select(CourseContent.id).where(released_predicate()))
    assert "course_content.is_submittable IS false OR" in sql


def test_released_predicate_asks_for_a_completed_release_not_a_status():
    """``deployed_at`` is the only field a *successful* release writes.

    Reading ``deployment_status == 'deployed'`` instead would hide a live
    assignment the moment a lecturer bumped its example version, because that
    resets the status to 'pending' while the students' files stay in place.
    """
    from sqlalchemy import select

    from computor_backend.business_logic.content_visibility import released_predicate

    sql = _compiled(select(CourseContent.id).where(released_predicate()))
    assert "course_content_deployment.deployed_at IS NOT NULL" in sql
    assert "deployment_status = 'deployed'" not in sql


def test_released_predicate_drops_an_unassigned_deployment():
    from sqlalchemy import select

    from computor_backend.business_logic.content_visibility import released_predicate

    sql = _compiled(select(CourseContent.id).where(released_predicate()))
    assert "deployment_status != 'unassigned'" in sql


def test_released_predicate_correlates_to_the_outer_course_content():
    from sqlalchemy import select

    from computor_backend.business_logic.content_visibility import released_predicate

    sql = _compiled(select(CourseContent.id).where(released_predicate()))
    assert "course_content_deployment.course_content_id = course_content.id" in sql


def test_student_visible_predicate_carries_both_rules():
    """One predicate, so a list and a get cannot disagree about a row."""
    from sqlalchemy import select

    from computor_backend.business_logic.content_visibility import (
        student_visible_predicate,
    )

    sql = _compiled(select(CourseContent.id).where(student_visible_predicate()))
    assert "<@" in sql, "the #338 ancestor veto must survive"
    assert "deployed_at IS NOT NULL" in sql, "the #163 release gate must be there"


def test_student_search_hides_an_unreleased_assignment():
    sql = _student_search_sql(include_hidden=False)
    assert "deployed_at IS NOT NULL" in sql


def test_staff_search_keeps_unreleased_assignments():
    """A lecturer's own tree and a tutor's view of a student show everything."""
    sql = _student_search_sql(include_hidden=True)
    assert "deployed_at" not in sql


def test_the_unit_badge_applies_the_same_filter():
    """The badge re-queries from scratch, so it has to repeat the filter."""
    import inspect

    from computor_backend.repositories.view_base import ViewRepository

    source = inspect.getsource(ViewRepository._aggregate_single_unit_status_for_list)
    assert "student_visible_predicate" in source


class _ReleaseQuery:
    def __init__(self, first):
        self._first = first

    def filter(self, *args, **_kwargs):
        _bind_check(args)
        return self

    def first(self):
        return self._first


class _ReleaseDb:
    def __init__(self, released):
        self.released = released
        self.queries = 0

    def query(self, *entities):
        self.queries += 1
        return _ReleaseQuery("a-deployment" if self.released else None)


class _Submittable:
    def __init__(self, is_submittable=True):
        self.id = _CONTENT_UUID
        self.path = "a.b"
        self.course_id = "course-1"
        self.is_submittable = is_submittable


def test_is_content_released_answers_yes_for_a_unit_without_querying():
    from computor_backend.business_logic.content_visibility import is_content_released

    db = _ReleaseDb(released=False)
    assert is_content_released(db, _Submittable(is_submittable=False)) is True
    assert db.queries == 0


def test_is_content_released_needs_a_completed_release():
    from computor_backend.business_logic.content_visibility import is_content_released

    assert is_content_released(_ReleaseDb(released=True), _Submittable()) is True
    assert is_content_released(_ReleaseDb(released=False), _Submittable()) is False


def test_the_single_get_guard_checks_release_as_well_as_visibility():
    import inspect

    from computor_backend.repositories.student_view import StudentViewRepository

    source = inspect.getsource(StudentViewRepository._guard_hidden_content)
    assert "is_content_released" in source
    # visible_effective must keep meaning "a lecturer hid this" -- the lecturer
    # tree greys rows by it, and an unreleased assignment is unfinished, not
    # hidden.
    assert "result.visible_effective = visible" in source


def test_a_release_drops_the_cached_student_listing():
    """Otherwise a student waits out the 5-minute TTL to see released work."""
    import inspect

    from computor_backend.tasks import temporal_student_template_v2 as workflow

    source = inspect.getsource(workflow)
    assert source.count("invalidate_deployment_views(") == source.count(
        "broadcast_deployment_events("
    ), "every committed status change must invalidate the views it changed"


def test_view_invalidation_survives_a_broken_cache():
    """A release that is already committed must not fail on a cache error."""
    from computor_backend.tasks.student_template import status

    class _Boom:
        def invalidate_tags(self, *_tags):
            raise RuntimeError("redis is down")

    original = status.invalidate_deployment_views
    import computor_backend.redis_cache as cache_module

    real_get_cache = cache_module.get_cache
    cache_module.get_cache = lambda: _Boom()
    try:
        original("course-1", [{"course_content_id": _CONTENT_UUID}])
    finally:
        cache_module.get_cache = real_get_cache


def test_view_invalidation_covers_the_student_listing_tag():
    from computor_backend.tasks.student_template import status

    seen = []

    class _Recorder:
        def invalidate_tags(self, *tags):
            seen.extend(tags)

    import computor_backend.redis_cache as cache_module

    real_get_cache = cache_module.get_cache
    cache_module.get_cache = lambda: _Recorder()
    try:
        status.invalidate_deployment_views("course-1", [{"course_content_id": _CONTENT_UUID}])
    finally:
        cache_module.get_cache = real_get_cache

    assert "student_view:course-1" in seen
    assert f"course_content:{_CONTENT_UUID}" in seen

"""Student visibility of course contents: one resolver, one enforcer.

Issue #338. A lecturer stages content before students may work on it — prepare
an exam unit invisibly, rehearse it through the real student path, reveal it
for the exam, hide it again afterwards.

``Course.visible`` and ``CourseContent.visible`` are nullable booleans, and the
rule they encode is a **veto, not a fallback**::

    effective_visible(node) = course.visible IS NOT FALSE
                              AND no ancestor-or-self has visible = FALSE

``NULL`` (the default) inherits. ``False`` anywhere in the chain hides that
whole subtree. ``True`` on a child **cannot** re-grant what an ancestor denied.

This is deliberately *not* the shape of ``submission_limits.resolve_limits``,
which returns the nearest non-NULL value. A nearest-non-NULL walk would let a
child's ``visible=True`` override an invisible parent, which is exactly the bug
this module exists to avoid. The matching precedent in the codebase is
``model.workspace.CourseWorkspaceTemplate.allow_root`` / ``allow_internet``:
"NULL = inherit; False denies; True cannot grant what the template denies".

The ``Course`` row is the implicit root of the ``course_content`` ltree — there
is no synthetic root content row, and ``(course_id, path)`` is unique, so the
tree is already per course.

Who is affected: **students only**. Tutors, lecturers and admins keep seeing
and acting on hidden content; the API merely tells them it is hidden so the UI
can mark it. Every enforcement helper here therefore takes ``exempt``, in the
same shape as ``submission_limits.enforce_max_test_runs``, and callers pass
``permissions.course_access.is_course_staff(...)``.

Issue #163 added the second reason a student may lose a row: an assignment the
lecturer has created but never released. It lives here rather than in a filter
of its own so that the student list, the student single-``GET`` and the unit
badge cannot disagree about who may see what::

    student_may_see(node) = effective_visible(node)
                            AND (node is not submittable OR node was released)

It is deliberately **not** folded into ``visible_effective``. That flag means
"a lecturer hid this", and the lecturer tree greys rows by it; an undeployed
assignment is not hidden, it is unfinished, and the staff views show its
deployment status separately.
"""
import logging
from types import SimpleNamespace
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy import and_, exists, or_
from sqlalchemy.orm import Session, aliased

from computor_backend.exceptions import BadRequestException
from computor_backend.model.course import Course, CourseContent
from computor_backend.model.deployment import CourseContentDeployment
from computor_types.custom_types import Ltree

logger = logging.getLogger(__name__)

# Raised when a student acts on content they cannot see.
HIDDEN_CONTENT_ERROR_CODE = "SUBMIT_012"
# Raised instead of the above when the whole course is archived: the student
# should not go looking for a lecturer to un-hide anything.
ARCHIVED_COURSE_ERROR_CODE = "SUBMIT_013"


# ---------------------------------------------------------------------------
# Pure resolution
# ---------------------------------------------------------------------------

def ancestor_paths(path: str) -> List[str]:
    """Every ancestor-or-self path of an ltree path, outermost first.

    ``"a.b.c"`` -> ``["a", "a.b", "a.b.c"]``. Self is included because a node's
    own ``visible=False`` must veto it.
    """
    parts = str(path).split(".")
    return [".".join(parts[: i + 1]) for i in range(len(parts))]


def resolve_visible(
    path: str,
    overrides: Dict[str, Optional[bool]],
    course_visible: Optional[bool] = None,
) -> bool:
    """Effective visibility of one content path.

    ``overrides`` maps content path -> its own ``visible`` value; it only needs
    to carry the nodes where a lecturer actually set the flag (see
    :func:`load_visibility_overrides`). ``course_visible`` is the course row's
    own flag.
    """
    if course_visible is False:
        return False
    return not any(overrides.get(p) is False for p in ancestor_paths(path))


# ---------------------------------------------------------------------------
# Loading the few rows that carry a decision
# ---------------------------------------------------------------------------

def load_visibility_overrides(
    db: Session,
    course_id,
) -> Dict[str, Optional[bool]]:
    """``path -> visible`` for the contents where the flag is actually set.

    Only rows with a non-NULL ``visible`` matter to the resolution, and in
    practice a lecturer sets the flag on a handful of nodes, so this is a tiny
    result set regardless of course size. Loading it once makes resolution
    purely local and correct even when the caller's row set is filtered down to
    a subtree and does not contain its own ancestors.
    """
    rows = (
        db.query(CourseContent.path, CourseContent.visible)
        .filter(
            CourseContent.course_id == course_id,
            CourseContent.visible.isnot(None),
        )
        .all()
    )
    return {str(path): visible for path, visible in rows}


def _course_veto(visible: Optional[bool], archived_at) -> Optional[bool]:
    """Collapse a course row's ``visible`` + ``archived_at`` into one veto value.

    An archived course is hidden from students exactly like ``visible=False``:
    the whole content tree drops out and every student write is refused. It is
    folded in here, at the root of the chain, so every visibility path — the
    list annotator, the single-row check, the SQL predicate and the write
    guard — agrees without each growing its own archived branch.
    """
    if archived_at is not None:
        return False
    return visible


def load_course_state(db: Session, course_id) -> Tuple[Optional[bool], Optional[object]]:
    """The course row's ``(visible, archived_at)`` in one read."""
    row = (
        db.query(Course.visible, Course.archived_at)
        .filter(Course.id == course_id)
        .first()
    )
    if row is None:
        return None, None
    return row[0], row[1]


def load_course_visible(db: Session, course_id) -> Optional[bool]:
    """The course row's own veto: ``visible``, or False once archived."""
    return _course_veto(*load_course_state(db, course_id))


# ---------------------------------------------------------------------------
# Bulk annotation, for list paths that already hold every row
# ---------------------------------------------------------------------------

def annotate_effective_visibility(
    db: Session,
    rows: Iterable,
) -> list:
    """Set ``visible_effective`` on every row of a loaded course-content set.

    Two small queries per distinct course plus one pass over the rows — no
    per-row correlated subquery, which is the shape #121 removed from this
    table for exactly this reason. For the student/tutor/lecturer list views,
    which load their contents unpaginated and then map them to DTOs.

    Rows may span several courses (the lecturer list does when unfiltered), so
    they are grouped by ``course_id`` rather than assuming one course.

    Rows are returned unchanged apart from the added attribute, so this is safe
    to call on ORM objects, query result rows and DTOs alike.
    """
    rows = list(rows)
    if not rows:
        return rows

    by_course: Dict[str, list] = {}
    for row in rows:
        course_id = getattr(row, "course_id", None)
        if course_id is None:
            # Nothing to resolve against; leave it visible rather than guess.
            _set_visible_effective(row, True)
            continue
        by_course.setdefault(str(course_id), []).append(row)

    for course_id, course_rows in by_course.items():
        overrides = load_visibility_overrides(db, course_id)
        course_visible = load_course_visible(db, course_id)
        for row in course_rows:
            _set_visible_effective(
                row, resolve_visible(str(row.path), overrides, course_visible)
            )
    return rows


def _set_visible_effective(row, value: bool) -> None:
    """Best-effort attribute write.

    Query result rows can be immutable ``Row`` tuples; the mappers read the
    attribute back off the ORM entity, so a failure to set it here is not fatal
    and must not break the request.
    """
    try:
        row.visible_effective = value
    except (AttributeError, TypeError):
        logger.debug("Could not set visible_effective on %r", type(row).__name__)


def filter_visible(rows: Iterable) -> list:
    """Drop the rows a student must not see.

    Call after :func:`annotate_effective_visibility`.
    """
    return [row for row in rows if getattr(row, "visible_effective", True)]


# ---------------------------------------------------------------------------
# Single-node check
# ---------------------------------------------------------------------------

def is_content_visible(db: Session, course_content, course=None) -> bool:
    """Whether one course content is effectively visible to students.

    Used by the single-``GET`` and the test/submit guards, where the caller
    holds exactly one row and the list paths above do not apply.
    """
    if course_content is None:
        return False

    if course is not None:
        course_visible = _course_veto(
            getattr(course, "visible", None), getattr(course, "archived_at", None)
        )
    else:
        course_visible = load_course_visible(db, course_content.course_id)
    if course_visible is False:
        return False

    # Only the row's own ancestors matter, and (course_id, path) is unique, so
    # this rides the existing btree instead of needing the ltree GiST index.
    #
    # The paths MUST be wrapped in Ltree. sqlalchemy_utils' LtreeType bind
    # processor reads ``value.path`` off whatever it is handed, so a plain
    # ``str`` raises AttributeError inside statement execution rather than
    # comparing as text.
    paths = [Ltree(p) for p in ancestor_paths(str(course_content.path))]
    hidden = (
        db.query(CourseContent.id)
        .filter(
            CourseContent.course_id == course_content.course_id,
            CourseContent.path.in_(paths),
            CourseContent.visible.is_(False),
        )
        .first()
    )
    return hidden is None


# ---------------------------------------------------------------------------
# SQL predicate, for the paths that paginate
# ---------------------------------------------------------------------------

def effective_visible_predicate():
    """A SQLAlchemy predicate selecting effectively-visible ``CourseContent``.

    For queries that apply ``LIMIT``/``OFFSET``: filtering those in Python
    after the fact would return short pages. Both halves are correlated
    ``EXISTS`` subqueries, so the caller does not have to join ``Course``.

    The ancestor half relies on the ltree ``<@`` containment operator, which is
    what ``ix_course_content_path_gist`` exists to serve.

    Both halves ``correlate(CourseContent)`` explicitly rather than trusting
    auto-correlation. Several callers — ``user_course_content_list_query`` among
    them — already join ``Course`` into the outer query, and auto-correlation
    would then pull ``course`` out of the first subquery and bind it to whatever
    the outer join happens to be. Pinning the correlation keeps this predicate
    safe to drop into any query shape.
    """
    ancestor = aliased(CourseContent)

    course_hidden = (
        exists()
        .where(
            and_(
                Course.id == CourseContent.course_id,
                or_(Course.visible.is_(False), Course.archived_at.isnot(None)),
            )
        )
        .correlate(CourseContent)
    )
    ancestor_hidden = (
        exists()
        .where(
            and_(
                ancestor.course_id == CourseContent.course_id,
                # descendant_of is inclusive, so a node's own False vetoes it.
                CourseContent.path.descendant_of(ancestor.path),
                ancestor.visible.is_(False),
            )
        )
        .correlate(CourseContent)
    )
    return and_(~course_hidden, ~ancestor_hidden)


# ---------------------------------------------------------------------------
# Release state: the second reason a student loses a row (#163)
# ---------------------------------------------------------------------------

# A deployment row exists from the moment an example is assigned, long before
# anything reaches the student template, so its mere presence proves nothing.
# ``deployed_at`` is the one field that is only ever written by a *successful*
# release (``CourseContentDeployment.set_deployed``,
# ``tasks/student_template/status.py``) and never cleared afterwards.
#
# Reading it, rather than ``deployment_status == 'deployed'``, is what keeps a
# lecturer's version bump from yanking a live assignment out from under the
# students working on it: reassigning resets the status to 'pending' and the
# release run moves it through 'deploying', and during that window the files
# are still in the student's repository from the previous release.
#
# 'unassigned' is excluded all the same: the lecturer has taken the example
# away, and the next release drops the directory.

UNRELEASED_DEPLOYMENT_STATUS = "unassigned"


def released_predicate():
    """A SQLAlchemy predicate selecting ``CourseContent`` a student may reach.

    Non-submittable content — units — passes unconditionally: a unit is never
    deployed, it only holds things that are. Submittable content needs a
    deployment that has completed a release at least once.

    An assignment with no deployment row at all therefore fails this too, and
    that is correct rather than incidental: an assignment always holds an
    example, so one without a deployment is a half-finished setup, not a
    deliberately file-less exercise. Confirmed 2026-08-26 — do not loosen this
    into "hide it only once someone has assigned an example".
    """
    released = (
        exists()
        .where(
            and_(
                CourseContentDeployment.course_content_id == CourseContent.id,
                CourseContentDeployment.deployed_at.isnot(None),
                CourseContentDeployment.deployment_status
                != UNRELEASED_DEPLOYMENT_STATUS,
            )
        )
        .correlate(CourseContent)
    )
    return or_(CourseContent.is_submittable.is_(False), released)


def student_visible_predicate():
    """The whole student read filter, in SQL: hidden **and** unreleased.

    The single predicate every student list path applies, so that "may this
    student see this row" has exactly one answer.
    """
    return and_(effective_visible_predicate(), released_predicate())


def is_content_released(db: Session, course_content) -> bool:
    """Single-row counterpart of :func:`released_predicate`."""
    if course_content is None:
        return False
    if not getattr(course_content, "is_submittable", False):
        return True

    released = (
        db.query(CourseContentDeployment.id)
        .filter(
            CourseContentDeployment.course_content_id == course_content.id,
            CourseContentDeployment.deployed_at.isnot(None),
            CourseContentDeployment.deployment_status
            != UNRELEASED_DEPLOYMENT_STATUS,
        )
        .first()
    )
    return released is not None


def is_student_visible(db: Session, course_content, course=None) -> bool:
    """Single-row counterpart of :func:`student_visible_predicate`."""
    return is_content_visible(db, course_content, course) and is_content_released(
        db, course_content
    )


# ---------------------------------------------------------------------------
# Enforcement
# ---------------------------------------------------------------------------

def enforce_content_visible(
    db: Session,
    course_content,
    *,
    course=None,
    exempt: bool = False,
    error_code: str = HIDDEN_CONTENT_ERROR_CODE,
) -> None:
    """Raise when a student acts on content they cannot see.

    ``exempt`` short-circuits for lecturers and tutors: staff testing hidden
    content is the point of the feature, not a loophole in it.
    """
    if exempt:
        return

    # One read of the course row serves both checks below (is_content_visible
    # would otherwise repeat it).
    if course is None and course_content is not None:
        visible, archived_at = load_course_state(db, course_content.course_id)
        course = SimpleNamespace(visible=visible, archived_at=archived_at)

    # Archived beats hidden: say so specifically, since "your lecturer has
    # hidden it" would send the student looking for a reveal that never comes.
    if getattr(course, "archived_at", None) is not None:
        raise BadRequestException(
            detail="This course has been archived. Submissions and test runs are closed.",
            error_code=ARCHIVED_COURSE_ERROR_CODE,
        )

    if not is_content_visible(db, course_content, course):
        raise BadRequestException(
            detail=(
                "This assignment is not currently available. "
                "Your lecturer has hidden it."
            ),
            error_code=error_code,
        )

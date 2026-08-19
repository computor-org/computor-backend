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
"""
import logging
from typing import Dict, Iterable, List, Optional

from sqlalchemy import and_, exists
from sqlalchemy.orm import Session, aliased

from computor_backend.exceptions import BadRequestException
from computor_backend.model.course import Course, CourseContent
from computor_types.custom_types import Ltree

logger = logging.getLogger(__name__)

# Raised when a student acts on content they cannot see.
HIDDEN_CONTENT_ERROR_CODE = "SUBMIT_012"


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


def load_course_visible(db: Session, course_id) -> Optional[bool]:
    """The course row's own ``visible`` flag."""
    return (
        db.query(Course.visible)
        .filter(Course.id == course_id)
        .scalar()
    )


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

    course_visible = getattr(course, "visible", None) if course is not None else None
    if course is None:
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
                Course.visible.is_(False),
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

    if not is_content_visible(db, course_content, course):
        raise BadRequestException(
            detail=(
                "This assignment is not currently available. "
                "Your lecturer has hidden it."
            ),
            error_code=error_code,
        )

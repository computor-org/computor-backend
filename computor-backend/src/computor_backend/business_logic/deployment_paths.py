"""Where a course content lands inside the student-template repository.

Issue #150. A lecturer who uses one example in two units — the same exercise in
week 2 and week 5 — used to end up with both contents pointing at the same
directory, because the directory name was simply the example's identifier
(``lecturer_deployment.assign_example_to_content``). The second release wrote
over the first, and the student's second assignment resolved onto the first
one's files: "duplicate" on open, and one of the two assignments unusable.

The directory name is a *deployment* property, not an example property. This
module is the one place that picks it, and it picks a name no other deployment
in the same course is already using::

    mathematical_constants          # free
    mathematical_constants-week5    # taken -> discriminate by the unit
    mathematical_constants-week5-2  # still taken -> count

The discriminator is read off the content's own ltree path, so the name stays
legible in a directory listing and in a student's repository.

Nothing renames an existing directory. A deployment that already has a
``deployment_path`` keeps it; only a fresh assignment (or a reassignment, which
is a fresh choice of example anyway) allocates. Renaming would move files under
students who have already cloned.
"""
import logging
from typing import Optional, Set

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# A deployment the lecturer has taken the example away from is not holding its
# directory any more — the next release drops it.
RELEASED_AWAY_STATUS = "unassigned"

# How many numbered candidates to try before giving up on a readable name.
_MAX_NUMBERED = 50


def _segments(path: Optional[str]) -> list:
    return [s for s in str(path or "").split(".") if s]


def _discriminators(content_path: Optional[str]) -> list:
    """Suffix candidates for one content, most legible first.

    ``week5.mathematical_constants`` offers ``week5`` (the unit, which is what
    the lecturer distinguishes the two copies by) and then the content's own
    slug. A root-level content only has the latter.
    """
    segments = _segments(content_path)
    candidates = []
    if len(segments) >= 2:
        candidates.append(segments[-2])
    if segments:
        candidates.append(segments[-1])
    # Two identical segments (``week5.week5``) would offer the same suffix twice.
    return list(dict.fromkeys(candidates))


def taken_deployment_paths(
    db: Session,
    course_id,
    *,
    exclude_course_content_id=None,
) -> Set[str]:
    """Directory names already spoken for by other deployments in this course.

    ``exclude_course_content_id`` leaves the content being assigned out, so a
    reassignment does not have to avoid its own current name.
    """
    from ..model.course import CourseContent
    from ..model.deployment import CourseContentDeployment

    query = (
        db.query(CourseContentDeployment.deployment_path)
        .join(CourseContent, CourseContent.id == CourseContentDeployment.course_content_id)
        .filter(
            CourseContent.course_id == str(course_id),
            CourseContentDeployment.deployment_path.isnot(None),
            CourseContentDeployment.deployment_status != RELEASED_AWAY_STATUS,
        )
    )
    if exclude_course_content_id is not None:
        query = query.filter(
            CourseContentDeployment.course_content_id != str(exclude_course_content_id)
        )
    return {row[0] for row in query.all() if row[0]}


def allocate_deployment_path(
    db: Session,
    course_content,
    base_name: str,
) -> str:
    """A directory name for this content that no sibling deployment holds.

    Returns ``base_name`` untouched in the ordinary case — one example, one
    course content — so nothing about existing courses changes.
    """
    taken = taken_deployment_paths(
        db,
        course_content.course_id,
        exclude_course_content_id=course_content.id,
    )
    if base_name not in taken:
        return base_name

    for discriminator in _discriminators(getattr(course_content, "path", None)):
        candidate = f"{base_name}-{discriminator}"
        if candidate not in taken:
            logger.info(
                "Deployment path %r is taken in course %s; using %r for content %s",
                base_name, course_content.course_id, candidate, course_content.id,
            )
            return candidate

    for n in range(2, _MAX_NUMBERED + 2):
        candidate = f"{base_name}-{n}"
        if candidate not in taken:
            logger.info(
                "Deployment path %r is taken in course %s; using %r for content %s",
                base_name, course_content.course_id, candidate, course_content.id,
            )
            return candidate

    # Unreachable in practice: it would take 50+ contents on one example.
    raise ValueError(
        f"Could not find a free deployment path for {base_name!r} in course "
        f"{course_content.course_id}"
    )

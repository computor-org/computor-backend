"""Moving a course content to a new path and/or position.

A move is a path change plus a reposition, and the path change has to cascade
to every descendant. Both halves are constrained by the database trigger
``trg_validate_course_content_hierarchy``, which re-validates the parent chain
of every row whose ``path`` it sees change. Two consequences drive this module
(computor-org/issues#323):

* **Order matters.** The moved item must be repathed *before* its descendants.
  While the item still sits at its old path, the descendants' new parent does
  not exist yet, so the trigger rejects them and a move of any unit that has
  children fails with a database error.
* **Validate first.** The trigger reports violations as a raw ``RAISE``, which
  reaches the client as a 500. :func:`validate_course_content_move` mirrors the
  trigger's rules in Python so a lecturer gets a 400 naming the actual problem,
  while the trigger stays as the last-resort invariant.

Reordering a content among its own siblings does not go through here at all:
that is a position-only ``PATCH /course-contents/{id}``. Changing ``path``
through that generic PATCH is rejected, because it would not cascade.
"""

import re
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy_utils import Ltree

from ..exceptions import BadRequestException
from ..model.course import CourseContent, CourseContentKind, CourseContentType

PATH_FORMAT = re.compile(r'^[a-z0-9_]+(\.[a-z0-9_]+)*$')


def parent_path_of(path: str) -> str:
    """The path of ``path``'s parent, or ``""`` when ``path`` is a root node."""
    head, _, _ = path.rpartition('.')
    return head


def validate_course_content_move(content: CourseContent, new_path: str, db: Session) -> None:
    """Check that ``content`` may be moved to ``new_path``.

    Raises :class:`BadRequestException` when the target path is malformed,
    would nest the content inside itself, collides with an existing content,
    or does not fit the course's content-kind hierarchy.
    """
    old_path = str(content.path)

    if not PATH_FORMAT.match(new_path):
        raise BadRequestException(
            detail="Invalid path format. Path must consist of lowercase alphanumeric segments separated by dots",
            context={"path": new_path},
        )

    if new_path == old_path:
        return

    if new_path.startswith(old_path + '.'):
        raise BadRequestException(
            detail="Cannot move an item into its own descendant",
            context={"old_path": old_path, "new_path": new_path},
        )

    _check_collisions(content, new_path, db)
    _check_hierarchy(content, new_path, db)


def _check_collisions(content: CourseContent, new_path: str, db: Session) -> None:
    """Refuse a move that would put two contents on the same path."""
    old_path = str(content.path)
    course_id = str(content.course_id)
    content_id = str(content.id)

    collision = db.query(CourseContent).filter(
        CourseContent.course_id == content.course_id,
        CourseContent.path == Ltree(new_path),
        CourseContent.id != content_id,
    ).first()
    if collision:
        raise BadRequestException(
            detail=f"Path '{new_path}' already exists in this course",
            context={
                "new_path": new_path,
                "conflicting_content_id": str(collision.id),
                "conflicting_content_title": collision.title,
            },
        )

    descendants = db.execute(
        text("""
            SELECT path FROM course_content
            WHERE path <@ :old_path
              AND id != :content_id
              AND course_id = :course_id
        """),
        {"old_path": old_path, "content_id": content_id, "course_id": course_id},
    ).fetchall()
    if not descendants:
        return

    old_depth = old_path.count('.') + 1
    new_descendant_paths = [
        new_path + '.' + '.'.join(str(row[0]).split('.')[old_depth:])
        for row in descendants
    ]

    placeholders = ', '.join(f':p{i}' for i in range(len(new_descendant_paths)))
    params = {f'p{i}': p for i, p in enumerate(new_descendant_paths)}
    params.update({"content_id": content_id, "course_id": course_id, "old_path": old_path})

    collision_count = db.execute(
        text(f"""
            SELECT COUNT(*) FROM course_content
            WHERE course_id = :course_id
              AND path::text IN ({placeholders})
              AND NOT path <@ :old_path
        """),
        params,
    ).scalar()

    if collision_count:
        raise BadRequestException(
            detail=f"Moving this item would cause {collision_count} path collision(s) among its children",
            context={"old_path": old_path, "new_path": new_path},
        )


def _check_hierarchy(content: CourseContent, new_path: str, db: Session) -> None:
    """Mirror ``trg_validate_course_content_hierarchy`` with readable errors."""
    parent_path = parent_path_of(new_path)

    if not parent_path:
        # Root placement is always allowed by the trigger.
        return

    parent = db.query(CourseContent).filter(
        CourseContent.course_id == content.course_id,
        CourseContent.path == Ltree(parent_path),
    ).first()
    if parent is None:
        raise BadRequestException(
            error_code="CONTENT_009",
            detail=f"No content exists at path '{parent_path}' in this course, so nothing can be moved below it",
            context={"new_path": new_path, "parent_path": parent_path},
        )

    parent_kind = _kind_of(parent, db)
    if parent_kind is not None and not parent_kind.has_descendants:
        raise BadRequestException(
            error_code="CONTENT_009",
            detail=(
                f"'{parent.title or parent_path}' is a {parent_kind.id} and cannot contain other content. "
                "Move this content into a unit, or to the course root"
            ),
            context={"new_path": new_path, "parent_path": parent_path, "parent_kind": str(parent_kind.id)},
        )

    own_kind = _kind_of(content, db)
    if own_kind is not None and not own_kind.has_ascendants:
        raise BadRequestException(
            error_code="CONTENT_009",
            detail=f"A {own_kind.id} cannot be placed inside other content; it belongs at the course root",
            context={"new_path": new_path, "kind": str(own_kind.id)},
        )


def _kind_of(content: CourseContent, db: Session) -> Optional[CourseContentKind]:
    """The content-kind row behind a content's type, or ``None`` when unset."""
    return db.query(CourseContentKind).join(
        CourseContentType,
        CourseContentType.course_content_kind_id == CourseContentKind.id,
    ).filter(
        CourseContentType.id == content.course_content_type_id,
    ).first()


def apply_course_content_move(
    db: Session,
    content: CourseContent,
    new_path: str,
    position: float,
) -> None:
    """Write the new path and position, cascading the path to all descendants.

    Raw SQL throughout, to bypass SQLAlchemy's Ltree change detection. The item
    is repathed first, then its descendants one tree level at a time, shallowest
    first: the hierarchy trigger looks up each row's parent as the row is
    written, so a parent must always be at its new path before its children get
    there. A single statement for all descendants would leave that order up to
    the planner and break as soon as the moved subtree is more than one level
    deep. The level filter still matches afterwards because descendants keep
    their old paths until their own level is rewritten.
    """
    old_path = str(content.path)
    course_id = str(content.course_id)
    content_id = str(content.id)

    db.execute(
        text("""
            UPDATE course_content
            SET path = :new_path,
                position = :position,
                updated_at = now()
            WHERE id = :content_id
              AND course_id = :course_id
        """),
        {
            "new_path": new_path,
            "position": position,
            "content_id": content_id,
            "course_id": course_id,
        },
    )

    if old_path == new_path:
        return

    levels = db.execute(
        text("""
            SELECT DISTINCT nlevel(path) AS level
            FROM course_content
            WHERE path <@ :old_path
              AND id != :content_id
              AND course_id = :course_id
            ORDER BY level
        """),
        {"old_path": old_path, "content_id": content_id, "course_id": course_id},
    ).fetchall()

    for row in levels:
        db.execute(
            text("""
                UPDATE course_content
                SET path = :new_path || subpath(path, nlevel(:old_path)),
                    updated_at = now()
                WHERE path <@ :old_path
                  AND id != :content_id
                  AND course_id = :course_id
                  AND nlevel(path) = :level
            """),
            {
                "new_path": new_path,
                "old_path": old_path,
                "content_id": content_id,
                "course_id": course_id,
                "level": row[0],
            },
        )

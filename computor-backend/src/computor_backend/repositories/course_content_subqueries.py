"""Reusable SQLAlchemy subquery builders for course-content read queries.

Low-level subquery/aggregation helpers (latest result, submission/result
counts, latest grade status, unread-message counts) composed by the larger
query builders in ``course_content_queries.py``. Extracted from that module to
keep the composite queries separate from their building blocks; these helpers
have no external importers.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import func, case, select, and_, literal
import sqlalchemy as sa
from sqlalchemy.orm import Session, joinedload, contains_eager, subqueryload
from pydantic import BaseModel, ConfigDict

from computor_backend.exceptions import NotFoundException
from computor_backend.model.course import (
    SubmissionGroupMember,
    Course,
    CourseContent,
    CourseContentKind,
    CourseMember,
    SubmissionGroup
)
from computor_backend.model.result import Result
from computor_backend.model.artifact import SubmissionArtifact, SubmissionGrade
from computor_backend.model.auth import User
from computor_backend.model.message import Message, MessageRead


def latest_result_subquery(
    user_id: UUID | str | None,
    course_member_id: UUID | str | None,
    course_content_id: UUID | str | None,
    db: Session,
    submission: Optional[bool] = None
):
    """
    Build subquery to get the latest result date per course content.

    Args:
        user_id: Filter by user ID (mutually exclusive with course_member_id)
        course_member_id: Filter by course member ID (mutually exclusive with user_id)
        course_content_id: Filter by specific course content ID
        db: Database session
        submission: Filter by submission status (True=official submissions only)

    Returns:
        Subquery with course_content_id and latest_result_date columns
    """
    query = db.query(
        Result.course_content_id,
        func.max(Result.created_at).label("latest_result_date")
    )

    if user_id is not None:
        query = query.join(SubmissionGroup, SubmissionGroup.id == Result.submission_group_id) \
            .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id) \
            .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id) \
            .filter(CourseMember.user_id == user_id)
    elif course_member_id is not None:
        query = query.join(SubmissionGroup, SubmissionGroup.id == Result.submission_group_id) \
            .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id) \
            .filter(SubmissionGroupMember.course_member_id == course_member_id)

    query = query.filter(Result.status == 0, Result.test_system_id.isnot(None))

    if course_content_id is not None:
        query = query.filter(Result.course_content_id == course_content_id)

    if submission is not None:
        # Join with SubmissionArtifact to filter by submit field
        query = query.join(SubmissionArtifact, SubmissionArtifact.id == Result.submission_artifact_id) \
            .filter(SubmissionArtifact.submit == submission)

    return query.group_by(Result.course_content_id).subquery()


def submission_count_subquery(
    user_id: UUID | str | None,
    course_member_id: UUID | str | None,
    course_content_id: UUID | str | None,
    db: Session
):
    """
    Count SubmissionArtifacts with submit=True per course content.

    This counts actual submissions, not test results.

    Args:
        user_id: Filter by user ID (mutually exclusive with course_member_id)
        course_member_id: Filter by course member ID (mutually exclusive with user_id)
        course_content_id: Filter by specific course content ID
        db: Database session

    Returns:
        Subquery with course_content_id and submission_count columns
    """
    query = db.query(
        SubmissionGroup.course_content_id.label("course_content_id"),
        func.count(SubmissionArtifact.id).label("submission_count")
    ).select_from(SubmissionArtifact) \
        .join(SubmissionGroup, SubmissionGroup.id == SubmissionArtifact.submission_group_id) \
        .filter(SubmissionArtifact.submit == True)

    if user_id is not None:
        query = query.join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id) \
            .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id) \
            .filter(CourseMember.user_id == user_id)
    elif course_member_id is not None:
        query = query.join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id) \
            .filter(SubmissionGroupMember.course_member_id == course_member_id)

    if course_content_id is not None:
        query = query.filter(SubmissionGroup.course_content_id == course_content_id)

    return query.group_by(SubmissionGroup.course_content_id).subquery()


def results_count_subquery(
    user_id: UUID | str | None,
    course_member_id: UUID | str | None,
    course_content_id: UUID | str | None,
    db: Session
):
    """
    Count test results (Results with test_system_id) per course content.

    This counts all test runs, regardless of whether they were official submissions.

    Args:
        user_id: Filter by user ID (mutually exclusive with course_member_id)
        course_member_id: Filter by course member ID (mutually exclusive with user_id)
        course_content_id: Filter by specific course content ID
        db: Database session

    Returns:
        Subquery with course_content_id and total_results_count columns
    """
    query = db.query(
        Result.course_content_id,
        func.count(case((Result.test_system_id.isnot(None), 1))).label("total_results_count"),
    ).join(SubmissionArtifact, SubmissionArtifact.id == Result.submission_artifact_id)

    if user_id is not None:
        query = query.join(SubmissionGroup, SubmissionGroup.id == Result.submission_group_id) \
            .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id) \
            .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id) \
            .filter(CourseMember.user_id == user_id)
    elif course_member_id is not None:
        query = query.join(SubmissionGroup, SubmissionGroup.id == Result.submission_group_id) \
            .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id) \
            .filter(SubmissionGroupMember.course_member_id == course_member_id)

    query = query.filter(Result.status == 0)

    if course_content_id is not None:
        query = query.filter(Result.course_content_id == course_content_id)

    return query.group_by(Result.course_content_id).subquery()


# NOTE: ``latest_grading_subquery`` was removed (#119). It always returned
# zero rows (``.filter(sa.literal(False))``) and contributed columns
# ``status`` / ``grading`` that were therefore always NULL — the mappers
# overwrite them downstream from ``latest_submission_grade_status_subquery``
# anyway. Callers now emit literal-NULL columns at the same positional
# slots so ``CourseMemberCourseContentQueryResult.from_tuple`` keeps its
# tuple layout unchanged.


def latest_submission_grade_status_subquery(db: Session):
    """
    Get the grade status of the latest submission artifact per submission group.

    For each submission group, finds the latest submitted artifact (submit=true)
    and returns its latest grade's status.

    Returns columns:
        - submission_group_id
        - latest_grade_status: The status of the latest grade on the latest submission
                              (0=NOT_REVIEWED, 1=CORRECTED, 2=CORRECTION_NECESSARY, 3=IMPROVEMENT_POSSIBLE)
                              NULL if no grades exist
        - is_unreviewed: 1 if unreviewed (no grades or latest grade status=0), 0 otherwise

    Args:
        db: Database session

    Returns:
        Subquery with latest submission grade status info
    """
    # Promote the "latest submitted artifact per submission_group"
    # aggregation to a CTE. Previously this was a ``.subquery()`` referenced
    # twice — once as the FROM in the outer return, and again inside the
    # rank-grades subquery — which made SQLAlchemy inline the same
    # ``SELECT submission_group_id, MAX(created_at) FROM submission_artifact
    # WHERE submit=true GROUP BY ...`` block twice, forcing Postgres to
    # compute the aggregation twice per request (#119). A CTE is materialised
    # once and referenced N times.
    latest_artifact_cte = (
        db.query(
            SubmissionArtifact.submission_group_id,
            func.max(SubmissionArtifact.created_at).label("latest_artifact_created_at"),
        )
        .filter(SubmissionArtifact.submit == True)
        .group_by(SubmissionArtifact.submission_group_id)
        .cte("latest_artifact_per_group")
    )

    # Rank grades for each (latest) artifact by graded_at DESC; the join
    # uses the CTE above, so that aggregation is shared.
    latest_grade_subquery = (
        db.query(
            SubmissionArtifact.submission_group_id,
            SubmissionGrade.status,
            func.row_number()
            .over(
                partition_by=SubmissionArtifact.submission_group_id,
                order_by=SubmissionGrade.graded_at.desc(),
            )
            .label("rn"),
        )
        .select_from(SubmissionArtifact)
        .join(
            latest_artifact_cte,
            and_(
                SubmissionArtifact.submission_group_id
                == latest_artifact_cte.c.submission_group_id,
                SubmissionArtifact.created_at
                == latest_artifact_cte.c.latest_artifact_created_at,
            ),
        )
        .join(SubmissionGrade, SubmissionGrade.artifact_id == SubmissionArtifact.id)
        .filter(SubmissionArtifact.submit == True)
        .subquery()
    )

    # Pick the rn=1 row per submission_group (latest grade).
    latest_grade_status = (
        db.query(
            latest_grade_subquery.c.submission_group_id,
            latest_grade_subquery.c.status.label("latest_grade_status"),
        )
        .filter(latest_grade_subquery.c.rn == 1)
        .subquery()
    )

    # Final shape: every submission_group that has any submitted artifact,
    # left-joined to its latest grade. ``is_unreviewed`` is 1 when no grade
    # exists yet (NULL) or the latest grade status is NOT_REVIEWED.
    return (
        db.query(
            latest_artifact_cte.c.submission_group_id,
            latest_grade_status.c.latest_grade_status,
            case(
                (latest_grade_status.c.latest_grade_status.is_(None), 1),
                (latest_grade_status.c.latest_grade_status == 0, 1),
                else_=0,
            ).label("is_unreviewed"),
        )
        .select_from(latest_artifact_cte)
        .outerjoin(
            latest_grade_status,
            latest_artifact_cte.c.submission_group_id
            == latest_grade_status.c.submission_group_id,
        )
        .subquery()
    )


def message_unread_subqueries(
    reader_user_id: UUID | str | None,
    db: Session,
):
    """Build per-content and per-submission-group unread-message counters
    from a single shared scan.

    Previously ``message_unread_by_content_subquery`` and
    ``message_unread_by_submission_group_subquery`` each issued their own
    ``message ⟕ message_read`` scan with identical filters and only
    different ``GROUP BY`` columns — Postgres ran the same outer join +
    archived/author/read predicates twice per request (#119). This helper
    runs the join once via a CTE and aggregates off it twice.

    Returns ``(content_unread_sub, submission_group_unread_sub)`` —
    either may be ``None`` only when ``reader_user_id`` is ``None`` (in
    which case both are ``None``).
    """
    if reader_user_id is None:
        return None, None

    cte = (
        db.query(
            Message.id.label("message_id"),
            Message.course_content_id.label("course_content_id"),
            Message.submission_group_id.label("submission_group_id"),
        )
        .outerjoin(
            MessageRead,
            and_(
                MessageRead.message_id == Message.id,
                MessageRead.reader_user_id == reader_user_id,
            ),
        )
        .filter(Message.archived_at.is_(None))
        .filter(MessageRead.id.is_(None))
        .filter(Message.author_id != reader_user_id)
        .cte("unread_messages_for_reader")
    )

    content_unread = (
        db.query(
            cte.c.course_content_id.label("course_content_id"),
            func.count(cte.c.message_id).label("unread_count"),
        )
        .filter(cte.c.course_content_id.isnot(None))
        .filter(cte.c.submission_group_id.is_(None))
        .group_by(cte.c.course_content_id)
        .subquery()
    )

    submission_group_unread = (
        db.query(
            cte.c.submission_group_id.label("submission_group_id"),
            func.count(cte.c.message_id).label("unread_count"),
        )
        .filter(cte.c.submission_group_id.isnot(None))
        .group_by(cte.c.submission_group_id)
        .subquery()
    )

    return content_unread, submission_group_unread


# Backwards-compatibility shims. New code paths in this module use
# ``message_unread_subqueries`` directly so both subqueries can share a
# CTE; these wrappers keep the old per-aggregate names available for any
# external caller that imported them directly.
def message_unread_by_content_subquery(reader_user_id: UUID | str | None, db: Session):
    content_sub, _ = message_unread_subqueries(reader_user_id, db)
    return content_sub


def message_unread_by_submission_group_subquery(reader_user_id: UUID | str | None, db: Session):
    _, sg_sub = message_unread_subqueries(reader_user_id, db)
    return sg_sub

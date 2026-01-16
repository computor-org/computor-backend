"""
Course content repository for complex query operations.

This module provides query builder functions for course content, submissions,
results, and grading data. These functions construct complex SQLAlchemy queries
with joins, subqueries, and aggregations for efficient data retrieval.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import func, case, select, and_, literal
import sqlalchemy as sa
from sqlalchemy.orm import Session, joinedload, contains_eager, subqueryload
from pydantic import BaseModel, ConfigDict

from computor_backend.api.exceptions import NotFoundException
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


class CourseMemberCourseContentQueryResult(BaseModel):
    """
    Typed result from course_member_course_content_query.

    This replaces the raw tuple unpacking with a proper typed model
    that provides named field access and type safety.

    Attributes:
        course_content: The course content entity
        result_count: Total number of test results for this content
        result: The latest result (if any)
        submission_group: The submission group (if any)
        submission_count: Number of official submissions
        submission_status_int: Latest grading status as integer
        submission_grading: Latest grading score
        content_unread_count: Unread messages at content level
        submission_group_unread_count: Unread messages at submission group level
        latest_grade_status_int: Grade status of the latest submission (0=NOT_REVIEWED, 1=CORRECTED, etc.)
        is_latest_unreviewed: 1 if latest submission is unreviewed (no grades or status=0), 0 otherwise
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    course_content: CourseContent
    result_count: Optional[int] = None
    result: Optional[Result] = None
    submission_group: Optional[SubmissionGroup] = None
    submission_count: Optional[int] = None
    submission_status_int: Optional[int] = None
    submission_grading: Optional[float] = None
    content_unread_count: int = 0
    submission_group_unread_count: int = 0
    latest_grade_status_int: Optional[int] = None
    is_latest_unreviewed: int = 0

    @classmethod
    def from_tuple(cls, raw_result: tuple) -> "CourseMemberCourseContentQueryResult":
        """
        Convert a raw tuple result into a typed model.

        This is used when query results are fetched via .all() or .first()
        from the query builder functions.

        Args:
            raw_result: The raw tuple from SQLAlchemy query

        Returns:
            Typed CourseMemberCourseContentQueryResult instance
        """
        return cls(
            course_content=raw_result[0],
            result_count=raw_result[1],
            result=raw_result[2],
            submission_group=raw_result[3],
            submission_count=raw_result[4] if len(raw_result) > 4 else None,
            submission_status_int=raw_result[5] if len(raw_result) > 5 else None,
            submission_grading=raw_result[6] if len(raw_result) > 6 else None,
            content_unread_count=raw_result[7] if len(raw_result) > 7 else 0,
            submission_group_unread_count=raw_result[8] if len(raw_result) > 8 else 0,
            latest_grade_status_int=raw_result[9] if len(raw_result) > 9 else None,
            is_latest_unreviewed=raw_result[10] if len(raw_result) > 10 else 0,
        )


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


def latest_grading_subquery(db: Session):
    """
    Latest grading per submission group using window function with deterministic ordering.

    Returns columns: submission_group_id, status, grading, rn (rn=1 is latest).

    NOTE: This needs to be migrated to use SubmissionGrade from artifact module
    which is tied to artifacts, not submission groups directly.

    Args:
        db: Database session

    Returns:
        Subquery with grading information (currently returns empty results)
    """
    # Temporarily return an empty subquery to avoid errors
    return db.query(
        SubmissionGroup.id.label('submission_group_id'),
        sa.literal(0).label('status'),
        sa.literal(0.0).label('grading'),
        sa.literal(datetime.now(timezone.utc)).label('created_at'),
        SubmissionGroup.id.label('id'),
        sa.literal(1).label('rn')
    ).filter(sa.literal(False)).subquery()  # Always empty for now


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
    # First, get the latest submission artifact per submission group
    latest_artifact_subquery = db.query(
        SubmissionArtifact.submission_group_id,
        func.max(SubmissionArtifact.created_at).label("latest_artifact_created_at")
    ).filter(
        SubmissionArtifact.submit == True
    ).group_by(
        SubmissionArtifact.submission_group_id
    ).subquery()

    # Then, for each latest artifact, get its latest grade
    # Using a window function to rank grades by graded_at DESC
    latest_grade_subquery = db.query(
        SubmissionArtifact.submission_group_id,
        SubmissionGrade.status,
        func.row_number().over(
            partition_by=SubmissionArtifact.submission_group_id,
            order_by=SubmissionGrade.graded_at.desc()
        ).label("rn")
    ).select_from(SubmissionArtifact).join(
        latest_artifact_subquery,
        and_(
            SubmissionArtifact.submission_group_id == latest_artifact_subquery.c.submission_group_id,
            SubmissionArtifact.created_at == latest_artifact_subquery.c.latest_artifact_created_at
        )
    ).join(
        SubmissionGrade,
        SubmissionGrade.artifact_id == SubmissionArtifact.id
    ).filter(
        SubmissionArtifact.submit == True
    ).subquery()

    # Get only rn=1 (latest grade) per submission group
    latest_grade_status = db.query(
        latest_grade_subquery.c.submission_group_id,
        latest_grade_subquery.c.status.label("latest_grade_status")
    ).filter(
        latest_grade_subquery.c.rn == 1
    ).subquery()

    # Now build the final subquery that includes all submission groups with submissions
    # and marks whether they are unreviewed
    return db.query(
        latest_artifact_subquery.c.submission_group_id,
        latest_grade_status.c.latest_grade_status,
        # is_unreviewed: 1 if no grade (NULL) or status=0 (NOT_REVIEWED)
        case(
            (latest_grade_status.c.latest_grade_status.is_(None), 1),
            (latest_grade_status.c.latest_grade_status == 0, 1),
            else_=0
        ).label("is_unreviewed")
    ).select_from(
        latest_artifact_subquery
    ).outerjoin(
        latest_grade_status,
        latest_artifact_subquery.c.submission_group_id == latest_grade_status.c.submission_group_id
    ).subquery()


def message_unread_by_content_subquery(reader_user_id: UUID | str | None, db: Session):
    """
    Count unread messages per course content.

    Args:
        reader_user_id: The user ID to check for unread messages
        db: Database session

    Returns:
        Subquery with course_content_id and unread_count columns, or None if no user_id
    """
    if reader_user_id is None:
        return None

    return (
        db.query(
            Message.course_content_id.label("course_content_id"),
            func.count(Message.id).label("unread_count"),
        )
        .outerjoin(
            MessageRead,
            and_(
                MessageRead.message_id == Message.id,
                MessageRead.reader_user_id == reader_user_id,
            ),
        )
        .filter(Message.archived_at.is_(None))
        .filter(Message.course_content_id.isnot(None))
        .filter(Message.submission_group_id.is_(None))
        .filter(MessageRead.id.is_(None))
        .filter(Message.author_id != reader_user_id)
        .group_by(Message.course_content_id)
        .subquery()
    )


def message_unread_by_submission_group_subquery(reader_user_id: UUID | str | None, db: Session):
    """
    Count unread messages per submission group.

    Args:
        reader_user_id: The user ID to check for unread messages
        db: Database session

    Returns:
        Subquery with submission_group_id and unread_count columns, or None if no user_id
    """
    if reader_user_id is None:
        return None

    return (
        db.query(
            Message.submission_group_id.label("submission_group_id"),
            func.count(Message.id).label("unread_count"),
        )
        .outerjoin(
            MessageRead,
            and_(
                MessageRead.message_id == Message.id,
                MessageRead.reader_user_id == reader_user_id,
            ),
        )
        .filter(Message.archived_at.is_(None))
        .filter(Message.submission_group_id.isnot(None))
        .filter(MessageRead.id.is_(None))
        .filter(Message.author_id != reader_user_id)
        .group_by(Message.submission_group_id)
        .subquery()
    )


def user_course_content_query(user_id: UUID | str, course_content_id: UUID | str, db: Session) -> CourseMemberCourseContentQueryResult:
    """
    Get detailed course content information for a specific user and course content.

    Includes submission groups, results, grades, and unread message counts.

    Args:
        user_id: The user ID
        course_content_id: The course content ID
        db: Database session

    Returns:
        CourseMemberCourseContentQueryResult with typed fields

    Raises:
        NotFoundException: If course content not found or user has no access
    """
    latest_result_sub = latest_result_subquery(user_id, None, course_content_id, db)
    results_count_sub = results_count_subquery(user_id, None, course_content_id, db)
    submission_count_sub = submission_count_subquery(user_id, None, course_content_id, db)
    latest_grading_sub = latest_grading_subquery(db)
    content_unread_sub = message_unread_by_content_subquery(user_id, db)
    submission_group_unread_sub = message_unread_by_submission_group_subquery(user_id, db)
    latest_submission_grade_sub = latest_submission_grade_status_subquery(db)

    content_unread_column = (
        func.coalesce(content_unread_sub.c.unread_count, 0).label("content_unread_count")
        if content_unread_sub is not None
        else literal(0).label("content_unread_count")
    )
    submission_group_unread_column = (
        func.coalesce(submission_group_unread_sub.c.unread_count, 0).label("submission_group_unread_count")
        if submission_group_unread_sub is not None
        else literal(0).label("submission_group_unread_count")
    )

    # Subquery to get only the user's submission groups
    user_submission_groups = select(SubmissionGroup.id).select_from(
        SubmissionGroup
    ).join(
        SubmissionGroupMember,
        SubmissionGroup.id == SubmissionGroupMember.submission_group_id
    ).join(
        CourseMember,
        SubmissionGroupMember.course_member_id == CourseMember.id
    ).where(
        CourseMember.user_id == user_id
    ).subquery()

    # Query specific course content including those without submission groups
    query_columns = [
        CourseContent,
        results_count_sub.c.total_results_count,
        Result,
        SubmissionGroup,
        submission_count_sub.c.submission_count,
        latest_grading_sub.c.status,
        latest_grading_sub.c.grading,
        content_unread_column,
        submission_group_unread_column,
        latest_submission_grade_sub.c.latest_grade_status,
        func.coalesce(latest_submission_grade_sub.c.is_unreviewed, 0).label("is_unreviewed"),
    ]

    course_contents_query = db.query(*query_columns) \
        .select_from(User) \
        .filter(User.id == user_id) \
        .join(CourseMember, CourseMember.user_id == User.id) \
        .join(Course, Course.id == CourseMember.course_id) \
        .join(CourseContent, (CourseContent.course_id == Course.id) & (CourseContent.id == course_content_id)) \
        .join(CourseContentKind, CourseContentKind.id == CourseContent.course_content_kind_id) \
        .outerjoin(SubmissionGroup,
                   (SubmissionGroup.course_content_id == CourseContent.id) &
                   (SubmissionGroup.id.in_(select(user_submission_groups.c.id)))) \
        .outerjoin(SubmissionGroupMember,
                   (SubmissionGroupMember.submission_group_id == SubmissionGroup.id) &
                   (SubmissionGroupMember.course_member_id == CourseMember.id)) \
        .outerjoin(
            latest_result_sub,
            CourseContent.id == latest_result_sub.c.course_content_id
        ).outerjoin(
            Result,
            (Result.course_content_id == latest_result_sub.c.course_content_id) &
            (Result.created_at == latest_result_sub.c.latest_result_date)
        ) \
        .outerjoin(
            results_count_sub,
            CourseContent.id == results_count_sub.c.course_content_id
        ).outerjoin(
            submission_count_sub,
            CourseContent.id == submission_count_sub.c.course_content_id
        ).outerjoin(
            latest_grading_sub,
            (latest_grading_sub.c.submission_group_id == SubmissionGroup.id)
            & (latest_grading_sub.c.rn == 1)
        ).outerjoin(
            latest_submission_grade_sub,
            latest_submission_grade_sub.c.submission_group_id == SubmissionGroup.id
        )

    if content_unread_sub is not None:
        course_contents_query = course_contents_query.outerjoin(
            content_unread_sub,
            CourseContent.id == content_unread_sub.c.course_content_id,
        )

    if submission_group_unread_sub is not None:
        course_contents_query = course_contents_query.outerjoin(
            submission_group_unread_sub,
            SubmissionGroup.id == submission_group_unread_sub.c.submission_group_id,
        )

    course_contents_query = course_contents_query.options(
        # Use contains_eager for submission_groups since we already joined it with a filter
        contains_eager(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.members)
        .joinedload(SubmissionGroupMember.course_member)
        .joinedload(CourseMember.user),
        # Load submission groups with artifacts
        contains_eager(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.submission_artifacts),
        # Load grades with grader info (separate chain)
        contains_eager(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.submission_artifacts)
        .joinedload(SubmissionArtifact.grades)
        .joinedload(SubmissionGrade.graded_by)
        .joinedload(CourseMember.user),
        # Also load course_role for grader
        contains_eager(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.submission_artifacts)
        .joinedload(SubmissionArtifact.grades)
        .joinedload(SubmissionGrade.graded_by)
        .joinedload(CourseMember.course_role),
    )

    course_contents_result = course_contents_query.distinct().first()

    if course_contents_result is None:
        raise NotFoundException()

    # Convert tuple to typed model using class method
    return CourseMemberCourseContentQueryResult.from_tuple(course_contents_result)


def user_course_content_list_query(user_id: UUID | str, db: Session):
    """
    Get list of all course contents for a specific user across all their courses.

    Includes submission groups, results, grades, and unread message counts.

    Args:
        user_id: The user ID
        db: Database session

    Returns:
        Query object that can be further filtered or executed
    """
    latest_result_sub = latest_result_subquery(user_id, None, None, db)
    results_count_sub = results_count_subquery(user_id, None, None, db)
    submission_count_sub = submission_count_subquery(user_id, None, None, db)
    latest_grading_sub = latest_grading_subquery(db)
    content_unread_sub = message_unread_by_content_subquery(user_id, db)
    submission_group_unread_sub = message_unread_by_submission_group_subquery(user_id, db)
    latest_submission_grade_sub = latest_submission_grade_status_subquery(db)

    content_unread_column = (
        func.coalesce(content_unread_sub.c.unread_count, 0).label("content_unread_count")
        if content_unread_sub is not None
        else literal(0).label("content_unread_count")
    )
    submission_group_unread_column = (
        func.coalesce(submission_group_unread_sub.c.unread_count, 0).label("submission_group_unread_count")
        if submission_group_unread_sub is not None
        else literal(0).label("submission_group_unread_count")
    )

    # Subquery to get only the user's submission groups
    user_submission_groups = select(SubmissionGroup.id).select_from(
        SubmissionGroup
    ).join(
        SubmissionGroupMember,
        SubmissionGroup.id == SubmissionGroupMember.submission_group_id
    ).join(
        CourseMember,
        SubmissionGroupMember.course_member_id == CourseMember.id
    ).where(
        CourseMember.user_id == user_id
    ).subquery()

    # Query ALL course contents where the user is a member, including those without submission groups
    query_columns = [
        CourseContent,
        results_count_sub.c.total_results_count,
        Result,
        SubmissionGroup,
        submission_count_sub.c.submission_count,
        latest_grading_sub.c.status,
        latest_grading_sub.c.grading,
        content_unread_column,
        submission_group_unread_column,
        latest_submission_grade_sub.c.latest_grade_status,
        func.coalesce(latest_submission_grade_sub.c.is_unreviewed, 0).label("is_unreviewed"),
    ]

    query = db.query(*query_columns) \
        .select_from(User) \
        .filter(User.id == user_id) \
        .join(CourseMember, CourseMember.user_id == User.id) \
        .join(Course, Course.id == CourseMember.course_id) \
        .join(CourseContent, CourseContent.course_id == Course.id) \
        .join(CourseContentKind, CourseContentKind.id == CourseContent.course_content_kind_id) \
        .outerjoin(SubmissionGroup,
                   (SubmissionGroup.course_content_id == CourseContent.id) &
                   (SubmissionGroup.id.in_(select(user_submission_groups.c.id)))) \
        .outerjoin(SubmissionGroupMember,
                   (SubmissionGroupMember.submission_group_id == SubmissionGroup.id) &
                   (SubmissionGroupMember.course_member_id == CourseMember.id)) \
        .outerjoin(
            latest_result_sub,
            CourseContent.id == latest_result_sub.c.course_content_id
        ).outerjoin(
            Result,
            (Result.course_content_id == latest_result_sub.c.course_content_id) &
            (Result.created_at == latest_result_sub.c.latest_result_date)
        ) \
        .outerjoin(
            results_count_sub,
            CourseContent.id == results_count_sub.c.course_content_id
        ).outerjoin(
            submission_count_sub,
            CourseContent.id == submission_count_sub.c.course_content_id
        ).outerjoin(
            latest_grading_sub,
            (latest_grading_sub.c.submission_group_id == SubmissionGroup.id)
            & (latest_grading_sub.c.rn == 1)
        ).outerjoin(
            latest_submission_grade_sub,
            latest_submission_grade_sub.c.submission_group_id == SubmissionGroup.id
        )

    if content_unread_sub is not None:
        query = query.outerjoin(
            content_unread_sub,
            CourseContent.id == content_unread_sub.c.course_content_id,
        )

    if submission_group_unread_sub is not None:
        query = query.outerjoin(
            submission_group_unread_sub,
            SubmissionGroup.id == submission_group_unread_sub.c.submission_group_id,
        )

    query = query.options(
        # Use contains_eager for submission_groups since we already joined it with a filter
        contains_eager(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.members)
        .joinedload(SubmissionGroupMember.course_member)
        .joinedload(CourseMember.user),
        # Load submission groups with artifacts and their grades
        contains_eager(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.submission_artifacts)
        .joinedload(SubmissionArtifact.grades)
        .joinedload(SubmissionGrade.graded_by)
        .joinedload(CourseMember.user),
    )

    query = query.distinct()

    return query


def course_member_course_content_query(
    course_member_id: UUID | str,
    course_content_id: UUID | str,
    db: Session,
    reader_user_id: UUID | str | None = None
) -> CourseMemberCourseContentQueryResult:
    """
    Get detailed course content information for a specific course member and course content.

    Used for lecturer/tutor views to see student progress. Includes submission groups,
    results, grades, and unread message counts.

    Args:
        course_member_id: The course member ID
        course_content_id: The course content ID
        db: Database session
        reader_user_id: Optional user ID for unread message counts

    Returns:
        CourseMemberCourseContentQueryResult with typed fields

    Raises:
        NotFoundException: If course content not found or member has no access
    """
    latest_result_sub = latest_result_subquery(None, course_member_id, course_content_id, db)
    results_count_sub = results_count_subquery(None, course_member_id, course_content_id, db)
    submission_count_sub = submission_count_subquery(None, course_member_id, course_content_id, db)
    latest_grading_sub = latest_grading_subquery(db)
    content_unread_sub = message_unread_by_content_subquery(reader_user_id, db)
    submission_group_unread_sub = message_unread_by_submission_group_subquery(reader_user_id, db)

    content_unread_column = (
        func.coalesce(content_unread_sub.c.unread_count, 0).label("content_unread_count")
        if content_unread_sub is not None
        else literal(0).label("content_unread_count")
    )
    submission_group_unread_column = (
        func.coalesce(submission_group_unread_sub.c.unread_count, 0).label("submission_group_unread_count")
        if submission_group_unread_sub is not None
        else literal(0).label("submission_group_unread_count")
    )

    course_contents_query = db.query(
        CourseContent,
        results_count_sub.c.total_results_count,
        Result,
        SubmissionGroup,
        submission_count_sub.c.submission_count,
        latest_grading_sub.c.status,
        latest_grading_sub.c.grading,
        content_unread_column,
        submission_group_unread_column,
    ) \
        .select_from(CourseMember) \
        .filter(CourseMember.id == course_member_id) \
        .join(SubmissionGroupMember, SubmissionGroupMember.course_member_id == CourseMember.id) \
        .join(SubmissionGroup, SubmissionGroup.id == SubmissionGroupMember.submission_group_id) \
        .join(CourseContent, (CourseContent.id == SubmissionGroup.course_content_id) & (CourseContent.id == course_content_id)) \
        .join(CourseContentKind, CourseContentKind.id == CourseContent.course_content_kind_id) \
        .outerjoin(
            latest_result_sub,
            CourseContent.id == latest_result_sub.c.course_content_id
        ).outerjoin(
            Result,
            (Result.course_content_id == latest_result_sub.c.course_content_id) &
            (Result.created_at == latest_result_sub.c.latest_result_date)
        ) \
        .outerjoin(
            results_count_sub,
            CourseContent.id == results_count_sub.c.course_content_id
        ).outerjoin(
            submission_count_sub,
            CourseContent.id == submission_count_sub.c.course_content_id
        ).outerjoin(
            latest_grading_sub,
            (latest_grading_sub.c.submission_group_id == SubmissionGroup.id)
            & (latest_grading_sub.c.rn == 1)
        )

    if content_unread_sub is not None:
        course_contents_query = course_contents_query.outerjoin(
            content_unread_sub,
            CourseContent.id == content_unread_sub.c.course_content_id,
        )

    if submission_group_unread_sub is not None:
        course_contents_query = course_contents_query.outerjoin(
            submission_group_unread_sub,
            SubmissionGroup.id == submission_group_unread_sub.c.submission_group_id,
        )

    course_contents_query = course_contents_query.options(
        # Use contains_eager for submission_groups since we already joined it
        contains_eager(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.members)
        .joinedload(SubmissionGroupMember.course_member)
        .joinedload(CourseMember.user),
        # Load submission groups with artifacts and their grades
        contains_eager(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.submission_artifacts)
        .joinedload(SubmissionArtifact.grades)
        .joinedload(SubmissionGrade.graded_by)
        .joinedload(CourseMember.user),
        # Load deployment information
        joinedload(CourseContent.deployment),
    )

    raw_result = course_contents_query.first()

    if raw_result is None:
        raise NotFoundException()

    # Convert tuple to typed model using class method
    return CourseMemberCourseContentQueryResult.from_tuple(raw_result)


def course_member_course_content_list_query(
    course_member_id: UUID | str,
    db: Session,
    reader_user_id: UUID | str | None = None
):
    """
    Get list of all course contents for a specific course member.

    Used for lecturer/tutor views to see student progress across all content.
    Includes submission groups, results, grades, and unread message counts.

    Args:
        course_member_id: The course member ID
        db: Database session
        reader_user_id: Optional user ID for unread message counts

    Returns:
        Query object that can be further filtered or executed
    """
    latest_result_sub = latest_result_subquery(None, course_member_id, None, db, True)
    results_count_sub = results_count_subquery(None, course_member_id, None, db)
    submission_count_sub = submission_count_subquery(None, course_member_id, None, db)
    latest_grading_sub = latest_grading_subquery(db)
    content_unread_sub = message_unread_by_content_subquery(reader_user_id, db)
    submission_group_unread_sub = message_unread_by_submission_group_subquery(reader_user_id, db)
    latest_submission_grade_sub = latest_submission_grade_status_subquery(db)

    content_unread_column = (
        func.coalesce(content_unread_sub.c.unread_count, 0).label("content_unread_count")
        if content_unread_sub is not None
        else literal(0).label("content_unread_count")
    )
    submission_group_unread_column = (
        func.coalesce(submission_group_unread_sub.c.unread_count, 0).label("submission_group_unread_count")
        if submission_group_unread_sub is not None
        else literal(0).label("submission_group_unread_count")
    )

    # Subquery to get the member's submission groups
    member_submission_groups = select(SubmissionGroup).select_from(
        SubmissionGroup
    ).join(
        SubmissionGroupMember,
        SubmissionGroup.id == SubmissionGroupMember.submission_group_id
    ).where(
        SubmissionGroupMember.course_member_id == course_member_id
    ).subquery()

    # Query ALL course contents for the course where the user is a member
    query = db.query(
        CourseContent,
        results_count_sub.c.total_results_count,
        Result,
        SubmissionGroup,
        submission_count_sub.c.submission_count,
        latest_grading_sub.c.status,
        latest_grading_sub.c.grading,
        content_unread_column,
        submission_group_unread_column,
        latest_submission_grade_sub.c.latest_grade_status,
        func.coalesce(latest_submission_grade_sub.c.is_unreviewed, 0).label("is_unreviewed"),
    ) \
        .select_from(CourseMember) \
        .filter(CourseMember.id == course_member_id) \
        .join(Course, Course.id == CourseMember.course_id) \
        .join(CourseContent, CourseContent.course_id == Course.id) \
        .join(CourseContentKind, CourseContentKind.id == CourseContent.course_content_kind_id) \
        .outerjoin(SubmissionGroup,
                   (SubmissionGroup.course_content_id == CourseContent.id) &
                   (SubmissionGroup.id.in_(select(member_submission_groups.c.id)))) \
        .outerjoin(
            latest_result_sub,
            CourseContent.id == latest_result_sub.c.course_content_id
        ).outerjoin(
            Result,
            (Result.course_content_id == latest_result_sub.c.course_content_id) &
            (Result.created_at == latest_result_sub.c.latest_result_date)
        ) \
        .outerjoin(
            results_count_sub,
            CourseContent.id == results_count_sub.c.course_content_id
        ).outerjoin(
            submission_count_sub,
            CourseContent.id == submission_count_sub.c.course_content_id
        ).outerjoin(
            latest_grading_sub,
            (latest_grading_sub.c.submission_group_id == SubmissionGroup.id)
            & (latest_grading_sub.c.rn == 1)
        ).outerjoin(
            latest_submission_grade_sub,
            latest_submission_grade_sub.c.submission_group_id == SubmissionGroup.id
        )

    if content_unread_sub is not None:
        query = query.outerjoin(
            content_unread_sub,
            CourseContent.id == content_unread_sub.c.course_content_id,
        )

    if submission_group_unread_sub is not None:
        query = query.outerjoin(
            submission_group_unread_sub,
            SubmissionGroup.id == submission_group_unread_sub.c.submission_group_id,
        )

    query = query.options(
        # Use contains_eager for submission_groups since we already joined it with a filter
        # This tells SQLAlchemy to use the already-joined data instead of loading all submission groups
        # Use subqueryload for nested relations to avoid row multiplication that breaks unread counts
        contains_eager(CourseContent.submission_groups)
        .subqueryload(SubmissionGroup.members)
        .joinedload(SubmissionGroupMember.course_member)
        .joinedload(CourseMember.user),
        contains_eager(CourseContent.submission_groups)
        .subqueryload(SubmissionGroup.submission_artifacts)
        .joinedload(SubmissionArtifact.grades)
        .joinedload(SubmissionGrade.graded_by)
        .joinedload(CourseMember.user),
        # Load deployment information
        joinedload(CourseContent.deployment),
    )

    return query


def course_course_member_list_query(db: Session):
    """
    Query to get course members with their latest submission result dates.

    Used for lecturer/tutor views to see student progress. Only includes results
    from official submissions (submit=True).

    Args:
        db: Database session

    Returns:
        Query object that returns tuples of (CourseMember, latest_result_date)
    """
    latest_result_subquery = db.query(
        Result.course_content_id,
        CourseMember.id.label("course_member_id"),
        func.max(Result.created_at).label("latest_result_date")
    ) \
        .join(SubmissionArtifact, SubmissionArtifact.id == Result.submission_artifact_id) \
        .join(SubmissionGroup, SubmissionGroup.id == Result.submission_group_id) \
        .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id) \
        .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id) \
        .filter(
            Result.status == 0,  # FINISHED status
            SubmissionArtifact.submit == True,  # Only official submissions
            Result.test_system_id.isnot(None)  # Only completed tests
        ) \
        .group_by(Result.course_content_id, CourseMember.id).subquery()

    latest_result_per_member = db.query(
        latest_result_subquery.c.course_member_id,
        func.max(latest_result_subquery.c.latest_result_date).label("latest_result_date")
    ) \
        .group_by(latest_result_subquery.c.course_member_id) \
        .subquery()

    course_member_results = db.query(
        CourseMember,
        latest_result_per_member.c.latest_result_date
    ) \
        .select_from(CourseMember) \
        .outerjoin(latest_result_per_member, latest_result_per_member.c.course_member_id == CourseMember.id)

    return course_member_results


def get_ungraded_submission_count_per_member(db: Session, course_id: Optional[str] = None):
    """
    Get count of ungraded latest submission artifacts per course member.

    For each course member, counts how many course contents have a latest submitted
    artifact that has NO associated submission_grade.

    Args:
        db: Database session
        course_id: Optional course ID to filter by

    Returns:
        Dictionary mapping course_member_id -> count of ungraded submissions
    """
    from sqlalchemy import func, and_
    from computor_backend.model.artifact import SubmissionArtifact, SubmissionGrade

    # Subquery to get the latest artifact per submission group
    latest_artifact_subquery = db.query(
        SubmissionArtifact.submission_group_id,
        func.max(SubmissionArtifact.created_at).label("latest_created_at")
    ).filter(
        SubmissionArtifact.submit == True  # Only submitted artifacts
    ).group_by(
        SubmissionArtifact.submission_group_id
    ).subquery()

    # Query to get latest artifacts with their submission group and course member info
    latest_artifacts_query = db.query(
        CourseMember.id.label("course_member_id"),
        SubmissionArtifact.id.label("artifact_id")
    ).select_from(SubmissionArtifact).join(
        latest_artifact_subquery,
        and_(
            SubmissionArtifact.submission_group_id == latest_artifact_subquery.c.submission_group_id,
            SubmissionArtifact.created_at == latest_artifact_subquery.c.latest_created_at
        )
    ).join(
        SubmissionGroup,
        SubmissionGroup.id == SubmissionArtifact.submission_group_id
    ).join(
        SubmissionGroupMember,
        SubmissionGroupMember.submission_group_id == SubmissionGroup.id
    ).join(
        CourseMember,
        CourseMember.id == SubmissionGroupMember.course_member_id
    ).filter(
        SubmissionArtifact.submit == True
    )

    # Filter by course if provided
    if course_id:
        latest_artifacts_query = latest_artifacts_query.filter(
            CourseMember.course_id == course_id
        )

    latest_artifacts = latest_artifacts_query.subquery()

    # Count artifacts that have NO grade
    ungraded_counts = db.query(
        latest_artifacts.c.course_member_id,
        func.count(latest_artifacts.c.artifact_id).label("ungraded_count")
    ).outerjoin(
        SubmissionGrade,
        SubmissionGrade.artifact_id == latest_artifacts.c.artifact_id
    ).filter(
        SubmissionGrade.id.is_(None)  # No grade exists
    ).group_by(
        latest_artifacts.c.course_member_id
    ).all()

    # Convert to dictionary
    return {str(row[0]): row[1] for row in ungraded_counts}


def get_unreviewed_submission_count_per_member(db: Session, course_id: Optional[str] = None):
    """
    Get count of unreviewed latest submission artifacts per course member.

    For each course member, counts how many course contents have a latest submitted
    artifact that is "unreviewed" - meaning either:
    1. It has NO associated submission_grade, OR
    2. Its latest submission_grade has status = 0 (NOT_REVIEWED)

    This differs from get_ungraded_submission_count_per_member which only counts
    artifacts with NO grades at all.

    Args:
        db: Database session
        course_id: Optional course ID to filter by

    Returns:
        Dictionary mapping course_member_id -> count of unreviewed submissions
    """
    from sqlalchemy import func, and_, or_
    from sqlalchemy.sql import expression
    from computor_backend.model.artifact import SubmissionArtifact, SubmissionGrade

    # Step 1: Get the latest artifact per submission group (submit=True)
    latest_artifact_subquery = db.query(
        SubmissionArtifact.submission_group_id,
        func.max(SubmissionArtifact.created_at).label("latest_created_at")
    ).filter(
        SubmissionArtifact.submit == True
    ).group_by(
        SubmissionArtifact.submission_group_id
    ).subquery()

    # Step 2: Get the actual latest artifact IDs with course_member mapping
    latest_artifacts_query = db.query(
        CourseMember.id.label("course_member_id"),
        SubmissionArtifact.id.label("artifact_id")
    ).select_from(SubmissionArtifact).join(
        latest_artifact_subquery,
        and_(
            SubmissionArtifact.submission_group_id == latest_artifact_subquery.c.submission_group_id,
            SubmissionArtifact.created_at == latest_artifact_subquery.c.latest_created_at
        )
    ).join(
        SubmissionGroup,
        SubmissionGroup.id == SubmissionArtifact.submission_group_id
    ).join(
        SubmissionGroupMember,
        SubmissionGroupMember.submission_group_id == SubmissionGroup.id
    ).join(
        CourseMember,
        CourseMember.id == SubmissionGroupMember.course_member_id
    ).filter(
        SubmissionArtifact.submit == True
    )

    if course_id:
        latest_artifacts_query = latest_artifacts_query.filter(
            CourseMember.course_id == course_id
        )

    latest_artifacts = latest_artifacts_query.subquery()

    # Step 3: For each artifact, get the latest grade's status (using window function)
    # We need to find artifacts where:
    # - No grades exist, OR
    # - The latest grade has status = 0

    # Subquery for latest grade status per artifact
    latest_grade_per_artifact = db.query(
        SubmissionGrade.artifact_id,
        SubmissionGrade.status.label("latest_grade_status"),
        func.row_number().over(
            partition_by=SubmissionGrade.artifact_id,
            order_by=SubmissionGrade.graded_at.desc()
        ).label("rn")
    ).subquery()

    # Get only the latest grade per artifact (rn = 1)
    latest_grade = db.query(
        latest_grade_per_artifact.c.artifact_id,
        latest_grade_per_artifact.c.latest_grade_status
    ).filter(
        latest_grade_per_artifact.c.rn == 1
    ).subquery()

    # Step 4: Count artifacts that are "unreviewed"
    # (no grades OR latest grade status = 0)
    unreviewed_counts = db.query(
        latest_artifacts.c.course_member_id,
        func.count(latest_artifacts.c.artifact_id).label("unreviewed_count")
    ).outerjoin(
        latest_grade,
        latest_grade.c.artifact_id == latest_artifacts.c.artifact_id
    ).filter(
        or_(
            latest_grade.c.artifact_id.is_(None),  # No grade exists
            latest_grade.c.latest_grade_status == 0  # Latest grade is NOT_REVIEWED
        )
    ).group_by(
        latest_artifacts.c.course_member_id
    ).all()

    return {str(row[0]): row[1] for row in unreviewed_counts}


def get_unread_message_count_per_member(db: Session, course_id: Optional[str] = None, reader_user_id: Optional[str] = None):
    """
    Get count of unread messages per course member.

    For each course member, counts messages in their submission groups that:
    1. Target a submission_group they belong to
    2. Have NOT been read by the reader_user_id (the tutor/viewer)
    3. Were not authored by the reader

    Args:
        db: Database session
        course_id: Optional course ID to filter by
        reader_user_id: The user ID of the person viewing (tutor). Messages unread by this user are counted.

    Returns:
        Dictionary mapping course_member_id -> count of unread messages
    """
    from sqlalchemy import func, and_
    from computor_backend.model.message import Message, MessageRead

    if reader_user_id is None:
        return {}

    # Base query: count messages per course_member via submission_group
    # where there's no MessageRead entry for that message by the reader (tutor)
    query = db.query(
        CourseMember.id.label("course_member_id"),
        func.count(Message.id).label("unread_count")
    ).select_from(CourseMember).join(
        SubmissionGroupMember,
        SubmissionGroupMember.course_member_id == CourseMember.id
    ).join(
        Message,
        Message.submission_group_id == SubmissionGroupMember.submission_group_id
    ).outerjoin(
        MessageRead,
        and_(
            MessageRead.message_id == Message.id,
            MessageRead.reader_user_id == reader_user_id
        )
    ).filter(
        MessageRead.id.is_(None),  # No read entry = unread by reader
        Message.archived_at.is_(None),  # Not deleted
        Message.author_id != reader_user_id  # Exclude reader's own messages
    )

    # Filter by course if provided
    if course_id:
        query = query.filter(CourseMember.course_id == course_id)

    query = query.group_by(CourseMember.id)

    results = query.all()

    # Convert to dictionary
    return {str(row[0]): row[1] for row in results}

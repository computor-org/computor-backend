from typing import Optional
from uuid import UUID
from sqlalchemy import func, case, select, and_, literal
from sqlalchemy.orm import Session, joinedload
from ctutor_backend.api.exceptions import NotFoundException
from ctutor_backend.model.course import SubmissionGroupMember
from ctutor_backend.model.result import Result
from ctutor_backend.model.auth import User
from ctutor_backend.model.course import Course, CourseContent, CourseContentKind, CourseMember, SubmissionGroup, SubmissionGroupGrading
from ctutor_backend.model.message import Message, MessageRead

def latest_result_subquery(user_id: UUID | str | None, course_member_id: UUID | str | None, course_content_id: UUID | str | None, db: Session, submission: Optional[bool] = None):

    query = db.query(
                Result.course_content_id,
                func.max(Result.created_at).label("latest_result_date")
            )
    
    if user_id != None:
        query = query.join(SubmissionGroup, SubmissionGroup.id == Result.submission_group_id) \
            .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id) \
            .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id) \
            .filter(CourseMember.user_id == user_id)
    elif course_member_id != None:
        query = query.join(SubmissionGroup, SubmissionGroup.id == Result.submission_group_id) \
            .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id) \
            .filter(SubmissionGroupMember.course_member_id == course_member_id)
    
    query = query.filter(Result.status == 0, Result.test_system_id.isnot(None))
    
    if course_content_id != None:
        query = query.filter(Result.course_content_id == course_content_id)
    
    if submission != None:
        query = query.filter(Result.submit == submission)
    
    return query.group_by(Result.course_content_id).subquery()

def results_count_subquery(user_id: UUID | str | None, course_member_id: UUID | str | None, course_content_id: UUID | str | None, db: Session):

    query = db.query(
                Result.course_content_id,
                func.count(case((Result.test_system_id.isnot(None), 1))).label("total_results_count"),
                func.count(case((Result.submit == True, 1))).label("submission_count"),
            )

    if user_id != None:
        query = query.join(SubmissionGroup, SubmissionGroup.id == Result.submission_group_id) \
            .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id) \
            .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id) \
            .filter(CourseMember.user_id == user_id)
    elif course_member_id != None:
        query = query.join(SubmissionGroup, SubmissionGroup.id == Result.submission_group_id) \
            .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id) \
            .filter(SubmissionGroupMember.course_member_id == course_member_id)

    query = query.filter(Result.status == 0)
    
    if course_content_id != None:
        query = query.filter(Result.course_content_id == course_content_id)
    
    return query.group_by(Result.course_content_id).subquery()

def latest_grading_subquery(db: Session):
    """
    Latest grading per submission group using window function with deterministic ordering.
    Returns columns: submission_group_id, status, grading, rn (rn=1 is latest).
    """
    return db.query(
        SubmissionGroupGrading.submission_group_id,
        SubmissionGroupGrading.status,
        SubmissionGroupGrading.grading,
        SubmissionGroupGrading.created_at,
        SubmissionGroupGrading.id,
        func.row_number().over(
            partition_by=SubmissionGroupGrading.submission_group_id,
            order_by=[
                SubmissionGroupGrading.created_at.desc(),
                SubmissionGroupGrading.id.desc(),
            ],
        ).label('rn')
    ).subquery()


def message_unread_by_content_subquery(reader_user_id: UUID | str | None, db: Session):
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

def user_course_content_query(user_id: UUID | str, course_content_id: UUID | str, db: Session):

    latest_result_sub = latest_result_subquery(user_id,None,course_content_id,db)
    results_count_sub = results_count_subquery(user_id,None,course_content_id,db)
    latest_grading_sub = latest_grading_subquery(db)
    content_unread_sub = message_unread_by_content_subquery(user_id, db)
    submission_group_unread_sub = message_unread_by_submission_group_subquery(user_id, db)

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
    # Use select() explicitly to avoid SQLAlchemy warning
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
        results_count_sub.c.submission_count,
        latest_grading_sub.c.status,
        latest_grading_sub.c.grading,
        content_unread_column,
        submission_group_unread_column,
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
        joinedload(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.gradings)
        .joinedload(SubmissionGroupGrading.graded_by)
        .joinedload(CourseMember.user),
        joinedload(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.gradings)
        .joinedload(SubmissionGroupGrading.graded_by)
        .joinedload(CourseMember.course_role),
        joinedload(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.members)
        .joinedload(SubmissionGroupMember.course_member)
        .joinedload(CourseMember.user),
    )

    course_contents_result = course_contents_query.distinct().first()
        
    if course_contents_result == None:
        raise NotFoundException()

    return course_contents_result

def user_course_content_list_query(user_id: UUID | str, db: Session):

    latest_result_sub = latest_result_subquery(user_id,None,None,db)
    results_count_sub = results_count_subquery(user_id,None,None,db)
    latest_grading_sub = latest_grading_subquery(db)
    content_unread_sub = message_unread_by_content_subquery(user_id, db)
    submission_group_unread_sub = message_unread_by_submission_group_subquery(user_id, db)

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
    # Use select() explicitly to avoid SQLAlchemy warning
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
        results_count_sub.c.submission_count,
        latest_grading_sub.c.status,
        latest_grading_sub.c.grading,
        content_unread_column,
        submission_group_unread_column,
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
            latest_grading_sub,
            (latest_grading_sub.c.submission_group_id == SubmissionGroup.id)
            & (latest_grading_sub.c.rn == 1)
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
        joinedload(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.gradings)
        .joinedload(SubmissionGroupGrading.graded_by)
        .joinedload(CourseMember.user),
        joinedload(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.gradings)
        .joinedload(SubmissionGroupGrading.graded_by)
        .joinedload(CourseMember.course_role),
        joinedload(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.members)
        .joinedload(SubmissionGroupMember.course_member)
        .joinedload(CourseMember.user),
    )

    query = query.distinct()

    return query

def course_member_course_content_query(course_member_id: UUID | str, course_content_id: UUID | str, db: Session, reader_user_id: UUID | str | None = None):

    latest_result_sub = latest_result_subquery(None,course_member_id,course_content_id,db)
    results_count_sub = results_count_subquery(None,course_member_id,course_content_id,db)
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
            results_count_sub.c.submission_count,
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
        joinedload(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.gradings)
        .joinedload(SubmissionGroupGrading.graded_by)
        .joinedload(CourseMember.user),
        joinedload(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.gradings)
        .joinedload(SubmissionGroupGrading.graded_by)
        .joinedload(CourseMember.course_role),
        joinedload(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.members)
        .joinedload(SubmissionGroupMember.course_member)
        .joinedload(CourseMember.user),
    )

    course_contents_result = course_contents_query.first()
        
    if course_contents_result == None:
        raise NotFoundException()

    return course_contents_result

def course_member_course_content_list_query(course_member_id: UUID | str, db: Session, reader_user_id: UUID | str | None = None):

    latest_result_sub = latest_result_subquery(None,course_member_id,None,db,True)
    results_count_sub = results_count_subquery(None,course_member_id,None,db)
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
            results_count_sub.c.submission_count,
            latest_grading_sub.c.status,
            latest_grading_sub.c.grading,
            content_unread_column,
            submission_group_unread_column,
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
            latest_grading_sub,
            (latest_grading_sub.c.submission_group_id == SubmissionGroup.id)
            & (latest_grading_sub.c.rn == 1)
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
        joinedload(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.gradings)
        .joinedload(SubmissionGroupGrading.graded_by)
        .joinedload(CourseMember.user),
        joinedload(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.gradings)
        .joinedload(SubmissionGroupGrading.graded_by)
        .joinedload(CourseMember.course_role),
        joinedload(CourseContent.submission_groups)
        .joinedload(SubmissionGroup.members)
        .joinedload(SubmissionGroupMember.course_member)
        .joinedload(CourseMember.user),
    )

    return query

def course_course_member_list_query(db: Session):

    latest_result_subquery =  db.query(
                    Result.course_content_id,
                    CourseMember.id.label("course_member_id"),
                    func.max(Result.created_at).label("latest_result_date")
                ) \
        .join(SubmissionGroup, SubmissionGroup.id == Result.submission_group_id) \
        .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id) \
        .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id) \
        .filter(
                Result.status == 0,
                Result.submit == True
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
        .outerjoin(latest_result_per_member,latest_result_per_member.c.course_member_id == CourseMember.id)

    return course_member_results

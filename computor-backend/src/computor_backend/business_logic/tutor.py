"""Business logic for tutor-specific operations."""
import logging
from uuid import UUID
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, contains_eager, joinedload, selectinload
from sqlalchemy.orm.attributes import set_committed_value

from computor_backend.business_logic.submission_limits import resolve_limits
from computor_backend.exceptions import BadRequestException, ForbiddenException, NotFoundException
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal, allowed_course_role_ids
from computor_backend.cache import Cache
from computor_backend.repositories.tutor_view import TutorViewRepository
from computor_backend.repositories.course_member import CourseMemberRepository
from computor_backend.repositories.submission_group import SubmissionGroupRepository
from computor_backend.repositories.submission_artifact import SubmissionArtifactRepository
from computor_backend.repositories.submission_grade_repo import SubmissionGradeRepository
from computor_backend.repositories.course_content_queries import (
    course_course_member_list_query,
    course_member_course_content_list_query,
    course_member_course_content_query,
    get_unread_message_count_per_member,
    get_unreviewed_submission_count_per_member,
)
from computor_backend.repositories.view_mappers import course_member_course_content_result_mapper
from computor_backend.model.auth import User
from computor_backend.model.course import Course, CourseMember, SubmissionGroup, SubmissionGroupMember
from computor_backend.model.artifact import SubmissionArtifact, SubmissionGrade
from computor_types.student_courses import CourseStudentQuery
from computor_types.student_course_contents import CourseContentStudentQuery
from computor_types.course_members import CourseMemberQuery
from computor_backend.interfaces.course_member import CourseMemberInterface
from computor_types.tutor_courses import CourseTutorGet, CourseTutorList
from computor_types.tutor_course_members import TutorCourseMemberCourseContent, TutorCourseMemberGet, TutorCourseMemberList
from computor_types.grading import GradingStatus
from computor_types.tutor_grading import TutorGradeResponse, GradedArtifactInfo
from computor_types.tutor_submission_groups import (
    TutorSubmissionGroupList,
    TutorSubmissionGroupGet,
    TutorSubmissionGroupQuery,
    TutorSubmissionGroupMember,
)

logger = logging.getLogger(__name__)


def _effective_max_test_runs(submission_group) -> Optional[int]:
    """Test-run budget a tutor should see: group override, else inherited."""
    max_test_runs, _ = resolve_limits(
        submission_group.course_content, submission_group
    )
    return max_test_runs


def _effective_max_submissions(submission_group) -> Optional[int]:
    """Submission budget a tutor should see: group override, else inherited."""
    _, max_submissions = resolve_limits(
        submission_group.course_content, submission_group
    )
    return max_submissions


async def get_tutor_course_content(
    course_member_id: UUID | str,
    course_content_id: UUID | str,
    permissions: Principal,
    cache: Optional[Cache] = None,
):
    """Get course content for a course member as a tutor with caching via repository."""
    repo = TutorViewRepository(cache=cache, user_id=permissions.get_user_id_or_throw())
    try:
        return await repo.get_course_content(course_member_id, course_content_id, permissions)
    finally:
        repo.close()


async def list_tutor_course_contents(
    course_member_id: UUID | str,
    permissions: Principal,
    params: CourseContentStudentQuery,
    cache: Optional[Cache] = None,
):
    """List course contents for a course member as a tutor with caching via repository."""
    repo = TutorViewRepository(cache=cache, user_id=permissions.get_user_id_or_throw())
    try:
        return await repo.list_course_contents(course_member_id, permissions, params)
    finally:
        repo.close()


async def update_tutor_course_content_grade(
    course_member_id: UUID | str,
    course_content_id: UUID | str,
    grade_value: Optional[float],
    grading_status: Optional[GradingStatus],
    feedback: Optional[str],
    artifact_id: Optional[UUID | str],
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
) -> TutorGradeResponse:
    """Update grade for a course content as a tutor.

    Args:
        course_member_id: The course member (student) to grade
        course_content_id: The course content being graded
        grade_value: The grade value (0.0 to 1.0)
        grading_status: The grading status
        feedback: Optional feedback comment
        artifact_id: Optional specific artifact to grade (defaults to latest)
        permissions: Current user permissions
        db: Database session
        cache: Optional cache instance

    Returns:
        TutorGradeResponse with updated course content and graded artifact info
    """

    # Initialize repositories with cache
    course_member_repo = CourseMemberRepository(db, cache)
    submission_group_repo = SubmissionGroupRepository(db, cache)
    submission_artifact_repo = SubmissionArtifactRepository(db, cache)
    submission_grade_repo = SubmissionGradeRepository(db, cache)

    # 1) Resolve the student's course member and related submission group for this content
    student_cm = course_member_repo.get_by_id_optional(course_member_id)
    if student_cm is None:
        raise NotFoundException(
            detail="Course member not found",
            context={"course_member_id": str(course_member_id)},
        )

    # Check if current user has tutor permissions for the student's course
    if check_course_permissions(permissions, CourseMember, "_tutor", db).filter(
        CourseMember.course_id == student_cm.course_id,
        CourseMember.user_id == permissions.get_user_id_or_throw()
    ).first() is None:
        raise ForbiddenException()

    # Find submission group for this course member and content
    # Query directly to ensure members are loaded
    from sqlalchemy.orm import joinedload
    submission_group = db.query(SubmissionGroup).options(
        joinedload(SubmissionGroup.members)
    ).join(
        SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id
    ).filter(
        SubmissionGroup.course_content_id == course_content_id,
        SubmissionGroupMember.course_member_id == course_member_id
    ).first()

    if submission_group is None:
        raise NotFoundException(
            detail="No submission group found for the requested course member and content. "
                   "The student may not have been assigned to this content yet.",
            context={
                "course_member_id": str(course_member_id),
                "course_content_id": str(course_content_id),
            },
        )

    # 2) Resolve the grader's course member (the current user in the same course)
    grader_cm = course_member_repo.find_by_course_and_user(
        course_id=student_cm.course_id,
        user_id=permissions.get_user_id_or_throw()
    )
    if grader_cm is None:
        raise ForbiddenException()

    # 3) Determine which artifact to grade
    if artifact_id:
        # Specific artifact requested - verify it belongs to this submission group
        artifact_to_grade = submission_artifact_repo.get_by_id_optional(artifact_id)
        if artifact_to_grade is None or str(artifact_to_grade.submission_group_id) != str(submission_group.id):
            raise NotFoundException(detail="Specified artifact not found or doesn't belong to this submission group")
    else:
        # Get the latest submission artifact for this submission group
        artifacts = submission_artifact_repo.find_by_submission_group(submission_group.id)
        if not artifacts:
            raise NotFoundException(detail="No submission artifact found for this submission group. Student must submit first.")
        artifact_to_grade = max(artifacts, key=lambda a: a.created_at)

    # 4) Get grading status
    status = grading_status if grading_status is not None else GradingStatus.NOT_REVIEWED

    # 5) Create a new artifact-based grade
    if grade_value is not None or grading_status is not None:
        grade = grade_value if grade_value is not None else 0.0

        new_grading = SubmissionGrade(
            artifact_id=artifact_to_grade.id,
            graded_by_course_member_id=grader_cm.id,
            grade=grade,
            status=status.value,
            comment=feedback,
        )
        # Use repository to ensure cache invalidation
        submission_grade_repo.create(new_grading)

        logger.info(f"Created grade for artifact {artifact_to_grade.id} by grader {grader_cm.id}")

        # CRITICAL: Invalidate student view cache so students see the new grade
        if cache:
            # Invalidate student view for this course (tagged in StudentViewRepository)
            cache.invalidate_tags(f"student_view:{student_cm.course_id}")
            # Also invalidate tutor/lecturer views
            cache.invalidate_tags(f"tutor_view:{student_cm.course_id}")
            cache.invalidate_tags(f"lecturer_view:{student_cm.course_id}")
            logger.info(f"Invalidated view caches for course {student_cm.course_id} after grading")

    # 6) Return fresh data
    reader_user_id = permissions.get_user_id_or_throw()
    course_contents_result = course_member_course_content_query(
        course_member_id, course_content_id, db, reader_user_id=reader_user_id
    )

    response = await course_member_course_content_result_mapper(course_contents_result, db)

    # Build typed artifact info
    # Handle created_at - it might be a datetime or already a string (from cache)
    created_at_str = None
    if artifact_to_grade.created_at:
        if isinstance(artifact_to_grade.created_at, str):
            created_at_str = artifact_to_grade.created_at
        else:
            created_at_str = artifact_to_grade.created_at.isoformat()

    artifact_info = GradedArtifactInfo(
        id=str(artifact_to_grade.id),
        created_at=created_at_str,
        properties=artifact_to_grade.properties,
    )

    # Return typed TutorGradeResponse
    return TutorGradeResponse(
        **response.model_dump(),
        graded_artifact_id=str(artifact_to_grade.id),
        graded_artifact_info=artifact_info,
    )


def get_tutor_course(
    course_id: UUID | str,
    permissions: Principal,
    cache: Optional[Cache] = None,
) -> CourseTutorGet:
    """Get a course for tutors with caching via repository."""
    repo = TutorViewRepository(cache=cache, user_id=permissions.get_user_id_or_throw())
    try:
        return repo.get_course(course_id, permissions)
    finally:
        repo.close()


def list_tutor_courses(
    permissions: Principal,
    params: CourseStudentQuery,
    cache: Optional[Cache] = None,
) -> List[CourseTutorList]:
    """List courses for tutors with caching via repository."""
    repo = TutorViewRepository(cache=cache, user_id=permissions.get_user_id_or_throw())
    try:
        return repo.list_courses(permissions, params)
    finally:
        repo.close()


def get_tutor_course_member(
    course_member_id: UUID | str,
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
) -> TutorCourseMemberGet:
    """Get a course member with unreviewed course contents."""

    course_member = check_course_permissions(permissions, CourseMember, "_tutor", db).options(
        joinedload(CourseMember.user)
    ).filter(
        CourseMember.id == course_member_id
    ).first()

    if course_member is None:
        raise NotFoundException(
            detail="Course member not found",
            context={"course_member_id": str(course_member_id)},
        )

    reader_user_id = permissions.get_user_id_or_throw()
    course_contents_results = course_member_course_content_list_query(course_member_id, db, reader_user_id=reader_user_id).all()

    response_list = []

    for course_contents_result in course_contents_results:
        query = course_contents_result
        course_content = query[0]
        result = query[2]

        if result is not None:
            # Get submit field from associated SubmissionArtifact
            submit = False
            if result.submission_artifact:
                submit = result.submission_artifact.submit
            status = result.status

            todo = True if submit is True and status is None else False
            if todo is True:
                response_list.append(TutorCourseMemberCourseContent(id=course_content.id, path=str(course_content.path)))

    tutor_course_member = TutorCourseMemberGet.model_validate(course_member, from_attributes=True)
    tutor_course_member.unreviewed_course_contents = response_list

    return tutor_course_member


def list_tutor_course_members(
    permissions: Principal,
    params: CourseMemberQuery,
    db: Session,
    cache: Optional[Cache] = None,
) -> List[TutorCourseMemberList]:
    """List course members for tutors."""

    reader_user_id = str(permissions.get_user_id_or_throw())
    course_id = params.course_id if params and hasattr(params, 'course_id') else None

    # Require course_id: the endpoint answers "who are the members of this course
    # through a tutor lens". Without a course there is no natural scope — the query
    # would otherwise fall back to a global aggregation across every course.
    if course_id is None:
        raise BadRequestException(detail="'course_id' query parameter is required")

    # Cache-first: mirror TutorViewRepository's query-view caching so the heavy
    # aggregations below only run on miss. The grading flow already invalidates
    # the `tutor_view:{course_id}` tag on new grades, so stale data self-heals.
    view_repo = TutorViewRepository(cache=cache, user_id=reader_user_id)
    cached = view_repo._get_cached_query_view(
        user_id=reader_user_id,
        view_type="tutor:course_members",
        params=params,
    )
    if cached is not None:
        return [TutorCourseMemberList.model_validate(item) for item in cached]

    # Left as a subquery rather than ``.all()``-ed into a Python list: the ids
    # only ever feed the IN below, and materialising them meant a round trip
    # plus a bind parameter per accessible course.
    tutor_course_ids = db.query(Course.id).select_from(User).filter(User.id == permissions.get_user_id_or_throw()) \
        .join(CourseMember, CourseMember.user_id == User.id) \
        .join(Course, Course.id == CourseMember.course_id) \
        .filter(CourseMember.course_role_id.in_((allowed_course_role_ids("_tutor")))).subquery()

    query = course_course_member_list_query(db, course_id=course_id)
    query = query.join(User, User.id == CourseMember.user_id)
    query = query.options(contains_eager(CourseMember.user))
    query = CourseMemberInterface.search(db, query, params)

    if not permissions.is_admin:
        query = query.join(Course, Course.id == CourseMember.course_id).filter(
            Course.id.in_(select(tutor_course_ids.c.id))
        )

    query = query.order_by(User.family_name)

    # Apply pagination only when the caller explicitly sets skip/limit,
    # so the default "return all members for a course" behaviour is preserved.
    fields_set = getattr(params, '__pydantic_fields_set__', set()) if params else set()
    if 'limit' in fields_set or 'skip' in fields_set:
        query = query.offset(params.skip or 0).limit(params.limit)

    query = query.all()

    # Restrict the count aggregations to the exact members we're about to return.
    # This turns a course-wide scan into a pruned lookup (matters a lot when a tutor
    # filters by course_group_id, or for admins viewing a slice of members).
    member_ids = [cm.id for cm, _ in query]

    # Get unreviewed submission counts for course members
    # "unreviewed" = latest submission has no grades OR latest grade has status = NOT_REVIEWED
    unreviewed_counts = get_unreviewed_submission_count_per_member(
        db, course_id, course_member_ids=member_ids
    )
    unread_message_counts = get_unread_message_count_per_member(
        db, course_id, reader_user_id, course_member_ids=member_ids
    )

    response_list = []

    for course_member, latest_result_date in query:
        tutor_course_member = TutorCourseMemberList.model_validate(course_member, from_attributes=True)
        tutor_course_member.unreviewed = True if latest_result_date is not None else False
        tutor_course_member.ungraded_submissions_count = unreviewed_counts.get(str(course_member.id), 0)
        tutor_course_member.unread_message_count = unread_message_counts.get(str(course_member.id), 0)
        response_list.append(tutor_course_member)

    # Tag with `tutor_view:{course_id}` so existing grade-invalidation hooks clear
    # this entry when a grade is updated (see update_tutor_course_content_grade).
    related_ids: dict = {}
    if course_id:
        related_ids['tutor_view'] = str(course_id)
    view_repo._set_cached_query_view(
        user_id=reader_user_id,
        view_type="tutor:course_members",
        params=params,
        data=view_repo._serialize_dto_list(response_list),
        ttl=view_repo.get_default_ttl(),
        related_ids=related_ids or None,
    )

    return response_list


def get_tutor_submission_group(
    submission_group_id: UUID | str,
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
) -> TutorSubmissionGroupGet:
    """Get a submission group with detailed information for tutors.

    Args:
        submission_group_id: ID of the submission group
        permissions: Current user permissions
        db: Database session
        cache: Optional cache instance

    Returns:
        TutorSubmissionGroupGet with members and statistics
    """
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func

    submission_group_repo = SubmissionGroupRepository(db, cache)
    submission_artifact_repo = SubmissionArtifactRepository(db, cache)
    submission_grade_repo = SubmissionGradeRepository(db, cache)

    # Get submission group with members loaded
    submission_group = db.query(SubmissionGroup).options(
        joinedload(SubmissionGroup.members).joinedload(SubmissionGroupMember.course_member).joinedload(CourseMember.user)
    ).filter(SubmissionGroup.id == submission_group_id).first()

    if submission_group is None:
        raise NotFoundException(
            detail="Submission group not found",
            context={"submission_group_id": str(submission_group_id)},
        )

    # Check tutor permissions for the course
    if check_course_permissions(permissions, CourseMember, "_tutor", db).filter(
        CourseMember.course_id == submission_group.course_id,
        CourseMember.user_id == permissions.get_user_id_or_throw()
    ).first() is None:
        raise ForbiddenException()

    # Get submission artifacts for statistics
    artifacts = submission_artifact_repo.find_by_submission_group(submission_group.id)

    # Separate submitted artifacts from test runs
    submitted_artifacts = [a for a in artifacts if a.submit]
    test_run_artifacts = [a for a in artifacts if not a.submit]

    # Get latest submission
    latest_submission = max(submitted_artifacts, key=lambda a: a.created_at) if submitted_artifacts else None

    # Get grading information
    graded_artifact_count = 0
    grades = []
    has_ungraded = False

    for artifact in submitted_artifacts:
        artifact_grades = submission_grade_repo.find_by_artifact(artifact.id)
        if artifact_grades:
            graded_artifact_count += 1
            latest_grade = max(artifact_grades, key=lambda g: g.created_at)
            if latest_grade.grade is not None:
                grades.append(latest_grade.grade)
        else:
            has_ungraded = True

    # Calculate grade statistics
    latest_grade = grades[-1] if grades else None
    average_grade = sum(grades) / len(grades) if grades else None

    # Build member list
    members = []
    for member in submission_group.members:
        if member.course_member and member.course_member.user:
            user = member.course_member.user
            members.append(TutorSubmissionGroupMember(
                id=str(member.id),
                course_member_id=str(member.course_member_id),
                user_id=str(user.id),
                given_name=user.given_name,
                family_name=user.family_name,
                email=user.email,
            ))

    # Determine display name
    display_name = submission_group.display_name
    if not display_name:
        display_name = submission_group.get_computed_display_name()

    return TutorSubmissionGroupGet(
        id=str(submission_group.id),
        course_id=str(submission_group.course_id),
        course_content_id=str(submission_group.course_content_id),
        display_name=display_name,
        max_group_size=submission_group.max_group_size,
        max_submissions=_effective_max_submissions(submission_group),
        max_test_runs=_effective_max_test_runs(submission_group),
        properties=submission_group.properties,
        members=members,
        member_count=len(members),
        submission_count=len(submitted_artifacts),
        test_run_count=len(test_run_artifacts),
        latest_submission_at=latest_submission.created_at if latest_submission else None,
        latest_submission_id=str(latest_submission.id) if latest_submission else None,
        has_ungraded_submissions=has_ungraded,
        graded_submission_count=graded_artifact_count,
        latest_grade=latest_grade,
        average_grade=average_grade,
        created_at=submission_group.created_at,
        updated_at=submission_group.updated_at,
    )


def _submission_stats_for_groups(group_ids, db: Session) -> dict:
    """``submission_group_id -> (submitted count, latest submitted at)``.

    Counted in SQL rather than by loading every artifact and measuring the
    list: the listing only ever shows the number and the timestamp.
    """
    if not group_ids:
        return {}

    from sqlalchemy import func

    rows = (
        db.query(
            SubmissionArtifact.submission_group_id,
            func.count(SubmissionArtifact.id),
            func.max(SubmissionArtifact.created_at),
        )
        .filter(
            SubmissionArtifact.submission_group_id.in_(group_ids),
            SubmissionArtifact.submit == True,  # noqa: E712 — SQLAlchemy column comparison
        )
        .group_by(SubmissionArtifact.submission_group_id)
        .all()
    )
    return {group_id: (count, latest) for group_id, count, latest in rows}


def _groups_with_ungraded_submissions(group_ids, db: Session) -> set:
    """The subset of ``group_ids`` holding a submitted artifact with no grade.

    One NOT EXISTS over the page instead of a grade lookup per artifact; the
    answer is a yes/no per group, so no grade rows need to come back at all.
    """
    if not group_ids:
        return set()

    from sqlalchemy import exists, and_

    rows = (
        db.query(SubmissionArtifact.submission_group_id)
        .filter(
            SubmissionArtifact.submission_group_id.in_(group_ids),
            SubmissionArtifact.submit == True,  # noqa: E712 — SQLAlchemy column comparison
            ~exists().where(SubmissionGrade.artifact_id == SubmissionArtifact.id),
        )
        .distinct()
        .all()
    )
    return {group_id for (group_id,) in rows}


def _members_for_groups(group_ids, db: Session) -> dict:
    """``submission_group_id -> [SubmissionGroupMember]`` for the display name.

    Only called for the groups that have no stored ``display_name``, since
    that is the only thing the members are needed for here.
    """
    if not group_ids:
        return {}

    members = (
        db.query(SubmissionGroupMember)
        .options(
            joinedload(SubmissionGroupMember.course_member).joinedload(CourseMember.user)
        )
        .filter(SubmissionGroupMember.submission_group_id.in_(group_ids))
        .all()
    )

    by_group: dict = {}
    for member in members:
        by_group.setdefault(member.submission_group_id, []).append(member)
    return by_group


def list_tutor_submission_groups(
    permissions: Principal,
    params: TutorSubmissionGroupQuery,
    db: Session,
    cache: Optional[Cache] = None,
) -> List[TutorSubmissionGroupList]:
    """List submission groups for tutors with filtering.

    Args:
        permissions: Current user permissions
        params: Query parameters for filtering
        db: Database session
        cache: Optional cache instance

    Returns:
        List of TutorSubmissionGroupList
    """
    from sqlalchemy import func, exists, and_
    from sqlalchemy.orm import joinedload

    # Require course_id: tutor/lecturer/student views always operate within a single
    # course context. Without a course filter the query scans every submission group
    # a tutor has access to — unbounded for admins.
    if not params.course_id:
        raise BadRequestException(detail="'course_id' query parameter is required")

    # Get courses where user is a tutor
    tutor_course_ids = db.query(Course.id).select_from(User).filter(
        User.id == permissions.get_user_id_or_throw()
    ).join(
        CourseMember, CourseMember.user_id == User.id
    ).join(
        Course, Course.id == CourseMember.course_id
    ).filter(
        CourseMember.course_role_id.in_(allowed_course_role_ids("_tutor"))
    ).subquery()

    # Base query with member count, excluding archived course content
    from computor_backend.model.course import CourseContent
    query = db.query(
        SubmissionGroup,
        func.count(SubmissionGroupMember.id).label('member_count')
    ).join(
        CourseContent, CourseContent.id == SubmissionGroup.course_content_id
    ).filter(
        CourseContent.archived_at.is_(None)
    ).outerjoin(
        SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id
    ).group_by(SubmissionGroup.id).options(
        # _effective_max_submissions / _effective_max_test_runs walk
        # group -> content -> course for every row. selectinload, not
        # contains_eager: this query aggregates with GROUP BY SubmissionGroup.id,
        # so widening its select list would mean widening the GROUP BY too.
        selectinload(SubmissionGroup.course_content).selectinload(CourseContent.course)
    )

    # Filter by tutor's courses (unless admin)
    if not permissions.is_admin:
        query = query.filter(SubmissionGroup.course_id.in_(select(tutor_course_ids.c.id)))

    # Apply filters from params
    if params.course_id:
        query = query.filter(SubmissionGroup.course_id == params.course_id)

    if params.course_content_id:
        query = query.filter(SubmissionGroup.course_content_id == params.course_content_id)

    if params.course_group_id:
        # Filter by course_group_id through CourseMember relationship
        query = query.join(
            CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id
        ).filter(CourseMember.course_group_id == params.course_group_id)

    if params.has_submissions is not None:
        if params.has_submissions:
            # Has at least one submitted artifact
            query = query.filter(
                exists().where(
                    and_(
                        SubmissionArtifact.submission_group_id == SubmissionGroup.id,
                        SubmissionArtifact.submit == True
                    )
                )
            )
        else:
            # Has no submitted artifacts
            query = query.filter(
                ~exists().where(
                    and_(
                        SubmissionArtifact.submission_group_id == SubmissionGroup.id,
                        SubmissionArtifact.submit == True
                    )
                )
            )

    if params.has_ungraded_submissions is not None:
        # Decided in SQL, not after paginating. This filter used to run in the
        # loop below with a ``continue``, which drops rows the database already
        # counted towards LIMIT: a page came back short, and the groups that
        # fell off the end of it were unreachable by paging further.
        has_ungraded = exists().where(
            and_(
                SubmissionArtifact.submission_group_id == SubmissionGroup.id,
                SubmissionArtifact.submit == True,
                ~exists().where(SubmissionGrade.artifact_id == SubmissionArtifact.id),
            )
        )
        query = query.filter(
            has_ungraded if params.has_ungraded_submissions else ~has_ungraded
        )

    # Apply pagination. The tiebreaker makes paging stable: without an ORDER BY
    # the database is free to hand back page 2 in a different order than it
    # ordered page 1 from, which repeats rows and hides others.
    query = query.order_by(SubmissionGroup.id)
    query = query.offset(params.offset).limit(params.limit)

    results = query.all()

    # Everything the loop below needs, fetched for the whole page at once.
    #
    # It used to fetch per group: the artifacts, then one grade lookup per
    # submitted artifact, then the members. A page of 100 groups issued over
    # 350 statements to render 100 rows.
    group_ids = [submission_group.id for submission_group, _ in results]
    submission_stats = _submission_stats_for_groups(group_ids, db)
    ungraded_group_ids = _groups_with_ungraded_submissions(group_ids, db)
    members_by_group = _members_for_groups(
        [submission_group.id for submission_group, _ in results
         if not submission_group.display_name],
        db,
    )

    # Build response list with additional statistics
    response_list = []

    for submission_group, member_count in results:
        submission_count, latest_submission_at = submission_stats.get(
            submission_group.id, (0, None)
        )
        has_ungraded = submission_group.id in ungraded_group_ids

        # Determine display name
        display_name = submission_group.display_name
        if not display_name:
            # set_committed_value, not plain assignment: assigning to a loaded
            # instance's relationship makes SQLAlchemy read the current
            # collection first so it can record the change — one query per
            # group, exactly what the batch above set out to avoid.
            set_committed_value(
                submission_group, "members", members_by_group.get(submission_group.id, [])
            )
            display_name = submission_group.get_computed_display_name()

        response_list.append(TutorSubmissionGroupList(
            id=str(submission_group.id),
            course_id=str(submission_group.course_id),
            course_content_id=str(submission_group.course_content_id),
            display_name=display_name,
            max_group_size=submission_group.max_group_size,
            max_submissions=_effective_max_submissions(submission_group),
            max_test_runs=_effective_max_test_runs(submission_group),
            member_count=member_count,
            submission_count=submission_count,
            latest_submission_at=latest_submission_at,
            has_ungraded_submissions=has_ungraded,
            created_at=submission_group.created_at,
            updated_at=submission_group.updated_at,
        ))

    return response_list

"""Business logic for tutor-specific operations."""
import logging
from uuid import UUID
from typing import List, Optional

from sqlalchemy.orm import Session

from computor_backend.api.exceptions import ForbiddenException, NotFoundException
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal, allowed_course_role_ids
from computor_backend.cache import Cache
from computor_backend.repositories.tutor_view import TutorViewRepository
from computor_backend.repositories.course_member import CourseMemberRepository
from computor_backend.repositories.submission_group import SubmissionGroupRepository
from computor_backend.repositories.submission_artifact import SubmissionArtifactRepository
from computor_backend.repositories.submission_grade_repo import SubmissionGradeRepository
from computor_backend.repositories.course_content import (
    course_course_member_list_query,
    course_member_course_content_list_query,
    course_member_course_content_query,
    get_ungraded_submission_count_per_member,
)
from computor_backend.api.mappers import course_member_course_content_result_mapper
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


def get_tutor_course_content(
    course_member_id: UUID | str,
    course_content_id: UUID | str,
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
):
    """Get course content for a course member as a tutor with caching via repository."""
    repo = TutorViewRepository(db, cache)
    return repo.get_course_content(course_member_id, course_content_id, permissions)


def list_tutor_course_contents(
    course_member_id: UUID | str,
    permissions: Principal,
    params: CourseContentStudentQuery,
    db: Session,
    cache: Optional[Cache] = None,
):
    """List course contents for a course member as a tutor with caching via repository."""
    repo = TutorViewRepository(db, cache)
    return repo.list_course_contents(course_member_id, permissions, params)


def update_tutor_course_content_grade(
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
        raise NotFoundException(detail=f"Course member {course_member_id} not found")

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
        raise NotFoundException(detail=f"No submission group found for course member {course_member_id} in course content {course_content_id}. The student may not have been assigned to this content yet.")

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

    response = course_member_course_content_result_mapper(course_contents_result, db)

    # Build typed artifact info
    artifact_info = GradedArtifactInfo(
        id=str(artifact_to_grade.id),
        created_at=artifact_to_grade.created_at.isoformat() if artifact_to_grade.created_at else None,
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
    db: Session,
    cache: Optional[Cache] = None,
) -> CourseTutorGet:
    """Get a course for tutors with caching via repository."""
    repo = TutorViewRepository(db, cache)
    return repo.get_course(course_id, permissions)


def list_tutor_courses(
    permissions: Principal,
    params: CourseStudentQuery,
    db: Session,
    cache: Optional[Cache] = None,
) -> List[CourseTutorList]:
    """List courses for tutors with caching via repository."""
    repo = TutorViewRepository(db, cache)
    return repo.list_courses(permissions, params)


def get_tutor_course_member(
    course_member_id: UUID | str,
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
) -> TutorCourseMemberGet:
    """Get a course member with unreviewed course contents."""

    course_member = check_course_permissions(permissions, CourseMember, "_tutor", db).filter(
        CourseMember.id == course_member_id
    ).first()

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

    subquery = db.query(Course.id).select_from(User).filter(User.id == permissions.get_user_id_or_throw()) \
        .join(CourseMember, CourseMember.user_id == User.id) \
        .join(Course, Course.id == CourseMember.course_id) \
        .filter(CourseMember.course_role_id.in_((allowed_course_role_ids("_tutor")))).all()

    query = course_course_member_list_query(db)
    query = CourseMemberInterface.search(db, query, params)

    if permissions.is_admin != True:
        query = query.join(Course, Course.id == CourseMember.course_id).filter(
            Course.id.in_([r.id for r in subquery])
        ).join(User, User.id == CourseMember.user_id).order_by(User.family_name).all()

    # Get ungraded submission counts for course members
    # Extract course_id from params if available
    course_id = params.course_id if params and hasattr(params, 'course_id') else None
    ungraded_counts = get_ungraded_submission_count_per_member(db, course_id)

    response_list = []

    for course_member, latest_result_date in query:
        tutor_course_member = TutorCourseMemberList.model_validate(course_member, from_attributes=True)
        tutor_course_member.unreviewed = True if latest_result_date is not None else False
        tutor_course_member.ungraded_submissions_count = ungraded_counts.get(str(course_member.id), 0)
        response_list.append(tutor_course_member)

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
        raise NotFoundException(detail=f"Submission group {submission_group_id} not found")

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
        max_submissions=submission_group.max_submissions,
        max_test_runs=submission_group.max_test_runs,
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

    # Get courses where user is a tutor
    tutor_course_ids = db.query(Course.id).select_from(User).filter(
        User.id == permissions.get_user_id_or_throw()
    ).join(
        CourseMember, CourseMember.user_id == User.id
    ).join(
        Course, Course.id == CourseMember.course_id
    ).filter(
        CourseMember.course_role_id.in_(allowed_course_role_ids("_tutor"))
    ).all()

    tutor_course_id_list = [c.id for c in tutor_course_ids]

    # Base query with member count
    query = db.query(
        SubmissionGroup,
        func.count(SubmissionGroupMember.id).label('member_count')
    ).outerjoin(
        SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id
    ).group_by(SubmissionGroup.id)

    # Filter by tutor's courses (unless admin)
    if not permissions.is_admin:
        query = query.filter(SubmissionGroup.course_id.in_(tutor_course_id_list))

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

    # Apply pagination
    query = query.offset(params.offset).limit(params.limit)

    results = query.all()

    # Build response list with additional statistics
    response_list = []
    submission_artifact_repo = SubmissionArtifactRepository(db, cache)
    submission_grade_repo = SubmissionGradeRepository(db, cache)

    for submission_group, member_count in results:
        # Get submission artifacts
        artifacts = submission_artifact_repo.find_by_submission_group(submission_group.id)
        submitted_artifacts = [a for a in artifacts if a.submit]

        # Get latest submission
        latest_submission = max(submitted_artifacts, key=lambda a: a.created_at) if submitted_artifacts else None

        # Check for ungraded submissions
        has_ungraded = False
        if params.has_ungraded_submissions is not None:
            for artifact in submitted_artifacts:
                artifact_grades = submission_grade_repo.find_by_artifact(artifact.id)
                if not artifact_grades:
                    has_ungraded = True
                    break

            # Skip if filtering for ungraded and this group doesn't match
            if params.has_ungraded_submissions and not has_ungraded:
                continue
            if not params.has_ungraded_submissions and has_ungraded:
                continue

        # Determine display name
        display_name = submission_group.display_name
        if not display_name:
            # Need to load members to compute display name
            members = db.query(SubmissionGroupMember).options(
                joinedload(SubmissionGroupMember.course_member).joinedload(CourseMember.user)
            ).filter(SubmissionGroupMember.submission_group_id == submission_group.id).all()
            submission_group.members = members
            display_name = submission_group.get_computed_display_name()

        response_list.append(TutorSubmissionGroupList(
            id=str(submission_group.id),
            course_id=str(submission_group.course_id),
            course_content_id=str(submission_group.course_content_id),
            display_name=display_name,
            max_group_size=submission_group.max_group_size,
            max_submissions=submission_group.max_submissions,
            max_test_runs=submission_group.max_test_runs,
            member_count=member_count,
            submission_count=len(submitted_artifacts),
            latest_submission_at=latest_submission.created_at if latest_submission else None,
            has_ungraded_submissions=has_ungraded,
            created_at=submission_group.created_at,
            updated_at=submission_group.updated_at,
        ))

    return response_list

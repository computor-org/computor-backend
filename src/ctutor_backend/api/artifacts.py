"""API endpoints for artifact grading and reviews."""
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from ctutor_backend.api.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from ctutor_backend.database import get_db
from ctutor_backend.model.artifact import (
    SubmissionArtifact,
    SubmissionGrade,
    SubmissionReview,
)
from ctutor_backend.model.result import Result
from ctutor_backend.model.course import CourseMember, SubmissionGroup, SubmissionGroupMember
from ctutor_backend.permissions.auth import get_current_permissions
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.interface.artifacts import (
    SubmissionGradeCreate,
    SubmissionGradeUpdate,
    SubmissionGradeListItem,
    SubmissionGradeDetail,
    SubmissionReviewCreate,
    SubmissionReviewUpdate,
    SubmissionReviewListItem,
)
from ctutor_backend.interface.results import (
    ResultCreate,
    ResultUpdate,
    ResultList,
)

logger = logging.getLogger(__name__)

artifacts_router = APIRouter(prefix="/artifacts", tags=["artifacts"])


# ===============================
# Artifact Grade Endpoints
# ===============================

@artifacts_router.post("/{artifact_id}/grades", response_model=SubmissionGradeDetail, status_code=status.HTTP_201_CREATED)
async def create_artifact_grade(
    artifact_id: UUID,
    grade_data: SubmissionGradeCreate,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """Create a grade for an artifact. Requires instructor/tutor permissions."""

    # Get the artifact and verify permissions
    artifact = db.query(SubmissionArtifact).options(
        joinedload(SubmissionArtifact.submission_group).joinedload(SubmissionGroup.course)
    ).filter(SubmissionArtifact.id == artifact_id).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Check if user has grading permissions (must be at least tutor)
    course = artifact.submission_group.course

    # Query for course member with tutor or higher permission
    grader_member = check_course_permissions(
        permissions, CourseMember, "_tutor", db
    ).filter(
        CourseMember.course_id == course.id,
        CourseMember.user_id == permissions.get_user_id()
    ).first()

    if not grader_member:
        raise ForbiddenException(detail="You must be a tutor or instructor to grade artifacts")

    # Validate grade
    if grade_data.grade < 0.0 or grade_data.grade > 1.0:
        raise BadRequestException(detail="Grade must be between 0.0 and 1.0")

    # Create the grade (use the grader's course member id)
    grade = SubmissionGrade(
        artifact_id=artifact_id,
        graded_by_course_member_id=grader_member.id,  # Use the authenticated grader's member ID
        grade=grade_data.grade,
        status=grade_data.status.value if hasattr(grade_data.status, 'value') else grade_data.status,
        comment=grade_data.comment,
    )

    db.add(grade)
    db.commit()
    db.refresh(grade)

    logger.info(f"Created grade {grade.id} for artifact {artifact_id}")

    return SubmissionGradeDetail.model_validate(grade)


@artifacts_router.get("/{artifact_id}/grades", response_model=list[SubmissionGradeListItem])
async def list_artifact_grades(
    artifact_id: UUID,
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """List all grades for an artifact. Students can view their own grades, tutors/instructors can view all."""

    # Verify artifact exists and get submission group
    artifact = db.query(SubmissionArtifact).options(
        joinedload(SubmissionArtifact.submission_group)
    ).filter(
        SubmissionArtifact.id == artifact_id
    ).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Check permissions - students can only see grades for their own submissions
    user_id = permissions.get_user_id()
    if user_id and not permissions.is_admin:
        # Check if user is a member of the submission group or has tutor/instructor permissions
        is_group_member = db.query(SubmissionGroupMember).join(
            CourseMember
        ).filter(
            SubmissionGroupMember.submission_group_id == artifact.submission_group_id,
            CourseMember.user_id == user_id
        ).first()

        if not is_group_member:
            # Check for tutor/instructor permissions
            has_elevated_perms = check_course_permissions(
                permissions, CourseMember, "_tutor", db
            ).filter(
                CourseMember.course_id == artifact.submission_group.course_id,
                CourseMember.user_id == user_id
            ).first()

            if not has_elevated_perms:
                raise ForbiddenException(detail="You don't have permission to view these grades")

    # Get grades for this artifact
    grades = db.query(SubmissionGrade).options(
        joinedload(SubmissionGrade.graded_by)
    ).filter(
        SubmissionGrade.artifact_id == artifact_id
    ).order_by(SubmissionGrade.graded_at.desc()).all()

    response.headers["X-Total-Count"] = str(len(grades))

    return [SubmissionGradeListItem.model_validate(grade) for grade in grades]


@artifacts_router.patch("/grades/{grade_id}", response_model=SubmissionGradeDetail)
async def update_artifact_grade(
    grade_id: UUID,
    update_data: SubmissionGradeUpdate,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """Update an existing grade. Only the grader can update their own grade."""

    grade = db.query(SubmissionGrade).options(
        joinedload(SubmissionGrade.graded_by)
    ).filter(SubmissionGrade.id == grade_id).first()

    if not grade:
        raise NotFoundException(detail="Grade not found")

    # Check if user is the grader
    principal_user_id = permissions.get_user_id()
    if str(grade.graded_by.user_id) != str(principal_user_id):
        raise ForbiddenException(detail="You can only update your own grades")

    # Update fields
    if update_data.grade is not None:
        grade.grade = update_data.grade
    if update_data.status is not None:
        grade.status = update_data.status.value if hasattr(update_data.status, 'value') else update_data.status
    if update_data.comment is not None:
        grade.comment = update_data.comment

    # Validate grade
    if grade.grade < 0.0 or grade.grade > 1.0:
        raise BadRequestException(detail="Grade must be between 0.0 and 1.0")

    db.commit()
    db.refresh(grade)

    return SubmissionGradeDetail.model_validate(grade)


@artifacts_router.delete("/grades/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact_grade(
    grade_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """Delete a grade. Only the grader or an admin can delete."""

    grade = db.query(SubmissionGrade).filter(SubmissionGrade.id == grade_id).first()

    if not grade:
        raise NotFoundException(detail="Grade not found")

    # Check permissions
    principal_user_id = permissions.get_user_id()
    if str(grade.graded_by.user_id) != str(principal_user_id):
        # Check if user is instructor (higher permission needed to delete others' grades)
        course = grade.artifact.submission_group.course
        is_instructor = check_course_permissions(
            permissions, CourseMember, "_lecturer", db  # Use _lecturer for instructor role
        ).filter(
            CourseMember.course_id == course.id,
            CourseMember.user_id == principal_user_id
        ).first()

        if not is_instructor:
            raise ForbiddenException(detail="Only instructors can delete other people's grades")

    db.delete(grade)
    db.commit()

    logger.info(f"Deleted grade {grade_id}")


# ===============================
# Artifact Review Endpoints
# ===============================

@artifacts_router.post("/{artifact_id}/reviews", response_model=SubmissionReviewListItem, status_code=status.HTTP_201_CREATED)
async def create_artifact_review(
    artifact_id: UUID,
    review_data: SubmissionReviewCreate,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """Create a review for an artifact."""

    # Get the artifact
    artifact = db.query(SubmissionArtifact).options(
        joinedload(SubmissionArtifact.submission_group)
    ).filter(SubmissionArtifact.id == artifact_id).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Check if user is a course member (any role can review)
    course = artifact.submission_group.course
    principal_user_id = permissions.get_user_id()

    # Use check_course_permissions to find the course member (works for any role)
    course_member = check_course_permissions(
        permissions, CourseMember, "_student", db  # _student is the minimum role
    ).filter(
        CourseMember.course_id == course.id,
        CourseMember.user_id == principal_user_id
    ).first()

    if not course_member:
        raise ForbiddenException(detail="You must be a course member to review artifacts")

    # Create the review (use authenticated user's course member id)
    review = SubmissionReview(
        artifact_id=artifact_id,
        reviewer_course_member_id=course_member.id,  # Use the authenticated reviewer's member ID
        body=review_data.body,
        review_type=review_data.review_type,
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    logger.info(f"Created review {review.id} for artifact {artifact_id}")

    return SubmissionReviewListItem.model_validate(review)


@artifacts_router.get("/{artifact_id}/reviews", response_model=list[SubmissionReviewListItem])
async def list_artifact_reviews(
    artifact_id: UUID,
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """List all reviews for an artifact. Any course member can view reviews."""

    # Verify artifact exists and get course info
    artifact = db.query(SubmissionArtifact).options(
        joinedload(SubmissionArtifact.submission_group)
    ).filter(
        SubmissionArtifact.id == artifact_id
    ).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Check if user is a course member (any role can view reviews)
    user_id = permissions.get_user_id()
    if user_id and not permissions.is_admin:
        is_course_member = check_course_permissions(
            permissions, CourseMember, "_student", db  # _student is minimum role
        ).filter(
            CourseMember.course_id == artifact.submission_group.course_id,
            CourseMember.user_id == user_id
        ).first()

        if not is_course_member:
            raise ForbiddenException(detail="You must be a course member to view reviews")

    # Get reviews for this artifact
    reviews = db.query(SubmissionReview).options(
        joinedload(SubmissionReview.reviewer)
    ).filter(
        SubmissionReview.artifact_id == artifact_id
    ).order_by(SubmissionReview.created_at.desc()).all()

    response.headers["X-Total-Count"] = str(len(reviews))

    return [SubmissionReviewListItem.model_validate(review) for review in reviews]


@artifacts_router.patch("/reviews/{review_id}", response_model=SubmissionReviewListItem)
async def update_artifact_review(
    review_id: UUID,
    update_data: SubmissionReviewUpdate,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """Update an existing review. Only the reviewer can update their own review."""

    review = db.query(SubmissionReview).options(
        joinedload(SubmissionReview.reviewer)
    ).filter(SubmissionReview.id == review_id).first()

    if not review:
        raise NotFoundException(detail="Review not found")

    # Check if user is the reviewer
    principal_user_id = permissions.get_user_id()
    if str(review.reviewer.user_id) != str(principal_user_id):
        raise ForbiddenException(detail="You can only update your own reviews")

    # Update fields
    if update_data.body is not None:
        review.body = update_data.body
    if update_data.review_type is not None:
        review.review_type = update_data.review_type

    db.commit()
    db.refresh(review)

    return SubmissionReviewListItem.model_validate(review)


@artifacts_router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact_review(
    review_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """Delete a review. Only the reviewer or an admin can delete."""

    review = db.query(SubmissionReview).filter(SubmissionReview.id == review_id).first()

    if not review:
        raise NotFoundException(detail="Review not found")

    # Check permissions
    principal_user_id = permissions.get_user_id()
    if str(review.reviewer.user_id) != str(principal_user_id):
        # Check if user is instructor (higher permission needed to delete others' reviews)
        course = review.artifact.submission_group.course
        is_instructor = check_course_permissions(
            permissions, CourseMember, "_lecturer", db  # Use _lecturer for instructor role
        ).filter(
            CourseMember.course_id == course.id,
            CourseMember.user_id == principal_user_id
        ).first()

        if not is_instructor:
            raise ForbiddenException(detail="Only instructors can delete other people's reviews")

    db.delete(review)
    db.commit()

    logger.info(f"Deleted review {review_id}")


# ===============================
# Test Result Endpoints
# ===============================

@artifacts_router.post("/{artifact_id}/test", response_model=ResultList, status_code=status.HTTP_201_CREATED)
async def create_test_result(
    artifact_id: UUID,
    test_data: ResultCreate,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """Create a test result for an artifact. Checks for test limitations."""

    # Get the artifact
    artifact = db.query(SubmissionArtifact).options(
        joinedload(SubmissionArtifact.submission_group)
    ).filter(SubmissionArtifact.id == artifact_id).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Check if user has permission to run tests (students can test their own, tutors/instructors can test any)
    principal_user_id = permissions.get_user_id()
    course = artifact.submission_group.course

    # First check if user is a course member at all
    course_member = check_course_permissions(
        permissions, CourseMember, "_student", db
    ).filter(
        CourseMember.course_id == course.id,
        CourseMember.user_id == principal_user_id
    ).first()

    if not course_member:
        raise ForbiddenException(detail="You must be a course member to run tests")

    # Check if student is testing their own submission
    is_own_submission = db.query(SubmissionGroupMember).filter(
        SubmissionGroupMember.submission_group_id == artifact.submission_group_id,
        SubmissionGroupMember.course_member_id == course_member.id
    ).first()

    if not is_own_submission:
        # If not their own submission, they need tutor or higher permissions
        has_test_permission = check_course_permissions(
            permissions, CourseMember, "_tutor", db
        ).filter(
            CourseMember.course_id == course.id,
            CourseMember.user_id == principal_user_id
        ).first()

        if not has_test_permission:
            raise ForbiddenException(detail="Students can only test their own submissions")

    # Check test limitations (prevent multiple successful tests by same member)
    existing_test = db.query(Result).filter(
        and_(
            Result.submission_artifact_id == artifact_id,
            Result.course_member_id == test_data.course_member_id,
            ~Result.status.in_([1, 2, 6])  # Not failed, cancelled, or crashed
        )
    ).first()

    if existing_test:
        raise BadRequestException(
            detail="You have already run a successful test on this artifact. "
                   "Multiple tests are not allowed unless the previous test failed."
        )

    # Check max test runs limit if configured
    submission_group = artifact.submission_group
    if submission_group.max_test_runs is not None:
        test_count = db.query(Result).filter(
            Result.submission_artifact_id == artifact_id
        ).count()

        if test_count >= submission_group.max_test_runs:
            raise BadRequestException(
                detail=f"Maximum test runs ({submission_group.max_test_runs}) reached for this artifact"
            )

    # Create the test result (use authenticated user's course member id)
    from ctutor_backend.interface.tasks import map_task_status_to_int

    result = Result(
        submission_artifact_id=artifact_id,
        course_member_id=course_member.id,  # Use authenticated user's course member ID
        execution_backend_id=test_data.execution_backend_id,
        test_system_id=test_data.test_system_id,
        status=map_task_status_to_int(test_data.status),
        grade=test_data.grade,
        result_json=test_data.result_json,
        properties=test_data.properties,
        log_text=test_data.log_text,
        version_identifier=test_data.version_identifier,
        reference_version_identifier=test_data.reference_version_identifier,
    )

    db.add(result)
    db.commit()
    db.refresh(result)

    logger.info(f"Created result {result.id} for artifact {artifact_id}")

    return ResultList.model_validate(result)


@artifacts_router.get("/{artifact_id}/tests", response_model=list[ResultList])
async def list_artifact_test_results(
    artifact_id: UUID,
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """List all test results for an artifact. Students see their own, tutors/instructors see all."""

    # Verify artifact exists and get course info
    artifact = db.query(SubmissionArtifact).options(
        joinedload(SubmissionArtifact.submission_group)
    ).filter(
        SubmissionArtifact.id == artifact_id
    ).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Check permissions
    user_id = permissions.get_user_id()
    if user_id and not permissions.is_admin:
        # Check if user is a member of the submission group
        is_group_member = db.query(SubmissionGroupMember).join(
            CourseMember
        ).filter(
            SubmissionGroupMember.submission_group_id == artifact.submission_group_id,
            CourseMember.user_id == user_id
        ).first()

        if not is_group_member:
            # If not in the group, check for tutor/instructor permissions
            has_elevated_perms = check_course_permissions(
                permissions, CourseMember, "_tutor", db
            ).filter(
                CourseMember.course_id == artifact.submission_group.course_id,
                CourseMember.user_id == user_id
            ).first()

            if not has_elevated_perms:
                raise ForbiddenException(detail="You can only view test results for your own submissions")

    # Get test results for this artifact
    results = db.query(Result).filter(
        Result.submission_artifact_id == artifact_id
    ).order_by(Result.created_at.desc()).all()

    response.headers["X-Total-Count"] = str(len(results))

    return [ResultList.model_validate(result) for result in results]


@artifacts_router.patch("/tests/{test_id}", response_model=ResultList)
async def update_test_result(
    test_id: UUID,
    update_data: ResultUpdate,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """Update a test result (e.g., when test completes). Only the test runner or admin can update."""

    result = db.query(Result).filter(Result.id == test_id).first()

    if not result:
        raise NotFoundException(detail="Test result not found")

    # Check permissions - either admin (service account) or the test runner
    user_id = permissions.get_user_id()
    is_admin = permissions.has_claim("_admin")

    if not is_admin:
        # Check if user is the one who ran the test
        course_member = db.query(CourseMember).filter(
            CourseMember.id == result.course_member_id
        ).first()

        if not course_member or str(course_member.user_id) != str(user_id):
            raise ForbiddenException(detail="Only the test runner or admin can update test results")

    # Update fields
    if update_data.status is not None:
        from ctutor_backend.interface.tasks import map_task_status_to_int
        result.status = map_task_status_to_int(update_data.status)
    if update_data.grade is not None:
        result.grade = update_data.grade
    if update_data.result_json is not None:
        result.result_json = update_data.result_json
    if update_data.properties is not None:
        result.properties = update_data.properties
    if update_data.log_text is not None:
        result.log_text = update_data.log_text
    if update_data.finished_at is not None:
        result.finished_at = update_data.finished_at

    db.commit()
    db.refresh(result)

    return ResultList.model_validate(result)
"""API endpoints for artifact grading and reviews."""
import logging
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from ctutor_backend.api.crud import list_db
from ctutor_backend.api.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from ctutor_backend.database import get_db
from ctutor_backend.model.artifact import (
    SubmissionArtifact,
    ArtifactGrade,
    ArtifactReview,
    TestResult,
)
from ctutor_backend.model.course import CourseMember, SubmissionGroup
from ctutor_backend.permissions.auth import get_current_permissions
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.interface.artifacts import (
    ArtifactGradeCreate,
    ArtifactGradeUpdate,
    ArtifactGradeInterface,
    ArtifactReviewCreate,
    ArtifactReviewUpdate,
    ArtifactReviewInterface,
    TestResultCreate,
    TestResultUpdate,
    TestResultInterface,
)

logger = logging.getLogger(__name__)

artifacts_router = APIRouter(prefix="/artifacts", tags=["artifacts"])


# ===============================
# Artifact Grade Endpoints
# ===============================

@artifacts_router.post("/{artifact_id}/grades", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_artifact_grade(
    artifact_id: UUID,
    grade_data: ArtifactGradeCreate,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """Create a grade for an artifact. Requires instructor/tutor permissions."""

    # Get the artifact and verify permissions
    artifact = db.query(SubmissionArtifact).options(
        joinedload(SubmissionArtifact.submission_group)
    ).filter(SubmissionArtifact.id == artifact_id).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Check if user has grading permissions (instructor/tutor)
    course = artifact.submission_group.course
    course_members = check_course_permissions(
        permissions, CourseMember, "_tutor", db
    ).filter(
        CourseMember.course_id == course.id,
        CourseMember.user_id == permissions.get_user_id()
    ).first()

    if not course_members:
        raise ForbiddenException(detail="You don't have permission to grade in this course")

    # Validate score
    if grade_data.score > grade_data.max_score:
        raise BadRequestException(detail="Score cannot exceed max_score")

    # Create the grade
    grade = ArtifactGrade(
        artifact_id=artifact_id,
        graded_by_course_member_id=grade_data.graded_by_course_member_id,
        score=grade_data.score,
        max_score=grade_data.max_score,
        rubric=grade_data.rubric,
        comment=grade_data.comment,
    )

    db.add(grade)
    db.commit()
    db.refresh(grade)

    logger.info(f"Created grade {grade.id} for artifact {artifact_id}")

    return {"id": grade.id, "message": "Grade created successfully"}


@artifacts_router.get("/{artifact_id}/grades", response_model=list)
async def list_artifact_grades(
    artifact_id: UUID,
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """List all grades for an artifact."""

    # Verify artifact exists
    artifact = db.query(SubmissionArtifact).filter(
        SubmissionArtifact.id == artifact_id
    ).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Get grades for this artifact
    grades = db.query(ArtifactGrade).options(
        joinedload(ArtifactGrade.graded_by)
    ).filter(
        ArtifactGrade.artifact_id == artifact_id
    ).order_by(ArtifactGrade.graded_at.desc()).all()

    response.headers["X-Total-Count"] = str(len(grades))

    return [
        {
            "id": grade.id,
            "artifact_id": grade.artifact_id,
            "graded_by_course_member_id": grade.graded_by_course_member_id,
            "score": grade.score,
            "max_score": grade.max_score,
            "comment": grade.comment,
            "graded_at": grade.graded_at,
        }
        for grade in grades
    ]


@artifacts_router.patch("/grades/{grade_id}", response_model=dict)
async def update_artifact_grade(
    grade_id: UUID,
    update_data: ArtifactGradeUpdate,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """Update an existing grade. Only the grader can update their own grade."""

    grade = db.query(ArtifactGrade).filter(ArtifactGrade.id == grade_id).first()

    if not grade:
        raise NotFoundException(detail="Grade not found")

    # Check if user is the grader
    principal_user_id = permissions.get_user_id()
    if str(grade.graded_by.user_id) != str(principal_user_id):
        raise ForbiddenException(detail="You can only update your own grades")

    # Update fields
    if update_data.score is not None:
        grade.score = update_data.score
    if update_data.max_score is not None:
        grade.max_score = update_data.max_score
    if update_data.rubric is not None:
        grade.rubric = update_data.rubric
    if update_data.comment is not None:
        grade.comment = update_data.comment

    # Validate score
    if grade.score > grade.max_score:
        raise BadRequestException(detail="Score cannot exceed max_score")

    db.commit()
    db.refresh(grade)

    return {"id": grade.id, "message": "Grade updated successfully"}


@artifacts_router.delete("/grades/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact_grade(
    grade_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """Delete a grade. Only the grader or an admin can delete."""

    grade = db.query(ArtifactGrade).filter(ArtifactGrade.id == grade_id).first()

    if not grade:
        raise NotFoundException(detail="Grade not found")

    # Check permissions
    principal_user_id = permissions.get_user_id()
    if str(grade.graded_by.user_id) != str(principal_user_id):
        # Check if user is admin/instructor
        course = grade.artifact.submission_group.course
        is_admin = check_course_permissions(
            permissions, CourseMember, "_instructor", db
        ).filter(
            CourseMember.course_id == course.id,
            CourseMember.user_id == principal_user_id
        ).first()

        if not is_admin:
            raise ForbiddenException(detail="You can only delete your own grades")

    db.delete(grade)
    db.commit()

    logger.info(f"Deleted grade {grade_id}")


# ===============================
# Artifact Review Endpoints
# ===============================

@artifacts_router.post("/{artifact_id}/reviews", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_artifact_review(
    artifact_id: UUID,
    review_data: ArtifactReviewCreate,
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

    # Check if user is a course member
    course = artifact.submission_group.course
    principal_user_id = permissions.get_user_id()
    course_member = db.query(CourseMember).filter(
        CourseMember.course_id == course.id,
        CourseMember.user_id == principal_user_id
    ).first()

    if not course_member:
        raise ForbiddenException(detail="You must be a course member to review artifacts")

    # Create the review
    review = ArtifactReview(
        artifact_id=artifact_id,
        reviewer_course_member_id=review_data.reviewer_course_member_id,
        body=review_data.body,
        review_type=review_data.review_type,
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    logger.info(f"Created review {review.id} for artifact {artifact_id}")

    return {"id": review.id, "message": "Review created successfully"}


@artifacts_router.get("/{artifact_id}/reviews", response_model=list)
async def list_artifact_reviews(
    artifact_id: UUID,
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """List all reviews for an artifact."""

    # Verify artifact exists
    artifact = db.query(SubmissionArtifact).filter(
        SubmissionArtifact.id == artifact_id
    ).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Get reviews for this artifact
    reviews = db.query(ArtifactReview).options(
        joinedload(ArtifactReview.reviewer)
    ).filter(
        ArtifactReview.artifact_id == artifact_id
    ).order_by(ArtifactReview.created_at.desc()).all()

    response.headers["X-Total-Count"] = str(len(reviews))

    return [
        {
            "id": review.id,
            "artifact_id": review.artifact_id,
            "reviewer_course_member_id": review.reviewer_course_member_id,
            "body": review.body,
            "review_type": review.review_type,
            "created_at": review.created_at,
        }
        for review in reviews
    ]


@artifacts_router.patch("/reviews/{review_id}", response_model=dict)
async def update_artifact_review(
    review_id: UUID,
    update_data: ArtifactReviewUpdate,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """Update an existing review. Only the reviewer can update their own review."""

    review = db.query(ArtifactReview).filter(ArtifactReview.id == review_id).first()

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

    return {"id": review.id, "message": "Review updated successfully"}


@artifacts_router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact_review(
    review_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """Delete a review. Only the reviewer or an admin can delete."""

    review = db.query(ArtifactReview).filter(ArtifactReview.id == review_id).first()

    if not review:
        raise NotFoundException(detail="Review not found")

    # Check permissions
    principal_user_id = permissions.get_user_id()
    if str(review.reviewer.user_id) != str(principal_user_id):
        # Check if user is admin/instructor
        course = review.artifact.submission_group.course
        is_admin = check_course_permissions(
            permissions, CourseMember, "_instructor", db
        ).filter(
            CourseMember.course_id == course.id,
            CourseMember.user_id == principal_user_id
        ).first()

        if not is_admin:
            raise ForbiddenException(detail="You can only delete your own reviews")

    db.delete(review)
    db.commit()

    logger.info(f"Deleted review {review_id}")


# ===============================
# Test Result Endpoints
# ===============================

@artifacts_router.post("/{artifact_id}/test", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_test_result(
    artifact_id: UUID,
    test_data: TestResultCreate,
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

    # Check if user has permission to run tests
    principal_user_id = permissions.get_user_id()
    course = artifact.submission_group.course
    course_member = db.query(CourseMember).filter(
        CourseMember.course_id == course.id,
        CourseMember.user_id == principal_user_id
    ).first()

    if not course_member:
        raise ForbiddenException(detail="You must be a course member to run tests")

    # Check test limitations (prevent multiple successful tests by same member)
    existing_test = db.query(TestResult).filter(
        and_(
            TestResult.submission_artifact_id == artifact_id,
            TestResult.course_member_id == test_data.course_member_id,
            ~TestResult.status.in_([1, 2, 6])  # Not failed, cancelled, or crashed
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
        test_count = db.query(TestResult).filter(
            TestResult.submission_artifact_id == artifact_id
        ).count()

        if test_count >= submission_group.max_test_runs:
            raise BadRequestException(
                detail=f"Maximum test runs ({submission_group.max_test_runs}) reached for this artifact"
            )

    # Create the test result
    test_result = TestResult(
        submission_artifact_id=artifact_id,
        course_member_id=test_data.course_member_id,
        execution_backend_id=test_data.execution_backend_id,
        test_system_id=test_data.test_system_id,
        status=test_data.status,
        score=test_data.score,
        max_score=test_data.max_score,
        result_json=test_data.result_json,
        properties=test_data.properties,
        log_text=test_data.log_text,
        version_identifier=test_data.version_identifier,
        reference_version_identifier=test_data.reference_version_identifier,
    )

    db.add(test_result)
    db.commit()
    db.refresh(test_result)

    logger.info(f"Created test result {test_result.id} for artifact {artifact_id}")

    return {"id": test_result.id, "message": "Test result created successfully"}


@artifacts_router.get("/{artifact_id}/tests", response_model=list)
async def list_artifact_test_results(
    artifact_id: UUID,
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """List all test results for an artifact."""

    # Verify artifact exists
    artifact = db.query(SubmissionArtifact).filter(
        SubmissionArtifact.id == artifact_id
    ).first()

    if not artifact:
        raise NotFoundException(detail="Submission artifact not found")

    # Get test results for this artifact
    test_results = db.query(TestResult).filter(
        TestResult.submission_artifact_id == artifact_id
    ).order_by(TestResult.created_at.desc()).all()

    response.headers["X-Total-Count"] = str(len(test_results))

    from ctutor_backend.interface.tasks import map_int_to_task_status

    return [
        {
            "id": result.id,
            "submission_artifact_id": result.submission_artifact_id,
            "course_member_id": result.course_member_id,
            "execution_backend_id": result.execution_backend_id,
            "test_system_id": result.test_system_id,
            "status": map_int_to_task_status(result.status).value,
            "score": result.score,
            "max_score": result.max_score,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "created_at": result.created_at,
        }
        for result in test_results
    ]


@artifacts_router.patch("/tests/{test_id}", response_model=dict)
async def update_test_result(
    test_id: UUID,
    update_data: TestResultUpdate,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    """Update a test result (e.g., when test completes)."""

    test_result = db.query(TestResult).filter(TestResult.id == test_id).first()

    if not test_result:
        raise NotFoundException(detail="Test result not found")

    # Update fields
    if update_data.status is not None:
        from ctutor_backend.interface.tasks import map_task_status_to_int
        test_result.status = map_task_status_to_int(update_data.status)
    if update_data.score is not None:
        test_result.score = update_data.score
    if update_data.max_score is not None:
        test_result.max_score = update_data.max_score
    if update_data.result_json is not None:
        test_result.result_json = update_data.result_json
    if update_data.properties is not None:
        test_result.properties = update_data.properties
    if update_data.log_text is not None:
        test_result.log_text = update_data.log_text
    if update_data.finished_at is not None:
        test_result.finished_at = update_data.finished_at

    db.commit()
    db.refresh(test_result)

    return {"id": test_result.id, "message": "Test result updated successfully"}
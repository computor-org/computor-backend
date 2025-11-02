"""
Temporal workflow for bulk student repository creation with rate limiting.

This workflow handles creating repositories for multiple course members in batches
to avoid overwhelming the GitLab API with concurrent requests.

Key features:
- Batch processing (configurable batch size)
- Rate limiting between batches
- Shared GitLab project lookups
- Sequential processing to respect API limits
"""
import logging
import asyncio
from datetime import timedelta
from typing import List, Dict, Any
from uuid import UUID

from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from sqlalchemy.orm import Session

from .temporal_base import BaseWorkflow, WorkflowResult
from .registry import register_task
from ..database import get_db
from ..model.course import CourseMember, SubmissionGroup, SubmissionGroupMember

logger = logging.getLogger(__name__)


@activity.defn
async def bulk_create_student_repositories_activity(
    course_member_ids: List[str],
    course_id: str,
    batch_size: int = 5,
    batch_delay_seconds: int = 10
) -> Dict[str, Any]:
    """
    Create student repositories for multiple course members in batches.

    This activity processes course members in batches to avoid overwhelming
    the GitLab API with concurrent requests.

    Args:
        course_member_ids: List of course member IDs to process
        course_id: Course ID
        batch_size: Number of members to process per batch (default: 5)
        batch_delay_seconds: Delay between batches in seconds (default: 10)

    Returns:
        Dict with success/failure counts and details
    """
    from .temporal_student_repository import create_student_repository_activity

    logger.info(
        f"Starting bulk repository creation for {len(course_member_ids)} members "
        f"(batch_size={batch_size}, batch_delay={batch_delay_seconds}s)"
    )

    results = {
        "total": len(course_member_ids),
        "success": 0,
        "failed": 0,
        "failures": []
    }

    # Process in batches
    for i in range(0, len(course_member_ids), batch_size):
        batch = course_member_ids[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(course_member_ids) + batch_size - 1) // batch_size

        logger.info(
            f"Processing batch {batch_num}/{total_batches} "
            f"({len(batch)} members)"
        )

        # Get submission groups for this batch
        db = next(get_db())
        try:
            batch_submission_groups = {}
            for course_member_id in batch:
                # Get submission groups for this member
                submission_groups = (
                    db.query(SubmissionGroup)
                    .join(
                        SubmissionGroupMember,
                        SubmissionGroupMember.submission_group_id == SubmissionGroup.id
                    )
                    .filter(SubmissionGroupMember.course_member_id == course_member_id)
                    .all()
                )
                batch_submission_groups[course_member_id] = [
                    str(sg.id) for sg in submission_groups
                ]
        finally:
            db.close()

        # Process each member in the batch sequentially
        for course_member_id in batch:
            try:
                submission_group_ids = batch_submission_groups.get(course_member_id, [])

                logger.info(
                    f"Creating repository for course member {course_member_id} "
                    f"({submission_group_ids})"
                )

                # Call the existing activity (this already handles retries)
                await create_student_repository_activity(
                    course_member_id=course_member_id,
                    course_id=course_id,
                    submission_group_ids=submission_group_ids,
                    is_team=False
                )

                results["success"] += 1
                logger.info(f"Successfully created repository for {course_member_id}")

            except Exception as e:
                results["failed"] += 1
                error_msg = f"Failed to create repository for {course_member_id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results["failures"].append({
                    "course_member_id": course_member_id,
                    "error": str(e)
                })

        # Rate limiting: wait between batches (except after last batch)
        if i + batch_size < len(course_member_ids):
            logger.info(
                f"Batch {batch_num}/{total_batches} complete. "
                f"Waiting {batch_delay_seconds}s before next batch..."
            )
            await asyncio.sleep(batch_delay_seconds)

    logger.info(
        f"Bulk repository creation complete: "
        f"{results['success']}/{results['total']} successful, "
        f"{results['failed']} failed"
    )

    return results


@workflow.defn
class BulkStudentRepositoryCreationWorkflow(BaseWorkflow):
    """
    Workflow for creating student repositories in bulk with rate limiting.

    This workflow processes multiple course members in batches to avoid
    overwhelming the GitLab API. It's designed to be used when importing
    large numbers of students.

    Parameters:
        - course_member_ids: List of course member IDs to process
        - course_id: Course ID
        - batch_size: Number of members per batch (default: 5)
        - batch_delay_seconds: Delay between batches (default: 10)
    """

    @classmethod
    def get_name(cls) -> str:
        """Get the workflow name."""
        return "BulkStudentRepositoryCreationWorkflow"

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        """
        Execute the bulk repository creation workflow.

        Args:
            parameters: Workflow parameters containing:
                - course_member_ids: List[str] - List of course member IDs
                - course_id: str - Course ID
                - batch_size: int - Members per batch (default: 5)
                - batch_delay_seconds: int - Delay between batches (default: 10)

        Returns:
            WorkflowResult with success/failure details
        """
        course_member_ids = parameters.get("course_member_ids", [])
        course_id = parameters.get("course_id")
        batch_size = parameters.get("batch_size", 5)
        batch_delay_seconds = parameters.get("batch_delay_seconds", 10)

        workflow.logger.info(
            f"Starting BulkStudentRepositoryCreationWorkflow for "
            f"{len(course_member_ids)} members in course {course_id}"
        )

        if not course_member_ids:
            return WorkflowResult(
                success=False,
                message="No course member IDs provided",
                data={"total": 0, "success": 0, "failed": 0}
            )

        if not course_id:
            return WorkflowResult(
                success=False,
                message="No course ID provided",
                data={"total": 0, "success": 0, "failed": 0}
            )

        try:
            # Execute bulk creation with retry policy
            results = await workflow.execute_activity(
                bulk_create_student_repositories_activity,
                args=[course_member_ids, course_id, batch_size, batch_delay_seconds],
                start_to_close_timeout=timedelta(hours=2),  # Long timeout for large batches
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=10),
                    maximum_interval=timedelta(minutes=5),
                    maximum_attempts=3,
                    non_retryable_error_types=["ValueError", "KeyError"]
                ),
            )

            success = results["failed"] == 0

            return WorkflowResult(
                success=success,
                message=(
                    f"Bulk repository creation completed: "
                    f"{results['success']}/{results['total']} successful"
                ),
                data=results
            )

        except Exception as e:
            workflow.logger.error(
                f"Bulk repository creation failed: {str(e)}",
                exc_info=True
            )
            return WorkflowResult(
                success=False,
                message=f"Bulk repository creation failed: {str(e)}",
                data={"total": len(course_member_ids), "success": 0, "failed": len(course_member_ids)}
            )


# Register the workflow using decorator pattern
BulkStudentRepositoryCreationWorkflow = register_task(BulkStudentRepositoryCreationWorkflow)

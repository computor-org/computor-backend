"""
Temporal workflows for organization, course family, and course hierarchy management.
"""
import logging
from datetime import timedelta
from typing import Dict, Any, Optional
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from .temporal_base import BaseWorkflow, WorkflowResult
from .registry import register_task
from computor_types.deployment_config import CourseConfig
from ..database import get_db_session
from ..model.organization import Organization
from ..model.course import CourseFamily, Course

logger = logging.getLogger(__name__)


# Activities
#
# Organization and course-family creation are NOT Temporal activities: with the
# course-level git model they are plain DB inserts with no external side
# effects, so they run synchronously via ``business_logic.deployment`` (CRUD).
# Only course creation stays here — it still provisions git / student templates.
@activity.defn(name="create_course_activity")
async def create_course_activity(
    course_config: Dict[str, Any],
    course_family_id: str,
    user_id: str,
) -> Dict[str, Any]:
    logger.info(f"Starting course creation activity for: {course_config.get('name')}")
    try:
        config = CourseConfig(
            name=course_config.get("name"),
            path=course_config.get("path"),
            description=course_config.get("description", ""),
        )
        with get_db_session() as db:
            family = db.query(CourseFamily).filter(CourseFamily.id == course_family_id).first()
            if not family:
                raise ValueError(f"Course family {course_family_id} not found")
            org = db.query(Organization).filter(Organization.id == family.organization_id).first()
            if not org:
                raise ValueError(f"Organization {family.organization_id} not found")

            # Course-level git model: create the course row, then bind it to a
            # registry git server if one was chosen at creation. Git is per-course
            # — not inherited from the org/family. Authorization at the API edge.
            from ..custom_types import Ltree

            course = (
                db.query(Course)
                .filter(
                    Course.course_family_id == family.id,
                    Course.path == Ltree(config.path),
                )
                .first()
            )
            if course is None:
                course = Course(
                    title=config.name,
                    description=config.description or "",
                    path=Ltree(config.path),
                    course_family_id=family.id,
                    organization_id=org.id,
                    properties={},
                    created_by=user_id,
                    updated_by=user_id,
                )
                db.add(course)
                db.flush()

            # Enroll the creator as course owner so they can manage the course
            # immediately (assign examples, release, ...). Idempotent on unique
            # (user_id, course_id).
            from ..model.course import CourseMember
            if user_id and (
                db.query(CourseMember)
                .filter(CourseMember.course_id == course.id, CourseMember.user_id == user_id)
                .first()
            ) is None:
                db.add(CourseMember(
                    course_id=course.id,
                    user_id=user_id,
                    course_role_id="_owner",
                    created_by=user_id,
                    updated_by=user_id,
                ))

            git_binding = None
            git_cfg = course_config.get("git") or {}
            # Accept both the runtime shape (a git_server_id UUID, from the
            # web/VSCode course-create form) and the portable deploy-file shape
            # (provider + base_url, resolved here to a GitServer). parent_group_id
            # + token are the per-course GitLab credentials carried on the binding.
            git_server_id = git_cfg.get("git_server_id")
            if not git_server_id and git_cfg.get("provider"):
                from ..business_logic.git_registry import resolve_git_server_ref

                server = resolve_git_server_ref(git_cfg.get("provider"), git_cfg.get("base_url"), db)
                git_server_id = str(server.id) if server is not None else None
            if git_server_id or git_cfg.get("provider"):
                from computor_types.course_git import CourseGitBindingUpsert
                from ..business_logic.course_git import _apply_course_git_binding

                binding = _apply_course_git_binding(
                    course,
                    CourseGitBindingUpsert(
                        delivery=git_cfg.get("delivery") or "git",
                        git_server_id=git_server_id,
                        parent_group_id=git_cfg.get("parent_group_id"),
                        token=git_cfg.get("token"),
                        template_repo=git_cfg.get("template_repo"),
                        template_url=git_cfg.get("template_url"),
                        default_branch=git_cfg.get("default_branch"),
                        student_repo_modes=git_cfg.get("student_repo_modes") or [],
                    ),
                    user_id,
                    db,
                )  # commits the course + binding together
                git_binding = {
                    "git_server_id": str(binding.git_server_id) if binding.git_server_id else None,
                    "template_url": binding.template_url,
                }
            else:
                db.commit()

            logger.info(f"Created course (course-level git model): {config.path} (ID: {course.id})")
            return {
                "course_id": str(course.id),
                "status": "created",
                "name": course_config.get("name"),
                "provider_entity_id": None,
                "git_binding": git_binding,
            }

    except Exception as e:
        logger.exception(f"Exception in course creation activity: {e}")
        raise


# Workflows
@register_task
@workflow.defn(name="create_course", sandboxed=False)
class CreateCourseWorkflow(BaseWorkflow):
    """Workflow for creating a course."""

    @classmethod
    def get_name(cls) -> str:
        return "create_course"

    @classmethod
    def get_task_queue(cls) -> str:
        return "computor-tasks"

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(minutes=10)

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        """
        Create course workflow.

        Args:
            parameters: Dictionary containing:
                - course_config: Course configuration
                - course_family_id: Parent course family ID
                - user_id: User ID creating the course
        """
        required_params = ['course_config', 'course_family_id', 'user_id']
        missing_params = [param for param in required_params if not parameters.get(param)]
        if missing_params:
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            workflow.logger.error(error_msg)
            return WorkflowResult(
                status="failed",
                result=None,
                error=error_msg,
                metadata={"workflow_type": "create_course"}
            )

        course_config = parameters.get('course_config', {})
        course_family_id = parameters.get('course_family_id')
        user_id = parameters.get('user_id')

        if not course_config.get('name') or not course_config.get('path'):
            error_msg = "Course config must include 'name' and 'path'"
            workflow.logger.error(error_msg)
            return WorkflowResult(
                status="failed",
                result=None,
                error=error_msg,
                metadata={"workflow_type": "create_course"}
            )

        workflow.logger.info(f"Creating course: {course_config.get('name')}")

        try:
            result = await workflow.execute_activity(
                create_course_activity,
                args=[course_config, course_family_id, user_id],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                )
            )

            return WorkflowResult(
                status="completed",
                result=result,
                metadata={"workflow_type": "create_course"}
            )

        except Exception as e:
            workflow.logger.error(f"Course creation failed: {str(e)}")
            return WorkflowResult(
                status="failed",
                result=None,
                error=str(e),
                metadata={"workflow_type": "create_course"}
            )


@register_task
@workflow.defn(name="deploy_computor_hierarchy", sandboxed=False)
class DeployComputorHierarchyWorkflow(BaseWorkflow):
    """
    Orchestrator workflow that creates the courses of a deployment.

    Organizations and course families are created synchronously (plain DB
    inserts, course-level git model) by ``business_logic.deployment`` before
    this workflow is submitted. This workflow only creates the courses — they
    still need Temporal for git / student-template provisioning — via
    ``CreateCourseWorkflow``.
    """

    @classmethod
    def get_name(cls) -> str:
        return "deploy_computor_hierarchy"

    @classmethod
    def get_task_queue(cls) -> str:
        return "computor-tasks"

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(minutes=30)

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        """
        Create the deployment's courses under their (already-created) families.

        Args:
            parameters: Dictionary containing:
                - courses: flat list of {course_config, course_family_id} items
                  (the org/family rows they hang under already exist)
                - user_id: ID of the user initiating the deployment
        """
        if not parameters.get('user_id'):
            error_msg = "Missing required parameter: user_id"
            workflow.logger.error(error_msg)
            return WorkflowResult(
                status="failed",
                result=None,
                error=error_msg,
                metadata={"workflow_type": "deploy_computor_hierarchy"}
            )

        courses = parameters.get('courses') or []
        user_id = parameters['user_id']

        created_entities = {"courses": []}

        try:
            workflow.logger.info(f"Deploying {len(courses)} course(s)")

            for course_idx, item in enumerate(courses):
                course_config = item.get("course_config", {})
                course_family_id = item.get("course_family_id")
                workflow.logger.info(
                    f"Processing course {course_idx + 1}/{len(courses)}: {course_config.get('name')}"
                )

                course_workflow_handle = await workflow.start_child_workflow(
                    CreateCourseWorkflow.run,
                    args=[{
                        "course_config": course_config,
                        "course_family_id": course_family_id,
                        "user_id": user_id,
                    }],
                    id=f"create-course-{course_idx}-{workflow.info().workflow_id}",
                    task_queue="computor-tasks",
                    execution_timeout=timedelta(minutes=10)
                )

                course_result = await course_workflow_handle
                if course_result.status != "completed":
                    raise Exception(f"Course '{course_config.get('name')}' creation failed: {course_result.error}")

                created_entities["courses"].append(course_result.result)

            workflow.logger.info(f"Course deployment completed: {len(courses)} course(s)")

            return WorkflowResult(
                status="completed",
                result={
                    "created_entities": created_entities,
                    "counts": {"courses": len(courses)},
                },
                metadata={"workflow_type": "deploy_computor_hierarchy"}
            )

        except Exception as e:
            error_msg = f"Course deployment failed: {str(e)}"
            workflow.logger.error(error_msg, exc_info=True)
            return WorkflowResult(
                status="failed",
                result=created_entities,
                error=error_msg,
                metadata={"workflow_type": "deploy_computor_hierarchy"}
            )


ACTIVITIES = [
    create_course_activity,
]

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
from computor_types.deployments_refactored import OrganizationConfig, CourseFamilyConfig, CourseConfig
from ..database import get_db_session
from ..model.organization import Organization
from ..model.course import CourseFamily, Course

logger = logging.getLogger(__name__)


# Activities
@activity.defn(name="create_organization_activity")
async def create_organization_activity(
    org_config: Dict[str, Any],
    git_provider_type: str,
    git_provider_url: str,
    git_provider_token: str,   # plaintext — encrypted before storage
    user_id: str,
) -> Dict[str, Any]:
    """
    Create an organization and its git provider row.
    The provider row is created here because the org doesn't exist yet when
    the task is submitted (chicken-and-egg: git_provider FK requires org.id).
    """
    from ..generator.gitlab_builder import GitLabBuilder
    from ..model.git_provider import GitProvider
    from computor_types.encryption import encrypt_secret
    from computor_types.gitlab import GitLabConfig

    logger.info(f"Starting organization creation activity for: {org_config.get('name')}")
    try:
        gitlab_config = GitLabConfig(
            url=git_provider_url,
            token=git_provider_token,
            parent=org_config.get("gitlab", {}).get("parent"),
            path=org_config.get("path"),
        )
        config = OrganizationConfig(
            name=org_config.get("name"),
            path=org_config.get("path"),
            description=org_config.get("description", ""),
            gitlab=gitlab_config,
        )
        with get_db_session() as db:
            if git_provider_type == "gitlab":
                builder = GitLabBuilder(db, git_provider_url, git_provider_token)
                result = builder._create_organization(config, user_id)
                if not result["success"]:
                    raise RuntimeError(f"Organization creation failed: {result.get('error')}")
                org = result["organization"]
            else:
                raise NotImplementedError(f"Provider type {git_provider_type!r} not yet supported for org creation")

            # Create the git_provider row now that we have the org id
            encrypted = encrypt_secret(git_provider_token)
            provider_row = GitProvider(
                organization_id=str(org.id),
                type=git_provider_type,
                url=git_provider_url,
                token=encrypted,
                created_by=user_id,
                updated_by=user_id,
            )
            db.add(provider_row)
            db.commit()

            return {
                "organization_id": str(org.id),
                "git_provider_id": str(provider_row.id),
                "status": "created",
                "name": org_config.get("name"),
                "provider_entity_id": str(result["gitlab_group"].id) if result.get("gitlab_group") else None,
            }
    except Exception as e:
        logger.exception(f"Exception in organization creation activity: {e}")
        raise


@activity.defn(name="create_course_family_activity")
async def create_course_family_activity(
    family_config: Dict[str, Any],
    organization_id: str,
    user_id: str,
) -> Dict[str, Any]:
    from ..git_provider import get_provider_client_from_db
    from ..model.git_provider import GitProvider
    from ..generator.gitlab_builder import GitLabBuilder

    logger.info(f"Starting course family creation activity for: {family_config.get('name')}")
    try:
        config = CourseFamilyConfig(
            name=family_config.get("name"),
            path=family_config.get("path"),
            description=family_config.get("description", ""),
        )
        with get_db_session() as db:
            org = db.query(Organization).filter(Organization.id == organization_id).first()
            if not org:
                raise ValueError(f"Organization {organization_id} not found")

            provider_row = db.query(GitProvider).filter(GitProvider.organization_id == organization_id).first()
            if not provider_row:
                # Course-level model: no legacy org-scoped GitProvider. Create the
                # family row and enroll the creator as owner. Course families carry
                # no git config in this model (git is per-course). Authorization
                # happened at the API edge.
                from ..custom_types import Ltree
                from ..model.course import CourseFamilyMember

                family = (
                    db.query(CourseFamily)
                    .filter(
                        CourseFamily.organization_id == org.id,
                        CourseFamily.path == Ltree(config.path),
                    )
                    .first()
                )
                if family is None:
                    family = CourseFamily(
                        title=config.name,
                        description=config.description or "",
                        path=Ltree(config.path),
                        organization_id=org.id,
                        properties={},
                        created_by=user_id,
                        updated_by=user_id,
                    )
                    db.add(family)
                    db.flush()

                # Enroll the creator as family owner (manage courses under it).
                # Idempotent on unique (user_id, course_family_id).
                if user_id and (
                    db.query(CourseFamilyMember)
                    .filter(
                        CourseFamilyMember.course_family_id == family.id,
                        CourseFamilyMember.user_id == user_id,
                    )
                    .first()
                ) is None:
                    db.add(CourseFamilyMember(
                        course_family_id=family.id,
                        user_id=user_id,
                        course_family_role_id="_owner",
                        created_by=user_id,
                        updated_by=user_id,
                    ))

                db.commit()
                logger.info(f"Created course family (course-level model): {config.path} (ID: {family.id})")
                return {
                    "course_family_id": str(family.id),
                    "status": "created",
                    "name": family_config.get("name"),
                    "provider_entity_id": None,
                }

            from ..git_provider import _decrypt
            token = _decrypt(provider_row.token)

            if provider_row.type == "gitlab":
                builder = GitLabBuilder(db, provider_row.url, token)
                result = builder._create_course_family(config, org, user_id)
                if not result["success"]:
                    raise RuntimeError(f"Course family creation failed: {result.get('error')}")
                db.commit()
                return {
                    "course_family_id": str(result["course_family"].id) if result.get("course_family") else None,
                    "status": "created",
                    "name": family_config.get("name"),
                    "provider_entity_id": str(result["gitlab_group"].id) if result.get("gitlab_group") else None,
                }
            elif provider_row.type == "forgejo":
                from ..git_provider.forgejo import ForgejoProviderClient
                client = ForgejoProviderClient(provider_row.url, token)
                # For Forgejo, we need the family DB entity first
                from ..repositories.course_family import CourseFamilyRepository
                family = CourseFamilyRepository(db).get_or_create(config, org, user_id)
                provider_result = client.setup_course_family(config, org, family, user_id)
                from sqlalchemy.orm.attributes import flag_modified
                props = family.properties or {}
                props.update(provider_result.properties)
                family.properties = props
                flag_modified(family, "properties")
                db.commit()
                return {
                    "course_family_id": str(family.id),
                    "status": "created",
                    "name": family_config.get("name"),
                    "provider_entity_id": provider_result.provider_entity_id,
                }
            else:
                raise NotImplementedError(f"Provider type {provider_row.type!r} not supported")

    except Exception as e:
        logger.exception(f"Exception in course family creation activity: {e}")
        raise


@activity.defn(name="create_course_activity")
async def create_course_activity(
    course_config: Dict[str, Any],
    course_family_id: str,
    user_id: str,
) -> Dict[str, Any]:
    from ..model.git_provider import GitProvider
    from ..generator.gitlab_builder import GitLabBuilder

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

            provider_row = db.query(GitProvider).filter(GitProvider.organization_id == str(org.id)).first()
            if not provider_row:
                # New course-level git model: no legacy org-scoped GitProvider.
                # Create the course row, then bind it to a registry git server if
                # one was chosen at creation. Git is per-course now — not inherited
                # from the org/family. Authorization happened at the API edge.
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
                # immediately (assign examples, release, ...). The legacy GitLab
                # path relied on group-membership sync; the course-level model
                # records ownership directly. Idempotent on unique (user_id, course_id).
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
                if git_cfg.get("git_server_id"):
                    from computor_types.course_git import CourseGitBindingUpsert
                    from ..business_logic.course_git import _apply_course_git_binding

                    binding = _apply_course_git_binding(
                        course,
                        CourseGitBindingUpsert(
                            delivery=git_cfg.get("delivery") or "git",
                            git_server_id=git_cfg.get("git_server_id"),
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

            from ..git_provider import _decrypt
            token = _decrypt(provider_row.token)

            if provider_row.type == "gitlab":
                builder = GitLabBuilder(db, provider_row.url, token)
                result = builder._create_course(config, org, family, user_id)
                if not result["success"]:
                    raise RuntimeError(f"Course creation failed: {result.get('error')}")
                db.commit()
                return {
                    "course_id": str(result["course"].id) if result.get("course") else None,
                    "status": "created",
                    "name": course_config.get("name"),
                    "provider_entity_id": str(result["gitlab_group"].id) if result.get("gitlab_group") else None,
                }
            elif provider_row.type == "forgejo":
                from ..git_provider.forgejo import ForgejoProviderClient
                client = ForgejoProviderClient(provider_row.url, token)
                from ..repositories.course import CourseRepository
                course = CourseRepository(db).get_or_create(config, org, family, user_id)
                provider_result = client.setup_course(config, org, family, course, user_id)
                from sqlalchemy.orm.attributes import flag_modified
                props = course.properties or {}
                props.update(provider_result.properties)
                course.properties = props
                flag_modified(course, "properties")
                db.commit()
                return {
                    "course_id": str(course.id),
                    "status": "created",
                    "name": course_config.get("name"),
                    "provider_entity_id": provider_result.provider_entity_id,
                }
            else:
                raise NotImplementedError(f"Provider type {provider_row.type!r} not supported")

    except Exception as e:
        logger.exception(f"Exception in course creation activity: {e}")
        raise


# Workflows
@register_task
@workflow.defn(name="create_organization", sandboxed=False)
class CreateOrganizationWorkflow(BaseWorkflow):
    """Workflow for creating an organization."""

    @classmethod
    def get_name(cls) -> str:
        return "create_organization"

    @classmethod
    def get_task_queue(cls) -> str:
        return "computor-tasks"

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(minutes=10)

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        """
        Create organization workflow.

        Args:
            parameters: Dictionary containing:
                - org_config: Organization configuration
                - gitlab_url: GitLab URL
                - gitlab_token: GitLab access token
                - user_id: User ID creating the organization
        """
        required_params = ['org_config', 'git_provider_type', 'git_provider_url', 'git_provider_token', 'user_id']
        missing_params = [param for param in required_params if not parameters.get(param)]
        if missing_params:
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            workflow.logger.error(error_msg)
            return WorkflowResult(
                status="failed",
                result=None,
                error=error_msg,
                metadata={"workflow_type": "create_organization"}
            )

        org_config = parameters.get('org_config', {})
        git_provider_type = parameters.get('git_provider_type')
        git_provider_url = parameters.get('git_provider_url')
        git_provider_token = parameters.get('git_provider_token')
        user_id = parameters.get('user_id')

        if not org_config.get('name') or not org_config.get('path'):
            error_msg = "Organization config must include 'name' and 'path'"
            workflow.logger.error(error_msg)
            return WorkflowResult(
                status="failed",
                result=None,
                error=error_msg,
                metadata={"workflow_type": "create_organization"}
            )

        workflow.logger.info(f"Creating organization: {org_config.get('name')}")

        try:
            result = await workflow.execute_activity(
                create_organization_activity,
                args=[org_config, git_provider_type, git_provider_url, git_provider_token, user_id],
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
                metadata={"workflow_type": "create_organization"}
            )

        except Exception as e:
            workflow.logger.error(f"Organization creation failed: {str(e)}")
            return WorkflowResult(
                status="failed",
                result=None,
                error=str(e),
                metadata={"workflow_type": "create_organization"}
            )


@register_task
@workflow.defn(name="create_course_family", sandboxed=False)
class CreateCourseFamilyWorkflow(BaseWorkflow):
    """Workflow for creating a course family."""

    @classmethod
    def get_name(cls) -> str:
        return "create_course_family"

    @classmethod
    def get_task_queue(cls) -> str:
        return "computor-tasks"

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(minutes=10)

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        """
        Create course family workflow.

        Args:
            parameters: Dictionary containing:
                - family_config: Course family configuration
                - organization_id: Parent organization ID
                - user_id: User ID creating the course family
        """
        required_params = ['family_config', 'organization_id', 'user_id']
        missing_params = [param for param in required_params if not parameters.get(param)]
        if missing_params:
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            workflow.logger.error(error_msg)
            return WorkflowResult(
                status="failed",
                result=None,
                error=error_msg,
                metadata={"workflow_type": "create_course_family"}
            )

        family_config = parameters.get('family_config', {})
        organization_id = parameters.get('organization_id')
        user_id = parameters.get('user_id')

        if not family_config.get('name') or not family_config.get('path'):
            error_msg = "Course family config must include 'name' and 'path'"
            workflow.logger.error(error_msg)
            return WorkflowResult(
                status="failed",
                result=None,
                error=error_msg,
                metadata={"workflow_type": "create_course_family"}
            )

        workflow.logger.info(f"Creating course family: {family_config.get('name')}")

        try:
            result = await workflow.execute_activity(
                create_course_family_activity,
                args=[family_config, organization_id, user_id],
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
                metadata={"workflow_type": "create_course_family"}
            )

        except Exception as e:
            workflow.logger.error(f"Course family creation failed: {str(e)}")
            return WorkflowResult(
                status="failed",
                result=None,
                error=str(e),
                metadata={"workflow_type": "create_course_family"}
            )


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
    Orchestrator workflow that chains existing workflows to deploy a complete
    organization -> course family -> course hierarchy from a deployment configuration.

    This workflow reuses the CreateOrganizationWorkflow, CreateCourseFamilyWorkflow,
    and CreateCourseWorkflow to create the full hierarchy from a YAML configuration.
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
        Execute the hierarchical deployment orchestration.

        Deploys multiple organizations, each containing multiple course families and courses.

        Args:
            parameters: Dictionary containing:
                - deployment_config: Hierarchical deployment configuration with organizations list
                - user_id: ID of the user initiating the deployment
        """
        if not parameters.get('deployment_config') or not parameters.get('user_id'):
            error_msg = "Missing required parameters: deployment_config and user_id"
            workflow.logger.error(error_msg)
            return WorkflowResult(
                status="failed",
                result=None,
                error=error_msg,
                metadata={"workflow_type": "deploy_computor_hierarchy"}
            )

        deployment_config = parameters['deployment_config']
        user_id = parameters['user_id']

        # Track created entities
        created_entities = {
            "organizations": [],
            "course_families": [],
            "courses": []
        }

        try:
            workflow.logger.info("Starting hierarchical deployment orchestration")

            organizations = deployment_config.get("organizations", [])
            if not organizations:
                raise Exception("No organizations specified in deployment configuration")

            total_orgs = len(organizations)
            total_families = sum(len(org.get("course_families", [])) for org in organizations)
            total_courses = sum(
                len(family.get("courses", []))
                for org in organizations
                for family in org.get("course_families", [])
            )

            workflow.logger.info(f"Deploying {total_orgs} organizations, {total_families} course families, {total_courses} courses")

            # Process each organization
            for org_idx, org_config in enumerate(organizations):
                workflow.logger.info(f"Processing organization {org_idx + 1}/{total_orgs}: {org_config['name']}")

                # Prepare git provider configuration for this organization
                git_provider_cfg = org_config.get("git_provider", {})
                git_provider_type = git_provider_cfg.get("type", "gitlab")
                git_provider_url = git_provider_cfg.get("url", "")
                git_provider_token = git_provider_cfg.get("token", "")

                # Handle environment variable substitution in token
                if git_provider_token.startswith("${") and git_provider_token.endswith("}"):
                    import os
                    env_var = git_provider_token[2:-1]
                    git_provider_token = os.environ.get(env_var, "")

                # Create organization
                org_params = {
                    "org_config": org_config,
                    "git_provider_type": git_provider_type,
                    "git_provider_url": git_provider_url,
                    "git_provider_token": git_provider_token,
                    "user_id": user_id
                }

                org_workflow_handle = await workflow.start_child_workflow(
                    CreateOrganizationWorkflow.run,
                    args=[org_params],
                    id=f"create-org-{org_idx}-{workflow.info().workflow_id}",
                    task_queue="computor-tasks",
                    execution_timeout=timedelta(minutes=10)
                )

                org_result = await org_workflow_handle
                if org_result.status != "completed":
                    raise Exception(f"Organization '{org_config['name']}' creation failed: {org_result.error}")

                created_entities["organizations"].append(org_result.result)
                org_id = org_result.result.get("organization_id")

                # Process course families for this organization
                course_families = org_config.get("course_families", [])
                for family_idx, family_config in enumerate(course_families):
                    workflow.logger.info(f"Processing course family {family_idx + 1}/{len(course_families)}: {family_config['name']}")

                    family_params = {
                        "family_config": family_config,
                        "organization_id": org_id,
                        "user_id": user_id
                    }

                    family_workflow_handle = await workflow.start_child_workflow(
                        CreateCourseFamilyWorkflow.run,
                        args=[family_params],
                        id=f"create-family-{org_idx}-{family_idx}-{workflow.info().workflow_id}",
                        task_queue="computor-tasks",
                        execution_timeout=timedelta(minutes=10)
                    )

                    family_result = await family_workflow_handle
                    if family_result.status != "completed":
                        raise Exception(f"Course family '{family_config['name']}' creation failed: {family_result.error}")

                    created_entities["course_families"].append(family_result.result)
                    family_id = family_result.result.get("course_family_id")

                    # Process courses for this course family
                    courses = family_config.get("courses", [])
                    for course_idx, course_config in enumerate(courses):
                        workflow.logger.info(f"Processing course {course_idx + 1}/{len(courses)}: {course_config['name']}")

                        course_params = {
                            "course_config": course_config,
                            "course_family_id": family_id,
                            "user_id": user_id
                        }

                        course_workflow_handle = await workflow.start_child_workflow(
                            CreateCourseWorkflow.run,
                            args=[course_params],
                            id=f"create-course-{org_idx}-{family_idx}-{course_idx}-{workflow.info().workflow_id}",
                            task_queue="computor-tasks",
                            execution_timeout=timedelta(minutes=10)
                        )

                        course_result = await course_workflow_handle
                        if course_result.status != "completed":
                            raise Exception(f"Course '{course_config['name']}' creation failed: {course_result.error}")

                        created_entities["courses"].append(course_result.result)

            workflow.logger.info(f"Hierarchical deployment completed: {total_orgs} orgs, {total_families} families, {total_courses} courses")

            return WorkflowResult(
                status="completed",
                result={
                    "created_entities": created_entities,
                    "counts": {
                        "organizations": total_orgs,
                        "course_families": total_families,
                        "courses": total_courses
                    }
                },
                metadata={"workflow_type": "deploy_computor_hierarchy"}
            )

        except Exception as e:
            error_msg = f"Deployment orchestration failed: {str(e)}"
            workflow.logger.error(error_msg, exc_info=True)
            return WorkflowResult(
                status="failed",
                result=created_entities,
                error=error_msg,
                metadata={"workflow_type": "deploy_computor_hierarchy"}
            )


WORKFLOWS = [
    CreateOrganizationWorkflow,
    CreateCourseFamilyWorkflow,
    CreateCourseWorkflow,
    DeployComputorHierarchyWorkflow,
]

ACTIVITIES = [
    create_organization_activity,
    create_course_family_activity,
    create_course_activity,
]

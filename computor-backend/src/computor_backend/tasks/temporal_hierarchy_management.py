"""
Temporal workflows for organization, course family, and course hierarchy management.
"""
import logging
from datetime import timedelta
from typing import Dict, Any, Optional
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from sqlalchemy.orm import Session

from .temporal_base import BaseWorkflow, WorkflowResult
from .registry import register_task
from computor_types.deployments import ComputorDeploymentConfig, OrganizationConfig, GitLabConfig, CourseFamilyConfig, CourseConfig
from ..database import get_db
from ..model.organization import Organization
from ..model.course import CourseFamily, Course
# transform_localhost_url removed - transformation now done in GitLabBuilder

logger = logging.getLogger(__name__)


# Activities
@activity.defn(name="create_organization_activity")
async def create_organization_activity(
    org_config: Dict[str, Any],
    gitlab_url: str,
    gitlab_token: str,
    user_id: str
) -> Dict[str, Any]:
    """Activity to create an organization using GitLabBuilder."""
    # Import GitLabBuilder inside activity to avoid workflow sandbox restrictions
    from ..generator.gitlab_builder import GitLabBuilder
    
    logger.info(f"Starting organization creation activity for: {org_config.get('name')}")
    logger.info(f"GitLab URL: {gitlab_url}")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Org config: {org_config}")
    
    try:
        # Keep original URL for database storage
        logger.info(f"Using GitLab URL: {gitlab_url}")
        
        # Convert dict to proper config objects
        gitlab_config = GitLabConfig(
            url=gitlab_url,
            token=gitlab_token,
            parent=org_config.get("gitlab", {}).get("parent"),
            path=org_config.get("path")
        )
        
        org_config_obj = OrganizationConfig(
            name=org_config.get("name"),
            path=org_config.get("path"),
            description=org_config.get("description", ""),
            gitlab=gitlab_config
        )
        
        # Create minimal dummy objects for required fields
        dummy_course_family = CourseFamilyConfig(
            name="temp",
            path="temp",
            description=""
        )
        
        dummy_course = CourseConfig(
            name="temp", 
            path="temp",
            description=""
        )
        
        deployment_config = ComputorDeploymentConfig(
            organization=org_config_obj,
            courseFamily=dummy_course_family,
            course=dummy_course
        )
        
        # Create the builder and organization
        logger.info("Creating database session and GitLab builder")
        db_gen = get_db()
        db = next(db_gen)
        try:
            logger.info("Database session created successfully")
            builder = GitLabBuilder(db, gitlab_url, gitlab_token)
            logger.info("GitLab builder created successfully")
            
            logger.info("Calling _create_organization method")
            result = builder._create_organization(deployment_config, user_id)
            logger.info(f"Organization creation result: {result}")
            
            if result["success"]:
                # Commit the transaction to save the organization
                db.commit()
                
                response = {
                    "organization_id": result["organization"].id if result["organization"] else None,
                    "status": "created",
                    "name": org_config.get("name"),
                    "gitlab_group_id": result["gitlab_group"].id if result["gitlab_group"] else None,
                    "gitlab_created": result["gitlab_created"],
                    "db_created": result["db_created"]
                }
                logger.info(f"Returning success response: {response}")
                return response
            else:
                error_response = {
                    "organization_id": None,
                    "status": "failed",
                    "name": org_config.get("name"),
                    "error": result.get("error", "Unknown error occurred")
                }
                logger.error(f"Organization creation failed: {error_response}")
                return error_response
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
                
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Exception in organization creation activity: {error_msg}")
        error_response = {
            "organization_id": None,
            "status": "failed", 
            "name": org_config.get("name"),
            "error": error_msg
        }
        logger.error(f"Returning error response: {error_response}")
        return error_response


@activity.defn(name="create_course_family_activity")
async def create_course_family_activity(
    family_config: Dict[str, Any],
    organization_id: str,
    user_id: str
) -> Dict[str, Any]:
    """Activity to create a course family using GitLabBuilder."""
    # Import GitLabBuilder inside activity to avoid workflow sandbox restrictions
    from ..generator.gitlab_builder import GitLabBuilder
    
    logger.info(f"Starting course family creation activity for: {family_config.get('name')}")
    logger.info(f"Organization ID: {organization_id}")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Family config: {family_config}")
    
    try:
        # Get organization from database to inherit GitLab credentials
        db_gen = get_db()
        db = next(db_gen)
        try:
            org = db.query(Organization).filter(Organization.id == organization_id).first()
            if not org:
                raise ValueError(f"Organization {organization_id} not found")
            
            # Extract GitLab config from organization
            logger.info(f"🔍 DEBUG: Organization properties: {org.properties}")
            org_gitlab = org.properties.get("gitlab", {}) if org.properties else {}
            logger.info(f"🔍 DEBUG: GitLab config: {org_gitlab}")
            
            gitlab_url = org_gitlab.get("url")
            encrypted_token = org_gitlab.get("token")
            
            logger.info(f"🔍 DEBUG: GitLab URL: {gitlab_url}")
            logger.info(f"🔍 DEBUG: Has encrypted token: {bool(encrypted_token)}")
            
            if not gitlab_url or not encrypted_token:
                logger.error(f"❌ Organization {org.title} is missing GitLab configuration:")
                logger.error(f"   - Has properties: {bool(org.properties)}")
                logger.error(f"   - Has gitlab config: {'gitlab' in (org.properties or {})}")
                logger.error(f"   - Has URL: {bool(gitlab_url)}")
                logger.error(f"   - Has token: {bool(encrypted_token)}")
                raise ValueError("Organization missing GitLab configuration")
            
            # Decrypt the GitLab token
            from computor_types.tokens import decrypt_api_key
            try:
                gitlab_token = decrypt_api_key(encrypted_token)
            except Exception as e:
                raise ValueError(f"Failed to decrypt GitLab token: {str(e)}")
                
            # Keep original URL for database storage
            logger.info(f"Using GitLab URL: {gitlab_url}")
            
            # Create course family config objects
            gitlab_config = GitLabConfig(
                url=gitlab_url,
                token=gitlab_token,
                parent=org_gitlab.get("group_id"),
                path=family_config.get("path")
            )
            
            family_config_obj = CourseFamilyConfig(
                name=family_config.get("name"),
                path=family_config.get("path"),
                description=family_config.get("description", "")
            )
            
            # Create minimal dummy objects for required fields
            dummy_org = OrganizationConfig(
                name=org.title or str(org.path),  # Organizations use 'title' not 'name'
                path=str(org.path),  # Convert Ltree to string
                description=org.description or "",
                gitlab=gitlab_config
            )
            
            dummy_course = CourseConfig(
                name="temp", 
                path="temp",
                description=""
            )
            
            deployment_config = ComputorDeploymentConfig(
                organization=dummy_org,
                courseFamily=family_config_obj,
                course=dummy_course
            )
            
            # Create the builder and course family
            builder = GitLabBuilder(db, gitlab_url, gitlab_token)
            result = builder._create_course_family(deployment_config, org, user_id)
            
            if result["success"]:
                # Commit the transaction to save the course family
                db.commit()
                
                response = {
                    "course_family_id": result["course_family"].id if result["course_family"] else None,
                    "status": "created",
                    "name": family_config.get("name"),
                    "gitlab_group_id": result["gitlab_group"].id if result["gitlab_group"] else None,
                    "gitlab_created": result["gitlab_created"],
                    "db_created": result["db_created"]
                }
                logger.info(f"Returning success response: {response}")
                return response
            else:
                error_response = {
                    "course_family_id": None,
                    "status": "failed",
                    "name": family_config.get("name"),
                    "error": result.get("error", "Unknown error occurred")
                }
                logger.error(f"Course family creation failed: {error_response}")
                return error_response
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
                
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Exception in course family creation activity: {error_msg}")
        error_response = {
            "course_family_id": None,
            "status": "failed", 
            "name": family_config.get("name"),
            "error": error_msg
        }
        logger.error(f"Returning error response: {error_response}")
        return error_response


@activity.defn(name="create_course_activity")
async def create_course_activity(
    course_config: Dict[str, Any],
    course_family_id: str,
    user_id: str
) -> Dict[str, Any]:
    """Activity to create a course using GitLabBuilder."""
    # Import GitLabBuilder inside activity to avoid workflow sandbox restrictions
    from ..generator.gitlab_builder import GitLabBuilder
    
    logger.info(f"Starting course creation activity for: {course_config.get('name')}")
    logger.info(f"Course Family ID: {course_family_id}")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Course config: {course_config}")
    
    try:
        # Get course family from database to inherit GitLab credentials
        db_gen = get_db()
        db = next(db_gen)
        try:
            family = db.query(CourseFamily).filter(CourseFamily.id == course_family_id).first()
            if not family:
                raise ValueError(f"Course family {course_family_id} not found")
            
            # Get organization for GitLab config
            org = db.query(Organization).filter(Organization.id == family.organization_id).first()
            if not org:
                raise ValueError(f"Organization {family.organization_id} not found")
            
            # Extract GitLab config from organization and course family
            org_gitlab = org.properties.get("gitlab", {}) if org.properties else {}
            family_gitlab = family.properties.get("gitlab", {}) if family.properties else {}
            
            gitlab_url = org_gitlab.get("url")
            encrypted_token = org_gitlab.get("token")
            
            if not gitlab_url or not encrypted_token:
                raise ValueError("Organization missing GitLab configuration")
            
            # Decrypt the GitLab token
            from computor_types.tokens import decrypt_api_key
            try:
                gitlab_token = decrypt_api_key(encrypted_token)
            except Exception as e:
                raise ValueError(f"Failed to decrypt GitLab token: {str(e)}")
                
            # Keep original URL for database storage
            logger.info(f"Using GitLab URL: {gitlab_url}")
            
            # Create course config objects
            gitlab_config = GitLabConfig(
                url=gitlab_url,
                token=gitlab_token,
                parent=family_gitlab.get("group_id"),
                path=course_config.get("path")
            )
            
            course_config_obj = CourseConfig(
                name=course_config.get("name"),
                path=course_config.get("path"),
                description=course_config.get("description", "")
            )
            
            # Create config objects for required fields
            org_config = OrganizationConfig(
                name=org.title or str(org.path),  # Organizations use 'title' not 'name'
                path=str(org.path),  # Convert Ltree to string
                description=org.description or "",
                gitlab=gitlab_config
            )
            
            family_config_obj = CourseFamilyConfig(
                name=family.title or str(family.path),  # Course families use 'title' not 'name'
                path=str(family.path),  # Convert Ltree to string
                description=family.description or ""
            )
            
            deployment_config = ComputorDeploymentConfig(
                organization=org_config,
                courseFamily=family_config_obj,
                course=course_config_obj
            )
            
            # Create the builder and course
            builder = GitLabBuilder(db, gitlab_url, gitlab_token)
            result = builder._create_course(deployment_config, org, family, user_id)
            
            if result["success"]:
                # Commit the transaction to save the course
                db.commit()
                
                response = {
                    "course_id": result["course"].id if result["course"] else None,
                    "status": "created",
                    "name": course_config.get("name"),
                    "gitlab_group_id": result["gitlab_group"].id if result["gitlab_group"] else None,
                    "gitlab_created": result["gitlab_created"],
                    "db_created": result["db_created"]
                }
                logger.info(f"Returning success response: {response}")
                return response
            else:
                error_response = {
                    "course_id": None,
                    "status": "failed",
                    "name": course_config.get("name"),
                    "error": result.get("error", "Unknown error occurred")
                }
                logger.error(f"Course creation failed: {error_response}")
                return error_response
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
                
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Exception in course creation activity: {error_msg}")
        error_response = {
            "course_id": None,
            "status": "failed", 
            "name": course_config.get("name"),
            "error": error_msg
        }
        logger.error(f"Returning error response: {error_response}")
        return error_response


@activity.defn(name="create_course_content_types_activity")
async def create_course_content_types_activity(
    course_id: str,
    content_types_config: list,
    user_id: str
) -> Dict[str, Any]:
    """Activity to create course content types for a course."""
    from ..model.course import CourseContentType
    
    logger.info(f"🎯 CONTENT TYPES ACTIVITY CALLED!")
    logger.info(f"Creating course content types for course: {course_id}")
    logger.info(f"Content types config: {content_types_config}")
    logger.info(f"User ID: {user_id}")
    
    try:
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            created_types = []
            
            for content_type_config in content_types_config:
                logger.info(f"Creating content type: {content_type_config}")
                
                # Check if content type already exists
                existing_type = db.query(CourseContentType).filter(
                    CourseContentType.course_id == course_id,
                    CourseContentType.slug == content_type_config["slug"]
                ).first()
                
                if existing_type:
                    logger.info(f"Content type already exists: {content_type_config['slug']}")
                    created_types.append({
                        "id": str(existing_type.id),
                        "slug": existing_type.slug,
                        "status": "exists"
                    })
                    continue
                
                # Create new content type
                content_type = CourseContentType(
                    slug=content_type_config["slug"],
                    title=content_type_config.get("title"),
                    description=content_type_config.get("description"),
                    color=content_type_config.get("color", "green"),
                    properties=content_type_config.get("properties", {}),
                    course_id=course_id,
                    course_content_kind_id=content_type_config.get("kind", content_type_config.get("course_content_kind_id")),
                    created_by=user_id,
                    updated_by=user_id
                )
                
                db.add(content_type)
                db.flush()  # Get the ID
                
                created_types.append({
                    "id": str(content_type.id),
                    "slug": content_type.slug,
                    "status": "created"
                })
                
                logger.info(f"Created content type: {content_type.slug} with ID: {content_type.id}")
            
            db.commit()
            
            response = {
                "status": "success",
                "course_id": course_id,
                "content_types": created_types,
                "total_created": len([ct for ct in created_types if ct["status"] == "created"]),
                "total_existing": len([ct for ct in created_types if ct["status"] == "exists"])
            }
            
            logger.info(f"Course content types creation completed: {response}")
            return response
            
        except Exception as e:
            db.rollback()
            error_msg = str(e)
            logger.exception(f"Database error in course content types creation: {error_msg}")
            error_response = {
                "status": "failed",
                "course_id": course_id,
                "error": error_msg,
                "content_types": []
            }
            return error_response
            
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Exception in course content types creation activity: {error_msg}")
        return {
            "status": "failed",
            "course_id": course_id,
            "error": error_msg,
            "content_types": []
        }


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
            
        Returns:
            WorkflowResult
        """
        # Validate required parameters
        required_params = ['org_config', 'gitlab_url', 'gitlab_token', 'user_id']
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
        
        # Extract parameters
        org_config = parameters.get('org_config', {})
        gitlab_url = parameters.get('gitlab_url')
        gitlab_token = parameters.get('gitlab_token')
        user_id = parameters.get('user_id')
        
        # Validate organization config
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
            # Execute creation activity
            result = await workflow.execute_activity(
                create_organization_activity,
                args=[org_config, gitlab_url, gitlab_token, user_id],
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
            
        Returns:
            WorkflowResult
        """
        # Validate required parameters
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
        
        # Extract parameters
        family_config = parameters.get('family_config', {})
        organization_id = parameters.get('organization_id')
        user_id = parameters.get('user_id')
        
        # Validate course family config
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
            # Execute creation activity
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
            
        Returns:
            WorkflowResult
        """
        # Validate required parameters
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
        
        # Extract parameters
        course_config = parameters.get('course_config', {})
        course_family_id = parameters.get('course_family_id')
        user_id = parameters.get('user_id')
        
        # Validate course config
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
            # Execute creation activity
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
            
        Returns:
            WorkflowResult with deployment status and created entity IDs
        """
        # Validate required parameters
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
        
        try:
            workflow.logger.info("Starting hierarchical deployment orchestration")
            
            # Track created entities
            created_entities = {
                "organizations": [],
                "course_families": [],
                "courses": [],
                "content_types": []
            }
            
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
                
                # Prepare GitLab configuration for this organization
                # NOTE: This reads from deployment YAML, not database - token is not encrypted yet
                gitlab_config = org_config.get("gitlab", {})
                gitlab_url = gitlab_config.get("url", "")
                gitlab_token = gitlab_config.get("token", "")
                
                # Handle environment variable substitution
                if gitlab_token.startswith("${") and gitlab_token.endswith("}"):
                    import os
                    env_var = gitlab_token[2:-1]
                    gitlab_token = os.environ.get(env_var, "")
                
                # Create organization
                org_params = {
                    "org_config": org_config,
                    "gitlab_url": gitlab_url,
                    "gitlab_token": gitlab_token,
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
                    
                    # Create course family
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
                        
                        # Create course
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
                        workflow.logger.info(f"Course creation result: {course_result}")
                        
                        if course_result.status != "completed":
                            raise Exception(f"Course '{course_config['name']}' creation failed: {course_result.error}")
                        
                        created_entities["courses"].append(course_result.result)
                        
                        # Create content types if configured
                        content_types = course_config.get('content_types', [])
                        workflow.logger.info(f"Found {len(content_types)} content types for course: {course_config['name']}")
                        
                        if content_types:
                            workflow.logger.info(f"Creating {len(content_types)} content types for course: {course_config['name']}")
                            workflow.logger.info(f"Course result structure: {course_result.result}")
                            
                            course_id = course_result.result.get("course_id") if course_result.result else None
                            workflow.logger.info(f"Extracted course_id: {course_id}")
                            
                            if not course_id:
                                workflow.logger.error(f"No course ID found in result: {course_result.result}")
                                continue
                            
                            content_types_result = await workflow.execute_activity(
                                create_course_content_types_activity,
                                args=[course_id, content_types, user_id],
                                start_to_close_timeout=timedelta(minutes=3),
                                retry_policy=RetryPolicy(
                                    initial_interval=timedelta(seconds=1),
                                    backoff_coefficient=2.0,
                                    maximum_attempts=3,
                                )
                            )
                            
                            created_entities["content_types"].append(content_types_result)
                            
                            if content_types_result.get("status") == "success":
                                workflow.logger.info(f"Created content types for course {course_config['name']}: {content_types_result.get('total_created')} created, {content_types_result.get('total_existing')} existing")
                            else:
                                workflow.logger.error(f"Failed to create content types for course {course_config['name']}: {content_types_result}")
            
            # Calculate content types statistics
            total_content_types_created = sum(r.get("total_created", 0) for r in created_entities["content_types"] if r.get("status") == "success")
            total_content_types_existing = sum(r.get("total_existing", 0) for r in created_entities["content_types"] if r.get("status") == "success")
            
            workflow.logger.info(f"Hierarchical deployment completed: {total_orgs} orgs, {total_families} families, {total_courses} courses, {total_content_types_created} content types created")
            
            return WorkflowResult(
                status="completed",
                result={
                    "created_entities": created_entities,
                    "counts": {
                        "organizations": total_orgs,
                        "course_families": total_families,  
                        "courses": total_courses,
                        "content_types_created": total_content_types_created,
                        "content_types_existing": total_content_types_existing
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

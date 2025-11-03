from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import Annotated, Optional, Dict, Any
from fastapi import Depends, APIRouter
from datetime import datetime, timezone
import logging

from computor_backend.exceptions import (
    BadRequestException,
    NotFoundException,
    ForbiddenException
)
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.core import check_admin, check_course_permissions, check_course_family_permissions
from computor_backend.permissions.principal import Principal

from computor_backend.database import get_db
from computor_types.system import (
    GitLabCredentials,
    OrganizationTaskRequest, CourseFamilyTaskRequest, CourseTaskRequest, TaskResponse,
    GenerateTemplateRequest, GenerateTemplateResponse,
    GenerateAssignmentsRequest, GenerateAssignmentsResponse,
)
from computor_backend.model.course import Course, CourseContent, CourseFamily
from computor_backend.model.organization import Organization
from computor_backend.tasks import get_task_executor, TaskSubmission
from computor_backend.business_logic.release_validation import (
    validate_course_for_release,
    validate_course_contents_for_release
)

system_router = APIRouter()
logger = logging.getLogger(__name__)

def convert_to_gitlab_config(gitlab: GitLabCredentials, parent_group_id: Optional[int], path: str) -> dict:
    """Convert GitLab credentials to config format."""
    config = {
        "url": gitlab.gitlab_url,
        "token": gitlab.gitlab_token,
        "path": path
    }
    if parent_group_id is not None:
        config["parent"] = parent_group_id
    return config

@system_router.post("/deploy/organizations", response_model=TaskResponse)
async def create_organization_async(
    request: OrganizationTaskRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """Create an organization asynchronously using Temporal workflows."""
    
    try:
        # Check permissions
        if not permissions.is_admin:
            raise NotFoundException("Insufficient permissions")
        
        # Convert to organization config format
        org_config = {
            "name": request.organization.get("title", ""),
            "path": request.organization.get("path", ""),
            "description": request.organization.get("description", ""),
            "gitlab": convert_to_gitlab_config(
                request.gitlab,
                request.parent_group_id,
                request.organization.get("path", "")
            )
        }
        
        # Submit task using Temporal
        task_executor = get_task_executor()
        task_submission = TaskSubmission(
            task_name="create_organization",
            parameters={
                "org_config": org_config,
                "gitlab_url": request.gitlab.gitlab_url,
                "gitlab_token": request.gitlab.gitlab_token,
                "user_id": permissions.user_id
            },
            queue="computor-tasks"
        )
        
        task_id = await task_executor.submit_task(task_submission)
        
        return TaskResponse(
            task_id=task_id,
            status="submitted",
            message="Organization creation task submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error submitting organization creation task: {e}")
        raise BadRequestException(f"Failed to submit organization creation task: {str(e)}")

@system_router.post("/deploy/course-families", response_model=TaskResponse)
async def create_course_family_async(
    request: CourseFamilyTaskRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """Create a course family asynchronously using Temporal workflows."""
    
    try:
        # Check permissions
        if not permissions.is_admin:
            raise NotFoundException("Insufficient permissions")
        
        # Validate parent organization exists
        organization = db.query(Organization).filter(Organization.id == request.organization_id).first()
        if not organization:
            raise NotFoundException(f"Organization with ID {request.organization_id} not found")
        
        # Check if organization has GitLab integration
        parent_gitlab_config = organization.properties.get("gitlab", {})
        has_gitlab = bool(parent_gitlab_config.get("group_id"))
        
        # Convert to course family config format
        family_config = {
            "name": request.course_family.get("title", ""),
            "path": request.course_family.get("path", ""),
            "description": request.course_family.get("description", ""),
            "organization_id": request.organization_id,
            "has_gitlab": has_gitlab
        }
        
        # Submit task using Temporal
        # The task will fetch GitLab credentials from the organization
        task_executor = get_task_executor()
        task_submission = TaskSubmission(
            task_name="create_course_family",
            parameters={
                "family_config": family_config,
                "organization_id": request.organization_id,
                "user_id": permissions.user_id
            },
            queue="computor-tasks"
        )
        
        task_id = await task_executor.submit_task(task_submission)
        
        return TaskResponse(
            task_id=task_id,
            status="submitted",
            message="Course family creation task submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error submitting course family creation task: {e}")
        raise BadRequestException(f"Failed to submit course family creation task: {str(e)}")

@system_router.post("/deploy/courses", response_model=TaskResponse)
async def create_course_async(
    request: CourseTaskRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """Create a course asynchronously using Temporal workflows."""
    
    try:
        # Check permissions
        if not permissions.is_admin:
            raise NotFoundException("Insufficient permissions")
        
        # Validate parent course family exists
        course_family = db.query(CourseFamily).filter(CourseFamily.id == request.course_family_id).first()
        if not course_family:
            raise NotFoundException(f"Course family with ID {request.course_family_id} not found")
        
        # Check if course family has GitLab integration
        parent_gitlab_config = course_family.properties.get("gitlab", {})
        has_gitlab = bool(parent_gitlab_config.get("group_id"))
        
        # Convert to course config format
        course_config = {
            "name": request.course.get("title", ""),
            "path": request.course.get("path", ""),
            "description": request.course.get("description", ""),
            "course_family_id": request.course_family_id,
            "has_gitlab": has_gitlab
        }
        
        # Submit task using Temporal
        # The task will fetch GitLab credentials from the course family
        task_executor = get_task_executor()
        task_submission = TaskSubmission(
            task_name="create_course",
            parameters={
                "course_config": course_config,
                "course_family_id": request.course_family_id,
                "user_id": permissions.user_id
            },
            queue="computor-tasks"
        )
        
        task_id = await task_executor.submit_task(task_submission)
        
        return TaskResponse(
            task_id=task_id,
            status="submitted",
            message="Course creation task submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error submitting course creation task: {e}")
        raise BadRequestException(f"Failed to submit course creation task: {str(e)}")

@system_router.post(
    "/courses/{course_id}/generate-student-template",
    response_model=GenerateTemplateResponse
)
async def generate_student_template(
    course_id: str,
    request: GenerateTemplateRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """
    Generate student template from assigned examples (Git operations).
    
    This is step 2 of the two-step process. It triggers a Temporal workflow
    that will:
    1. Download examples from MinIO based on CourseContent assignments
    2. Process them according to meta.yaml rules
    3. Generate the student-template repository
    4. Commit and push the changes
    """
    # Check permissions
    if check_course_permissions(permissions, Course, "_lecturer", db).filter(Course.id == course_id).first() is None:
        raise ForbiddenException(
            detail="Not authorized to generate template for this course",
            context={"course_id": str(course_id)}
        )

    # Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise NotFoundException(
            error_code="NF_003",
            detail="Course not found",
            context={"course_id": str(course_id)}
        )
    
    # Get student-template and assignments URLs
    student_template_url = None
    assignments_url = None
    
    # First check if course has GitLab properties
    if course.properties and "gitlab" in course.properties:
        course_gitlab = course.properties["gitlab"]
        
        # Option 1: Direct URLs stored (backward compatibility)
        if "student_template_url" in course_gitlab:
            student_template_url = course_gitlab["student_template_url"]
        if "assignments_url" in course_gitlab:
            assignments_url = course_gitlab["assignments_url"]
        
        # Option 2: Construct from course's full_path
        if "full_path" in course_gitlab and (not student_template_url or not assignments_url):
            # Get GitLab URL from organization
            if not course.course_family_id:
                raise BadRequestException(
                    error_code="VAL_001",
                    detail="Course missing course family reference",
                    context={"course_id": str(course_id)}
                )

            family = db.query(CourseFamily).filter(CourseFamily.id == course.course_family_id).first()
            if not family or not family.organization_id:
                raise BadRequestException(
                    error_code="VAL_001",
                    detail="Course family or organization not found",
                    context={
                        "course_id": str(course_id),
                        "course_family_id": str(course.course_family_id)
                    }
                )

            org = db.query(Organization).filter(Organization.id == family.organization_id).first()
            if not org or not org.properties or "gitlab" not in org.properties:
                raise BadRequestException(
                    error_code="DEPLOY_003",
                    detail="Organization missing GitLab configuration",
                    context={
                        "organization_id": str(family.organization_id),
                        "course_id": str(course_id)
                    }
                )

            gitlab_url = org.properties["gitlab"].get("url")
            if not gitlab_url:
                raise BadRequestException(
                    error_code="DEPLOY_003",
                    detail="Organization missing GitLab URL",
                    context={"organization_id": str(org.id)}
                )
            
            # Construct URLs: {gitlab_url}/{course_full_path}/student-template and assignments
            if not student_template_url:
                student_template_url = f"{gitlab_url}/{course_gitlab['full_path']}/student-template"
            if not assignments_url:
                assignments_url = f"{gitlab_url}/{course_gitlab['full_path']}/assignments"
    
    if not student_template_url:
        raise BadRequestException(
            error_code="DEPLOY_003",
            detail="Unable to determine student-template repository URL",
            context={
                "course_id": str(course_id),
                "required_fields": ["student_template_url", "full_path"]
            }
        )
    
    # PRE-FLIGHT VALIDATION: Check that selected assignments have valid examples
    # Extract selection parameters from release if available
    course_content_ids = None
    parent_id = None
    include_descendants = True
    all_flag = False

    if request.release:
        course_content_ids = request.release.course_content_ids
        parent_id = request.release.parent_id
        include_descendants = request.release.include_descendants if hasattr(request.release, 'include_descendants') else True
        all_flag = getattr(request.release, 'all', False)

    is_valid, validation_errors = validate_course_for_release(
        course_id=course_id,
        db=db,
        force_redeploy=request.force_redeploy,
        course_content_ids=course_content_ids,
        parent_id=parent_id,
        include_descendants=include_descendants,
        all_flag=all_flag
    )

    if not is_valid:
        logger.error(
            f"Release validation failed for course {course_id}: "
            f"{len(validation_errors)} issues found"
        )
        raise BadRequestException(
            error_code="VAL_001",
            detail="Cannot release course: Some assignments are missing examples or have invalid deployments",
            context={
                "course_id": str(course_id),
                "validation_errors": validation_errors,
                "total_issues": len(validation_errors)
            }
        )

    logger.info(f"Pre-flight validation passed for course {course_id}")

    # Count contents to process - check for deployments instead of example_id
    from computor_backend.model.deployment import CourseContentDeployment

    contents_with_examples = db.query(func.count(CourseContent.id)).filter(
        and_(
            CourseContent.course_id == course_id,
            CourseContent.id.in_(
                db.query(CourseContentDeployment.course_content_id)
                .filter(CourseContentDeployment.deployment_status == 'deployed')
            )
        )
    ).scalar()

    # Use Temporal task executor
    task_executor = get_task_executor()
    
    task_submission = TaskSubmission(
        task_name="generate_student_template_v2",
        parameters={
            "course_id": course_id,
            "student_template_url": student_template_url,
            "assignments_url": assignments_url,
            "commit_message": request.commit_message or f"Update student template - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            "force_redeploy": request.force_redeploy,
            # Pass through optional release selection for strict commit/path control
            "release": (request.release.model_dump() if request.release else None),
        },
        queue="computor-tasks"
    )
    
    workflow_id = await task_executor.submit_task(task_submission)
    
    # Don't update status here - let the workflow handle all status transitions
    # Just count how many deployments are ready to process
    statuses_to_count = ["pending", "failed"]
    if request.force_redeploy:
        statuses_to_count.append("deployed")
    
    deployment_ids = db.query(CourseContentDeployment.id).join(
        CourseContent,
        CourseContentDeployment.course_content_id == CourseContent.id
    ).filter(
        and_(
            CourseContent.course_id == course_id,
            CourseContentDeployment.deployment_status.in_(statuses_to_count)
        )
    ).all()
    
    return GenerateTemplateResponse(
        workflow_id=workflow_id,
        status="started",
        contents_to_process=len(deployment_ids) if deployment_ids else 0
    )

@system_router.post(
    "/courses/{course_id}/generate-assignments",
    response_model=GenerateAssignmentsResponse
)
async def generate_assignments(
    course_id: str,
    request: GenerateAssignmentsRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    # Permissions
    if check_course_permissions(permissions, Course, "_lecturer", db).filter(Course.id == course_id).first() is None:
        raise ForbiddenException(
            detail="Not authorized to generate assignments",
            context={"course_id": str(course_id)}
        )

    # Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise NotFoundException(
            error_code="NF_003",
            detail="Course not found",
            context={"course_id": str(course_id)}
        )

    # Determine assignments URL if not provided
    assignments_url = request.assignments_url
    if not assignments_url and course.properties and 'gitlab' in course.properties:
        course_gitlab = course.properties['gitlab']
        if 'assignments_url' in course_gitlab:
            assignments_url = course_gitlab['assignments_url']
        elif 'full_path' in course_gitlab:
            family = db.query(CourseFamily).filter(CourseFamily.id == course.course_family_id).first()
            if not family:
                raise NotFoundException(
                    error_code="NF_001",
                    detail="Course family not found",
                    context={
                        "course_id": str(course_id),
                        "course_family_id": str(course.course_family_id)
                    }
                )
            org = db.query(Organization).filter(Organization.id == family.organization_id).first()
            gitlab_url = (org.properties or {}).get('gitlab', {}).get('url') if org and org.properties else None
            if gitlab_url:
                assignments_url = f"{gitlab_url}/{course_gitlab['full_path']}/assignments"

    # PRE-FLIGHT VALIDATION: Check that selected assignments have valid examples
    is_valid, validation_errors = validate_course_contents_for_release(
        course_id=course_id,
        course_content_ids=request.course_content_ids if request.course_content_ids else None,
        db=db,
        force_redeploy=False,  # Assignments repository doesn't support force_redeploy
        parent_id=request.parent_id,
        include_descendants=request.include_descendants,
        all_flag=request.all
    )

    if not is_valid:
        logger.error(
            f"Release validation failed for assignments in course {course_id}: "
            f"{len(validation_errors)} issues found"
        )
        raise BadRequestException(
            error_code="VAL_001",
            detail="Cannot release assignments: Some assignments are missing examples or have invalid deployments",
            context={
                "course_id": str(course_id),
                "validation_errors": validation_errors,
                "total_issues": len(validation_errors)
            }
        )

    logger.info(f"Pre-flight validation passed for assignments in course {course_id}")

    # Count selected contents (best-effort)
    contents_q = db.query(func.count(CourseContent.id)).filter(CourseContent.course_id == course_id)
    if request.course_content_ids:
        contents_q = contents_q.filter(CourseContent.id.in_(request.course_content_ids))
    count_estimate = contents_q.scalar()

    # Submit Temporal workflow
    task_executor = get_task_executor()
    selection = {
        'course_content_ids': request.course_content_ids,
        'parent_id': request.parent_id,
        'include_descendants': request.include_descendants,
        'all': request.all,
    }
    task_submission = TaskSubmission(
        task_name="generate_assignments_repository",
        parameters={
            'course_id': course_id,
            'assignments_url': assignments_url,
            'selection': selection,
            'overwrite_strategy': request.overwrite_strategy,
            'commit_message': request.commit_message,
        },
        queue="computor-tasks"
    )
    workflow_id = await task_executor.submit_task(task_submission)

    return GenerateAssignmentsResponse(
        workflow_id=workflow_id,
        status="started",
        contents_to_process=count_estimate or 0
    )

@system_router.post("/course-families/{course_family_id}/sync-documents", response_model=Dict[str, Any])
async def sync_documents_repository(
    course_family_id: str,
    force_update: bool = False,
    permissions: Annotated[Principal, Depends(get_current_principal)] = None,
    db: Session = Depends(get_db)
):
    """
    Sync the documents repository from GitLab to shared filesystem.

    This endpoint triggers a Temporal workflow that:
    1. Clones the documents repository from the course family's GitLab group
    2. Removes the .git directory
    3. Syncs files to ${SYSTEM_DEPLOYMENT_PATH}/shared/documents/{org}/{family}/
    4. Files become accessible via the static-server at /docs/{org}/{family}/

    Args:
        course_family_id: The CourseFamily ID
        force_update: If True, delete existing files and re-clone; if False, update incrementally

    Returns:
        Dict with workflow_id and status
    """
    from ..model.course import CourseFamily

    # Check if user has permissions (lecturer or admin)
    course_family = db.query(CourseFamily).filter(CourseFamily.id == course_family_id).first()
    if not course_family:
        raise NotFoundException(
            detail=f"CourseFamily with id {course_family_id} not found",
            context={"course_family_id": course_family_id}
        )

    # Check permissions - user must be lecturer (or higher: maintainer, owner) in any course of this family, or admin
    check_course_family_permissions(permissions, course_family_id, "_lecturer", db)

    logger.info(f"Syncing documents repository for CourseFamily {course_family_id} (force_update={force_update})")

    # Submit Temporal workflow
    task_executor = get_task_executor()

    task_submission = TaskSubmission(
        task_name="sync_documents_repository",
        parameters={
            "course_family_id": course_family_id,
            "force_update": force_update
        },
        queue="computor-tasks"
    )

    workflow_id = await task_executor.submit_task(task_submission)

    return {
        "workflow_id": workflow_id,
        "status": "started",
        "course_family_id": course_family_id,
        "force_update": force_update,
        "message": f"Documents sync started for course family {course_family.title}"
    }

@system_router.get(
    "/courses/{course_id}/gitlab-status",
    response_model=Dict[str, Any]
)
async def get_course_gitlab_status(
    course_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """
    Check GitLab configuration status for a course.
    
    Returns information about GitLab integration and what's missing.
    """
    # Check permissions
    if check_course_permissions(permissions, Course, "_lecturer", db).filter(Course.id == course_id).first() is None:
        raise ForbiddenException(
            detail="Not authorized to view this course",
            context={"course_id": str(course_id)}
        )

    # Get course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise NotFoundException(
            error_code="NF_003",
            detail="Course not found",
            context={"course_id": str(course_id)}
        )
    
    # Check GitLab configuration
    status = {
        "course_id": course_id,
        "has_gitlab_config": False,
        "has_group_id": False,
        "has_student_template_url": False,
        "gitlab_config": {},
        "missing_items": [],
        "recommendations": []
    }
    
    if course.properties and "gitlab" in course.properties:
        status["has_gitlab_config"] = True
        gitlab_props = course.properties["gitlab"]
        
        # Check for group ID
        if "group_id" in gitlab_props:
            status["has_group_id"] = True
            status["gitlab_config"]["group_id"] = gitlab_props["group_id"]
        else:
            status["missing_items"].append("GitLab group ID")
            
        # Check for student template URL
        if "student_template_url" in gitlab_props:
            status["has_student_template_url"] = True
            status["gitlab_config"]["student_template_url"] = gitlab_props["student_template_url"]
        else:
            status["missing_items"].append("Student template repository URL")
            
        # Check for other GitLab properties
        if "projects" in gitlab_props:
            status["gitlab_config"]["projects"] = gitlab_props["projects"]
            
    else:
        status["missing_items"].append("GitLab configuration")
        
    # Get course family for additional context
    if course.course_family_id:
        family = db.query(CourseFamily).filter(CourseFamily.id == course.course_family_id).first()
        if family and family.properties and "gitlab" in family.properties:
            status["course_family_gitlab"] = {
                "has_config": True,
                "group_id": family.properties["gitlab"].get("group_id")
            }
            
    # Add recommendations
    if not status["has_gitlab_config"]:
        status["recommendations"].append(
            "The course needs to be created with GitLab integration enabled. "
            "Please recreate the course or contact an administrator to enable GitLab integration."
        )
    elif not status["has_student_template_url"]:
        status["recommendations"].append(
            "The course has partial GitLab configuration but is missing the student-template repository. "
            "The course may need to be recreated or the GitLab projects need to be created manually."
        )
        
    status["can_generate_template"] = status["has_student_template_url"]
    
    return status

# DEPLOYMENT CONFIGURATION ENDPOINTS

@system_router.post("/hierarchy/create", response_model=dict)
async def create_hierarchy(
    payload: dict,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """
    Create a complete organization -> course family -> course hierarchy from a configuration.
    
    This endpoint accepts a deployment configuration and creates the entire hierarchy
    using the DeployComputorHierarchyWorkflow Temporal workflow.
    """
    # Check admin permissions
    if not check_admin(permissions):
        raise ForbiddenException(
            detail="Only administrators can deploy configurations",
            context={"operation": "create_hierarchy"}
        )

    # Extract configuration
    deployment_config = payload.get("deployment_config")
    validate_only = payload.get("validate_only", False)

    if not deployment_config:
        raise BadRequestException(
            error_code="VAL_002",
            detail="deployment_config is required",
            context={"missing_field": "deployment_config"}
        )
    
    # Validate the configuration structure
    from computor_types.deployments_refactored import ComputorDeploymentConfig
    try:
        config = ComputorDeploymentConfig(**deployment_config)
    except Exception as e:
        raise BadRequestException(
            error_code="VAL_001",
            detail=f"Invalid deployment configuration: {str(e)}",
            context={"validation_error": str(e)}
        )
    
    if validate_only:
        return {
            "status": "validated",
            "message": "Configuration is valid",
            "deployment_path": config.get_full_course_path()
        }
    
    # Submit to Temporal workflow
    task_executor = get_task_executor()
    
    task_submission = TaskSubmission(
        task_name="deploy_computor_hierarchy",
        parameters={
            "deployment_config": config.model_dump(),
            "user_id": permissions.user_id
        },
        queue="computor-tasks"
    )
    
    workflow_id = await task_executor.submit_task(task_submission)
    
    # Get first organization name for message
    org_name = config.organizations[0].name if config.organizations else "Unknown Organization"
    
    return {
        "workflow_id": workflow_id,
        "status": "started",
        "deployment_path": config.get_full_course_path(),
        "message": f"Deployment started for {org_name}"
    }

@system_router.get("/hierarchy/status/{workflow_id}", response_model=dict)
async def get_hierarchy_status(
    workflow_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)]
):
    """
    Get the status of a deployment workflow.
    
    Returns the current status of the deployment workflow, including any errors
    or the final result if completed.
    """
    task_executor = get_task_executor()
    
    try:
        # Get workflow status
        result = await task_executor.get_task_status(workflow_id)
        
        if result:
            # Map status to what CLI expects
            status = result.status_display.lower()
            if status == "finished":
                status = "completed"  # CLI expects "completed" not "finished"
            
            return {
                "workflow_id": workflow_id,
                "status": status,
                "error": result.error,
                "result": None,  # TaskInfo doesn't have result field
                "started_at": result.started_at.isoformat() if result.started_at else None,
                "completed_at": result.completed_at.isoformat() if result.completed_at else None
            }
        else:
            return {
                "workflow_id": workflow_id,
                "status": "not_found",
                "error": "Workflow not found or expired"
            }
    except Exception as e:
        logger.error(f"Error getting deployment status: {e}")
        return {
            "workflow_id": workflow_id,
            "status": "error",
            "error": str(e)
        }

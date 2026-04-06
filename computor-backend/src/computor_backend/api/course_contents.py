"""
Refactored course contents API using the new deployment system.

This module handles course content management with clean separation
between content hierarchy and example deployments.
"""

import json
import logging
from typing import Annotated, Optional, Dict, Any
from datetime import datetime

from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, text

logger = logging.getLogger(__name__)


from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal

from computor_backend.custom_types import Ltree
from computor_backend.exceptions import (
    BadRequestException,
    NotFoundException,
    ForbiddenException
)
from computor_backend.database import get_db, get_db_session, set_db_user
from computor_types.course_contents import CourseContentGet
from computor_backend.interfaces import CourseContentInterface
from computor_types.deployment import (
    CourseContentDeploymentGet,
    DeploymentHistoryGet,
    DeploymentWithHistory,
    DeploymentSummary,
)
from computor_backend.api.api_builder import CrudRouter
from computor_backend.model.course import CourseContent, Course
from computor_backend.model.deployment import CourseContentDeployment, DeploymentHistory
from computor_backend.redis_cache import get_redis_client, get_cache
from computor_backend.repositories import (
    CourseContentRepository,
    CourseContentDeploymentRepository,
)
from aiocache import BaseCache

# Create the router
course_content_router = CrudRouter(CourseContentInterface)

def _build_deployment_with_history(
    deployment: CourseContentDeployment,
    db: Session,
) -> DeploymentWithHistory:
    """Serialize a deployment and its history for API responses."""
    # Query DeploymentHistory directly (no repository needed for history queries)
    history = (
        db.query(DeploymentHistory)
        .filter(DeploymentHistory.deployment_id == deployment.id)
        .order_by(DeploymentHistory.created_at.desc())
        .all()
    )

    # Convert deployment to Pydantic model - handle Ltree conversion
    deployment_dict = {
        "id": deployment.id,
        "course_content_id": deployment.course_content_id,
        "example_version_id": deployment.example_version_id,
        "example_identifier": str(deployment.example_identifier) if deployment.example_identifier else None,
        "version_tag": deployment.version_tag,
        "deployment_status": deployment.deployment_status,
        "deployment_message": deployment.deployment_message,
        "assigned_at": deployment.assigned_at,
        "deployed_at": deployment.deployed_at,
        "last_attempt_at": deployment.last_attempt_at,
        "deployment_path": deployment.deployment_path,
        "version_identifier": deployment.version_identifier,
        "deployment_metadata": deployment.deployment_metadata,
        "workflow_id": deployment.workflow_id,
        "created_at": deployment.created_at,
        "updated_at": deployment.updated_at,
        "created_by": deployment.created_by,
        "updated_by": deployment.updated_by,
    }
    deployment_dto = CourseContentDeploymentGet.model_validate(deployment_dict)

    # Convert history entries to Pydantic models - handle Ltree conversion
    history_dtos = []
    for h in history:
        h_dict = {
            "id": h.id,
            "deployment_id": h.deployment_id,
            "action": h.action,
            "example_version_id": h.example_version_id,
            "previous_example_version_id": h.previous_example_version_id,
            "example_identifier": str(h.example_identifier) if h.example_identifier else None,
            "version_tag": h.version_tag,
            "workflow_id": h.workflow_id,
            "created_at": h.created_at,
            "created_by": h.created_by,
        }
        history_dtos.append(DeploymentHistoryGet.model_validate(h_dict))

    return DeploymentWithHistory(
        deployment=deployment_dto,
        history=history_dtos,
    )

# # Event handlers for filesystem mirroring
# # Note: Background task hooks should create their own sessions, not receive them as params
# async def event_wrapper(entity: CourseContentGet, permissions: Principal):
#     try:
#         with get_db_session(permissions.user_id) as db:
#             await mirror_entity_to_filesystem(str(entity.id), CourseContentInterface, db)
#     except Exception as e:
#         print(e)

# Event handler for submission group provisioning
async def provision_submission_groups_wrapper(entity: CourseContentGet, permissions: Principal):
    """
    Provision submission groups for all enrolled students when a new assignment is created.

    This is called as a background task after a CourseContent is created.
    Only creates groups for individual assignments (max_group_size = 1 or None).
    Team assignments (max_group_size > 1) require manual creation or team formation workflow.

    Note: This function creates its own database session to avoid connection leaks.
    Background tasks should never receive sessions from the request scope.
    """
    try:
        from computor_backend.repositories.submission_group_provisioning import (
            provision_submission_groups_for_course_content
        )

        # Create a fresh database session for this background task
        # This ensures proper connection lifecycle management
        with get_db_session(permissions.user_id) as db:
            created_count = provision_submission_groups_for_course_content(
                course_content_id=str(entity.id),
                db=db
            )

            if created_count > 0:
                logger.info(
                    f"Successfully provisioned {created_count} submission groups "
                    f"for CourseContent {entity.id}"
                )
    except Exception as e:
        logger.error(
            f"Error provisioning submission groups for CourseContent {entity.id}: {e}",
            exc_info=True
        )

# course_content_router.on_created.append(event_wrapper)
course_content_router.on_created.append(provision_submission_groups_wrapper)
# course_content_router.on_updated.append(event_wrapper)

@course_content_router.router.delete(
    "/{content_id}/example",
    response_model=Dict[str, str]
)
async def unassign_example_from_content(
    content_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Annotated[BaseCache, Depends(get_redis_client)] = None
):
    """
    Remove example assignment from course content.

    This updates the deployment record to unassigned status.
    The actual removal from student-template happens during next generation.
    """
    # Initialize repositories
    content_repo = CourseContentRepository(db, get_cache())
    deployment_repo = CourseContentDeploymentRepository(db, get_cache())

    # Get course content
    content = content_repo.get_by_id(str(content_id))
    if not content:
        raise NotFoundException(
            error_code="CONTENT_001",
            detail="Course content not found",
            context={"course_content_id": str(content_id)}
        )

    # Check permissions
    if check_course_permissions(permissions, Course, "_maintainer", db).filter(
        Course.id == content.course_id
    ).first() is None:
        raise ForbiddenException(
            detail="Not authorized to modify this course content",
            context={
                "course_content_id": str(content_id),
                "required_permission": "modify_content"
            }
        )

    # Get deployment record
    deployment = deployment_repo.find_by_content(str(content_id))

    if not deployment:
        raise NotFoundException(
            error_code="DEPLOY_001",
            detail="No deployment found for this content",
            context={"course_content_id": str(content_id)}
        )
    
    # Update deployment status
    previous_version_id = deployment.example_version_id
    deployment.example_version_id = None
    deployment.deployment_status = "unassigned"
    deployment.deployment_message = "Example unassigned"
    deployment.updated_by = permissions.user_id if hasattr(permissions, 'user_id') else None

    # Update via repository
    deployment = deployment_repo.update(deployment)

    # Add history entry
    history_entry = DeploymentHistory(
        deployment_id=deployment.id,
        action="unassigned",
        previous_example_version_id=str(previous_version_id) if previous_version_id else None,
        created_by=permissions.user_id if hasattr(permissions, 'user_id') else None
    )
    db.add(history_entry)

    db.commit()
    
    # Clear cache
    if cache:
        await cache.delete(f"course:{content.course_id}:deployments")
    
    return {"status": "unassigned", "message": "Example unassigned successfully"}

@course_content_router.router.get(
    "/deployment/{content_id}",
    response_model=Dict[str, Any]
)
async def get_deployment_status_with_workflow(
    content_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """
    Get detailed deployment status including Temporal workflow information.

    Returns deployment data and checks the Temporal workflow status if one is running.
    """
    # Initialize repositories
    content_repo = CourseContentRepository(db, get_cache())
    deployment_repo = CourseContentDeploymentRepository(db, get_cache())

    # Check content exists
    content = content_repo.get_by_id(str(content_id))
    if not content:
        raise NotFoundException(
            error_code="CONTENT_001",
            detail="Course content not found",
            context={"course_content_id": str(content_id)}
        )
    
    # Check permissions
    if check_course_permissions(permissions, Course, "_student", db).filter(
        Course.id == content.course_id
    ).first() is None:
        raise ForbiddenException(
            detail="Not authorized to view deployment status",
            context={"course_content_id": str(content_id)}
        )
    
    # Get deployment with relationships
    deployment = deployment_repo.find_by_content(str(content_id))
    
    if not deployment:
        return {
            "deployment": None,
            "workflow": None,
            "message": "No deployment found for this content"
        }
    
    # Build deployment info
    deployment_info = {
        "id": str(deployment.id),
        "course_content_id": str(deployment.course_content_id),
        "example_version_id": str(deployment.example_version_id) if deployment.example_version_id else None,
        "example_identifier": str(deployment.example_identifier) if getattr(deployment, 'example_identifier', None) is not None else None,
        "version_tag": deployment.version_tag,
        "deployment_status": deployment.deployment_status,
        "deployment_message": deployment.deployment_message,
        "assigned_at": deployment.assigned_at.isoformat() if deployment.assigned_at else None,
        "deployed_at": deployment.deployed_at.isoformat() if deployment.deployed_at else None,
        "last_attempt_at": deployment.last_attempt_at.isoformat() if deployment.last_attempt_at else None,
        "deployment_path": deployment.deployment_path,
        "version_identifier": deployment.version_identifier,
        "workflow_id": deployment.workflow_id
    }
    
    # If there's an example version, include its info
    if deployment.example_version:
        deployment_info["example_version"] = {
            "id": str(deployment.example_version.id),
            "version_tag": deployment.example_version.version_tag,
            "example": {
                "id": str(deployment.example_version.example.id),
                "identifier": str(deployment.example_version.example.identifier),
                "title": deployment.example_version.example.title
            } if deployment.example_version.example else None
        }
    
    # Check Temporal workflow status if workflow_id exists
    workflow_info = None
    if deployment.workflow_id:
        try:
            # Import Temporal client
            from temporalio.client import Client
            from datetime import datetime, timezone
            import os
            
            # Get Temporal configuration
            temporal_host = os.environ.get('TEMPORAL_HOST', 'localhost')
            temporal_port = os.environ.get('TEMPORAL_PORT', '7233')
            temporal_namespace = os.environ.get('TEMPORAL_NAMESPACE', 'default')
            
            # Create Temporal client
            async def get_workflow_status():
                client = await Client.connect(
                    f"{temporal_host}:{temporal_port}",
                    namespace=temporal_namespace
                )
                
                try:
                    # Get workflow handle
                    handle = client.get_workflow_handle(deployment.workflow_id)
                    
                    # Describe the workflow to get its status
                    description = await handle.describe()
                    
                    return {
                        "workflow_id": deployment.workflow_id,
                        "status": description.status.name if description.status else "UNKNOWN",
                        "start_time": description.start_time.isoformat() if description.start_time else None,
                        "close_time": description.close_time.isoformat() if description.close_time else None,
                        "execution_time": description.execution_time.isoformat() if description.execution_time else None,
                        "task_queue": description.task_queue,
                        "workflow_type": description.workflow_type,
                        "is_running": description.status.name in ["RUNNING", "PENDING"] if description.status else False
                    }
                except Exception as e:
                    return {
                        "workflow_id": deployment.workflow_id,
                        "status": "NOT_FOUND",
                        "error": str(e),
                        "is_running": False
                    }
            
            # Run the async function
            workflow_info = await get_workflow_status()
            
            # Auto-update deployment status based on workflow status
            if workflow_info["status"] == "COMPLETED" and deployment.deployment_status == "in_progress":
                deployment.deployment_status = "deployed"
                deployment.deployed_at = datetime.now(timezone.utc)
                deployment.deployment_message = "Deployment completed successfully"
                db.commit()
                deployment_info["deployment_status"] = "deployed"
                deployment_info["deployed_at"] = deployment.deployed_at.isoformat()
                
            elif workflow_info["status"] in ["FAILED", "TERMINATED", "TIMED_OUT"] and deployment.deployment_status == "in_progress":
                deployment.deployment_status = "failed"
                deployment.deployment_message = f"Workflow {workflow_info['status'].lower()}"
                db.commit()
                deployment_info["deployment_status"] = "failed"
                
        except Exception as e:
            workflow_info = {
                "error": f"Failed to connect to Temporal: {str(e)}",
                "workflow_id": deployment.workflow_id
            }
    
    # Get recent history
    history = db.query(DeploymentHistory).filter(
        DeploymentHistory.deployment_id == deployment.id
    ).order_by(DeploymentHistory.created_at.desc()).limit(5).all()
    
    history_items = [
        {
            "id": str(h.id),
            "action": h.action,
            "workflow_id": h.workflow_id,
            "created_at": h.created_at.isoformat()
        } for h in history
    ]
    
    return {
        "deployment": deployment_info,
        "workflow": workflow_info,
        "recent_history": history_items
    }

@course_content_router.router.get(
    "/courses/{course_id}/deployment-summary",
    response_model=DeploymentSummary
)
async def get_course_deployment_summary(
    course_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Annotated[BaseCache, Depends(get_redis_client)] = None
):
    """
    Get deployment summary for a course.

    Shows statistics about example deployments in the course.
    """
    # Initialize repositories
    content_repo = CourseContentRepository(db, get_cache())
    deployment_repo = CourseContentDeploymentRepository(db, get_cache())

    # Check permissions
    if check_course_permissions(permissions, Course, "_tutor", db).filter(
        Course.id == course_id
    ).first() is None:
        raise ForbiddenException(
            detail="Not authorized to view this course",
            context={"course_id": course_id, "required_permission": "view_course"}
        )

    # Try cache first
    cache_key = f"course:{course_id}:deployment-summary"
    if cache:
        cached = await cache.get(cache_key)
        if cached:
            return cached

    # Get total course content count
    total_content_list = content_repo.find_by_course(course_id)
    total_content = len([c for c in total_content_list if c.archived_at is None])
    
    # Get submittable content count
    submittable_list = content_repo.find_submittable_by_course(course_id)
    submittable_content = len([c for c in submittable_list if c.archived_at is None])

    # Get deployment statistics - need direct query for join
    deployments = db.query(CourseContentDeployment).join(
        CourseContent
    ).filter(
        CourseContent.course_id == course_id
    ).all()
    
    deployments_total = len(deployments)
    deployments_pending = sum(1 for d in deployments if d.deployment_status == "pending")
    deployments_deployed = sum(1 for d in deployments if d.deployment_status == "deployed")
    deployments_failed = sum(1 for d in deployments if d.deployment_status == "failed")
    
    # Get last deployment timestamp
    last_deployment = None
    for d in deployments:
        if d.deployed_at and (last_deployment is None or d.deployed_at > last_deployment):
            last_deployment = d.deployed_at
    
    summary = DeploymentSummary(
        course_id=course_id,
        total_content=total_content,
        submittable_content=submittable_content,
        deployments_total=deployments_total,
        deployments_pending=deployments_pending,
        deployments_deployed=deployments_deployed,
        deployments_failed=deployments_failed,
        last_deployment_at=last_deployment
    )
    
    # Cache the result
    if cache:
        await cache.set(cache_key, json.dumps(summary.dict()), ex=300)  # 5 minutes
    
    return summary

@course_content_router.router.get(
    "/{content_id}/deployment",
    response_model=Optional[DeploymentWithHistory]
)
async def get_content_deployment(
    content_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """
    Get deployment information for specific course content.

    Returns deployment record with full history if exists.
    """
    # Initialize repositories
    content_repo = CourseContentRepository(db, get_cache())
    deployment_repo = CourseContentDeploymentRepository(db, get_cache())

    # Get course content to check permissions
    content = content_repo.get_by_id(str(content_id))
    if not content:
        raise NotFoundException(
            error_code="CONTENT_001",
            detail="Course content not found",
            context={"course_content_id": str(content_id)}
        )

    # Check permissions
    if check_course_permissions(permissions, Course, "_tutor", db).filter(
        Course.id == content.course_id
    ).first() is None:
        raise ForbiddenException(
            detail="Not authorized to view this content",
            context={
                "course_content_id": str(content_id),
                "required_permission": "view_content"
            }
        )
    
    # Get deployment
    deployment = deployment_repo.find_by_content(str(content_id))
    
    if not deployment:
        return None
    
    # Get history
    history = db.query(DeploymentHistory).filter(
        DeploymentHistory.deployment_id == deployment.id
    ).order_by(DeploymentHistory.created_at.desc()).all()
    
    return DeploymentWithHistory(
        deployment=deployment,
        history=history
    )


class CourseContentMoveRequest(BaseModel):
    """Request body for moving a course content (path change + position)."""
    path: str
    position: float


@course_content_router.router.patch(
    "/{content_id}/move",
    response_model=CourseContentGet
)
async def move_course_content(
    content_id: str,
    move_request: CourseContentMoveRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Annotated[BaseCache, Depends(get_redis_client)] = None
):
    """
    Move a course content to a new path and/or position.

    Updates the content's path and position, and cascades the path change
    to all descendants in a single transaction using ltree functions.
    """
    set_db_user(db, permissions.user_id)

    content = db.query(CourseContent).filter(CourseContent.id == content_id).first()
    if not content:
        raise NotFoundException(
            error_code="CONTENT_001",
            detail="Course content not found",
            context={"course_content_id": content_id}
        )

    if check_course_permissions(permissions, Course, "_lecturer", db).filter(
        Course.id == content.course_id
    ).first() is None:
        raise ForbiddenException(
            detail="Not authorized to modify this course content",
            context={"course_content_id": content_id}
        )

    old_path = str(content.path)
    new_path = move_request.path
    course_id = str(content.course_id)

    # Prevent moving an item into its own descendant
    if new_path.startswith(old_path + '.'):
        raise BadRequestException(
            detail="Cannot move an item into its own descendant",
            context={"old_path": old_path, "new_path": new_path}
        )

    # Validate path format
    import re
    if not re.match(r'^[a-z0-9_]+(\.[a-z0-9_]+)*$', new_path):
        raise BadRequestException(
            detail="Invalid path format. Path must consist of lowercase alphanumeric segments separated by dots",
            context={"path": new_path}
        )

    # Check for path collisions before executing the move
    if old_path != new_path:
        # Check if the new path already exists for a different content
        collision = db.query(CourseContent).filter(
            CourseContent.course_id == content.course_id,
            CourseContent.path == Ltree(new_path),
            CourseContent.id != content_id
        ).first()
        if collision:
            raise BadRequestException(
                detail=f"Path '{new_path}' already exists in this course",
                context={
                    "new_path": new_path,
                    "conflicting_content_id": str(collision.id),
                    "conflicting_content_title": collision.title
                }
            )

        # Check if any descendant paths would collide after the move
        descendants = db.execute(
            text("""
                SELECT path FROM course_content
                WHERE path <@ :old_path
                  AND id != :content_id
                  AND course_id = :course_id
            """),
            {"old_path": old_path, "content_id": content_id, "course_id": course_id}
        ).fetchall()

        if descendants:
            old_depth = old_path.count('.') + 1
            new_descendant_paths = []
            for row in descendants:
                desc_path = str(row[0])
                relative = desc_path.split('.')[old_depth:]
                new_desc_path = new_path + '.' + '.'.join(relative)
                new_descendant_paths.append(new_desc_path)

            if new_descendant_paths:
                placeholders = ', '.join(f':p{i}' for i in range(len(new_descendant_paths)))
                params = {f'p{i}': p for i, p in enumerate(new_descendant_paths)}
                params['content_id'] = content_id
                params['course_id'] = course_id
                params['old_path'] = old_path

                collision_count = db.execute(
                    text(f"""
                        SELECT COUNT(*) FROM course_content
                        WHERE course_id = :course_id
                          AND path::text IN ({placeholders})
                          AND NOT path <@ :old_path
                    """),
                    params
                ).scalar()

                if collision_count > 0:
                    raise BadRequestException(
                        detail=f"Moving this item would cause {collision_count} path collision(s) among its children",
                        context={"old_path": old_path, "new_path": new_path}
                    )

    # Use raw SQL for all updates to bypass SQLAlchemy Ltree change detection issues.
    # Cascade descendants first, then update the item itself.
    if old_path != new_path:
        db.execute(
            text("""
                UPDATE course_content
                SET path = :new_path || subpath(path, nlevel(:old_path)),
                    updated_at = now()
                WHERE path <@ :old_path
                  AND id != :content_id
                  AND course_id = :course_id
            """),
            {
                "new_path": new_path,
                "old_path": old_path,
                "content_id": content_id,
                "course_id": course_id,
            }
        )

    # Update the item itself via raw SQL
    db.execute(
        text("""
            UPDATE course_content
            SET path = :new_path,
                position = :position,
                updated_at = now()
            WHERE id = :content_id
              AND course_id = :course_id
        """),
        {
            "new_path": new_path,
            "position": move_request.position,
            "content_id": content_id,
            "course_id": course_id,
        }
    )

    # Expire the ORM object so refresh picks up the raw SQL changes
    db.expire(content)
    db.commit()
    db.refresh(content)

    # Clear old-style Redis cache
    if cache:
        table_name = CourseContent.__tablename__
        try:
            if hasattr(cache, 'keys') and callable(cache.keys):
                cache_keys = await cache.keys(f"{table_name}:*")
                if cache_keys:
                    await cache.delete(*cache_keys)
        except Exception:
            pass

    # Invalidate lecturer/tutor user view caches for this course
    try:
        view_cache = get_cache()
        view_cache.invalidate_user_views(
            entity_type="lecturer_view",
            entity_id=course_id
        )
        view_cache.invalidate_user_views(
            entity_type="course_id",
            entity_id=course_id
        )
    except Exception:
        pass

    return content

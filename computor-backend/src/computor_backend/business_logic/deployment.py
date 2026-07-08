"""Business logic for deployment operations."""
import logging
import yaml
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from computor_types.deployment_config import ComputorDeploymentConfig
from computor_backend.database import get_db_session
from computor_backend.permissions.principal import Principal
from computor_backend.tasks import get_task_executor, TaskSubmission
from computor_backend.exceptions import BadRequestException, ForbiddenException
from computor_backend.permissions.core import check_admin

logger = logging.getLogger(__name__)


def create_organization_sync(org_config: Dict[str, Any], user_id: str, db: Session) -> str:
    """Create an organization row and enroll the creator as ``_owner``.

    Course-level git model: organizations carry no git configuration, so this
    is a plain DB insert — no Temporal activity needed. Idempotent on
    (organization_type, path). Returns the organization id.
    """
    from computor_backend.custom_types import Ltree
    from computor_backend.model.organization import Organization, OrganizationMember

    org_type = org_config.get("organization_type") or "organization"
    org = (
        db.query(Organization)
        .filter(
            Organization.organization_type == org_type,
            Organization.path == Ltree(org_config["path"]),
        )
        .first()
    )
    if org is None:
        org = Organization(
            title=org_config.get("name"),
            description=org_config.get("description", ""),
            path=Ltree(org_config["path"]),
            organization_type=org_type,
            properties={},
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(org)
        db.flush()

    # Idempotent on unique (user_id, organization_id).
    if user_id and (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user_id,
        )
        .first()
    ) is None:
        db.add(OrganizationMember(
            organization_id=org.id,
            user_id=user_id,
            organization_role_id="_owner",
            created_by=user_id,
            updated_by=user_id,
        ))

    db.commit()
    logger.info("Created organization (course-level git model): %s (ID: %s)", org_config.get("path"), org.id)
    return str(org.id)


def create_course_family_sync(
    family_config: Dict[str, Any], organization_id: str, user_id: str, db: Session
) -> str:
    """Create a course family row and enroll the creator as ``_owner``.

    Course families carry no git config (git is per-course), so this is a plain
    DB insert. Idempotent on (organization_id, path). Returns the family id.
    """
    from computor_backend.custom_types import Ltree
    from computor_backend.model.organization import Organization
    from computor_backend.model.course import CourseFamily, CourseFamilyMember

    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise ValueError(f"Organization {organization_id} not found")

    family = (
        db.query(CourseFamily)
        .filter(
            CourseFamily.organization_id == org.id,
            CourseFamily.path == Ltree(family_config["path"]),
        )
        .first()
    )
    if family is None:
        family = CourseFamily(
            title=family_config.get("name"),
            description=family_config.get("description", "") or "",
            path=Ltree(family_config["path"]),
            organization_id=org.id,
            properties={},
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(family)
        db.flush()

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
    logger.info("Created course family: %s (ID: %s)", family_config.get("path"), family.id)
    return str(family.id)


def precreate_hierarchy_and_collect_courses(
    config: ComputorDeploymentConfig, user_id: str, db: Session
) -> List[Dict[str, Any]]:
    """Create every organization + course family synchronously (course-level
    git model — plain DB inserts) and return the flat list of courses still to
    be created via the deploy workflow: ``[{course_config, course_family_id}]``.
    """
    courses: List[Dict[str, Any]] = []
    for org in config.organizations:
        org_id = create_organization_sync(org.model_dump(), user_id, db)
        for family in org.course_families:
            family_id = create_course_family_sync(family.model_dump(), org_id, user_id, db)
            for course in family.courses:
                courses.append({
                    "course_config": course.model_dump(),
                    "course_family_id": family_id,
                })
    return courses


def deploy_from_configuration(
    deployment_config: Dict[str, Any],
    permissions: Principal,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Deploy organization -> course family -> course hierarchy from configuration.

    Args:
        deployment_config: Deployment configuration as dictionary
        permissions: Current user permissions
        validate_only: If true, only validate without deploying

    Returns:
        Dictionary with workflow_id, status, message, deployment_path

    Raises:
        ForbiddenException: If user is not admin
        BadRequestException: If configuration is invalid
        Exception: If deployment fails
    """
    # Check admin permissions
    if not check_admin(permissions):
        raise ForbiddenException("Admin permissions required for deployment")

    # Validate configuration
    config = ComputorDeploymentConfig(**deployment_config)

    if validate_only:
        return {
            "workflow_id": "validation-only",
            "status": "validated",
            "message": "Configuration is valid",
            "deployment_path": config.get_full_course_path()
        }

    # Organizations + course families are plain DB inserts (course-level git
    # model) — create them synchronously here, then let the workflow create only
    # the courses (which still need Temporal for git / student-template setup).
    with get_db_session() as db:
        courses = precreate_hierarchy_and_collect_courses(config, str(permissions.user_id), db)

    # Submit to Temporal workflow
    task_executor = get_task_executor()
    workflow_id = f"deploy-{uuid4()}"

    task_submission = TaskSubmission(
        task_name="deploy_computor_hierarchy",
        parameters={
            "courses": courses,
            "user_id": str(permissions.user_id)
        },
        queue="computor-tasks",
        workflow_id=workflow_id
    )

    result = task_executor.submit_task(task_submission)

    return {
        "workflow_id": workflow_id,
        "status": "submitted",
        "message": "Deployment workflow started",
        "deployment_path": config.get_full_course_path()
    }


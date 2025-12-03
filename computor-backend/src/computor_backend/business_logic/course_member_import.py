"""Business logic for course member import."""
import logging
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from computor_backend.model.auth import User, StudentProfile
from computor_backend.model.course import Course, CourseMember, CourseGroup
from computor_backend.permissions.principal import Principal, course_role_hierarchy
from computor_backend.permissions.core import check_course_permissions
from computor_backend.api.exceptions import ForbiddenException, BadRequestException

from computor_types.course_member_import import (
    CourseMemberImportRequest,
    CourseMemberImportResponse,
)
from computor_types.course_members import CourseMemberGet
from computor_types.course_groups import CourseGroupGet

logger = logging.getLogger(__name__)


async def trigger_post_create_for_member(
    course_member: CourseMember,
    db: Session,
    permissions: Optional[Principal] = None,
) -> Optional[str]:
    """
    Trigger post-create hook for a single imported course member.

    Provisions submission groups and triggers repository creation workflow.
    Skips service accounts (is_service=True).

    Args:
        course_member: Newly created course member
        db: Database session
        permissions: Optional principal for task tracking

    Returns:
        workflow_id if task was submitted successfully, None otherwise
    """
    from computor_backend.repositories.submission_group_provisioning import provision_submission_groups_for_user
    from computor_backend.task_tracker import get_task_tracker
    from computor_types.tasks import TaskSubmission

    # Skip service accounts
    if course_member.user and course_member.user.is_service:
        logger.info(f"Skipping post-create hooks for service account {course_member.user_id}")
        return None

    # Step 1: Provision submission groups (fast, synchronous)
    try:
        provision_submission_groups_for_user(
            user_id=course_member.user_id,
            course_id=course_member.course_id,
            db=db
        )
        logger.info(f"Provisioned submission groups for course member {course_member.id}")
    except Exception as e:
        logger.error(
            f"Failed to provision submission groups for course member {course_member.id}: {e}"
        )
        # Don't fail the entire import if provisioning fails

    # Step 2: Trigger repository creation workflow (asynchronous) with task tracking
    try:
        task_tracker = await get_task_tracker()

        task_submission = TaskSubmission(
            task_name="BulkStudentRepositoryCreationWorkflow",
            parameters={
                "course_member_ids": [str(course_member.id)],
                "course_id": str(course_member.course_id),
                "batch_size": 1,
                "batch_delay_seconds": 0
            },
            queue="computor-tasks"
        )

        # Get organization_id from course for permission tracking
        course = db.query(Course).filter(Course.id == course_member.course_id).first()
        org_id = str(course.organization_id) if course and course.organization_id else None

        # Determine created_by for task tracking
        created_by = permissions.user_id if permissions else str(course_member.created_by or course_member.user_id)

        workflow_id = await task_tracker.submit_and_track_task(
            task_submission=task_submission,
            created_by=created_by,
            user_id=str(course_member.user_id),
            course_id=str(course_member.course_id),
            organization_id=org_id,
            entity_type="course_member",
            entity_id=str(course_member.id),
            description=f"Creating repository for {course_member.user.email if course_member.user else 'course member'}"
        )
        logger.info(
            f"Triggered repository creation workflow: {workflow_id} for course member {course_member.id}"
        )
        return workflow_id
    except Exception as e:
        logger.error(
            f"Failed to trigger repository creation workflow: {e}",
            exc_info=True
        )
        # Don't fail the entire import if workflow submission fails
        return None


async def import_course_member(
    course_id: str | UUID,
    member_request: CourseMemberImportRequest,
    permissions: Principal,
    db: Session,
    username_strategy: str = "name",
) -> CourseMemberImportResponse:
    """Import a course member.

    Args:
        course_id: ID of the course to import member into
        member_request: Member data to import
        permissions: Current user's permissions
        db: Database session
        username_strategy: Strategy for username generation ("name" or "email")

    Returns:
        Import response with course member and created group (if any)

    Raises:
        ForbiddenException: If user lacks permissions
    """
    # Validate course exists and user has permissions (lecturer role or higher)
    course = check_course_permissions(permissions, Course, "_lecturer", db).filter(
        Course.id == course_id
    ).first()

    if not course:
        raise ForbiddenException(
            "You don't have permission to import course members. "
            "Lecturer role or higher is required."
        )

    # Validate role assignment - user can only assign roles at or below their own level
    user_role = permissions.get_highest_course_role(str(course_id))
    target_role = member_request.course_role_id

    if not user_role:
        raise ForbiddenException(
            "You don't have a role in this course."
        )

    if not course_role_hierarchy.can_assign_role(user_role, target_role):
        raise ForbiddenException(
            f"You cannot assign the role '{target_role}'. "
            f"Your role '{user_role}' can only assign roles at or below your privilege level."
        )

    # Initialize tracking variables
    created_group: Optional[CourseGroup] = None
    is_new_member = False

    try:
        # Find or create user by email
        user, user_created = _find_or_create_user(
            email=member_request.email.strip().lower(),
            given_name=member_request.given_name,
            family_name=member_request.family_name,
            db=db,
            username_strategy=username_strategy,
        )

        if user_created:
            logger.info(f"Created new user: {member_request.email}")
        elif member_request.given_name or member_request.family_name:
            # Update user names if provided
            if member_request.given_name:
                user.given_name = member_request.given_name
            if member_request.family_name:
                user.family_name = member_request.family_name
            db.flush()
            logger.info(f"Updated user: {member_request.email}")

        # Prevent users from modifying their own course role (unless admin)
        if str(user.id) == permissions.user_id and not permissions.is_admin:
            raise ForbiddenException(
                "You cannot modify your own course role. Please contact an administrator."
            )

        # Handle course group
        course_group_id = None
        if member_request.course_group_title:
            course_group = _get_or_create_course_group(
                course=course,
                group_title=member_request.course_group_title,
                create_missing=member_request.create_missing_group,
                permissions=permissions,
                db=db,
            )
            if course_group:
                course_group_id = course_group.id
                # Track if we created a new group
                existing_group = db.query(CourseGroup).filter(
                    CourseGroup.id == course_group.id
                ).first()
                if not existing_group.created_at or (
                    existing_group.created_at and
                    existing_group.created_by == permissions.user_id
                ):
                    created_group = course_group

        # Check if course member already exists
        existing_member = (
            db.query(CourseMember)
            .filter(
                CourseMember.user_id == user.id,
                CourseMember.course_id == course.id,
            )
            .first()
        )

        if existing_member:
            # Check if target course member has equal or higher role - cannot modify peers or superiors
            target_current_role = existing_member.course_role_id
            if target_current_role and not permissions.is_admin:
                target_current_level = course_role_hierarchy.get_role_level(target_current_role)
                user_level = course_role_hierarchy.get_role_level(user_role)
                if target_current_level >= user_level:
                    raise ForbiddenException(
                        f"You cannot modify a course member with role '{target_current_role}'. "
                        f"Your role '{user_role}' can only modify members with lower privilege levels."
                    )

            # Update existing member
            existing_member.course_role_id = member_request.course_role_id
            if course_group_id:
                existing_member.course_group_id = course_group_id
            existing_member.updated_by = permissions.user_id
            db.flush()

            course_member = existing_member
            message = "Course member updated successfully"
        else:
            # Create new course member
            new_member = CourseMember(
                user_id=user.id,
                course_id=course.id,
                course_role_id=member_request.course_role_id,
                course_group_id=course_group_id,
                created_by=permissions.user_id,
                updated_by=permissions.user_id,
            )
            db.add(new_member)
            db.flush()  # Flush to get the auto-generated ID

            course_member = new_member
            is_new_member = True
            message = "Course member created successfully"
            logger.info(f"Created course member for {member_request.email} in course {course.id}")

        # Convert to DTOs
        course_member_dto = CourseMemberGet.model_validate(course_member)
        course_member_dict = course_member_dto.model_dump()

        created_group_dict = None
        if created_group:
            created_group_dto = CourseGroupGet.model_validate(created_group)
            created_group_dict = created_group_dto.model_dump()

        # Trigger post-create hooks if new member
        workflow_id = None
        if is_new_member:
            try:
                workflow_id = await trigger_post_create_for_member(course_member, db, permissions)
            except Exception as e:
                logger.error(f"Failed to trigger post-create hooks: {e}", exc_info=True)
                # Don't fail the import if post-create hooks fail

        return CourseMemberImportResponse(
            success=True,
            message=message,
            course_member=course_member_dict,
            created_group=created_group_dict,
            workflow_id=workflow_id,
        )

    except ForbiddenException:
        # Re-raise permission errors - don't swallow them
        raise
    except Exception as e:
        logger.error(f"Error importing member: {e}", exc_info=True)
        return CourseMemberImportResponse(
            success=False,
            message=f"Error: {str(e)}",
            course_member=None,
            created_group=None,
        )


def _find_or_create_user(
    email: str,
    given_name: Optional[str],
    family_name: Optional[str],
    db: Session,
    username_strategy: str = "name",
) -> Tuple[User, bool]:
    """Find existing user by email or create a new one.

    Args:
        email: User email
        given_name: User's given name
        family_name: User's family name
        db: Database session
        username_strategy: Strategy for username generation ("name" or "email")

    Returns:
        Tuple of (User, was_created)
    """
    from computor_backend.utils.username_generation import generate_username_from_names

    # Try to find by email
    user = db.query(User).filter(User.email == email).first()

    if user:
        return user, False

    # Also check student profiles in case the email is stored there
    student_profile = db.query(StudentProfile).filter(StudentProfile.student_email == email).first()
    if student_profile:
        return student_profile.user, False

    # Create new user with generated username based on strategy
    if username_strategy == "name":
        username = generate_username_from_names(given_name, family_name, db)
    else:
        # Fallback to email-based generation
        username = _generate_username_from_email(email, db)

    new_user = User(
        email=email,
        username=username,
        given_name=given_name.strip() if given_name else None,
        family_name=family_name.strip() if family_name else None,
    )
    db.add(new_user)
    db.flush()  # Flush to get the auto-generated ID

    logger.info(f"Created new user: {email} with username {username} (strategy: {username_strategy})")
    return new_user, True


def _generate_username_from_email(email: str, db: Session) -> str:
    """Generate a unique username from email.

    Args:
        email: Email address
        db: Database session

    Returns:
        Unique username
    """
    # Take the part before @ as base username
    base_username = email.split('@')[0].lower()
    # Remove special characters
    base_username = ''.join(c if c.isalnum() or c in ('_', '-', '.') else '_' for c in base_username)

    # Check if username exists
    username = base_username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1

    return username


def _get_or_create_course_group(
    course: Course,
    group_title: str,
    create_missing: bool,
    permissions: Principal,
    db: Session,
) -> Optional[CourseGroup]:
    """Get or create a course group.

    Args:
        course: Course entity
        group_title: Group title
        create_missing: Whether to create if missing
        permissions: Current user's permissions
        db: Database session

    Returns:
        CourseGroup entity or None if not found and not created
    """
    # Check database
    course_group = (
        db.query(CourseGroup)
        .filter(
            CourseGroup.course_id == course.id,
            CourseGroup.title == group_title,
        )
        .first()
    )

    if course_group:
        return course_group

    # Create if allowed
    if not create_missing:
        return None

    new_group = CourseGroup(
        course_id=course.id,
        title=group_title,
        description=f"Auto-created group during import",
        created_by=permissions.user_id,
        updated_by=permissions.user_id,
    )
    db.add(new_group)
    db.flush()  # Flush to get the auto-generated ID

    logger.info(f"Created course group: {group_title}")

    return new_group

"""Business logic for bulk course member import."""
import logging
from typing import List, Optional, Dict, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_

from computor_backend.model.auth import User, StudentProfile
from computor_backend.model.course import Course, CourseMember, CourseGroup
from computor_backend.model.organization import Organization
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.core import check_course_permissions
from computor_backend.api.exceptions import NotFoundException, ForbiddenException, BadRequestException

from computor_types.course_member_import import (
    CourseMemberImportRow,
    CourseMemberImportResult,
    CourseMemberImportResponse,
    ImportStatus,
)

logger = logging.getLogger(__name__)


async def trigger_post_create_for_members(
    course_members: List[CourseMember],
    db: Session
) -> None:
    """
    Trigger post-create hook for bulk-imported course members.

    This reuses the existing post_create_course_member logic from CourseMemberInterface,
    which provisions submission groups and triggers StudentRepositoryCreationWorkflow.

    All course members (students, tutors, lecturers) get their own student repository
    forked from student-template. Access to the assignments repository (reference with
    solutions) is controlled separately via GitLab group memberships in _sync_gitlab_memberships:
    - Students: NO access to assignments
    - Tutors: READ access (inherited via course group)
    - Lecturers: FULL access (Maintainer)

    Only skips:
    - Service accounts (is_service=True)

    Args:
        course_members: List of newly created course members
        db: Database session
    """
    from computor_backend.interfaces.course_member import post_create_course_member

    for course_member in course_members:
        # Skip service accounts only
        if course_member.user and course_member.user.is_service:
            logger.info(f"Skipping post_create for service account: {course_member.id}")
            continue

        try:
            logger.info(
                f"Triggering post_create for course member {course_member.id} "
                f"(role: {course_member.course_role_id})"
            )
            await post_create_course_member(course_member, db)
        except Exception as e:
            logger.error(
                f"Failed to trigger post_create for course member {course_member.id}: {e}",
                exc_info=True
            )
            # Don't fail the entire import if post-create fails for one member


async def import_course_members(
    course_id: str | UUID,
    members: List[CourseMemberImportRow],
    default_course_role_id: str,
    update_existing: bool,
    create_missing_groups: bool,
    permissions: Principal,
    db: Session,
    username_strategy: str = "name",
) -> CourseMemberImportResponse:
    """Import course members in bulk.

    Args:
        course_id: ID of the course to import members into
        members: List of member data to import
        default_course_role_id: Default role for members (e.g., "_student")
        update_existing: Whether to update existing users
        create_missing_groups: Whether to auto-create missing course groups
        permissions: Current user's permissions
        db: Database session
        username_strategy: Strategy for username generation ("name" or "email")
            - "name": Generate from given/family name (e.g., "Max Mustermann" → "mmusterm")
            - "email": Generate from email prefix (default fallback)

    Returns:
        Import response with detailed results

    Raises:
        NotFoundException: If course not found
        ForbiddenException: If user lacks permissions
    """
    # Validate course exists and user has permissions (lecturer role or higher)
    # This uses the standard permission check pattern from the codebase
    course = check_course_permissions(permissions, Course, "_lecturer", db).filter(
        Course.id == course_id
    ).first()

    if not course:
        raise ForbiddenException(
            "You don't have permission to import course members. "
            "Lecturer role or higher is required."
        )

    # Get organization from course
    organization_id = course.organization_id

    # Track results and newly created members
    results: List[CourseMemberImportResult] = []
    created_groups: List[str] = []
    group_cache: Dict[str, CourseGroup] = {}
    newly_created_members: List[CourseMember] = []  # Track for post-create hooks

    # Cache existing groups
    existing_groups = db.query(CourseGroup).filter(CourseGroup.course_id == course_id).all()
    for group in existing_groups:
        group_cache[group.title.lower()] = group

    # Process each member
    for row_number, member_data in enumerate(members, start=1):
        result = _import_single_member(
            course=course,
            member_data=member_data,
            default_course_role_id=default_course_role_id,
            update_existing=update_existing,
            create_missing_groups=create_missing_groups,
            organization_id=organization_id,
            group_cache=group_cache,
            created_groups=created_groups,
            row_number=row_number,
            permissions=permissions,
            db=db,
            username_strategy=username_strategy,
        )
        results.append(result)

        # Track newly created members for post-create hooks
        if result.status == ImportStatus.SUCCESS and result.course_member_id:
            course_member = db.query(CourseMember).filter(
                CourseMember.id == result.course_member_id
            ).first()
            if course_member:
                newly_created_members.append(course_member)

    # Calculate summary statistics
    total = len(results)
    success = sum(1 for r in results if r.status == ImportStatus.SUCCESS)
    errors = sum(1 for r in results if r.status == ImportStatus.ERROR)
    skipped = sum(1 for r in results if r.status == ImportStatus.SKIPPED)
    updated = sum(1 for r in results if r.status == ImportStatus.UPDATED)

    logger.info(
        f"Import completed: {total} total, {success} success, "
        f"{errors} errors, {skipped} skipped, {updated} updated"
    )

    # Trigger post-create hooks for newly created members
    # This provisions submission groups and triggers repository creation workflows
    if newly_created_members:
        logger.info(f"Triggering post-create hooks for {len(newly_created_members)} new members")
        try:
            await trigger_post_create_for_members(newly_created_members, db)
        except Exception as e:
            logger.error(f"Failed to trigger post-create hooks: {e}", exc_info=True)
            # Don't fail the import if post-create hooks fail

    return CourseMemberImportResponse(
        total=total,
        success=success,
        errors=errors,
        skipped=skipped,
        updated=updated,
        results=results,
        missing_groups=created_groups,
    )


def _import_single_member(
    course: Course,
    member_data: CourseMemberImportRow,
    default_course_role_id: str,
    update_existing: bool,
    create_missing_groups: bool,
    organization_id: UUID,
    group_cache: Dict[str, CourseGroup],
    created_groups: List[str],
    row_number: int,
    permissions: Principal,
    db: Session,
    username_strategy: str = "name",
) -> CourseMemberImportResult:
    """Import a single course member.

    Args:
        course: Course entity
        member_data: Member data to import
        default_course_role_id: Default role ID
        update_existing: Whether to update existing users
        create_missing_groups: Whether to create missing groups
        organization_id: Organization ID
        group_cache: Cache of existing groups
        created_groups: List to track created groups
        row_number: Row number in import file
        permissions: Current user's permissions
        db: Database session
        username_strategy: Strategy for username generation ("name" or "email")

    Returns:
        Import result for this member
    """
    warnings = []

    try:
        # Validate email
        if not member_data.email:
            return CourseMemberImportResult(
                row_number=row_number,
                status=ImportStatus.ERROR,
                email="",
                message="Email is required",
            )

        email = member_data.email.strip().lower()

        # Find or create user by email
        user, user_created = _find_or_create_user(
            email=email,
            given_name=member_data.given_name,
            family_name=member_data.family_name,
            update_existing=update_existing,
            db=db,
            username_strategy=username_strategy,
        )

        if user_created:
            logger.info(f"Created new user: {email}")
        elif update_existing and (member_data.given_name or member_data.family_name):
            # Update user names if provided
            if member_data.given_name:
                user.given_name = member_data.given_name
            if member_data.family_name:
                user.family_name = member_data.family_name
            db.flush()
            logger.info(f"Updated user: {email}")

        # Create or update student profile if student_id provided
        if member_data.student_id:
            _create_or_update_student_profile(
                user=user,
                student_id=member_data.student_id,
                student_email=email,
                organization_id=organization_id,
                db=db,
            )

        # Determine course role
        course_role_id = member_data.course_role_id or default_course_role_id

        # Handle course group
        course_group_id = None
        if member_data.course_group_title:
            course_group = _get_or_create_course_group(
                course=course,
                group_title=member_data.course_group_title,
                create_missing=create_missing_groups,
                group_cache=group_cache,
                created_groups=created_groups,
                permissions=permissions,
                db=db,
            )
            if course_group:
                course_group_id = course_group.id
            else:
                warnings.append(f"Course group '{member_data.course_group_title}' not found")

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
            if update_existing:
                # Update existing member
                existing_member.course_role_id = course_role_id
                if course_group_id:
                    existing_member.course_group_id = course_group_id
                existing_member.updated_by = permissions.user_id
                db.flush()

                return CourseMemberImportResult(
                    row_number=row_number,
                    status=ImportStatus.UPDATED,
                    email=email,
                    user_id=str(user.id),
                    course_member_id=str(existing_member.id),
                    message="Course member updated",
                    warnings=warnings,
                )
            else:
                return CourseMemberImportResult(
                    row_number=row_number,
                    status=ImportStatus.SKIPPED,
                    email=email,
                    user_id=str(user.id),
                    course_member_id=str(existing_member.id),
                    message="User already a course member (skipped)",
                    warnings=warnings,
                )

        # Create new course member
        new_member = CourseMember(
            user_id=user.id,
            course_id=course.id,
            course_role_id=course_role_id,
            course_group_id=course_group_id,
            created_by=permissions.user_id,
            updated_by=permissions.user_id,
        )
        db.add(new_member)
        db.flush()  # Flush to get the auto-generated ID from database

        logger.info(f"Created course member for {email} in course {course.id}")

        return CourseMemberImportResult(
            row_number=row_number,
            status=ImportStatus.SUCCESS,
            email=email,
            user_id=str(user.id),
            course_member_id=str(new_member.id),
            message="Course member created successfully",
            warnings=warnings,
        )

    except Exception as e:
        logger.error(f"Error importing member at row {row_number}: {e}", exc_info=True)
        db.rollback()  # Rollback this member's changes
        return CourseMemberImportResult(
            row_number=row_number,
            status=ImportStatus.ERROR,
            email=member_data.email if member_data.email else "",
            message=f"Error: {str(e)}",
        )


def _find_or_create_user(
    email: str,
    given_name: Optional[str],
    family_name: Optional[str],
    update_existing: bool,
    db: Session,
    username_strategy: str = "name",
) -> Tuple[User, bool]:
    """Find existing user by email or create a new one.

    Args:
        email: User email
        given_name: User's given name
        family_name: User's family name
        update_existing: Whether to update existing user
        db: Database session
        username_strategy: Strategy for username generation ("name" or "email")
            - "name": Generate from given/family name (e.g., "Max Mustermann" → "mmusterm")
            - "email": Generate from email prefix (e.g., "john.doe@example.com" → "john.doe")

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
    db.flush()  # Flush to get the auto-generated ID from database

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


def _create_or_update_student_profile(
    user: User,
    student_id: str,
    student_email: str,
    organization_id: UUID,
    db: Session,
) -> StudentProfile:
    """Create or update student profile.

    Args:
        user: User entity
        student_id: Student ID (Matrikelnummer)
        student_email: Student email
        organization_id: Organization ID
        db: Database session

    Returns:
        StudentProfile entity
    """
    # Check if student profile exists for this user
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()

    if student_profile:
        # Update existing profile
        if student_id:
            student_profile.student_id = student_id
        if student_email:
            student_profile.student_email = student_email
        db.flush()
        logger.info(f"Updated student profile for user {user.id}")
        return student_profile

    # Create new student profile
    student_profile = StudentProfile(
        user_id=user.id,
        student_id=student_id,
        student_email=student_email,
        organization_id=organization_id,
    )
    db.add(student_profile)
    db.flush()  # Flush to get the auto-generated ID from database

    logger.info(f"Created student profile for user {user.id}")
    return student_profile


def _get_or_create_course_group(
    course: Course,
    group_title: str,
    create_missing: bool,
    group_cache: Dict[str, CourseGroup],
    created_groups: List[str],
    permissions: Principal,
    db: Session,
) -> Optional[CourseGroup]:
    """Get or create a course group.

    Args:
        course: Course entity
        group_title: Group title
        create_missing: Whether to create if missing
        group_cache: Cache of groups
        created_groups: List to track created groups
        permissions: Current user's permissions
        db: Database session

    Returns:
        CourseGroup entity or None if not found and not created
    """
    group_title_lower = group_title.strip().lower()

    # Check cache first
    if group_title_lower in group_cache:
        return group_cache[group_title_lower]

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
        group_cache[group_title_lower] = course_group
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
    db.flush()  # Flush to get the auto-generated ID from database

    group_cache[group_title_lower] = new_group
    created_groups.append(group_title)
    logger.info(f"Created course group: {group_title}")

    return new_group

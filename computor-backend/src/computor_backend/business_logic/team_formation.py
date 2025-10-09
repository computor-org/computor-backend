"""Business logic for team formation rules and validation."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from computor_backend.model.course import Course, CourseContent

logger = logging.getLogger(__name__)


# Default team formation rules
DEFAULT_TEAM_FORMATION_RULES = {
    "mode": "self_organized",
    "min_group_size": 1,
    "formation_deadline": None,
    "allow_student_group_creation": True,
    "allow_student_join_groups": True,
    "allow_student_leave_groups": True,
    "auto_assign_unmatched": False,
    "lock_teams_at_deadline": True,
    "require_approval": False,
}


def get_team_formation_rules(
    course_content: CourseContent,
    course: Optional[Course] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Get team formation rules with inheritance pattern.

    Resolution order (field-by-field):
    1. System defaults (DEFAULT_TEAM_FORMATION_RULES)
    2. Course-level rules (Course.properties.team_formation) - if not None
    3. CourseContent-level rules (CourseContent.properties.team_formation) - if not None

    Args:
        course_content: The course content (assignment)
        course: Optional course object (will be fetched if not provided)
        db: Optional database session (required if course not provided)

    Returns:
        Resolved team formation rules dictionary

    Example:
        # Course default: teams of 3
        # This assignment: override to teams of 4 with custom deadline
        rules = get_team_formation_rules(course_content)
        # Returns: {mode: "self_organized", max_group_size: 4, ...}
    """
    # Start with system defaults
    resolved = DEFAULT_TEAM_FORMATION_RULES.copy()

    # Get course if not provided
    if course is None:
        if db is None:
            raise ValueError("Either course or db must be provided")
        course = db.query(Course).filter(Course.id == course_content.course_id).first()
        if not course:
            logger.warning(f"Course {course_content.course_id} not found, using defaults")
            return resolved

    # Apply course-level defaults
    course_rules = course.properties.get('team_formation', {}) if course.properties else {}
    for key, value in course_rules.items():
        if value is not None:
            resolved[key] = value

    # Apply course_content-level overrides
    content_rules = course_content.properties.get('team_formation', {}) if course_content.properties else {}
    for key, value in content_rules.items():
        if value is not None:
            resolved[key] = value

    # Special handling: max_group_size from CourseContent.max_group_size if not in properties
    if 'max_group_size' not in resolved or resolved['max_group_size'] is None:
        resolved['max_group_size'] = course_content.max_group_size or 1

    logger.debug(
        f"Resolved team formation rules for course_content {course_content.id}: "
        f"max_group_size={resolved.get('max_group_size')}, "
        f"mode={resolved.get('mode')}, "
        f"deadline={resolved.get('formation_deadline')}"
    )

    return resolved


def is_team_assignment(course_content: CourseContent) -> bool:
    """
    Check if a course content is a team assignment.

    Args:
        course_content: The course content to check

    Returns:
        True if max_group_size > 1 (team assignment), False otherwise
    """
    max_group_size = course_content.max_group_size
    return max_group_size is not None and max_group_size > 1


def validate_team_formation_action(
    course_content: CourseContent,
    action: str,
    course: Optional[Course] = None,
    db: Optional[Session] = None
) -> tuple[bool, Optional[str]]:
    """
    Validate if a team formation action is allowed based on rules.

    Args:
        course_content: The course content (assignment)
        action: The action to validate ("create" | "join" | "leave")
        course: Optional course object
        db: Optional database session

    Returns:
        Tuple of (is_allowed: bool, error_message: Optional[str])

    Example:
        allowed, error = validate_team_formation_action(content, "create")
        if not allowed:
            raise BadRequestException(detail=error)
    """
    rules = get_team_formation_rules(course_content, course, db)

    # Check if this is a team assignment
    if not is_team_assignment(course_content):
        return False, f"Course content '{course_content.title}' is not a team assignment (max_group_size={course_content.max_group_size})"

    # Check action-specific permissions
    if action == "create":
        if not rules.get("allow_student_group_creation", True):
            return False, "Student team creation is not allowed for this assignment"

    elif action == "join":
        if not rules.get("allow_student_join_groups", True):
            return False, "Joining teams is not allowed for this assignment"

    elif action == "leave":
        if not rules.get("allow_student_leave_groups", True):
            return False, "Leaving teams is not allowed for this assignment"

    # Check formation deadline
    deadline = rules.get("formation_deadline")
    if deadline:
        # Parse deadline if string
        if isinstance(deadline, str):
            try:
                deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid formation_deadline format: {deadline}")
                deadline_dt = None
        else:
            deadline_dt = deadline

        if deadline_dt and datetime.now(deadline_dt.tzinfo) > deadline_dt:
            return False, f"Team formation deadline has passed ({deadline})"

    return True, None


def get_formation_deadline(
    course_content: CourseContent,
    course: Optional[Course] = None,
    db: Optional[Session] = None
) -> Optional[datetime]:
    """
    Get the team formation deadline for a course content.

    Handles both absolute deadlines and relative offsets.

    Args:
        course_content: The course content
        course: Optional course object
        db: Optional database session

    Returns:
        Deadline as datetime or None if no deadline set
    """
    rules = get_team_formation_rules(course_content, course, db)
    deadline = rules.get("formation_deadline")

    if not deadline:
        return None

    # If already a datetime object
    if isinstance(deadline, datetime):
        return deadline

    # If string, try to parse as ISO format
    if isinstance(deadline, str):
        try:
            return datetime.fromisoformat(deadline.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Could not parse formation_deadline: {deadline}")
            return None

    return None


def should_auto_assign_unmatched(
    course_content: CourseContent,
    course: Optional[Course] = None,
    db: Optional[Session] = None
) -> bool:
    """
    Check if unmatched students should be auto-assigned to teams.

    Args:
        course_content: The course content
        course: Optional course object
        db: Optional database session

    Returns:
        True if auto_assign_unmatched is enabled
    """
    rules = get_team_formation_rules(course_content, course, db)
    return rules.get("auto_assign_unmatched", False)


def should_lock_teams_at_deadline(
    course_content: CourseContent,
    course: Optional[Course] = None,
    db: Optional[Session] = None
) -> bool:
    """
    Check if teams should be locked at deadline.

    Args:
        course_content: The course content
        course: Optional course object
        db: Optional database session

    Returns:
        True if teams should be locked at deadline
    """
    rules = get_team_formation_rules(course_content, course, db)
    return rules.get("lock_teams_at_deadline", True)


def get_min_group_size(
    course_content: CourseContent,
    course: Optional[Course] = None,
    db: Optional[Session] = None
) -> int:
    """
    Get the minimum team size for validation.

    Args:
        course_content: The course content
        course: Optional course object
        db: Optional database session

    Returns:
        Minimum team size (default: 1)
    """
    rules = get_team_formation_rules(course_content, course, db)
    return rules.get("min_group_size", 1)


def get_max_group_size(
    course_content: CourseContent,
    course: Optional[Course] = None,
    db: Optional[Session] = None
) -> int:
    """
    Get the maximum team size.

    Args:
        course_content: The course content
        course: Optional course object
        db: Optional database session

    Returns:
        Maximum team size
    """
    rules = get_team_formation_rules(course_content, course, db)
    return rules.get("max_group_size", course_content.max_group_size or 1)

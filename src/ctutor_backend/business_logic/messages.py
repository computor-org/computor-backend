"""Business logic for message operations."""
from uuid import UUID
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from ctutor_backend.api.exceptions import BadRequestException, NotImplementedException, ForbiddenException
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.model.message import MessageRead, Message
from ctutor_backend.model.course import CourseMember, SubmissionGroup, SubmissionGroupMember
from ctutor_backend.interface.messages import MessageCreate, MessageGet


def create_message_with_author(
    payload: MessageCreate,
    permissions: Principal,
    db: Session,
) -> dict:
    """Create a message with enforced author_id and defaults.

    Permission rules per target:
    - user_id: NOT IMPLEMENTED - throws NotImplementedException
    - course_member_id: NOT IMPLEMENTED - throws NotImplementedException
    - submission_group_id: Writeable by submission_group_members and non-_student course roles
    - course_group_id: Read-only - throws ForbiddenException on create
    - course_content_id: LECTURER+ ONLY - requires _lecturer, _maintainer, or _owner role
    - course_id: LECTURER+ ONLY - requires _lecturer, _maintainer, or _owner role

    Args:
        payload: Message creation data
        permissions: Current user permissions
        db: Database session

    Returns:
        Dictionary with model_dump ready for create_db

    Raises:
        BadRequestException: If title or content missing
        NotImplementedException: If user_id or course_member_id target
        ForbiddenException: If trying to write to read-only target or lacking permissions
    """
    # Enforce author_id from current user
    if not payload.title or not payload.content:
        raise BadRequestException(detail="Title and content are required")

    model_dump = payload.model_dump(exclude_unset=True)
    model_dump['author_id'] = permissions.user_id

    # Validate that only ONE target is set (messages should have a single, clear scope)
    target_fields = ['user_id', 'course_member_id', 'submission_group_id', 'course_group_id', 'course_content_id', 'course_id']
    set_targets = [k for k in target_fields if model_dump.get(k)]

    # If parent_id is set, inherit target from parent message
    if model_dump.get('parent_id'):
        from ctutor_backend.model.message import Message
        parent_message = db.query(Message).filter(Message.id == model_dump['parent_id']).first()
        if not parent_message:
            raise BadRequestException(detail=f"Parent message {model_dump['parent_id']} not found")

        # Inherit target fields from parent
        for field in target_fields:
            parent_value = getattr(parent_message, field, None)
            if parent_value is not None:
                # Don't override if user explicitly set a target (will be caught by validation below)
                if field not in model_dump or model_dump[field] is None:
                    model_dump[field] = parent_value

        # Recalculate set_targets after inheriting from parent
        set_targets = [k for k in target_fields if model_dump.get(k)]

    if len(set_targets) == 0:
        # Allow user-only message by setting user_id to current user if nothing else provided
        model_dump['user_id'] = permissions.user_id
    elif len(set_targets) > 1:
        raise BadRequestException(detail=f"Only ONE target field should be set, but got: {', '.join(set_targets)}. Please specify only one of: user_id, course_member_id, submission_group_id, course_group_id, course_content_id, or course_id.")

    # Check target-specific write permissions
    if model_dump.get('user_id'):
        raise NotImplementedException(detail="Direct user messages (user_id target) are not implemented")

    if model_dump.get('course_member_id'):
        raise NotImplementedException(detail="Course member messages (course_member_id target) are not implemented")

    if model_dump.get('course_group_id'):
        raise ForbiddenException(detail="Cannot create messages directly to course_group_id (read-only target)")

    # submission_group_id: Check if user is a member or has elevated role
    if model_dump.get('submission_group_id'):
        submission_group_id = model_dump['submission_group_id']
        _check_submission_group_write_permission(permissions, submission_group_id, db)

    # course_content_id: Check if user has submission group with that content
    if model_dump.get('course_content_id') and not model_dump.get('submission_group_id'):
        course_content_id = model_dump['course_content_id']
        _check_course_content_write_permission(permissions, course_content_id, db)

    # course_id: Check if user is a member
    if model_dump.get('course_id'):
        course_id = model_dump['course_id']
        _check_course_write_permission(permissions, course_id, db)

    # Default level
    if 'level' not in model_dump or model_dump['level'] is None:
        model_dump['level'] = 0

    return model_dump


def _check_submission_group_write_permission(
    permissions: Principal,
    submission_group_id: str,
    db: Session,
) -> None:
    """Check if user can write to a submission group.

    Rules:
    - User must be a submission_group_member OR
    - User must have a course role other than _student in the submission group's course

    Raises:
        ForbiddenException: If user lacks permission
    """
    # Check if user is a submission group member
    is_member = db.query(
        db.query(SubmissionGroupMember.id)
        .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id)
        .filter(
            SubmissionGroupMember.submission_group_id == submission_group_id,
            CourseMember.user_id == permissions.user_id
        )
        .exists()
    ).scalar()

    if is_member:
        return

    # Check if user has non-student role in the course
    submission_group = db.query(SubmissionGroup).filter(
        SubmissionGroup.id == submission_group_id
    ).first()

    if not submission_group:
        raise ForbiddenException(detail="Submission group not found")

    # Check course membership with elevated role
    has_elevated_role = db.query(
        db.query(CourseMember.id)
        .filter(
            CourseMember.course_id == submission_group.course_id,
            CourseMember.user_id == permissions.user_id,
            CourseMember.course_role_id != "_student"
        )
        .exists()
    ).scalar()

    if not has_elevated_role:
        raise ForbiddenException(detail="You must be a submission group member or have elevated course role to write messages to this submission group")


def _check_course_content_write_permission(
    permissions: Principal,
    course_content_id: str,
    db: Session,
) -> None:
    """Check if user can write to a course content.

    Only _lecturer and above can write to course_content_id.
    Students and tutors cannot write here.

    Raises:
        ForbiddenException: If user lacks permission
    """
    from ctutor_backend.model.course import CourseContent

    # Get the course_content to find the course
    course_content = db.query(CourseContent).filter(
        CourseContent.id == course_content_id
    ).first()

    if not course_content:
        raise ForbiddenException(detail="Course content not found")

    # Check if user has _lecturer or higher role in the course
    has_lecturer_role = db.query(
        db.query(CourseMember.id)
        .filter(
            CourseMember.course_id == course_content.course_id,
            CourseMember.user_id == permissions.user_id,
            CourseMember.course_role_id.in_(["_lecturer", "_maintainer", "_owner"])
        )
        .exists()
    ).scalar()

    if not has_lecturer_role:
        raise ForbiddenException(detail="Only lecturers and above can write messages to course_content_id. Students and tutors should use submission_group_id instead.")


def _check_course_write_permission(
    permissions: Principal,
    course_id: str,
    db: Session,
) -> None:
    """Check if user can write to a course.

    Only _lecturer and above can write to course_id.
    Students and tutors cannot write here.

    Raises:
        ForbiddenException: If user lacks permission
    """
    # Check if user has _lecturer or higher role in the course
    has_lecturer_role = db.query(
        db.query(CourseMember.id)
        .filter(
            CourseMember.course_id == course_id,
            CourseMember.user_id == permissions.user_id,
            CourseMember.course_role_id.in_(["_lecturer", "_maintainer", "_owner"])
        )
        .exists()
    ).scalar()

    if not has_lecturer_role:
        raise ForbiddenException(detail="Only lecturers and above can write messages to course_id. Students and tutors should use submission_group_id instead.")


def get_message_with_read_status(
    message_id: UUID | str,
    message: MessageGet,
    permissions: Principal,
    db: Session,
) -> MessageGet:
    """Get a message with read status for current user.

    Args:
        message_id: Message ID
        message: Message entity from get_id_db
        permissions: Current user permissions
        db: Database session

    Returns:
        Message with is_read field populated
    """
    reader_user_id = permissions.user_id
    is_read = False
    if reader_user_id:
        exists = (
            db.query(MessageRead.id)
            .filter(
                MessageRead.message_id == message_id,
                MessageRead.reader_user_id == reader_user_id,
            )
            .first()
        )
        is_read = exists is not None

    return message.model_copy(update={"is_read": is_read})


def list_messages_with_read_status(
    items: list[MessageGet],
    permissions: Principal,
    db: Session,
) -> list[MessageGet]:
    """Add read status to a list of messages for current user.

    Args:
        items: List of messages
        permissions: Current user permissions
        db: Database session

    Returns:
        List of messages with is_read field populated
    """
    reader_user_id = permissions.user_id

    if reader_user_id and items:
        message_ids = [item.id for item in items]
        read_rows = (
            db.query(MessageRead.message_id)
            .filter(
                MessageRead.reader_user_id == reader_user_id,
                MessageRead.message_id.in_(message_ids),
            )
            .all()
        )
        read_ids = {str(row[0]) for row in read_rows}
    else:
        read_ids = set()

    return [item.model_copy(update={"is_read": item.id in read_ids}) for item in items]


def mark_message_as_read(
    message_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> None:
    """Mark a message as read for the current user.

    Args:
        message_id: Message ID
        permissions: Current user permissions
        db: Database session
    """
    # Upsert read record for current user
    exists = (
        db.query(MessageRead)
        .filter(MessageRead.message_id == message_id, MessageRead.reader_user_id == permissions.user_id)
        .first()
    )
    if not exists:
        db.add(MessageRead(message_id=message_id, reader_user_id=permissions.user_id))
        db.commit()


def mark_message_as_unread(
    message_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> None:
    """Mark a message as unread for the current user.

    Args:
        message_id: Message ID
        permissions: Current user permissions
        db: Database session
    """
    read = (
        db.query(MessageRead)
        .filter(MessageRead.message_id == message_id, MessageRead.reader_user_id == permissions.user_id)
        .first()
    )
    if read:
        db.delete(read)
        db.commit()

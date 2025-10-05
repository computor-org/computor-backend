"""Business logic for course member comment operations."""
from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import case

from ctutor_backend.api.exceptions import BadRequestException, ForbiddenException, NotFoundException
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.model.course import CourseMember, CourseMemberComment
from ctutor_backend.interface.course_member_comments import CourseMemberCommentList


def _is_owner_expr(transmitter_id):
    """SQLAlchemy expression to mark if comment is owned by transmitter."""
    return case(
        (CourseMemberComment.transmitter_id == transmitter_id, True),
        else_=False,
    ).label("owner")


def get_current_transmitter(
    db: Session,
    permissions: Principal,
    course_member_id: str
) -> CourseMember:
    """Get the current user's course member record in the target course.

    Args:
        db: Database session
        permissions: Current user permissions
        course_member_id: Target course member ID

    Returns:
        Current user's course member in the same course

    Raises:
        NotFoundException: If target course member not found
        ForbiddenException: If current user has no membership in the target course
    """
    target_cm: Optional[CourseMember] = (
        db.query(CourseMember)
        .filter(CourseMember.id == course_member_id)
        .first()
    )
    if target_cm is None:
        raise NotFoundException()

    transmitter: Optional[CourseMember] = (
        db.query(CourseMember)
        .filter(
            CourseMember.user_id == permissions.user_id,
            CourseMember.course_id == target_cm.course_id,
        )
        .first()
    )
    if transmitter is None:
        # Current user has no membership in the target course
        raise ForbiddenException()
    return transmitter


def list_comments_for_course_member(
    course_member_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> List[CourseMemberCommentList]:
    """List comments for a course member.

    Args:
        course_member_id: Course member ID
        permissions: Current user permissions
        db: Database session

    Returns:
        List of comments

    Raises:
        NotFoundException: If user lacks permission
    """
    # Admin: return without owner flag (model has no owner)
    if permissions.is_admin:
        comments = (
            db.query(CourseMemberComment)
            .filter(CourseMemberComment.course_member_id == course_member_id)
            .all()
        )
        return [
            CourseMemberCommentList(
                id=c.id,
                message=c.message,
                transmitter_id=c.transmitter_id,
                transmitter=c.transmitter,
                course_member_id=c.course_member_id,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in comments
        ]

    # Tutors (and above) only for now
    if (
        check_course_permissions(permissions, CourseMember, "_tutor", db)
        .filter(CourseMember.id == course_member_id)
        .first()
        is None
    ):
        raise NotFoundException()

    transmitter = get_current_transmitter(db, permissions, str(course_member_id))

    comments = (
        db.query(CourseMemberComment, _is_owner_expr(transmitter.id))
        .filter(CourseMemberComment.course_member_id == course_member_id)
        .all()
    )

    # Drop owner flag from response to match DTO
    return [
        CourseMemberCommentList(
            id=c.id,
            message=c.message,
            transmitter_id=c.transmitter_id,
            transmitter=c.transmitter,
            course_member_id=c.course_member_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c, _owner in comments
    ]


def create_course_member_comment(
    course_member_id: UUID | str,
    message: str,
    permissions: Principal,
    db: Session,
) -> List[CourseMemberCommentList]:
    """Create a comment for a course member.

    Args:
        course_member_id: Course member ID
        message: Comment message
        permissions: Current user permissions
        db: Database session

    Returns:
        Updated list of all comments for this course member

    Raises:
        BadRequestException: If admin tries to create or message is empty
        NotFoundException: If user lacks permission
        ForbiddenException: If user not in course
    """
    if permissions.is_admin:
        # For now, do not allow admin to impersonate a transmitter
        raise BadRequestException(detail="[admin] is not permitted.")

    # Tutors (and above) of the target course member's course
    if (
        check_course_permissions(permissions, CourseMember, "_tutor", db)
        .filter(CourseMember.id == course_member_id)
        .first()
        is None
    ):
        raise NotFoundException()

    transmitter = get_current_transmitter(db, permissions, str(course_member_id))

    if not message or len(message.strip()) == 0:
        raise BadRequestException(detail="The comment is empty.")

    db_item = CourseMemberComment(
        message=message.strip(),
        transmitter_id=transmitter.id,
        course_member_id=str(course_member_id),
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    comments = (
        db.query(CourseMemberComment, _is_owner_expr(transmitter.id))
        .filter(CourseMemberComment.course_member_id == course_member_id)
        .all()
    )

    return [
        CourseMemberCommentList(
            id=c.id,
            message=c.message,
            transmitter_id=c.transmitter_id,
            transmitter=c.transmitter,
            course_member_id=c.course_member_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c, _owner in comments
    ]


def update_course_member_comment(
    course_member_comment_id: UUID | str,
    message: str,
    permissions: Principal,
    db: Session,
) -> List[CourseMemberCommentList]:
    """Update a course member comment.

    Args:
        course_member_comment_id: Comment ID
        message: Updated message
        permissions: Current user permissions
        db: Database session

    Returns:
        Updated list of all comments for this course member

    Raises:
        BadRequestException: If admin tries to update or message is empty
        NotFoundException: If comment not found or user lacks permission
        ForbiddenException: If user not the transmitter
    """
    if permissions.is_admin:
        raise BadRequestException(detail="[admin] is not permitted.")

    db_item: Optional[CourseMemberComment] = (
        db.query(CourseMemberComment)
        .filter(CourseMemberComment.id == course_member_comment_id)
        .first()
    )
    if db_item is None:
        raise NotFoundException()

    # Ensure the user is a tutor of the course and is the transmitter
    if (
        check_course_permissions(permissions, CourseMember, "_tutor", db)
        .filter(CourseMember.id == db_item.course_member_id)
        .first()
        is None
    ):
        raise NotFoundException()

    transmitter = get_current_transmitter(db, permissions, str(db_item.course_member_id))
    if str(db_item.transmitter_id) != str(transmitter.id):
        raise ForbiddenException()

    if not message or len(message.strip()) == 0:
        raise BadRequestException(detail="The comment is empty.")

    db_item.message = message.strip()
    db.commit()
    db.refresh(db_item)

    comments = (
        db.query(CourseMemberComment, _is_owner_expr(transmitter.id))
        .filter(CourseMemberComment.course_member_id == db_item.course_member_id)
        .all()
    )
    return [
        CourseMemberCommentList(
            id=c.id,
            message=c.message,
            transmitter_id=c.transmitter_id,
            transmitter=c.transmitter,
            course_member_id=c.course_member_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c, _owner in comments
    ]


def delete_course_member_comment(
    course_member_comment_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> List[CourseMemberCommentList]:
    """Delete a course member comment.

    Args:
        course_member_comment_id: Comment ID
        permissions: Current user permissions
        db: Database session

    Returns:
        Updated list of all comments for this course member

    Raises:
        BadRequestException: If admin tries to delete
        NotFoundException: If comment not found or user lacks permission
        ForbiddenException: If user not the transmitter and not maintainer/owner
    """
    if permissions.is_admin:
        raise BadRequestException(detail="[admin] is not permitted.")

    db_item: Optional[CourseMemberComment] = (
        db.query(CourseMemberComment)
        .filter(CourseMemberComment.id == course_member_comment_id)
        .first()
    )
    if db_item is None:
        raise NotFoundException()

    # Must be tutor of the course and either owner or maintainer/owner role
    if (
        check_course_permissions(permissions, CourseMember, "_tutor", db)
        .filter(CourseMember.id == db_item.course_member_id)
        .first()
        is None
    ):
        raise NotFoundException()

    transmitter = get_current_transmitter(db, permissions, str(db_item.course_member_id))

    # Load the transmitter record to check role
    if str(db_item.transmitter_id) != str(transmitter.id) and transmitter.course_role_id not in [
        "_maintainer",
        "_owner",
    ]:
        raise ForbiddenException()

    course_member_id = db_item.course_member_id
    db.delete(db_item)
    db.commit()

    comments = (
        db.query(CourseMemberComment, _is_owner_expr(transmitter.id))
        .filter(CourseMemberComment.course_member_id == course_member_id)
        .all()
    )
    return [
        CourseMemberCommentList(
            id=c.id,
            message=c.message,
            transmitter_id=c.transmitter_id,
            transmitter=c.transmitter,
            course_member_id=c.course_member_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c, _owner in comments
    ]

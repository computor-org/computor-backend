from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import case

from ctutor_backend.api.exceptions import BadRequestException, ForbiddenException, NotFoundException
from ctutor_backend.database import get_db
from ctutor_backend.interface.course_member_comments import CourseMemberCommentList
from ctutor_backend.model.course import Course, CourseMember, CourseMemberComment
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.core import check_course_permissions


router = APIRouter()


class CommentCreate(BaseModel):
    course_member_id: UUID | str
    message: str


class CommentUpdate(BaseModel):
    message: str


def _is_owner_expr(transmitter_id):
    return case(
        (CourseMemberComment.transmitter_id == transmitter_id, True),
        else_=False,
    ).label("owner")


def _get_current_transmitter(db: Session, permissions: Principal, course_member_id: str) -> CourseMember:
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


@router.get("", response_model=list[CourseMemberCommentList])
async def list_comments(
    course_member_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
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

    transmitter = _get_current_transmitter(db, permissions, str(course_member_id))

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


@router.post("", response_model=list[CourseMemberCommentList])
async def create_comment(
    payload: CommentCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    if permissions.is_admin:
        # For now, do not allow admin to impersonate a transmitter
        raise BadRequestException(detail="[admin] is not permitted.")

    # Tutors (and above) of the target course member's course
    if (
        check_course_permissions(permissions, CourseMember, "_tutor", db)
        .filter(CourseMember.id == payload.course_member_id)
        .first()
        is None
    ):
        raise NotFoundException()

    transmitter = _get_current_transmitter(db, permissions, str(payload.course_member_id))

    if not payload.message or len(payload.message.strip()) == 0:
        raise BadRequestException(detail="The comment is empty.")

    db_item = CourseMemberComment(
        message=payload.message.strip(),
        transmitter_id=transmitter.id,
        course_member_id=str(payload.course_member_id),
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    comments = (
        db.query(CourseMemberComment, _is_owner_expr(transmitter.id))
        .filter(CourseMemberComment.course_member_id == payload.course_member_id)
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


@router.patch("/{course_member_comment_id}", response_model=list[CourseMemberCommentList])
async def update_comment(
    course_member_comment_id: UUID | str,
    payload: CommentUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
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

    transmitter = _get_current_transmitter(db, permissions, str(db_item.course_member_id))
    if str(db_item.transmitter_id) != str(transmitter.id):
        raise ForbiddenException()

    if not payload.message or len(payload.message.strip()) == 0:
        raise BadRequestException(detail="The comment is empty.")

    db_item.message = payload.message.strip()
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


@router.delete("/{course_member_comment_id}", response_model=list[CourseMemberCommentList])
async def delete_comment(
    course_member_comment_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
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

    transmitter = _get_current_transmitter(db, permissions, str(db_item.course_member_id))

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


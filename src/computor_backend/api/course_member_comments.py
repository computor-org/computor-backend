from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_types.course_member_comments import CourseMemberCommentList
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.auth import get_current_principal

# Import business logic
from computor_backend.business_logic.course_member_comments import (
    list_comments_for_course_member,
    create_course_member_comment,
    update_course_member_comment,
    delete_course_member_comment,
)

router = APIRouter()

class CommentCreate(BaseModel):
    course_member_id: UUID | str
    message: str

class CommentUpdate(BaseModel):
    message: str

@router.get("", response_model=list[CourseMemberCommentList])
async def list_comments(
    course_member_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """List comments for a course member."""
    return list_comments_for_course_member(course_member_id, permissions, db)

@router.post("", response_model=list[CourseMemberCommentList])
async def create_comment(
    payload: CommentCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Create a comment for a course member."""
    return create_course_member_comment(
        payload.course_member_id,
        payload.message,
        permissions,
        db,
    )

@router.patch("/{course_member_comment_id}", response_model=list[CourseMemberCommentList])
async def update_comment(
    course_member_comment_id: UUID | str,
    payload: CommentUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Update a course member comment."""
    return update_course_member_comment(
        course_member_comment_id,
        payload.message,
        permissions,
        db,
    )

@router.delete("/{course_member_comment_id}", response_model=list[CourseMemberCommentList])
async def delete_comment(
    course_member_comment_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Delete a course member comment."""
    return delete_course_member_comment(
        course_member_comment_id,
        permissions,
        db,
    )

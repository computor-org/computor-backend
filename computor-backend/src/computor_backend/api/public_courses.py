"""Public course discovery and safe self-subscription endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from computor_backend.business_logic.course_member_post_create import (
    course_member_post_create,
)
from computor_backend.database import get_db
from computor_backend.exceptions import NotFoundException
from computor_backend.model.course import Course, CourseGroup, CourseMember
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_types.courses import CourseList
from computor_types.course_members import CourseMemberGet


public_courses_router = APIRouter(tags=["public-courses"])


@public_courses_router.get("/public/courses", response_model=list[CourseList])
def list_public_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[CourseList]:
    """List only courses explicitly made public by a course manager.

    This endpoint intentionally does not expose course content, members, git
    configuration, or organization internals. A user must authenticate and
    subscribe before the normal course permissions grant access to course
    resources.
    """
    courses = (
        db.query(Course)
        .filter(Course.is_public.is_(True))
        .order_by(Course.title.asc(), Course.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [CourseList.model_validate(course, from_attributes=True) for course in courses]


def _get_or_create_public_group(course: Course, db: Session) -> CourseGroup:
    """Return the stable default group required by the student FK invariant."""
    group = (
        db.query(CourseGroup)
        .filter(CourseGroup.course_id == course.id)
        .order_by(CourseGroup.title.asc(), CourseGroup.id.asc())
        .first()
    )
    if group is not None:
        return group

    group = CourseGroup(
        course_id=course.id,
        title="Public students",
        description="Students who self-subscribed to this public course.",
    )
    db.add(group)
    db.flush()
    return group


@public_courses_router.post(
    "/courses/{course_id}/subscribe",
    response_model=CourseMemberGet,
    summary="Subscribe the current user to a public course",
)
async def subscribe_to_public_course(
    course_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> CourseMemberGet:
    """Idempotently create exactly a ``_student`` membership.

    The request contains no role or group fields. This is deliberate: social
    registration and self-subscription can never grant lecturer, maintainer,
    owner, administrator, or organization roles.
    """
    course = (
        db.query(Course)
        .filter(Course.id == str(course_id), Course.is_public.is_(True))
        .first()
    )
    if course is None:
        # Do not reveal whether a private course exists.
        raise NotFoundException(detail="Public course not found")

    existing = (
        db.query(CourseMember)
        .filter(
            CourseMember.course_id == course.id,
            CourseMember.user_id == permissions.get_user_id_or_throw(),
        )
        .first()
    )
    if existing is not None:
        return CourseMemberGet.model_validate(existing, from_attributes=True)

    group = _get_or_create_public_group(course, db)
    member = CourseMember(
        user_id=permissions.get_user_id_or_throw(),
        course_id=course.id,
        course_group_id=group.id,
        course_role_id="_student",
        properties={"self_subscribed": True},
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    # Preserve the existing membership lifecycle: student profile,
    # submission-group provisioning, and any configured repository workflow.
    await course_member_post_create(member, db)
    return CourseMemberGet.model_validate(member, from_attributes=True)

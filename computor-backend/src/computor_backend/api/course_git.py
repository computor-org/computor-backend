"""Lecturer-facing course git binding endpoints.

Sets/views where a course's student-template lives and which student-repo modes
the course offers. Distinct from the student-facing descriptor at
``GET /user/courses/{course_id}/git`` (which is membership-gated and token-free).
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from computor_backend.business_logic.course_git import (
    get_course_git_binding,
    upsert_course_git_binding,
)
from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_types.course_git import CourseGitBindingGet, CourseGitBindingUpsert

course_git_router = APIRouter()


@course_git_router.put("/courses/{course_id}/git", response_model=CourseGitBindingGet)
def upsert_course_git_binding_endpoint(
    course_id: UUID | str,
    data: CourseGitBindingUpsert,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Create or replace the course's git binding (lecturer cohort only)."""
    return upsert_course_git_binding(course_id, data, permissions, db)


@course_git_router.get("/courses/{course_id}/git", response_model=CourseGitBindingGet)
def get_course_git_binding_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Full git binding for a course (lecturer cohort only)."""
    return get_course_git_binding(course_id, permissions, db)

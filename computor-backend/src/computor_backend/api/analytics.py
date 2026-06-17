from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from computor_backend.analytics import AnalyticsCutoffs
from computor_backend.analytics.service import AnalyticsService
from computor_backend.database import get_db
from computor_backend.exceptions import ForbiddenException, NotFoundException
from computor_backend.model.auth import User
from computor_backend.model.course import CourseMember
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal
from computor_types.analytics import (
    AnalyticsCourseAccess,
    AnalyticsCourseSummary,
    AnalyticsJobStatus,
    AnalyticsRefreshRequest,
    AnalyticsStudentList,
    AnalyticsStudentReport,
    AnalyticsStudentTimeline,
)


analytics_router = APIRouter(prefix="/analytics")
ANALYTICS_READ_ROLE = "_tutor"
ANALYTICS_REFRESH_ROLE = "_lecturer"


@analytics_router.get(
    "/courses",
    response_model=list[AnalyticsCourseAccess],
)
async def list_analytics_courses(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> list[AnalyticsCourseAccess]:
    return AnalyticsService.from_settings().list_courses(
        user_email=_principal_email(permissions, db),
        minimum_role=ANALYTICS_READ_ROLE,
        include_all=permissions.is_admin,
    )


@analytics_router.post(
    "/courses/{course_id}/refresh",
    response_model=AnalyticsJobStatus,
)
async def refresh_course_analytics(
    course_id: str,
    request: AnalyticsRefreshRequest,
    background_tasks: BackgroundTasks,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> AnalyticsJobStatus:
    _require_course_role(
        permissions,
        db,
        course_id,
        ANALYTICS_REFRESH_ROLE,
        source_name=request.source_name,
    )
    service = AnalyticsService.from_settings(source_name=request.source_name)
    return service.trigger_refresh(
        course_id=course_id,
        request=request,
        requested_by_user_id=permissions.get_user_id(),
        background_tasks=background_tasks,
    )


@analytics_router.get(
    "/courses/{course_id}/jobs",
    response_model=list[AnalyticsJobStatus],
)
async def list_course_analytics_jobs(
    course_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
) -> list[AnalyticsJobStatus]:
    _require_course_role(permissions, db, course_id, ANALYTICS_READ_ROLE)
    return AnalyticsService.from_settings().list_jobs(course_id, limit=limit)


@analytics_router.get(
    "/jobs/{job_id}",
    response_model=AnalyticsJobStatus,
)
async def get_analytics_job(
    job_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> AnalyticsJobStatus:
    job = AnalyticsService.from_settings().get_job(job_id)
    _require_course_role(permissions, db, job.course_id, ANALYTICS_READ_ROLE)
    return job


@analytics_router.get(
    "/courses/{course_id}/summary",
    response_model=AnalyticsCourseSummary,
)
async def get_course_analytics_summary(
    course_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    submission_cutoff: datetime | None = None,
    grading_cutoff: datetime | None = None,
) -> AnalyticsCourseSummary:
    _require_course_role(permissions, db, course_id, ANALYTICS_READ_ROLE)
    return AnalyticsService.from_settings().course_summary(
        course_id,
        _cutoffs(submission_cutoff, grading_cutoff),
    )


@analytics_router.get(
    "/courses/{course_id}/students",
    response_model=AnalyticsStudentList,
)
async def list_course_analytics_students(
    course_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    submission_cutoff: datetime | None = None,
    grading_cutoff: datetime | None = None,
) -> AnalyticsStudentList:
    _require_course_role(permissions, db, course_id, ANALYTICS_READ_ROLE)
    return AnalyticsService.from_settings().student_list(
        course_id,
        _cutoffs(submission_cutoff, grading_cutoff),
    )


@analytics_router.get(
    "/courses/{course_id}/students/{course_member_id}",
    response_model=AnalyticsStudentReport,
)
async def get_course_analytics_student_report(
    course_id: str,
    course_member_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    submission_cutoff: datetime | None = None,
    grading_cutoff: datetime | None = None,
) -> AnalyticsStudentReport:
    _require_course_role(permissions, db, course_id, ANALYTICS_READ_ROLE)
    return AnalyticsService.from_settings().student_report(
        course_id,
        course_member_id,
        _cutoffs(submission_cutoff, grading_cutoff),
    )


@analytics_router.get(
    "/courses/{course_id}/students/{course_member_id}/timeline",
    response_model=AnalyticsStudentTimeline,
)
async def get_course_analytics_student_timeline(
    course_id: str,
    course_member_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    submission_cutoff: datetime | None = None,
    grading_cutoff: datetime | None = None,
) -> AnalyticsStudentTimeline:
    _require_course_role(permissions, db, course_id, ANALYTICS_READ_ROLE)
    return AnalyticsService.from_settings().student_timeline(
        course_id,
        course_member_id,
        _cutoffs(submission_cutoff, grading_cutoff),
    )


def _require_course_role(
    permissions: Principal,
    db: Session,
    course_id: str,
    minimum_role: str,
    source_name: str | None = None,
) -> None:
    if permissions.is_admin:
        return
    has_course_role = check_course_permissions(
        permissions,
        CourseMember,
        minimum_role,
        db,
    ).filter(
        CourseMember.course_id == course_id,
        CourseMember.user_id == permissions.get_user_id(),
    ).first()
    if has_course_role:
        return

    email = _principal_email(permissions, db)
    if email is None:
        raise ForbiddenException("Analytics access requires course staff role")
    try:
        has_analytics_role = AnalyticsService.from_settings(
            source_name=source_name,
        ).has_course_role(course_id, email, minimum_role)
    except NotFoundException:
        has_analytics_role = False
    if not has_analytics_role:
        raise ForbiddenException("Analytics access requires course staff role")


def _principal_email(permissions: Principal, db: Session) -> str | None:
    user_id = permissions.get_user_id()
    if not user_id or not hasattr(db, "query"):
        return None
    row = db.query(User.email).filter(User.id == user_id).first()
    if row is None:
        return None
    email = row[0] if hasattr(row, "__getitem__") else getattr(row, "email", None)
    return str(email) if email else None


def _cutoffs(
    submission_cutoff: datetime | None,
    grading_cutoff: datetime | None,
) -> AnalyticsCutoffs:
    return AnalyticsCutoffs(
        submission=submission_cutoff,
        grading=grading_cutoff,
    ).normalized()

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from computor_types.course_member_gradings import (
    CourseMemberGradingsGet,
    CourseMemberGradingsList,
)


class AnalyticsRefreshRequest(BaseModel):
    source_name: str = "green"
    submission_cutoff: datetime | None = None
    grading_cutoff: datetime | None = None
    run_id: str | None = None
    tables: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalyticsJobStatus(BaseModel):
    job_id: str
    course_id: str
    source_name: str
    requested_by_user_id: str | None = None
    status: str
    progress: dict[str, Any] = Field(default_factory=dict)
    submission_cutoff: datetime | None = None
    grading_cutoff: datetime | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    snapshot_path: str | None = None
    row_counts: dict[str, int] = Field(default_factory=dict)
    high_water_marks: dict[str, dict[str, str]] = Field(default_factory=dict)
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalyticsCourseAccess(BaseModel):
    course_id: str
    title: str | None = None
    path: str | None = None
    source_name: str
    role: str | None = None
    total_students: int = 0
    latest_job: AnalyticsJobStatus | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalyticsCourseSummary(BaseModel):
    course_id: str
    total_students: int
    total_max_assignments: int
    total_submitted_assignments: int
    submitted_percentage: float
    total_graded_assignments: int
    graded_percentage: float
    average_grading: float | None = None
    latest_submission_at: datetime | None = None
    submission_cutoff: datetime | None = None
    grading_cutoff: datetime | None = None
    latest_job: AnalyticsJobStatus | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalyticsStudentCheckpoint(BaseModel):
    course_member_id: str
    course_id: str
    user_id: str | None = None
    username: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    student_id: str | None = None
    total_max_assignments: int
    total_submitted_assignments: int
    submitted_percentage: float
    total_graded_assignments: int
    graded_percentage: float
    average_grading: float | None = None
    latest_submission_at: datetime | None = None
    late_submission_count: int = 0
    # Score-pass over standard (submittable) examples: a pass means the latest
    # grade reached the pass threshold, not merely that the student submitted.
    standard_total: int = 0
    standard_passed: int = 0
    pass_rate: float = 0.0
    average_score: float | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalyticsTutorComment(BaseModel):
    author_role: str
    text: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalyticsStandardExample(BaseModel):
    content_id: str
    path: str
    title: str
    category: str | None = None
    unit: str | None = None
    score: float | None = None
    passed: bool = False
    test_rounds: int = 0
    submitted_at: datetime | None = None
    official: bool = False
    late: bool = False
    flags: list[str] = Field(default_factory=list)
    comments: list[AnalyticsTutorComment] = Field(default_factory=list)
    href: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalyticsExampleSourceFile(BaseModel):
    name: str
    content: str

    model_config = ConfigDict(from_attributes=True)


class AnalyticsExampleSource(BaseModel):
    content_id: str
    title: str
    files: list[AnalyticsExampleSourceFile] = Field(default_factory=list)
    href: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalyticsTimelineEvent(BaseModel):
    occurred_at: datetime
    event_type: str
    course_content_id: str | None = None
    path: str | None = None
    title: str | None = None
    artifact_id: str | None = None
    result_id: str | None = None
    grade: float | None = None
    status: int | None = None
    submit: bool | None = None
    version_identifier: str | None = None
    relation_to_submission_cutoff: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalyticsStudentTimeline(BaseModel):
    course_id: str
    course_member_id: str
    submission_cutoff: datetime | None = None
    grading_cutoff: datetime | None = None
    events: list[AnalyticsTimelineEvent] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AnalyticsStudentReport(BaseModel):
    checkpoint: AnalyticsStudentCheckpoint
    grading: CourseMemberGradingsGet
    timeline: AnalyticsStudentTimeline

    model_config = ConfigDict(from_attributes=True)


class AnalyticsStudentList(BaseModel):
    students: list[AnalyticsStudentCheckpoint]
    gradings: list[CourseMemberGradingsList] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

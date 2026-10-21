"""
Course analytics DTOs for the lecturer dashboard.

Everything here is derived from data the platform already stores: test runs
(``result`` rows and their stored test report), submitted artifacts and
human gradings. Nothing is tracked in addition, so every figure can be traced
back to the runs and submissions it was computed from.
"""

from datetime import datetime

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Typical errors
# ---------------------------------------------------------------------------


class TypicalErrorExample(BaseModel):
    """One concrete failing run that produced an error group."""

    result_id: str
    course_member_id: str
    student_name: str | None = None
    created_at: datetime | None = None
    message: str | None = Field(
        None, description="The original, un-normalized message of this run"
    )


class TypicalError(BaseModel):
    """A failing test and normalized message shared by one or more runs."""

    course_content_id: str
    course_content_title: str | None = None
    test_name: str = Field(description="Failing test, as 'collection / test'")
    message: str = Field(
        description="Normalized message: numbers, quoted values and paths replaced by placeholders"
    )
    occurrences: int = Field(description="Number of failing runs in this group")
    affected_students: int = Field(description="Distinct course members with at least one such run")
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    examples: list[TypicalErrorExample] = Field(
        default_factory=list, description="Up to three example runs, newest first"
    )


class TypicalErrorsGet(BaseModel):
    """Aggregated failing tests for a course or one assignment."""

    course_id: str
    course_content_id: str | None = None
    results_scanned: int = Field(description="Test runs whose stored report was read")
    results_without_report: int = Field(
        description="Scanned runs for which no stored test report was available"
    )
    truncated: bool = Field(
        description="True when more runs exist than were scanned (newest runs are scanned first)"
    )
    errors: list[TypicalError] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Attempt timeline and history
# ---------------------------------------------------------------------------


class ActivityEvent(BaseModel):
    """One entry of a student's chronological history."""

    kind: str = Field(description="'test_run', 'submission' or 'grading'")
    at: datetime
    course_content_id: str
    course_content_title: str | None = None
    result_id: str | None = None
    artifact_id: str | None = None
    grade: float | None = Field(None, description="0.0-1.0; test result or human grade")
    status: str | None = Field(
        None, description="Test system status for runs, grading status slug for gradings"
    )
    is_submission: bool = Field(False, description="Test run executed on an official submission")
    feedback: str | None = None
    graded_by: str | None = None


class AttemptTimeline(BaseModel):
    """Attempt timeline ("Bearbeitungsverlauf") of one student on one assignment."""

    course_content_id: str
    course_content_title: str | None = None
    test_runs: int = 0
    submissions: int = 0
    first_activity_at: datetime | None = None
    last_activity_at: datetime | None = None
    first_submission_at: datetime | None = None
    last_submission_at: datetime | None = None
    first_full_score_at: datetime | None = Field(
        None, description="First test run that reached the full score"
    )
    best_grade: float | None = None
    latest_grade: float | None = None
    active_days: int = Field(0, description="Distinct calendar days (UTC) with a run or submission")
    median_gap_minutes: float | None = Field(
        None, description="Median time between consecutive test runs"
    )
    estimated_active_minutes: float | None = Field(
        None,
        description=(
            "Estimate: sum of gaps between consecutive runs that are at most "
            "session_gap_minutes apart. Work without test runs is not visible."
        ),
    )
    hours_before_due: float | None = Field(
        None,
        description="Due date minus last submission in hours (negative = after the due date); only with due_at",
    )


class FlagReason(BaseModel):
    """A rule that fired for a student, with the evidence behind it."""

    code: str = Field(
        description=(
            "many_failed_attempts | last_minute | late_submission | "
            "sudden_jump | inactive | low_progress"
        )
    )
    severity: str = Field(description="'info' or 'warning'")
    title: str
    reason: str = Field(description="Plain-language explanation with the numbers that triggered it")
    course_content_id: str | None = None
    course_content_title: str | None = None


class FlagRule(BaseModel):
    """Description of one rule and its threshold, as applied to this response."""

    code: str
    title: str
    description: str


class StudentActivityGet(BaseModel):
    """History, attempt timelines and flags for one course member."""

    course_member_id: str
    course_id: str
    due_at: datetime | None = None
    session_gap_minutes: int
    events: list[ActivityEvent] = Field(default_factory=list, description="Newest first")
    timelines: list[AttemptTimeline] = Field(default_factory=list)
    flags: list[FlagReason] = Field(default_factory=list)
    rules: list[FlagRule] = Field(default_factory=list)


class StudentFlags(BaseModel):
    course_member_id: str
    student_name: str | None = None
    student_id: str | None = None
    flags: list[FlagReason] = Field(default_factory=list)


class CourseFlagsGet(BaseModel):
    """Rule-based flags ("Auffälligkeiten") for every student of a course."""

    course_id: str
    due_at: datetime | None = None
    rules: list[FlagRule] = Field(default_factory=list)
    students: list[StudentFlags] = Field(
        default_factory=list, description="Only students with at least one flag"
    )

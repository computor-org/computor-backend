"""Test-run and submission budgets: one resolver, one counter, one enforcer.

Before this module the two budgets were counted in three different places at
three different scopes — enforcement counted ``Result`` rows *per artifact*,
the student/tutor trees counted finished results *per course content*, and the
grading view counted every result *per course member*. A student with a limit
of 2 could therefore run 5 tests and be shown "5/2". Display and enforcement
must derive from the same definitions, so both now import from here.

Two rules worth stating explicitly:

Inheritance is three-tiered, most specific first::

    submission group override -> course content -> course default -> unlimited

``None`` at every tier means "no limit". The group columns are a *deliberate
override* (e.g. a tutor granting one student extra attempts) and nothing else;
they used to be a copy taken when the group was created, which is why editing
a course content never reached students who had already started.

A run consumes budget unless it is retryable. ``RETRYABLE_RESULT_STATUSES``
(failed/cancelled/crashed) is the project's own already-encoded notion of "this
run does not occupy the slot" — the partial unique indexes on ``result`` are
built from the same tuple — so a student is never charged for an
infrastructure failure, while a queued or running test reserves its slot
immediately.
"""
import logging
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from computor_backend.exceptions import BadRequestException
from computor_backend.model.artifact import SubmissionArtifact
from computor_backend.model.result import Result
from computor_types.tasks import RETRYABLE_RESULT_STATUSES

logger = logging.getLogger(__name__)

# Error codes raised from here. SUBMIT_004 predates this module.
TEST_LIMIT_ERROR_CODE = "SUBMIT_004"
SUBMISSION_LIMIT_ERROR_CODE = "SUBMIT_009"
BOTH_LIMITS_ERROR_CODE = "SUBMIT_010"


def resolve_limits(
    course_content,
    submission_group=None,
    course=None,
) -> Tuple[Optional[int], Optional[int]]:
    """Return the effective ``(max_test_runs, max_submissions)``.

    Walks the three tiers described in the module docstring and returns the
    first value that is set at each. ``None`` means unlimited.
    """
    if course is None and course_content is not None:
        course = getattr(course_content, "course", None)

    def pick(attribute: str) -> Optional[int]:
        for holder in (submission_group, course_content, course):
            if holder is None:
                continue
            value = getattr(holder, attribute, None)
            if value is not None:
                return value
        return None

    return pick("max_test_runs"), pick("max_submissions")


def count_consumed_test_runs(db: Session, submission_group_id: UUID | str) -> int:
    """Count the test runs that have consumed budget for a submission group.

    Joined through ``SubmissionArtifact`` rather than ``Result.submission_group_id``:
    that column is nullable and is not populated on every insert path, whereas
    every countable run necessarily has an artifact.
    """
    return db.query(func.count(Result.id)).select_from(Result).join(
        SubmissionArtifact, SubmissionArtifact.id == Result.submission_artifact_id
    ).filter(
        SubmissionArtifact.submission_group_id == submission_group_id,
        Result.test_system_id.isnot(None),
        Result.status.notin_(RETRYABLE_RESULT_STATUSES),
    ).scalar() or 0


def count_consumed_submissions(db: Session, submission_group_id: UUID | str) -> int:
    """Count the official submissions of a submission group."""
    return db.query(func.count(SubmissionArtifact.id)).filter(
        SubmissionArtifact.submission_group_id == submission_group_id,
        SubmissionArtifact.submit.is_(True),
    ).scalar() or 0


def has_test_budget(db: Session, submission_group, course_content, course=None) -> bool:
    """Whether another test run is within the effective test limit."""
    max_test_runs, _ = resolve_limits(course_content, submission_group, course)
    if max_test_runs is None:
        return True
    return count_consumed_test_runs(db, submission_group.id) < max_test_runs


def has_submission_budget(db: Session, submission_group, course_content, course=None) -> bool:
    """Whether another submission is within the effective submission limit."""
    _, max_submissions = resolve_limits(course_content, submission_group, course)
    if max_submissions is None:
        return True
    return count_consumed_submissions(db, submission_group.id) < max_submissions


def enforce_max_test_runs(
    db: Session,
    submission_group,
    course_content,
    *,
    course=None,
    exempt: bool = False,
    error_code: str = TEST_LIMIT_ERROR_CODE,
) -> None:
    """Raise when the effective test-run budget is exhausted.

    ``exempt`` short-circuits for lecturers and tutors, who are not subject to
    student budgets.
    """
    if exempt:
        return

    max_test_runs, _ = resolve_limits(course_content, submission_group, course)
    if max_test_runs is None:
        return

    used = count_consumed_test_runs(db, submission_group.id)
    if used >= max_test_runs:
        raise BadRequestException(
            detail=(
                f"Maximum test runs reached for this assignment "
                f"({used} of {max_test_runs} used)"
            ),
            error_code=error_code,
        )


def enforce_max_submissions(
    db: Session,
    submission_group,
    course_content,
    *,
    course=None,
    exempt: bool = False,
    error_code: str = SUBMISSION_LIMIT_ERROR_CODE,
) -> None:
    """Raise when the effective submission budget is exhausted."""
    if exempt:
        return

    _, max_submissions = resolve_limits(course_content, submission_group, course)
    if max_submissions is None:
        return

    used = count_consumed_submissions(db, submission_group.id)
    if used >= max_submissions:
        raise BadRequestException(
            detail=(
                f"Maximum submissions reached for this assignment "
                f"({used} of {max_submissions} used)"
            ),
            error_code=error_code,
        )

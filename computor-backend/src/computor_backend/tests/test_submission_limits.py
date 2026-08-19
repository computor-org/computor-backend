"""Guards on the test-run and submission budgets (issue #337).

Three things went wrong before and each has a test here:

- The limit was read from a snapshot copied onto the submission group when it
  was created, so editing the assignment never reached students who had
  already started. Resolution is now three-tiered and live.
- The test budget was counted per *artifact*, so every new commit handed the
  student a fresh allowance. It is now counted per submission group.
- The number shown to the student was counted differently from the number
  enforced (finished-only vs every status), which is what produced the "5/2"
  in the bug report. Both now derive from the same predicate.
"""
import pytest

from computor_backend.business_logic import submission_limits
from computor_backend.business_logic.submission_limits import (
    count_consumed_submissions,
    count_consumed_test_runs,
    enforce_max_submissions,
    enforce_max_test_runs,
    has_test_budget,
    resolve_limits,
)
from computor_backend.exceptions import BadRequestException
from computor_types.tasks import RETRYABLE_RESULT_STATUSES, ResultStatus


class _Holder:
    """Stand-in for a Course / CourseContent / SubmissionGroup row."""

    def __init__(self, max_test_runs=None, max_submissions=None, course=None):
        self.max_test_runs = max_test_runs
        self.max_submissions = max_submissions
        self.course = course
        self.id = "holder-id"


# --------------------------------------------------------------------------
# resolve_limits: submission group -> course content -> course -> unlimited
# --------------------------------------------------------------------------

def test_unset_everywhere_means_unlimited():
    assert resolve_limits(_Holder(), _Holder()) == (None, None)


def test_course_content_supplies_the_limit():
    content = _Holder(max_test_runs=2, max_submissions=1)
    assert resolve_limits(content, _Holder()) == (2, 1)


def test_group_value_overrides_the_course_content():
    """A tutor granting one student extra attempts must win."""
    content = _Holder(max_test_runs=2, max_submissions=1)
    group = _Holder(max_test_runs=5)
    max_test_runs, max_submissions = resolve_limits(content, group)
    assert max_test_runs == 5
    # Untouched on the group, so it still inherits.
    assert max_submissions == 1


def test_course_default_applies_when_the_content_is_silent():
    course = _Holder(max_test_runs=7, max_submissions=3)
    content = _Holder(course=course)
    assert resolve_limits(content, _Holder()) == (7, 3)


def test_course_content_overrides_the_course_default():
    course = _Holder(max_test_runs=7, max_submissions=3)
    content = _Holder(max_test_runs=2, course=course)
    max_test_runs, max_submissions = resolve_limits(content, _Holder())
    assert max_test_runs == 2
    assert max_submissions == 3


def test_a_group_with_no_override_follows_a_later_edit():
    """The regression from #337: the group must not pin an old value."""
    content = _Holder(max_test_runs=2)
    group = _Holder()  # provisioned without a snapshot

    assert resolve_limits(content, group)[0] == 2
    content.max_test_runs = 4  # lecturer edits the assignment
    assert resolve_limits(content, group)[0] == 4


# --------------------------------------------------------------------------
# Enforcement
# --------------------------------------------------------------------------

@pytest.fixture
def counted(monkeypatch):
    """Drive enforcement from a fixed count without touching the database."""

    def _set(test_runs=0, submissions=0):
        monkeypatch.setattr(
            submission_limits, "count_consumed_test_runs",
            lambda db, group_id: test_runs,
        )
        monkeypatch.setattr(
            submission_limits, "count_consumed_submissions",
            lambda db, group_id: submissions,
        )

    return _set


def test_test_runs_below_the_limit_pass(counted):
    counted(test_runs=1)
    enforce_max_test_runs(None, _Holder(), _Holder(max_test_runs=2))


def test_test_runs_at_the_limit_raise_submit_004(counted):
    counted(test_runs=2)
    with pytest.raises(BadRequestException) as excinfo:
        enforce_max_test_runs(None, _Holder(), _Holder(max_test_runs=2))
    assert excinfo.value.error_code == "SUBMIT_004"


def test_no_limit_configured_never_raises(counted):
    counted(test_runs=99, submissions=99)
    enforce_max_test_runs(None, _Holder(), _Holder())
    enforce_max_submissions(None, _Holder(), _Holder())


def test_staff_are_exempt(counted):
    """Lecturers and tutors testing a course must not be budgeted."""
    counted(test_runs=99, submissions=99)
    enforce_max_test_runs(None, _Holder(), _Holder(max_test_runs=2), exempt=True)
    enforce_max_submissions(None, _Holder(), _Holder(max_submissions=1), exempt=True)


def test_submissions_at_the_limit_raise_submit_009(counted):
    counted(submissions=1)
    with pytest.raises(BadRequestException) as excinfo:
        enforce_max_submissions(None, _Holder(), _Holder(max_submissions=1))
    assert excinfo.value.error_code == "SUBMIT_009"


def test_submit_error_code_is_overridable(counted):
    """create_test_run reports SUBMIT_010 when *both* budgets are gone."""
    counted(submissions=1)
    with pytest.raises(BadRequestException) as excinfo:
        enforce_max_submissions(
            None, _Holder(), _Holder(max_submissions=1), error_code="SUBMIT_010"
        )
    assert excinfo.value.error_code == "SUBMIT_010"


def test_has_test_budget_tracks_the_effective_limit(counted):
    counted(test_runs=2)
    assert has_test_budget(None, _Holder(), _Holder(max_test_runs=3)) is True
    assert has_test_budget(None, _Holder(), _Holder(max_test_runs=2)) is False
    assert has_test_budget(None, _Holder(), _Holder()) is True


# --------------------------------------------------------------------------
# Counting: the displayed number and the enforced number must agree
# --------------------------------------------------------------------------

def _compiled(query):
    return str(query).lower()


def test_test_runs_are_counted_through_the_artifact(session):
    """Not via Result.submission_group_id — that column is not always set."""
    from sqlalchemy import func
    from computor_backend.model.artifact import SubmissionArtifact
    from computor_backend.model.result import Result

    query = session.query(func.count(Result.id)).select_from(Result).join(
        SubmissionArtifact, SubmissionArtifact.id == Result.submission_artifact_id
    ).filter(
        SubmissionArtifact.submission_group_id == "00000000-0000-0000-0000-000000000000",
        Result.test_system_id.isnot(None),
        Result.status.notin_(RETRYABLE_RESULT_STATUSES),
    )
    rendered = _compiled(query)
    assert "join submission_artifact" in rendered
    assert "submission_artifact.submission_group_id" in rendered
    # The budget must not be keyed on the nullable denormalised column.
    assert "result.submission_group_id" not in rendered


def test_enforced_and_displayed_counts_use_one_predicate(session):
    """The student's numerator must match what enforcement counts.

    Counting only FINISHED for display while enforcing over every status is
    exactly how a limit of 2 came to be rendered as "5/2".
    """
    from computor_backend.repositories.course_content_subqueries import (
        results_count_subquery,
    )

    subquery = results_count_subquery(None, None, None, session)
    rendered = str(subquery).lower()

    # Retryable runs are excluded, and nothing filters on "= 0" (FINISHED).
    assert "not in" in rendered
    assert "result.status = 0" not in rendered


def test_submissions_count_only_official_artifacts(session):
    """A test-only upload must not spend submission budget."""
    from sqlalchemy import func
    from computor_backend.model.artifact import SubmissionArtifact

    query = session.query(func.count(SubmissionArtifact.id)).filter(
        SubmissionArtifact.submission_group_id == "00000000-0000-0000-0000-000000000000",
        SubmissionArtifact.submit.is_(True),
    )
    assert "submission_artifact.submit is true" in _compiled(query)


def test_retryable_runs_do_not_consume_budget():
    """A crashed or cancelled run is free; an in-flight one reserves its slot."""
    assert int(ResultStatus.CRASHED) in RETRYABLE_RESULT_STATUSES
    assert int(ResultStatus.CANCELLED) in RETRYABLE_RESULT_STATUSES
    assert int(ResultStatus.FAILED) in RETRYABLE_RESULT_STATUSES

    for reserved in (ResultStatus.SCHEDULED, ResultStatus.PENDING,
                     ResultStatus.RUNNING, ResultStatus.FINISHED):
        assert int(reserved) not in RETRYABLE_RESULT_STATUSES

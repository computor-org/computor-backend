"""Re-testing an already-FINISHED version must 400, never 500 (issue #307).

Two ``SubmissionArtifact`` rows can share a ``version_identifier`` — a
byte-identical re-upload hashes to the same content id — so the artifact-keyed
``find_active_test`` guard does not catch it. The version-keyed guard did catch
it but only *raised* while the workflow was still running; a FINISHED row fell
through to the INSERT and violated
``result_version_identifier_member_content_partial_key`` with a 500.

Policy is unchanged (one completed test per version); it just reports itself
properly now, via the same SUBMIT_008 the artifact-keyed guard already uses.
"""
import pytest

from computor_backend.business_logic.testing_orchestration import (
    IN_PROGRESS_STATUSES,
    RETRYABLE_STATUSES,
)
from computor_types.tasks import ResultStatus


def test_finished_is_neither_retryable_nor_in_progress():
    """This is exactly why #307 fell through both guards into the INSERT."""
    finished = int(ResultStatus.FINISHED)
    assert finished not in RETRYABLE_STATUSES
    assert finished not in IN_PROGRESS_STATUSES


@pytest.mark.parametrize(
    "status",
    [
        int(ResultStatus.FINISHED),
        int(ResultStatus.SCHEDULED),
        int(ResultStatus.PENDING),
        int(ResultStatus.RUNNING),
        int(ResultStatus.PAUSED),
    ],
)
def test_every_index_occupying_status_is_refused_not_inserted(status):
    """The endpoint's post-sync guard is `status not in RETRYABLE_STATUSES`.

    That predicate must be true for every status the partial unique index
    counts, otherwise the request proceeds to an INSERT the index will reject.
    """
    assert status not in RETRYABLE_STATUSES, (
        f"status {status} occupies the unique index but would not be refused"
    )


@pytest.mark.parametrize("status", list(RETRYABLE_STATUSES))
def test_retryable_statuses_still_allow_a_new_run(status):
    """A failed/cancelled/crashed run must remain re-runnable."""
    assert status in RETRYABLE_STATUSES
    assert status not in IN_PROGRESS_STATUSES


def test_guard_predicate_matches_the_index_predicate():
    """The endpoint filter and the guard must use the same set as the index.

    `create_test_run` selects existing rows with
    `Result.status.notin_(RETRYABLE_STATUSES)` and then refuses any row whose
    status is `not in RETRYABLE_STATUSES` — so every row the query can return
    is refused, and nothing reaches the INSERT.
    """
    from computor_types.tasks import RETRYABLE_RESULT_STATUSES

    selectable = [s for s in range(8) if s not in RETRYABLE_RESULT_STATUSES]
    for status in selectable:
        assert status not in RETRYABLE_STATUSES, (
            f"status {status} is selectable by the guard query but not refused"
        )


def test_endpoint_refuses_before_insert_and_catches_the_race():
    """Source-level guard for the two things #307 needed.

    Deliberately keys on the *version*-worded message, not on ``SUBMIT_008``:
    the pre-existing artifact-keyed guard already used that code earlier in the
    same function, so asserting on the code alone would pass against the very
    bug this test exists to prevent.
    """
    import inspect

    from computor_backend.api import tests as tests_api

    source = inspect.getsource(tests_api.create_test_run)

    version_refusal = "already tested this version"
    assert version_refusal in source, (
        "the version-keyed already-tested refusal is missing — a FINISHED row "
        "would fall through to the INSERT and 500 (issue #307)"
    )
    assert source.index(version_refusal) < source.index("db.add(result)"), (
        "the refusal must precede the INSERT it is protecting"
    )

    # The concurrent-double-submit net around the commit.
    assert "except IntegrityError" in source
    assert source.index("except IntegrityError") > source.index("db.add(result)")

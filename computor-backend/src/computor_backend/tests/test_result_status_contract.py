"""Guards on the ``Result.status`` vocabulary.

The retryable-status set exists in two forms that MUST agree: the Python tuple
the endpoints filter on, and the ``status NOT IN (...)`` predicate baked into
the partial unique indexes on ``result``. When they drifted, the app happily
decided "no blocking run exists" and the INSERT then died on the index with an
IntegrityError 500. Both are now derived from one definition; these tests fail
if anyone re-introduces a literal or changes the set without a migration.
"""
import pytest
from sqlalchemy import text

from computor_types.tasks import (
    RETRYABLE_RESULT_STATUSES,
    RETRYABLE_RESULT_STATUSES_SQL,
    ResultStatus,
)


def _partial_unique_predicates():
    from computor_backend.model.result import Result

    return {
        ix.name: str(ix.dialect_options["postgresql"]["where"])
        for ix in Result.__table__.indexes
        if ix.unique
    }


def test_retryable_set_is_failed_cancelled_crashed():
    """Changing this set requires a migration — it is baked into DB indexes."""
    assert RETRYABLE_RESULT_STATUSES == (
        int(ResultStatus.FAILED),
        int(ResultStatus.CANCELLED),
        int(ResultStatus.CRASHED),
    )
    assert RETRYABLE_RESULT_STATUSES_SQL == "1, 2, 6"


def test_index_predicates_match_the_python_set():
    predicates = _partial_unique_predicates()
    assert predicates, "expected partial unique indexes on result"

    expected = f"status NOT IN ({RETRYABLE_RESULT_STATUSES_SQL})"
    for name, predicate in predicates.items():
        assert predicate == expected, f"{name} predicate drifted from the Python set"


def test_index_predicates_match_the_deployed_migration():
    """The shipped schema says NOT IN (1, 2, 6); regeneration must not change it."""
    for predicate in _partial_unique_predicates().values():
        assert predicate == "status NOT IN (1, 2, 6)"


def test_in_progress_and_retryable_are_disjoint():
    """A run cannot be both 'still blocking' and 'safe to retry'."""
    from computor_backend.business_logic.testing_orchestration import (
        IN_PROGRESS_STATUSES,
        RETRYABLE_STATUSES,
    )

    assert RETRYABLE_STATUSES == RETRYABLE_RESULT_STATUSES
    assert not set(IN_PROGRESS_STATUSES) & set(RETRYABLE_STATUSES)
    # FINISHED is deliberately in neither: it blocks a re-run and is not retryable.
    assert int(ResultStatus.FINISHED) not in IN_PROGRESS_STATUSES
    assert int(ResultStatus.FINISHED) not in RETRYABLE_STATUSES

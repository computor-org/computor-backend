"""The tutor-test *write* endpoints must be service-account only.

``POST /tutors/tests/{id}/results`` and ``.../artifacts/upload`` are how the
testing worker reports a run's outcome. Both had authentication (the router
requires a principal) but no authorization whatsoever — no owner check, no
service check — while their sibling ``input/download`` carefully gated on
owner/admin/service. Any signed-in user could therefore overwrite the result
JSON and artifacts of any tutor test whose id they could guess (the path
parameter is a plain ``str``, not even a UUID).

The only callers are the two worker activities in ``temporal_tutor_testing``,
so the endpoints are now restricted to service accounts and admins.
"""
import pytest

from computor_backend.api.tutor import _assert_may_report_for_tutor_test
from computor_backend.exceptions import ForbiddenException, NotFoundException
from computor_backend.permissions.principal import Principal

TEST_ID = "11111111-2222-3333-4444-555555555555"
OWNER_ID = "owner-user-id"


class _Redis:
    """Stands in for the Redis client; only metadata lookup is exercised."""

    def __init__(self, metadata):
        self._metadata = metadata


@pytest.fixture
def redis_with_test(monkeypatch):
    async def _get_metadata(redis, test_id):
        return redis._metadata

    monkeypatch.setattr(
        "computor_backend.api.tutor.get_tutor_test_metadata", _get_metadata
    )
    return _Redis({"test_id": TEST_ID, "user_id": OWNER_ID})


@pytest.fixture
def redis_without_test(monkeypatch):
    async def _get_metadata(redis, test_id):
        return None

    monkeypatch.setattr(
        "computor_backend.api.tutor.get_tutor_test_metadata", _get_metadata
    )
    return _Redis(None)


@pytest.mark.asyncio
async def test_service_account_may_report(redis_with_test):
    """The testing worker must keep working — it authenticates as a service."""
    principal = Principal(user_id="worker-user", is_service=True)
    metadata = await _assert_may_report_for_tutor_test(
        TEST_ID, principal, redis_with_test
    )
    assert metadata["test_id"] == TEST_ID


@pytest.mark.asyncio
async def test_admin_may_report(redis_with_test):
    principal = Principal(user_id="admin-user", is_admin=True)
    await _assert_may_report_for_tutor_test(TEST_ID, principal, redis_with_test)


@pytest.mark.asyncio
async def test_unrelated_user_is_rejected(redis_with_test):
    """The actual hole: any logged-in user could poison any tutor test."""
    principal = Principal(user_id="some-other-user")
    with pytest.raises(ForbiddenException):
        await _assert_may_report_for_tutor_test(TEST_ID, principal, redis_with_test)


@pytest.mark.asyncio
async def test_even_the_owning_tutor_cannot_report(redis_with_test):
    """Results are reported by the runner, never self-asserted by the tutor."""
    principal = Principal(user_id=OWNER_ID)
    with pytest.raises(ForbiddenException):
        await _assert_may_report_for_tutor_test(TEST_ID, principal, redis_with_test)


@pytest.mark.asyncio
async def test_unknown_test_is_not_found(redis_without_test):
    """A guessed/expired id must 404 before any storage write happens."""
    principal = Principal(user_id="worker-user", is_service=True)
    with pytest.raises(NotFoundException):
        await _assert_may_report_for_tutor_test(
            TEST_ID, principal, redis_without_test
        )

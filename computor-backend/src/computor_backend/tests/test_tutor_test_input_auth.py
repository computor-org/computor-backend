"""Regression tests for the tutor-test ``input/download`` auth check.

PR #101 added a per-user ownership check to ``download_tutor_test_input``
to close a "any authenticated user can read any tutor's input" hole.
That check was correct in spirit but broke the Temporal worker, which
calls the same endpoint with an API-token-backed service account
whose ``user_id`` is the worker's, not the tutor's. Result: every
tutor-testing workflow died at the input-fetch step → no artifacts
produced → users later saw a confusing 404 on
``/tutors/tests/{id}/artifacts/download``.

The fix wires ``is_service`` (from ``User.is_service``) onto the
``Principal``, and the input-download endpoint now bypasses the
ownership check for service accounts in addition to admins.

Tests below cover both layers:

1. ``Principal.is_service`` exists, defaults to False, round-trips
   through Pydantic serialisation (used by the auth cache).
2. The ``is_admin or is_service`` predicate behaves correctly across
   the four relevant cases (owner / admin / service / outsider).

The endpoint itself isn't directly callable in a unit test (FastAPI
dependency injection, Redis), so we exercise the predicate the
endpoint uses — same shape, no infra.
"""

import pytest

from computor_backend.permissions.principal import Principal


# ---------------------------------------------------------------------------
# Principal.is_service plumbing
# ---------------------------------------------------------------------------


class TestPrincipalIsService:
    def test_default_false(self):
        # Existing call sites that don't set is_service must still get
        # a non-service principal — backward compat.
        p = Principal(user_id="u-1")
        assert p.is_service is False

    def test_explicit_true(self):
        p = Principal(user_id="u-svc", is_service=True)
        assert p.is_service is True

    def test_round_trips_through_serialisation(self):
        # ``PrincipalBuilder.build_with_cache`` writes the Principal
        # to Redis as ``model_dump_json`` and rehydrates with
        # ``model_validate``. is_service must survive that round-trip
        # so cached service principals don't lose their service flag.
        original = Principal(user_id="u-svc", is_service=True, is_admin=False)
        rehydrated = Principal.model_validate(original.model_dump())
        assert rehydrated.is_service is True
        assert rehydrated.is_admin is False

    def test_is_admin_and_is_service_are_independent(self):
        # The two flags don't imply each other. Admins aren't
        # automatically service accounts; service accounts aren't
        # automatically admins.
        admin = Principal(user_id="u-a", is_admin=True)
        service = Principal(user_id="u-s", is_service=True)
        assert admin.is_service is False
        assert service.is_admin is False


# ---------------------------------------------------------------------------
# The ownership-bypass predicate the endpoint uses.
# ---------------------------------------------------------------------------


def _input_download_authorised(principal: Principal, owner_user_id: str) -> bool:
    """Mirror of the predicate in ``download_tutor_test_input``.

    Kept as a free function in the test so the test stays decoupled
    from the FastAPI endpoint — what we're guarding against is the
    LOGIC, not the routing.
    """
    if not owner_user_id:
        return True  # legacy entries without a user_id slot through
    if str(principal.user_id) == owner_user_id:
        return True
    return bool(principal.is_admin or principal.is_service)


class TestInputDownloadAuthorisation:
    OWNER_ID = "u-tutor"

    def test_owner_allowed(self):
        owner = Principal(user_id=self.OWNER_ID)
        assert _input_download_authorised(owner, self.OWNER_ID) is True

    def test_admin_allowed(self):
        admin = Principal(user_id="u-admin", is_admin=True)
        assert _input_download_authorised(admin, self.OWNER_ID) is True

    def test_service_account_allowed(self):
        # The whole point of the fix — the worker, authenticating as
        # a service account, can fetch the tutor's input even though
        # it isn't the tutor.
        worker = Principal(user_id="u-worker", is_service=True)
        assert _input_download_authorised(worker, self.OWNER_ID) is True

    def test_outsider_denied(self):
        # Regression: another regular user must STILL get rejected.
        # PR #101's intent was to close exactly this case.
        snoop = Principal(user_id="u-snoop")
        assert _input_download_authorised(snoop, self.OWNER_ID) is False

    def test_outsider_with_neither_flag_denied(self):
        # Defensive: explicit False on both flags is the same as default.
        snoop = Principal(user_id="u-snoop", is_admin=False, is_service=False)
        assert _input_download_authorised(snoop, self.OWNER_ID) is False

    def test_legacy_entry_without_owner_user_id_allowed(self):
        # Defensive: if Redis ever returns an entry without a
        # ``user_id`` field (pre-PR-#101 metadata that's still
        # within TTL during a deploy), we don't want to lock it down
        # surprisingly. The endpoint guards with ``if metadata.get(...)``
        # already; this just documents the behaviour.
        anybody = Principal(user_id="u-x")
        assert _input_download_authorised(anybody, "") is True

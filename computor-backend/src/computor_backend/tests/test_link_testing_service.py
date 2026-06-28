"""Unit tests for ``_link_testing_service`` — assign-time testing-service linking.

It must be **best-effort**: link when the example version's executionBackend
resolves to an enabled service, but NEVER raise (and never block the assignment)
when it can't — the testing service is only needed at test-execution time.
Regression guard for "assigning an example 400s because no backend is registered".
"""
from types import SimpleNamespace

from computor_backend.business_logic.lecturer_deployment import _link_testing_service


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *a, **k):
        return self

    def first(self):
        return self._result


class _FakeDB:
    def __init__(self, service=None):
        self._service = service

    def query(self, *a, **k):
        return _FakeQuery(self._service)


_PRINCIPAL = SimpleNamespace(user_id="u1")


def _content(**kw):
    base = dict(testing_service_id=None, updated_by=None, updated_at=None, path="unit/x")
    base.update(kw)
    return SimpleNamespace(**base)


def _version(slug=None, testing_service_id=None):
    return SimpleNamespace(
        id="ev1",
        testing_service_id=testing_service_id,
        get_execution_backend_slug=lambda: slug,
    )


class TestLinkTestingServiceBestEffort:
    def test_null_fk_no_slug_does_not_raise(self):
        content = _content()
        _link_testing_service(content, _version(slug=None), _PRINCIPAL, _FakeDB())
        assert content.testing_service_id is None  # assignment proceeds, unlinked

    def test_null_fk_slug_but_no_service_does_not_raise(self):
        content = _content()
        _link_testing_service(content, _version(slug="python"), _PRINCIPAL, _FakeDB(service=None))
        assert content.testing_service_id is None

    def test_null_fk_resolves_and_links_when_service_exists(self):
        svc = SimpleNamespace(id="svc-1")
        content = _content()
        version = _version(slug="python")
        _link_testing_service(content, version, _PRINCIPAL, _FakeDB(service=svc))
        assert content.testing_service_id == "svc-1"
        assert version.testing_service_id == "svc-1"  # self-healed back onto the version

    def test_existing_fk_is_propagated_without_lookup(self):
        content = _content()
        # db has no service; must still propagate the already-set FK.
        _link_testing_service(content, _version(testing_service_id="svc-9"), _PRINCIPAL, _FakeDB())
        assert content.testing_service_id == "svc-9"

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

    def all(self):
        # The language route scans candidates rather than filtering by slug.
        return [self._result] if self._result is not None else []


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


def _version(slug=None, testing_service_id=None, language=None, version=None):
    """Stub of ExampleVersion.

    Carries the real ``execution_backend`` JSONB block, which is what the shared
    resolver reads — the old stub only exposed the slug accessor and so drifted
    out of shape once slug stopped being the only way to bind.
    """
    execution_backend = None
    if slug or language:
        execution_backend = {}
        if slug:
            execution_backend["slug"] = slug
        if language:
            execution_backend["language"] = language
        if version:
            execution_backend["version"] = version
    return SimpleNamespace(
        id="ev1",
        testing_service_id=testing_service_id,
        execution_backend=execution_backend,
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
        svc = SimpleNamespace(id="svc-1", slug="itpcp.exec.py", config={"language": "python"})
        content = _content()
        version = _version(slug="python")
        _link_testing_service(content, version, _PRINCIPAL, _FakeDB(service=svc))
        assert content.testing_service_id == "svc-1"
        assert version.testing_service_id == "svc-1"  # self-healed back onto the version

    def test_null_fk_resolves_by_language_when_no_slug_is_pinned(self):
        """The portable binding: the example says what it is, not who runs it."""
        svc = SimpleNamespace(id="svc-oct", slug="acme.octave", config={"language": "octave"})
        content = _content()
        version = _version(language="octave")
        _link_testing_service(content, version, _PRINCIPAL, _FakeDB(service=svc))
        assert content.testing_service_id == "svc-oct"
        assert version.testing_service_id == "svc-oct"

    def test_existing_fk_is_propagated_without_lookup(self):
        content = _content()
        # db has no service; must still propagate the already-set FK.
        _link_testing_service(content, _version(testing_service_id="svc-9"), _PRINCIPAL, _FakeDB())
        assert content.testing_service_id == "svc-9"

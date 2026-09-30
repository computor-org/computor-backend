"""``ForgejoProviderClient.repo_exists`` / ``delete_repo`` — no live Forgejo.

``delete_repo`` is only ever called for a course's own template/reference
repos; the ``repo_exists`` probe is what keeps student provisioning from
adopting a repo left behind by a deleted course.
"""
import pytest

from computor_backend.git_provider import forgejo as forgejo_mod
from computor_backend.git_provider.forgejo import ForgejoProviderClient


class _Resp:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = ""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeHttpClient:
    def __init__(self, status):
        self._status = status
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, **kw):
        self.calls.append(("GET", url))
        return _Resp(self._status)

    def delete(self, url, **kw):
        self.calls.append(("DELETE", url))
        return _Resp(self._status)


@pytest.fixture
def wire(monkeypatch):
    def _wire(status):
        fake = _FakeHttpClient(status)
        monkeypatch.setattr(forgejo_mod.httpx, "Client", lambda **kw: fake)
        return fake

    return _wire


def _client():
    return ForgejoProviderClient("https://forge.example", "tok")


def test_repo_exists_true_on_200(wire):
    fake = wire(200)
    assert _client().repo_exists("org", "mmusterm") is True
    assert fake.calls == [("GET", "/api/v1/repos/org/mmusterm")]


def test_repo_exists_false_on_404(wire):
    wire(404)
    assert _client().repo_exists("org", "mmusterm") is False


def test_repo_exists_raises_on_server_error(wire):
    """A dead server must not look like "free": provisioning fails loudly."""
    wire(500)
    with pytest.raises(RuntimeError):
        _client().repo_exists("org", "mmusterm")


def test_delete_repo_204_and_404_are_success(wire):
    fake = wire(204)
    assert _client().delete_repo("org", "template") is True
    assert fake.calls == [("DELETE", "/api/v1/repos/org/template")]
    wire(404)
    assert _client().delete_repo("org", "reference") is True


def test_delete_repo_reports_other_failures(wire):
    wire(500)
    assert _client().delete_repo("org", "template") is False

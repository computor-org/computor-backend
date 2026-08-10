"""Resolving ``executionBackend`` to the Service that runs it.

An example used to be required to name a *service instance* (`slug`), which
hardcoded one deployment's naming into the content: rename the service, or hand
the example to another institution, and it stops resolving. It can now declare
what it actually needs — `language: octave` — with `slug` demoted to an optional
pin. All three call sites (upload, assignment, test run) share this one rule.
"""
from types import SimpleNamespace

import pytest

from computor_backend.business_logic import testing_service as ts


class _FakeQuery:
    """Just enough of a SQLAlchemy query for the resolver's two shapes."""

    def __init__(self, rows):
        self._rows = rows

    def filter(self, *criteria):
        rows = self._rows
        for crit in criteria:
            # Only `Service.slug == <value>` is used on this path.
            wanted = crit.right.value
            rows = [r for r in rows if r.slug == wanted]
        return _FakeQuery(rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


def _service(slug, language=None, language_version=None):
    config = {}
    if language:
        config["language"] = language
    if language_version:
        config["language_version"] = language_version
    return SimpleNamespace(slug=slug, config=config, id=f"id-{slug}")


@pytest.fixture
def services(monkeypatch):
    """Install a fleet; returns the mutable list so tests can shape it."""
    fleet = []
    monkeypatch.setattr(ts, "_enabled_services", lambda db: _FakeQuery(fleet))
    return fleet


def _resolve(eb):
    return ts.resolve_service_for_execution_backend(db=None, execution_backend=eb)


# --- the existing 166 examples must keep working -----------------------------

def test_pinned_slug_still_resolves(services):
    services.append(_service("itpcp.exec.py", language="python"))
    assert _resolve({"slug": "itpcp.exec.py", "version": "3.13"}).slug == "itpcp.exec.py"


def test_pinned_slug_that_does_not_exist_returns_none(services):
    services.append(_service("itpcp.exec.py", language="python"))
    assert _resolve({"slug": "nope"}) is None


def test_a_pin_is_never_silently_substituted(services):
    """A slug names ONE runner. Missing pin must not fall back to language."""
    services.append(_service("other.python.runner", language="python"))
    assert _resolve({"slug": "itpcp.exec.py", "language": "python"}) is None


# --- the new, portable form ---------------------------------------------------

def test_language_selects_a_runner(services):
    services.append(_service("acme.octave", language="octave"))
    services.append(_service("acme.python", language="python"))
    assert _resolve({"language": "octave"}).slug == "acme.octave"


def test_language_is_case_and_space_tolerant(services):
    services.append(_service("acme.r", language="R"))
    assert _resolve({"language": " r "}).slug == "acme.r"


def test_unknown_language_resolves_to_nothing(services):
    services.append(_service("acme.python", language="python"))
    assert _resolve({"language": "cobol"}) is None


def test_empty_block_resolves_to_nothing(services):
    assert _resolve(None) is None
    assert _resolve({}) is None
    assert _resolve({"language": "  "}) is None


# --- version routing ----------------------------------------------------------

def test_exact_version_wins(services):
    services.append(_service("py311", language="python", language_version="3.11"))
    services.append(_service("py313", language="python", language_version="3.13"))
    assert _resolve({"language": "python", "version": "3.13"}).slug == "py313"
    assert _resolve({"language": "python", "version": "3.11"}).slug == "py311"


def test_unmatched_version_falls_back_to_the_generic_runner(services):
    services.append(_service("py311", language="python", language_version="3.11"))
    services.append(_service("pygeneric", language="python"))
    assert _resolve({"language": "python", "version": "3.12"}).slug == "pygeneric"


def test_unmatched_version_with_no_generic_runner_resolves_to_nothing(services):
    """Better no runner than an arbitrarily-versioned one."""
    services.append(_service("py311", language="python", language_version="3.11"))
    assert _resolve({"language": "python", "version": "3.13"}) is None


def test_no_version_requested_takes_any_runner_for_the_language(services):
    services.append(_service("py311", language="python", language_version="3.11"))
    assert _resolve({"language": "python"}).slug == "py311"


def test_version_is_normalised(services):
    services.append(_service("mat", language="matlab", language_version="R2025b"))
    assert _resolve({"language": "matlab", "version": " r2025b "}).slug == "mat"


def test_numeric_version_is_accepted(services):
    """meta.yaml may carry an unquoted number (coerce_numbers_to_str)."""
    services.append(_service("c13", language="c", language_version="13"))
    assert _resolve({"language": "c", "version": 13}).slug == "c13"

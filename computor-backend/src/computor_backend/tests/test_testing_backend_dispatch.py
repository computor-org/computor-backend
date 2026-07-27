"""Unit tests for testing-runner dispatch.

Regression guard for the coupling this replaced: ``TestingBackendFactory``
used to look the *service slug* up in a hardcoded table of eight
``itpcp.exec.*`` names (and ``ComputorTestingBackend`` had a second copy of
the same table). A testing system registered under any other slug bound to
examples correctly and then died at execution with "Unknown testing backend",
so adding one was a code change and a redeploy.

The slug is the ``meta.yaml`` ``properties.executionBackend.slug`` contract —
an identifier. ``Service.config.language`` selects the runner. Nothing may
dispatch on a slug literal again.
"""
import pytest

from computor_backend.testing.backends import (
    ComputorTestingBackend,
    MatlabTestingBackend,
    TestingBackendFactory,
)


@pytest.mark.parametrize(
    "slug",
    [
        "acme.exec.py",     # a real-world third-party name
        "acme.runner",        # no dots-suffix convention at all
        "itpcp.exec.py",      # the historical name still works
        "x",                  # degenerate
    ],
)
def test_any_slug_works_given_a_language(slug):
    backend = TestingBackendFactory.create_backend(slug, language="python")
    assert isinstance(backend, ComputorTestingBackend)
    assert backend.service_slug == slug
    assert backend.language == "python"


def test_matlab_routes_to_the_pyro_backend():
    backend = TestingBackendFactory.create_backend("anything.at.all", language="matlab")
    assert isinstance(backend, MatlabTestingBackend)


def test_language_is_case_and_space_insensitive():
    assert isinstance(
        TestingBackendFactory.create_backend("s", language="  Python "),
        ComputorTestingBackend,
    )


def test_slug_alone_no_longer_resolves():
    """The whole point: a legacy slug must NOT be enough on its own."""
    with pytest.raises(ValueError) as exc:
        TestingBackendFactory.create_backend("itpcp.exec.py")
    assert "config.language" in str(exc.value)


def test_missing_language_names_the_service_and_the_fix():
    with pytest.raises(ValueError) as exc:
        TestingBackendFactory.create_backend("demo.svc")
    message = str(exc.value)
    assert "demo.svc" in message
    assert "python" in message  # lists the valid values


def test_unknown_language_is_rejected():
    with pytest.raises(ValueError) as exc:
        TestingBackendFactory.create_backend("demo.svc", language="klingon")
    assert "klingon" in str(exc.value)


def test_no_slug_keyed_dispatch_table_remains():
    """Guards against reintroducing either hardcoded table."""
    assert not hasattr(TestingBackendFactory, "_backends")
    assert not hasattr(ComputorTestingBackend, "LANGUAGE_MAP")
    for key in TestingBackendFactory._language_backends:
        assert "." not in key and ":" not in key, (
            f"'{key}' looks like a slug, not a language"
        )


def test_doc_is_aliased_to_the_document_subcommand():
    backend = TestingBackendFactory.create_backend("s", language="doc")
    assert backend._SUBCOMMAND_ALIASES["doc"] == "document"

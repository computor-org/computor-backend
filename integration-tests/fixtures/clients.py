"""Session-scoped HTTP clients, one per persona.

Each persona logs in exactly once (in `fixtures.personas`) via the SSO dance;
these fixtures just surface the persona's pre-authenticated `httpx.Client`.
`admin_client` and `anonymous_client` live in `fixtures.api`.

The persona set and how they're seeded is documented in `fixtures.personas`.
"""

from __future__ import annotations

import httpx
import pytest

from fixtures.personas import Persona


def _persona_client(personas: dict[str, Persona], name: str) -> httpx.Client:
    return personas[name].client


@pytest.fixture(scope="session")
def uma_client(personas: dict[str, Persona]) -> httpx.Client:
    """_user_manager."""
    return _persona_client(personas, "uma")


@pytest.fixture(scope="session")
def orga_client(personas: dict[str, Persona]) -> httpx.Client:
    """_organization_manager."""
    return _persona_client(personas, "orga")


@pytest.fixture(scope="session")
def exma_client(personas: dict[str, Persona]) -> httpx.Client:
    """_example_manager."""
    return _persona_client(personas, "exma")


@pytest.fixture(scope="session")
def lena_client(personas: dict[str, Persona]) -> httpx.Client:
    """Course lecturer (course role assigned during course setup)."""
    return _persona_client(personas, "lena")


@pytest.fixture(scope="session")
def tobi_client(personas: dict[str, Persona]) -> httpx.Client:
    """Course tutor (course role assigned during course setup)."""
    return _persona_client(personas, "tobi")


@pytest.fixture(scope="session")
def student_correct_client(personas: dict[str, Persona]) -> httpx.Client:
    return _persona_client(personas, "s_correct")


@pytest.fixture(scope="session")
def student_empty_client(personas: dict[str, Persona]) -> httpx.Client:
    return _persona_client(personas, "s_empty")


@pytest.fixture(scope="session")
def student_mixed_client(personas: dict[str, Persona]) -> httpx.Client:
    return _persona_client(personas, "s_mixed")

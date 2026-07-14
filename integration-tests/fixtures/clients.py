"""Session-scoped HTTP clients, one per persona.

System-role personas (uma/orga/exma) log in during `fixtures.personas` — their
roles are assigned at invite time, before login, so their tokens carry them.

Course-role actors (lena/tobi/students) are a special case: course-role claims
are baked into the session token at LOGIN, and personas log everyone in before
any course membership exists. So these clients RE-authenticate after the
relevant membership fixture (`seated_staff` for lena/tobi, `enrolled_students`
for the students), giving a token that actually carries the course role.

`admin_client` and `anonymous_client` live in `fixtures.api`.
"""

from __future__ import annotations

from typing import Iterator

import httpx
import pytest

from fixtures.api import DEFAULT_TIMEOUT
from fixtures.keycloak_auth import authenticate
from fixtures.personas import Persona


def _fresh_client(persona: Persona, api_base_url: str) -> httpx.Client:
    """A client whose token is minted NOW (picks up current course claims)."""
    creds = authenticate(persona.email, persona.spec.password, api_base=api_base_url)
    return httpx.Client(
        base_url=api_base_url,
        headers={"Authorization": f"Bearer {creds.token}"},
        timeout=DEFAULT_TIMEOUT,
    )


# ---- system-role personas (roles baked at invite time — no re-auth needed) ----

@pytest.fixture(scope="session")
def uma_client(personas: dict[str, Persona]) -> httpx.Client:
    """_user_manager."""
    return personas["uma"].client


@pytest.fixture(scope="session")
def orga_client(personas: dict[str, Persona]) -> httpx.Client:
    """_organization_manager."""
    return personas["orga"].client


@pytest.fixture(scope="session")
def exma_client(personas: dict[str, Persona]) -> httpx.Client:
    """_example_manager."""
    return personas["exma"].client


# ---- course-role actors (re-auth AFTER their membership is assigned) ----------

@pytest.fixture(scope="session")
def lena_client(
    personas: dict[str, Persona], seated_staff: dict, api_base_url: str
) -> Iterator[httpx.Client]:
    """Course lecturer — token minted after seating so it carries _lecturer."""
    client = _fresh_client(personas["lena"], api_base_url)
    yield client
    client.close()


@pytest.fixture(scope="session")
def tobi_client(
    personas: dict[str, Persona], seated_staff: dict, api_base_url: str
) -> Iterator[httpx.Client]:
    """Course tutor — token minted after seating so it carries _tutor."""
    client = _fresh_client(personas["tobi"], api_base_url)
    yield client
    client.close()


def _student_client(personas, enrolled_students, api_base_url, key) -> Iterator[httpx.Client]:
    client = _fresh_client(personas[key], api_base_url)
    yield client
    client.close()


@pytest.fixture(scope="session")
def student_correct_client(
    personas: dict[str, Persona], enrolled_students: dict, api_base_url: str
) -> Iterator[httpx.Client]:
    yield from _student_client(personas, enrolled_students, api_base_url, "s_correct")


@pytest.fixture(scope="session")
def student_empty_client(
    personas: dict[str, Persona], enrolled_students: dict, api_base_url: str
) -> Iterator[httpx.Client]:
    yield from _student_client(personas, enrolled_students, api_base_url, "s_empty")


@pytest.fixture(scope="session")
def student_mixed_client(
    personas: dict[str, Persona], enrolled_students: dict, api_base_url: str
) -> Iterator[httpx.Client]:
    yield from _student_client(personas, enrolled_students, api_base_url, "s_mixed")

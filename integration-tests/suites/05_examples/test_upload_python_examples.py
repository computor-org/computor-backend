"""Examples library — `exma` uploads the Python examples into MinIO.

Golden-path phase 2 (03-personas §Phase 2): the _example_manager uploads the six
itpcp.pgph.py examples; lecturers later assign them to course content.
"""

from __future__ import annotations

import httpx
import pytest

from fixtures.examples import ExampleFixture, upload_example

pytestmark = pytest.mark.examples


def test_all_python_examples_upload(
    uploaded_examples: dict[str, dict], python_examples: tuple[ExampleFixture, ...]
) -> None:
    assert set(uploaded_examples) == {ex.directory for ex in python_examples}
    assert len(uploaded_examples) == 6


def test_examples_are_listed(exma_client: httpx.Client, uploaded_examples: dict[str, dict]) -> None:
    r = exma_client.get("/examples")
    assert r.status_code == 200, r.text
    listed = {e["directory"] for e in r.json()}
    assert set(uploaded_examples).issubset(listed)


def test_example_has_expected_version(
    exma_client: httpx.Client,
    uploaded_examples: dict[str, dict],
    python_examples: tuple[ExampleFixture, ...],
) -> None:
    ex = next(e for e in python_examples if e.directory == "itpcp.pgph.py.datentypen")
    example = uploaded_examples[ex.directory]
    r = exma_client.get(f"/examples/{example['id']}/versions")
    assert r.status_code == 200, r.text
    tags = {v.get("version_tag") for v in r.json()}
    assert ex.version_tag in tags, f"{ex.version_tag} not in {tags}"


def test_lecturer_cannot_upload_examples(
    lena_client: httpx.Client,
    example_repository_id: str,
    python_examples: tuple[ExampleFixture, ...],
) -> None:
    # example:upload is _example_manager-only.
    r = upload_example(lena_client, example_repository_id, python_examples[0])
    assert r.status_code == 403, r.text


def test_org_manager_cannot_upload_examples(
    orga_client: httpx.Client,
    example_repository_id: str,
    python_examples: tuple[ExampleFixture, ...],
) -> None:
    # org-manager has read-only example claims.
    r = upload_example(orga_client, example_repository_id, python_examples[0])
    assert r.status_code == 403, r.text

"""Discover the Python example fixtures and upload them via the Examples API.

The examples live in the sibling `computor-testing/examples/itpcp.pgph.py/*`
tree (fixture data — NOT a test target). Each directory is a self-contained
example (meta.yaml + test.yaml + student stub + master solution +
content/localTests). We upload them into the seeded MinIO example repository as
`exma` (the _example_manager), then later phases assign + release them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
import pytest
import yaml

# integration-tests/ -> repo root -> computor-testing/examples/itpcp.pgph.py
EXAMPLES_ROOT = (
    Path(__file__).resolve().parents[2]
    / "computor-testing"
    / "examples"
    / "itpcp.pgph.py"
)


@dataclass(frozen=True)
class ExampleFixture:
    directory: str  # == meta identifier, e.g. "itpcp.pgph.py.datentypen"
    path: Path

    @property
    def meta(self) -> dict:
        return yaml.safe_load((self.path / "meta.yaml").read_text(encoding="utf-8"))

    @property
    def version_tag(self) -> str:
        # meta 'version' normalized to semver by the backend (1.0 -> 1.0.0).
        raw = str(self.meta.get("version", "1.0.0"))
        parts = raw.split(".")
        while len(parts) < 3:
            parts.append("0")
        return ".".join(parts[:3])

    @property
    def student_files(self) -> list[str]:
        return list(self.meta.get("properties", {}).get("studentSubmissionFiles", []))

    def files(self) -> dict[str, str]:
        """All *text* files under the example dir, keyed by POSIX relative path.

        Binary assets (e.g. content media images) are skipped — they aren't
        needed for assignment/testing and JSON upload carries text only.
        """
        out: dict[str, str] = {}
        for f in sorted(self.path.rglob("*")):
            if not f.is_file():
                continue
            try:
                out[f.relative_to(self.path).as_posix()] = f.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue  # binary asset — not needed for testing
        return out

    def correct_solution_files(self) -> dict[str, str]:
        """The full known-good submission from localTests/correctSolution.

        Returns ALL files in that directory (submission + any additionalFiles /
        data the test needs) — not just studentSubmissionFiles, because several
        examples need supporting files to pass.
        """
        src = self.path / "localTests" / "correctSolution"
        out: dict[str, str] = {}
        if src.is_dir():
            for f in sorted(src.iterdir()):
                if f.is_file():
                    try:
                        out[f.name] = f.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        continue
        return out

    def broken_files(self) -> dict[str, str]:
        """A guaranteed-failing submission (the '_empty' case).

        NOTE: the example student stubs ship pre-solved (stub == solution), so an
        unsolved submission must be synthesised — an empty/no-op file per
        studentSubmissionFile reliably fails the tests.
        """
        return {name: "# no solution\n" for name in self.student_files}


def discover_examples() -> list[ExampleFixture]:
    if not EXAMPLES_ROOT.is_dir():
        return []
    return [
        ExampleFixture(directory=p.name, path=p)
        for p in sorted(EXAMPLES_ROOT.iterdir())
        if p.is_dir() and (p / "meta.yaml").is_file()
    ]


PYTHON_EXAMPLES: tuple[ExampleFixture, ...] = tuple(discover_examples())


@pytest.fixture(scope="session")
def python_examples() -> tuple[ExampleFixture, ...]:
    assert PYTHON_EXAMPLES, f"no python examples found under {EXAMPLES_ROOT}"
    return PYTHON_EXAMPLES


@pytest.fixture(scope="session")
def example_repository_id(exma_client: httpx.Client) -> str:
    """The seeded MinIO-backed example repository (ensure_bootstrap_services)."""
    r = exma_client.get("/example-repositories")
    r.raise_for_status()
    for repo in r.json():
        if repo.get("source_type") == "minio":
            return repo["id"]
    raise AssertionError("no MinIO example repository was seeded")


def upload_example(
    exma_client: httpx.Client, repository_id: str, ex: ExampleFixture
) -> httpx.Response:
    return exma_client.post(
        "/examples/upload",
        json={"repository_id": repository_id, "directory": ex.directory, "files": ex.files()},
    )


def _find_example(exma_client: httpx.Client, directory: str) -> Optional[dict]:
    r = exma_client.get("/examples")
    r.raise_for_status()
    for ex in r.json():
        if ex.get("directory") == directory:
            return ex
    return None


@pytest.fixture(scope="session")
def uploaded_examples(
    exma_client: httpx.Client,
    example_repository_id: str,
    python_examples: tuple[ExampleFixture, ...],
) -> dict[str, dict]:
    """Upload every python example once; return {directory: example dict}.

    Idempotent: an example already present (VERSION_001 on re-run) is fetched
    from GET /examples instead of re-uploaded.
    """
    out: dict[str, dict] = {}
    for ex in python_examples:
        r = upload_example(exma_client, example_repository_id, ex)
        if r.status_code == 200:
            existing = _find_example(exma_client, ex.directory)
            assert existing is not None, f"uploaded {ex.directory} but not listed"
            out[ex.directory] = existing
        elif r.status_code == 400 and "VERSION_001" in r.text:
            existing = _find_example(exma_client, ex.directory)
            assert existing is not None, f"{ex.directory} reported existing but not listed"
            out[ex.directory] = existing
        else:
            raise AssertionError(f"upload {ex.directory} failed: {r.status_code} {r.text}")
    return out

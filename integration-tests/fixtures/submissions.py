"""Golden-path phase 4: students provision repos, submit, and run tests.

Each student submits a solution per assignment and triggers a test run
(executed by the Temporal testing worker against the assigned example's
reference). Cases (03-personas §Phase 4):
    s_correct : correctSolution for every assignment            -> pass
    s_empty   : the untouched student stub for every assignment -> fail
    s_mixed   : correct for half, stub for the other half       -> mixed

Idempotent against the accumulating stack: a submission group that already has a
terminal result is reused (re-testing the same content-addressed submission
would hit the backend's duplicate-result 500).
"""

from __future__ import annotations

import io
import json
import time
import zipfile

import httpx
import pytest

from fixtures.examples import ExampleFixture

TERMINAL = {"finished", "failed", "cancelled", "crashed", "completed"}

# s_mixed: correct for these, stub for the rest.
MIXED_CORRECT_DIRS = {
    "itpcp.pgph.py.datentypen",
    "itpcp.pgph.py.dict_und_json",
    "itpcp.pgph.py.lambda",
}


def solution_files(student: str, ex: ExampleFixture) -> dict[str, str]:
    """The files a given student submits for a given example."""
    if student == "s_correct":
        return ex.correct_solution_files()
    if student == "s_empty":
        return ex.broken_files()
    if student == "s_mixed":
        return ex.correct_solution_files() if ex.directory in MIXED_CORRECT_DIRS else ex.broken_files()
    raise ValueError(student)


def _zip_bytes(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _submission_group_id(client: httpx.Client, course_id: str, path: str) -> str:
    contents = client.get("/students/course-contents", params={"course_id": course_id}).json()
    cc = next(c for c in contents if isinstance(c, dict) and c.get("path") == path)
    return cc["submission_group"]["id"]


def _result_for_version(
    client: httpx.Client, submission_group_id: str, version_identifier: str | None
) -> dict | None:
    """A terminal result for this submission group + content version, if any.

    Tying reuse to the content-addressed `version_identifier` means a re-run with
    the SAME solution reuses its result (dodging the duplicate-test 500), while a
    changed submission gets a fresh test.
    """
    r = client.get("/results", params={"submission_group_id": submission_group_id})
    if r.status_code != 200:
        return None
    for res in r.json():
        if not isinstance(res, dict) or str(res.get("status")).lower() not in TERMINAL:
            continue
        if version_identifier is None or res.get("version_identifier") == version_identifier:
            return res
    return None


def _poll_result(client: httpx.Client, result_id: str, tries: int = 40) -> dict:
    for _ in range(tries):
        st = str(client.get(f"/tests/status/{result_id}").json().get("status")).lower()
        if st in TERMINAL:
            return client.get(f"/results/{result_id}").json()
        time.sleep(3)
    raise AssertionError(f"result {result_id} never reached a terminal state")


def submit_and_test(
    client: httpx.Client, course_id: str, content_path: str, files: dict[str, str]
) -> dict:
    """Submit `files` for the assignment at `content_path` and return its result.

    Reuses an existing terminal result (idempotent); otherwise submits, triggers a
    test (respecting the 1/s rate limit), and polls to a terminal state.
    """
    sgid = _submission_group_id(client, course_id, content_path)

    r = client.post(
        "/submissions/artifacts",
        files={"file": ("submission.zip", _zip_bytes(files), "application/zip")},
        data={"submission_create": json.dumps({"submission_group_id": sgid, "submit": True})},
    )
    assert r.status_code == 201, f"submit {content_path}: {r.status_code} {r.text}"
    body = r.json()
    artifact_id = body["artifacts"][0]
    version_identifier = body.get("version_identifier")

    # Reuse a result for THIS exact content if it was already tested.
    existing = _result_for_version(client, sgid, version_identifier)
    if existing is not None:
        return existing

    time.sleep(1.2)  # /tests is rate-limited 1/s per user
    rt = client.post("/tests", json={"artifact_id": artifact_id})
    if rt.status_code >= 300:
        existing = _result_for_version(client, sgid, version_identifier)
        if existing is not None:
            return existing
        raise AssertionError(f"test {content_path}: {rt.status_code} {rt.text}")
    result = rt.json()[0] if isinstance(rt.json(), list) else rt.json()
    return _poll_result(client, result["id"])


# ---- fixtures ------------------------------------------------------------

_STUDENT_CLIENT_FIXTURES = {
    "s_correct": "student_correct_client",
    "s_empty": "student_empty_client",
    "s_mixed": "student_mixed_client",
}


@pytest.fixture(scope="session")
def provisioned_repos(
    request,
    target_course: dict,
    released_template: dict,
    enrolled_students: dict,
) -> dict:
    """Each student provisions their managed Forgejo repo (self-migrated template)."""
    out: dict = {}
    for student, client_name in _STUDENT_CLIENT_FIXTURES.items():
        client = request.getfixturevalue(client_name)
        r = client.post(f"/user/courses/{target_course['id']}/provision-repository", json={})
        assert r.status_code == 200, f"provision {student}: {r.status_code} {r.text}"
        out[student] = r.json()
    return out


@pytest.fixture(scope="session")
def student_results(
    request,
    target_course: dict,
    python_examples: tuple,
    enrolled_students: dict,
    assigned_examples: dict,
) -> dict:
    """{student: {example_directory: result}} for all three students × 6 assignments."""
    from fixtures.authoring import example_label

    cid = target_course["id"]
    out: dict = {s: {} for s in _STUDENT_CLIENT_FIXTURES}
    for student, client_name in _STUDENT_CLIENT_FIXTURES.items():
        client = request.getfixturevalue(client_name)
        for ex in python_examples:
            path = f"unit.{example_label(ex.directory)}"
            out[student][ex.directory] = submit_and_test(
                client, cid, path, solution_files(student, ex)
            )
    return out

"""The reader's language reaches the test backend and the worker's own messages."""

import pytest

import computor_backend.testing as testing
from computor_backend.tasks.temporal_student_testing import execute_tests_activity


def _run(tmp_path, monkeypatch, test_config):
    reference = tmp_path / "reference"
    student = tmp_path / "work" / "student"
    reference.mkdir()
    student.mkdir(parents=True)
    (reference / "test.yaml").write_text("type: python\n")
    seen = {}

    async def fake_backend(**kwargs):
        seen.update(kwargs["test_job_config"])
        return {"error": "stopped by the test", "passed": 0, "failed": 1, "total": 1}

    monkeypatch.setattr(testing, "execute_tests_with_backend", fake_backend)
    execute_tests_activity(
        reference_path=str(reference),
        student_path=str(student),
        test_config=test_config,
        service_config={},
        service_type_config={},
        store_graphics_artifacts=False,
    )
    return seen


def test_job_language_is_passed_to_the_backend(tmp_path, monkeypatch):
    seen = _run(tmp_path, monkeypatch, {"testing_service_slug": "python", "language": "de"})
    assert seen["language"] == "de"


def test_missing_language_stays_unset(tmp_path, monkeypatch):
    seen = _run(tmp_path, monkeypatch, {"testing_service_slug": "python"})
    assert seen["language"] is None


class _ProfileQuery:
    def __init__(self, language):
        self.language = language

    def query(self, *_):
        return self

    def filter(self, *_):
        return self

    def scalar(self):
        return self.language


@pytest.mark.parametrize("profile, header, expected", [
    ("en", "de-AT,de;q=0.9", "en"),   # the profile wins
    (None, "de-AT,en;q=0.5", "de"),   # else the browser
    (None, "fr-FR", "en"),            # any other browser language reads English
])
def test_test_language_is_the_readers_language(profile, header, expected):
    from computor_backend.business_logic.testing_service import resolve_test_language

    assert resolve_test_language("u1", header, _ProfileQuery(profile)) == expected


def _activity_result(tmp_path, monkeypatch, language):
    reference = tmp_path / "reference"
    student = tmp_path / "work" / "student"
    reference.mkdir()
    student.mkdir(parents=True)
    (reference / "test.yaml").write_text("type: python\n")

    async def no_report(**kwargs):
        return None

    monkeypatch.setattr(testing, "execute_tests_with_backend", no_report)
    return execute_tests_activity(
        reference_path=str(reference),
        student_path=str(student),
        test_config={"testing_service_slug": "python", "language": language},
        service_config={},
        service_type_config={},
        store_graphics_artifacts=False,
    )


def test_worker_message_follows_the_job_language(tmp_path, monkeypatch):
    assert _activity_result(tmp_path, monkeypatch, "de")["error"] == (
        "Es wurde keine Datei mit Testergebnissen gefunden"
    )


def test_worker_message_is_english_otherwise(tmp_path, monkeypatch):
    assert _activity_result(tmp_path, monkeypatch, "en")["error"] == "No test results file found"

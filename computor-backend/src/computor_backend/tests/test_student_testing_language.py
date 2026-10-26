"""The course language reaches the test backend (runner messages in German)."""

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


def test_course_language_is_passed_to_the_backend(tmp_path, monkeypatch):
    seen = _run(tmp_path, monkeypatch, {"testing_service_slug": "python", "language": "de"})
    assert seen["language"] == "de"


def test_missing_language_stays_unset(tmp_path, monkeypatch):
    seen = _run(tmp_path, monkeypatch, {"testing_service_slug": "python"})
    assert seen["language"] is None

"""The task queue is derived from the service's language unless pinned.

"One worker image per language" is the intended topology, but the queue used to
be a third free-form string that had to agree with the service's language and
with the container's ``--queues`` by hand, with nothing checking any of it. It
is now a function of the language, with an explicit ``temporal.task_queue``
still winning so existing deployments and bespoke topologies are untouched.
"""
from types import SimpleNamespace

import pytest

from computor_backend.business_logic.testing_orchestration import (
    default_task_queue_for_language,
    resolve_task_queue,
    service_language,
    service_language_version,
)
from computor_backend.exceptions import BadRequestException

TESTING_TYPE = SimpleNamespace(path="testing.temporal")


def _service(config, name="Test Service"):
    return SimpleNamespace(config=config, name=name)


@pytest.mark.parametrize(
    "language,expected",
    [
        ("python", "testing-python"),
        ("octave", "testing-octave"),
        ("r", "testing-r"),
        ("julia", "testing-julia"),
        ("matlab", "testing-matlab"),
    ],
)
def test_queue_derives_from_language(language, expected):
    assert default_task_queue_for_language(language) == expected
    assert resolve_task_queue(_service({"language": language}), TESTING_TYPE) == expected


def test_explicit_queue_always_wins():
    """The shipped services pin 'testing' / 'testing-matlab' — must not move."""
    shipped_python = {"language": "python", "temporal": {"task_queue": "testing"}}
    shipped_matlab = {"language": "matlab", "temporal": {"task_queue": "testing-matlab"}}
    assert resolve_task_queue(_service(shipped_python), TESTING_TYPE) == "testing"
    assert resolve_task_queue(_service(shipped_matlab), TESTING_TYPE) == "testing-matlab"


def test_explicit_queue_wins_even_when_it_contradicts_the_language():
    """A bespoke topology stays possible — derivation is only a fallback."""
    config = {"language": "python", "temporal": {"task_queue": "testing-python-gpu"}}
    assert resolve_task_queue(_service(config), TESTING_TYPE) == "testing-python-gpu"


def test_language_is_normalised():
    assert service_language(_service({"language": "  OCTAVE "})) == "octave"
    assert resolve_task_queue(_service({"language": " R "}), TESTING_TYPE) == "testing-r"


def test_missing_language_and_queue_is_refused():
    """Nothing to route on — must fail loudly rather than guess a queue."""
    with pytest.raises(BadRequestException) as exc:
        resolve_task_queue(_service({}), TESTING_TYPE)
    assert "language" in str(exc.value.detail)


def test_non_testing_service_type_still_rejected():
    with pytest.raises(BadRequestException):
        resolve_task_queue(
            _service({"language": "python"}), SimpleNamespace(path="agent")
        )


def test_tutor_path_skips_the_service_type_check():
    """Tutor tests may run on a non-testing.* service type."""
    queue = resolve_task_queue(
        _service({"language": "octave"}),
        SimpleNamespace(path="agent"),
        require_testing_path=False,
    )
    assert queue == "testing-octave"


def test_service_language_returns_none_when_absent():
    assert service_language(_service({})) is None
    assert service_language(_service(None)) is None
    assert service_language(_service({"language": "   "})) is None


# --- one queue per RUNNER, and a runner is (language, version) ---------------


def test_two_versions_of_one_language_get_separate_queues():
    """The whole point of version routing.

    Keying the queue on language alone put python 3.11 and python 3.13 on the
    same queue, where whichever worker polled first executed the test and the
    resolved version was silently ignored.
    """
    py311 = _service({"language": "python", "language_version": "3.11"})
    py313 = _service({"language": "python", "language_version": "3.13"})
    q311 = resolve_task_queue(py311, TESTING_TYPE)
    q313 = resolve_task_queue(py313, TESTING_TYPE)
    assert q311 == "testing-python-3.11"
    assert q313 == "testing-python-3.13"
    assert q311 != q313, "versions must not share a queue"


def test_versionless_service_keeps_the_plain_queue_name():
    """Single-version installations are unaffected."""
    assert resolve_task_queue(_service({"language": "python"}), TESTING_TYPE) == "testing-python"


def test_version_is_normalised_into_the_queue_name():
    svc = _service({"language": "matlab", "language_version": "R2025b"})
    assert resolve_task_queue(svc, TESTING_TYPE) == "testing-matlab-r2025b"


def test_queue_name_stays_shell_and_temporal_safe():
    """Odd version strings must not produce spaces or exotic characters."""
    svc = _service({"language": "c", "language_version": "GCC 13 (beta)"})
    queue = resolve_task_queue(svc, TESTING_TYPE)
    assert queue == "testing-c-gcc-13-beta"
    assert " " not in queue and "(" not in queue


def test_numeric_language_version_is_accepted():
    svc = _service({"language": "c", "language_version": 13})
    assert service_language_version(svc) == "13"
    assert resolve_task_queue(svc, TESTING_TYPE) == "testing-c-13"


def test_explicit_queue_still_wins_over_a_versioned_derivation():
    svc = _service({
        "language": "python",
        "language_version": "3.13",
        "temporal": {"task_queue": "testing"},
    })
    assert resolve_task_queue(svc, TESTING_TYPE) == "testing"


def test_default_queue_helper_is_a_pure_function():
    """Operators derive the same name by hand for --queues=."""
    assert default_task_queue_for_language("python") == "testing-python"
    assert default_task_queue_for_language("python", "3.13") == "testing-python-3.13"
    assert default_task_queue_for_language("python", "") == "testing-python"
    assert default_task_queue_for_language("python", None) == "testing-python"

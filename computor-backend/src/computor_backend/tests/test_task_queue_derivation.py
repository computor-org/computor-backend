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

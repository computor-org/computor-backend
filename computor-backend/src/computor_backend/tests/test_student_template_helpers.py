"""Unit tests for the extracted student-template release helpers."""
from types import SimpleNamespace

from computor_backend.tasks.student_template.selection import resolve_deployment_directory
from computor_backend.tasks.student_template.status import (
    collect_failed_events,
    failed_event,
)


def _deployment(**kw):
    base = dict(
        deployment_path=None,
        example_identifier=None,
        example_version=None,
        id="dep-1",
        version_tag=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


class TestResolveDeploymentDirectory:
    def test_prefers_deployment_path(self):
        dep = _deployment(deployment_path="already", example_identifier="ident")
        assert resolve_deployment_directory(dep) == "already"

    def test_falls_back_to_example_identifier(self):
        dep = _deployment(example_identifier="ident")
        assert resolve_deployment_directory(dep) == "ident"

    def test_persist_writes_back(self):
        dep = _deployment(example_identifier="ident")
        assert resolve_deployment_directory(dep, persist=True) == "ident"
        assert dep.deployment_path == "ident"

    def test_no_persist_leaves_path(self):
        dep = _deployment(example_identifier="ident")
        resolve_deployment_directory(dep, persist=False)
        assert dep.deployment_path is None

    def test_falls_back_to_example_version_identifier(self):
        ev = SimpleNamespace(example=SimpleNamespace(identifier="ev-ident"))
        dep = _deployment(example_version=ev)
        assert resolve_deployment_directory(dep) == "ev-ident"

    def test_returns_none_when_unresolvable(self):
        assert resolve_deployment_directory(_deployment()) is None

    def test_detached_relationship_returns_none(self):
        class Boom:
            @property
            def example(self):
                raise AttributeError("detached")

        dep = _deployment(example_version=Boom())
        assert resolve_deployment_directory(dep) is None


class TestFailedEvents:
    def _content(self, dep_id, status="failed", message="boom"):
        deployment = SimpleNamespace(
            id=dep_id,
            deployment_status=status,
            deployment_message=message,
            version_tag="v1",
            example_identifier="ex",
        )
        return SimpleNamespace(id=f"c-{dep_id}", deployment=deployment)

    def test_failed_event_shape(self):
        evt = failed_event(self._content("d1"))
        assert evt["deployment_id"] == "d1"
        assert evt["new_status"] == "failed"
        assert evt["previous_status"] == "deploying"
        assert evt["deployment_message"] == "boom"

    def test_collect_skips_already_tracked(self):
        contents = [self._content("d1"), self._content("d2")]
        tracked = [{"deployment_id": "d1"}]
        events = collect_failed_events(contents, tracked)
        assert [e["deployment_id"] for e in events] == ["d2"]

    def test_collect_skips_non_failed(self):
        contents = [self._content("d1", status="deployed")]
        assert collect_failed_events(contents, []) == []

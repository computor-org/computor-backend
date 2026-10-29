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


class TestMainReadme:
    """The template README is shared by all learners: German first, then English."""

    @staticmethod
    def _content(path, title, title_i18n=None, identifier=None):
        deployment = None
        if identifier:
            deployment = SimpleNamespace(example_version=SimpleNamespace(
                example=SimpleNamespace(identifier=identifier), version_tag="v1"))
        return SimpleNamespace(path=path, title=title, title_i18n=title_i18n, deployment=deployment)

    def test_both_languages_with_translated_titles(self):
        from computor_backend.tasks.student_template.readme import render_main_readme

        course = SimpleNamespace(title="Datenanalyse", title_i18n={"en": "Data Analysis"})
        unit = self._content("week1", "Woche 1", {"en": "Week 1"})
        task = self._content("week1.loops", "Schleifen", {"en": "Loops"}, identifier="loops")
        text = render_main_readme(course, [task], {"week1": unit, "week1.loops": task})

        german, english = text.split("\n---\n")
        assert german.startswith("# Datenanalyse – Aufgabenvorlage")
        assert "| Woche 1 / Schleifen | [`loops/`](./loops) | Schleifen | v1 |" in german
        assert "Reiche jede Aufgabe" in german
        assert english.lstrip().startswith("# Data Analysis – Student Template")
        assert "| Week 1 / Loops | [`loops/`](./loops) | Loops | v1 |" in english

    def test_missing_translation_keeps_the_source_title(self):
        from computor_backend.tasks.student_template.readme import render_main_readme

        course = SimpleNamespace(title="Python", title_i18n=None)
        text = render_main_readme(course, [], {})
        assert "*Es sind noch keine Aufgaben veröffentlicht.*" in text
        assert "*No assignments deployed yet.*" in text
        assert text.index("# Python – Aufgabenvorlage") < text.index("# Python – Student Template")

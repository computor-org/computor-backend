"""Two contents on one example must not share a directory (issue #150).

The lecturer's ask is ordinary — the same exercise in week 2 and week 5 — and
it used to be answered in two bad ways at once: the assign endpoint refused it
outright (DEPLOY_005), and where a duplicate already existed the release run
wrote both contents into one directory, so the student opened the second
assignment onto the first one's files.

The fix is one directory name per deployment, allocated when the example is
assigned. These tests pin the allocation and the release-time backstop that
covers the courses assigned before it existed.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from computor_backend.business_logic.deployment_paths import (
    _discriminators,
    allocate_deployment_path,
)
from computor_backend.tasks.student_template.selection import resolve_directory_owners


class _TakenDb:
    """Answers the one query allocate_deployment_path makes."""

    def __init__(self, taken):
        self.taken = taken

    def query(self, *_entities):
        return self

    def join(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return [(name,) for name in self.taken]


def _content(path="week5.mathematical_constants", content_id="content-1"):
    return SimpleNamespace(id=content_id, course_id="course-1", path=path)


class TestDiscriminators:
    def test_prefers_the_unit_segment(self):
        """`mathematical_constants-week5` reads as the lecturer thinks of it."""
        assert _discriminators("week5.mathematical_constants")[0] == "week5"

    def test_falls_back_to_the_content_slug_at_root_level(self):
        assert _discriminators("standalone") == ["standalone"]

    def test_never_offers_the_same_suffix_twice(self):
        assert _discriminators("week5.week5") == ["week5"]

    def test_survives_a_missing_path(self):
        assert _discriminators(None) == []


class TestAllocateDeploymentPath:
    def test_the_ordinary_case_is_the_example_identifier_untouched(self):
        """One example, one content: nothing about existing courses changes."""
        db = _TakenDb([])
        assert allocate_deployment_path(db, _content(), "maths") == "maths"

    def test_a_second_content_on_the_same_example_gets_its_unit(self):
        db = _TakenDb(["maths"])
        assert allocate_deployment_path(db, _content("week5.maths"), "maths") == "maths-week5"

    def test_a_third_falls_through_to_the_content_slug(self):
        db = _TakenDb(["maths", "maths-week5"])
        assert (
            allocate_deployment_path(db, _content("week5.constants"), "maths")
            == "maths-constants"
        )

    def test_it_counts_when_it_runs_out_of_names(self):
        db = _TakenDb(["maths", "maths-week5", "maths-constants"])
        assert (
            allocate_deployment_path(db, _content("week5.constants"), "maths")
            == "maths-2"
        )

    def test_a_content_does_not_have_to_avoid_its_own_name(self):
        """Reassigning the same content must not walk its directory forward.

        The exclusion happens in the query; this pins that the caller passes
        the content id at all, by way of the filter it builds.
        """
        seen = {}

        class _Db(_TakenDb):
            def filter(self, *args, **_kwargs):
                seen["filters"] = seen.get("filters", 0) + len(args)
                return self

        allocate_deployment_path(_Db([]), _content(), "maths")
        # base filters + the exclusion filter
        assert seen["filters"] >= 4


class TestResolveDirectoryOwners:
    """Legacy courses can still hold two contents pointing at one directory."""

    def _row(self, content_id, path, directory, deployed_at=None):
        content = SimpleNamespace(id=content_id, path=path)
        deployment = SimpleNamespace(
            deployment_path=directory,
            example_identifier=None,
            example_version=None,
            deployed_at=deployed_at,
        )
        return content, deployment

    class _Db:
        def __init__(self, rows):
            self.rows = rows

        def query(self, *_entities):
            return self

        def join(self, *_args, **_kwargs):
            return self

        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def all(self):
            return self.rows

    def test_one_content_per_directory_is_its_own_owner(self):
        rows = [self._row("c1", "week2.maths", "maths")]
        assert resolve_directory_owners(self._Db(rows), "course-1") == {"maths": "c1"}

    def test_a_released_content_outranks_one_that_never_released(self):
        """A new assignment must never take a directory students are working in."""
        released = datetime.now(timezone.utc)
        rows = [
            self._row("c1", "week2.maths", "maths"),                    # never released
            self._row("c2", "week5.maths", "maths", deployed_at=released),
        ]
        assert resolve_directory_owners(self._Db(rows), "course-1")["maths"] == "c2"

    def test_the_earlier_release_wins_between_two_released_contents(self):
        first = datetime.now(timezone.utc) - timedelta(days=7)
        second = datetime.now(timezone.utc)
        rows = [
            self._row("c1", "week2.maths", "maths", deployed_at=second),
            self._row("c2", "week5.maths", "maths", deployed_at=first),
        ]
        assert resolve_directory_owners(self._Db(rows), "course-1")["maths"] == "c2"

    def test_ties_fall_back_to_path_order_so_runs_agree(self):
        rows = [
            self._row("c1", "week2.maths", "maths"),
            self._row("c2", "week5.maths", "maths"),
        ]
        # rows arrive ordered by path; the first claim stands.
        assert resolve_directory_owners(self._Db(rows), "course-1")["maths"] == "c1"

    def test_a_deployment_without_a_directory_claims_nothing(self):
        rows = [self._row("c1", "week2.maths", None)]
        assert resolve_directory_owners(self._Db(rows), "course-1") == {}


def test_the_release_run_refuses_to_write_into_another_contents_directory():
    """The backstop for courses assigned before paths were allocated."""
    import inspect

    from computor_backend.tasks import temporal_student_template_v2 as workflow

    source = inspect.getsource(workflow)
    assert "resolve_directory_owners(db, course_id)" in source
    assert "directory_owners.get(str(directory_name))" in source


def test_assigning_an_example_twice_in_one_course_is_allowed_again():
    """The old answer was DEPLOY_005; the new one is a distinct directory."""
    import inspect

    from computor_backend.business_logic import lecturer_deployment

    source = inspect.getsource(lecturer_deployment.assign_example_to_content)
    assert "allocate_deployment_path" in source
    assert "DEPLOY_005" not in source.replace(
        "# DEPLOY_005) only moved the problem into the lecturer's way. What must not", ""
    )


def test_a_version_bump_keeps_the_directory_it_already_has():
    """Renaming would orphan the old directory in every student's clone."""
    import inspect

    from computor_backend.business_logic import lecturer_deployment

    source = inspect.getsource(lecturer_deployment.assign_example_to_content)
    assert "if not (is_same_example and existing_deployment.deployment_path):" in source

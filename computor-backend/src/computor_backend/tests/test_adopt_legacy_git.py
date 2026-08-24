"""Unit tests for the legacy-GitLab adoption mapping.

Pure functions only — no database, no network. The mapping is where the
previous adoption scripts went wrong, in ways that only showed up much later
(a binding pointing at a group instead of a repository; a 500 on every read of
the binding; solutions silently no longer pushed), so it is worth pinning
precisely.
"""

import ast
import json
import pathlib

import pytest

from computor_backend.scripts.adopt_legacy_git import (
    ADOPTED_SCHEMA,
    MemberRepoPlan,
    as_dict,
    bridge_token,
    build_binding_properties,
    build_member_repo_plan,
    detect_repo_ref_collisions,
    legacy_base_url,
    legacy_group_ids,
    legacy_reference_ref,
    legacy_template_ref,
    strip_secrets,
)


def legacy_course_blob(**overrides):
    """A course blob shaped exactly as ``main``'s gitlab_builder writes one."""
    blob = {
        "url": "https://gitlab.example.org",
        "group_id": 5678,
        "full_path": "org/fam/course",
        "parent": 1234,
        "parent_id": 1234,
        "namespace_id": 1234,
        "namespace_path": "fam",
        "web_url": "https://gitlab.example.org/groups/org/fam/course",
        "visibility": "private",
        "last_synced_at": "2026-01-01T00:00:00+00:00",
        "students_group": {
            "group_id": 5679,
            "full_path": "org/fam/course/students",
            "web_url": "https://gitlab.example.org/groups/org/fam/course/students",
        },
        "tutors_group": {"group_id": 5680, "full_path": "org/fam/course/tutors"},
        "projects": {
            "student_template": {
                "path": "student-template",
                "full_path": "org/fam/course/student-template",
                "web_url": "https://gitlab.example.org/org/fam/course/student-template",
            },
            "assignments": {
                "path": "assignments",
                "full_path": "org/fam/course/assignments",
                "web_url": "https://gitlab.example.org/org/fam/course/assignments",
            },
        },
        "student_template_url": "https://gitlab.example.org/org/fam/course/student-template",
        "assignments_url": "https://gitlab.example.org/org/fam/course/assignments",
    }
    blob.update(overrides)
    return blob


class TestTemplateRef:
    def test_resolves_the_repository_not_the_course_group(self):
        """The regression that broke every adopted course.

        ``full_path`` is the course GROUP. The old probe order was
        ``template_path or full_path``, and since legacy blobs never carry
        ``template_path``, every binding was written pointing at the group.
        """
        repo, url = legacy_template_ref(legacy_course_blob(), "https://gitlab.example.org")
        assert repo == "org/fam/course/student-template"
        assert repo != "org/fam/course"
        assert url == "https://gitlab.example.org/org/fam/course/student-template.git"

    def test_falls_back_to_the_conventional_path(self):
        blob = legacy_course_blob()
        del blob["projects"]
        del blob["student_template_url"]
        repo, url = legacy_template_ref(blob, "https://gitlab.example.org")
        assert repo == "org/fam/course/student-template"
        assert url == "https://gitlab.example.org/org/fam/course/student-template.git"

    def test_recovers_the_path_from_the_stored_url(self):
        blob = {"student_template_url": "https://gitlab.example.org/a/b/student-template"}
        repo, url = legacy_template_ref(blob, "https://gitlab.example.org")
        assert repo == "a/b/student-template"
        assert url.endswith("/a/b/student-template.git")

    def test_returns_nothing_when_there_is_nothing_to_go_on(self):
        assert legacy_template_ref({}, "https://gitlab.example.org") == (None, None)


class TestReferenceRef:
    def test_maps_legacy_assignments_to_the_reference_repository(self):
        """The naming mapping: release calls this repo `reference`, legacy calls
        it `assignments`, and push_reference_repo skips silently without it."""
        repo, _ = legacy_reference_ref(legacy_course_blob(), "https://gitlab.example.org")
        assert repo == "org/fam/course/assignments"

    def test_falls_back_to_the_conventional_path(self):
        blob = legacy_course_blob()
        del blob["projects"]
        del blob["assignments_url"]
        repo, _ = legacy_reference_ref(blob, "https://gitlab.example.org")
        assert repo == "org/fam/course/assignments"

    def test_returns_nothing_when_there_is_nothing_to_go_on(self):
        assert legacy_reference_ref({}, None) == (None, None)


class TestGroupIds:
    def test_parent_group_id_is_a_string_and_the_rest_are_ints(self):
        """``CourseGitBindingGet.parent_group_id`` is typed ``Optional[str]``;
        an int makes pydantic reject it and every read of the binding 500s.
        Every other id is handed to python-gitlab and must stay an int."""
        ids = legacy_group_ids(legacy_course_blob())
        assert ids["parent_group_id"] == "1234"
        assert isinstance(ids["parent_group_id"], str)
        for key in ("course_group_id", "students_group_id", "tutors_group_id"):
            assert isinstance(ids[key], int)

    def test_carries_the_group_paths(self):
        ids = legacy_group_ids(legacy_course_blob())
        assert ids["course_group_path"] == "org/fam/course"
        assert ids["students_group_path"] == "org/fam/course/students"

    def test_derives_the_students_group_path_when_absent(self):
        blob = legacy_course_blob()
        del blob["students_group"]
        ids = legacy_group_ids(blob)
        assert ids["students_group_path"] == "org/fam/course/students"
        assert "students_group_id" not in ids

    def test_prefers_parent_id_but_accepts_parent(self):
        blob = legacy_course_blob()
        del blob["parent_id"]
        assert legacy_group_ids(blob)["parent_group_id"] == "1234"


class TestBaseUrl:
    def test_prefers_the_course_blob(self):
        """The course blob survives `alembic upgrade head`; the org blob does
        not — migration b1c2d3e4f5a6 strips url and token from it."""
        url = legacy_base_url(legacy_course_blob(), {"url": "https://old.example.org"}, None)
        assert url == "https://gitlab.example.org"

    def test_falls_back_to_the_organization(self):
        blob = legacy_course_blob()
        del blob["url"]
        del blob["student_template_url"]
        assert legacy_base_url(blob, {"url": "https://org.example.org/"}, None) == "https://org.example.org"

    def test_recovers_the_host_from_the_template_url(self):
        blob = {"student_template_url": "https://recovered.example.org/a/b/student-template"}
        assert legacy_base_url(blob, {}, None) == "https://recovered.example.org"

    def test_override_wins(self):
        assert legacy_base_url(legacy_course_blob(), {}, "https://override.example.org") == \
            "https://override.example.org"

    def test_returns_none_when_nothing_is_known(self):
        assert legacy_base_url({}, {}, None) is None


class TestBindingProperties:
    def build(self, **kwargs):
        return build_binding_properties(
            legacy_course_blob(),
            template_repo="org/fam/course/student-template",
            template_url="https://gitlab.example.org/org/fam/course/student-template.git",
            reference_path="org/fam/course/assignments",
            adopted_at="2026-08-24T00:00:00+00:00",
            **kwargs,
        )["gitlab"]

    def test_matches_the_key_set_ensure_course_structure_produces(self):
        """The highest-value assertion here: adoption and native provisioning
        must be indistinguishable to every consumer of the binding, so that
        _provision_gitlab_managed, push_reference_repo and the DTO all work
        unchanged — only pointed at the legacy names."""
        native_keys = {
            "parent_group_id",
            "course_group_id",
            "course_group_path",
            "template_project_id",
            "template_path",
            "template_url",
            "reference_project_id",
            "reference_path",
            "students_group_id",
            "students_group_path",
        }
        adopted = self.build(resolved_ids={"template_project_id": 60552, "reference_project_id": 60553})
        assert native_keys <= set(adopted)

    def test_records_the_legacy_naming_as_provenance(self):
        adopted = self.build()["adopted"]
        assert adopted["naming"] == {"template": "student-template", "reference": "assignments"}
        assert adopted["schema"] == ADOPTED_SCHEMA
        assert adopted["legacy"]["full_path"] == "org/fam/course"

    def test_resolved_ids_win_over_derived_values(self):
        adopted = self.build(resolved_ids={"students_group_id": 999})
        assert adopted["students_group_id"] == 999

    def test_is_json_serialisable(self):
        json.dumps(self.build())

    def test_never_carries_a_token_into_provenance(self):
        """A course-level token would be a ciphertext under the OLD secret:
        undecryptable here, and able to shadow the bridged one."""
        blob = legacy_course_blob(token="gAAAAA-legacy-ciphertext")
        properties = build_binding_properties(
            blob,
            template_repo="org/fam/course/student-template",
            template_url=None,
            reference_path=None,
        )
        assert "token" not in properties["gitlab"]["adopted"]["legacy"]
        # The ciphertext value itself must be gone. (`adopted.token` remains as
        # provenance — it records only which source the credential came from.)
        assert "gAAAAA-legacy-ciphertext" not in json.dumps(properties)
        assert properties["gitlab"]["adopted"]["token"] == {"bridged": False, "from": None}


class TestStripSecrets:
    def test_removes_the_token_and_keeps_everything_else(self):
        stripped = strip_secrets({"token": "secret", "url": "https://x", "group_id": 1})
        assert stripped == {"url": "https://x", "group_id": 1}


class TestMemberRepoPlan:
    def member_blob(self, **overrides):
        blob = {
            "url": "https://gitlab.example.org",
            "full_path": "org/fam/course/students/john.doe",
            "group_id": 4242,
            "namespace_id": 5679,
            "gitlab_project_id": 4242,
            "gitlab_project_path": "org/fam/course/students/john.doe",
            "http_url_to_repo": "https://gitlab.example.org/org/fam/course/students/john.doe.git",
            "ssh_url_to_repo": "git@gitlab.example.org:org/fam/course/students/john.doe.git",
            "web_url": "https://gitlab.example.org/org/fam/course/students/john.doe",
        }
        blob.update(overrides)
        return blob

    def test_carries_the_project_id_downstream_code_requires(self):
        """register_gitlab_managed_access refuses without properties.gitlab.project_id."""
        plan = build_member_repo_plan("m1", self.member_blob(), "https://gitlab.example.org")
        assert plan.properties["gitlab"]["project_id"] == 4242
        assert isinstance(plan.properties["gitlab"]["project_id"], int)

    def test_falls_back_to_group_id_for_the_project_id(self):
        """On a MEMBER blob `group_id` is the project id (it is the namespace id
        on a team submission-group blob — never share an extractor)."""
        blob = self.member_blob()
        del blob["gitlab_project_id"]
        plan = build_member_repo_plan("m1", blob, "https://gitlab.example.org")
        assert plan.properties["gitlab"]["project_id"] == 4242

    def test_maps_the_repository_urls(self):
        plan = build_member_repo_plan("m1", self.member_blob(), "https://gitlab.example.org")
        assert plan.repo_ref == "org/fam/course/students/john.doe"
        assert plan.mode == "managed"
        assert plan.http_url.endswith("/students/john.doe.git")
        assert plan.ssh_url.startswith("git@")

    def test_derives_urls_when_the_blob_omits_them(self):
        blob = {"full_path": "org/fam/course/students/jane", "gitlab_project_id": 7}
        plan = build_member_repo_plan("m1", blob, "https://gitlab.example.org")
        assert plan.http_url == "https://gitlab.example.org/org/fam/course/students/jane.git"
        assert plan.web_url == "https://gitlab.example.org/org/fam/course/students/jane"

    def test_skips_a_member_with_no_repository_path(self):
        assert build_member_repo_plan("m1", {"group_id": 1}, "https://gitlab.example.org") is None

    def test_never_carries_a_token_into_provenance(self):
        plan = build_member_repo_plan("m1", self.member_blob(token="s3cret"), None)
        assert "s3cret" not in json.dumps(plan.properties)


class TestCollisionDetection:
    def plan(self, repo_ref, member_id="m", mode="managed"):
        return MemberRepoPlan(member_id, mode, repo_ref, None, None, None, {})

    def test_detects_a_duplicate_within_one_course(self):
        problems = detect_repo_ref_collisions(
            [self.plan("a/b", "m1"), self.plan("a/b", "m2")], "srv", set()
        )
        assert len(problems) == 1
        assert "a/b" in problems[0]

    def test_detects_a_clash_with_an_existing_row(self):
        problems = detect_repo_ref_collisions([self.plan("a/b")], "srv", {("srv", "a/b")})
        assert len(problems) == 1

    def test_ignores_a_same_path_on_a_different_server(self):
        assert detect_repo_ref_collisions([self.plan("a/b")], "srv", {("other", "a/b")}) == []

    def test_ignores_non_managed_rows(self):
        """The unique index is partial: managed rows with a repo_ref only."""
        assert detect_repo_ref_collisions(
            [self.plan("a/b", "m1", "external"), self.plan("a/b", "m2", "external")], "srv", set()
        ) == []

    def test_accepts_distinct_paths(self):
        assert detect_repo_ref_collisions([self.plan("a/b", "m1"), self.plan("a/c", "m2")], "srv", set()) == []


class TestTokenBridge:
    def test_round_trips_between_two_secrets(self):
        keycove = pytest.importorskip("keycove")
        legacy, new = keycove.generate_secret_key(), keycove.generate_secret_key()
        ciphertext = keycove.encrypt("glpat-abc123", legacy)

        bridged = bridge_token(ciphertext, legacy, new)

        assert keycove.decrypt(bridged, new) == "glpat-abc123"
        assert bridged != ciphertext

    def test_raises_on_the_wrong_legacy_secret(self):
        """A wrong secret must be loud: the old scripts could otherwise write a
        NULL token, leaving the course silently unable to push or provision."""
        keycove = pytest.importorskip("keycove")
        legacy, wrong, new = (keycove.generate_secret_key() for _ in range(3))
        ciphertext = keycove.encrypt("glpat-abc123", legacy)

        with pytest.raises(Exception):
            bridge_token(ciphertext, wrong, new)


class TestAsDict:
    def test_passes_through_a_dict(self):
        assert as_dict({"a": 1}) == {"a": 1}

    def test_parses_a_json_string(self):
        assert as_dict('{"a": 1}') == {"a": 1}

    def test_degrades_to_empty_rather_than_raising(self):
        assert as_dict(None) == {}
        assert as_dict("not json") == {}
        assert as_dict("[1,2]") == {}


class TestStdinPipeable:
    """The module is piped into a running container (``docker exec -i … python3 -``)
    so a migration never needs an image rebuild. That only works if it never
    reaches for its own path and never uses a relative import."""

    def source(self):
        import computor_backend.scripts.adopt_legacy_git as module

        # Resolved via the imported module rather than a hardcoded path so this
        # keeps working if the file moves.
        return pathlib.Path(module.__spec__.origin).read_text()

    def test_never_uses_dunder_file(self):
        tree = ast.parse(self.source())
        assert [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == "__file__"] == []

    def test_uses_no_relative_imports(self):
        tree = ast.parse(self.source())
        assert [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and (n.level or 0) > 0] == []

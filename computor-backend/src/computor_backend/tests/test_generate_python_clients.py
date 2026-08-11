"""Naming rules for the generated Python client.

The generator used to name methods from whatever order routes happened to be
registered in, resolving clashes by "first one wins" and by slicing the tail of
the path. That produced two classes of bug these tests pin down:

* truncation artefacts (``get_urse_member_id_course_contents``), and
* the same name meaning opposite things in different modules — ``courses()``
  fetched one course under the ``tutors`` tag but listed them under
  ``students``, purely because of registration order.
"""

import random

from computor_backend.scripts.generate_python_clients import (
    disambiguate_method_name,
    generate_client_class,
    path_to_method_name,
)


def _op(schema=None, is_list=False):
    """Build a minimal operation with the given 200 response shape."""
    if schema is None:
        content = {}
    elif is_list:
        content = {"application/json": {"schema": {
            "type": "array", "items": {"$ref": f"#/components/schemas/{schema}"}}}}
    else:
        content = {"application/json": {"schema": {"$ref": f"#/components/schemas/{schema}"}}}
    return {"responses": {"200": {"content": content}}}


class TestPathToMethodName:
    def test_bare_crud_keeps_short_names(self):
        assert path_to_method_name("/courses", "GET", _op("CourseList", True), ["courses"]) == "list"
        assert path_to_method_name("/courses/{id}", "GET", _op("CourseGet"), ["courses"]) == "get"
        assert path_to_method_name("/courses", "POST", _op("CourseGet"), ["courses"]) == "create"
        assert path_to_method_name("/courses/{id}", "PATCH", _op("CourseGet"), ["courses"]) == "update"
        assert path_to_method_name("/courses/{id}", "DELETE", _op(), ["courses"]) == "delete"

    def test_list_vs_get_follows_the_response_shape_not_the_route_order(self):
        """The regression: `courses` meant "get one" or "list" depending on tag."""
        for tag in ("tutors", "students", "lecturers"):
            listing = path_to_method_name(
                f"/{tag}/courses", "GET", _op("CourseList", True), [tag])
            single = path_to_method_name(
                f"/{tag}/courses/{{course_id}}", "GET", _op("CourseGet"), [tag])
            assert listing == "list_courses", tag
            assert single == "get_courses", tag

    def test_action_subpaths_do_not_land_in_the_list_namespace(self):
        # Ends in a plain segment, but answers with a file — not a listing.
        assert path_to_method_name(
            "/submissions/artifacts/download", "GET", _op(), ["submissions"]
        ) == "get_artifacts_download"

    def test_nested_collection_and_item_are_distinct(self):
        base = "/tutors/course-members/{course_member_id}/course-contents"
        assert path_to_method_name(
            base, "GET", _op("CourseContentStudentList", True), ["tutors"]
        ) == "list_course_members_course_contents"
        assert path_to_method_name(
            base + "/{course_content_id}", "GET", _op("CourseContentStudentGet"), ["tutors"]
        ) == "get_course_members_course_contents"

    def test_post_actions_keep_the_path_verb(self):
        assert path_to_method_name(
            "/courses/{course_id}/validate", "POST", _op(), ["courses"]
        ) == "validate"

    def test_every_name_part_is_a_whole_path_segment(self):
        """`get_urse_member_id_...` came from slicing the tail of the path.

        Guard the general property: every underscore-separated part of the name
        is either a verb or a whole word taken from the path — never a fragment
        of one.
        """
        path = "/tutors/course-members/{course_member_id}/course-contents"
        name = path_to_method_name(path, "GET", _op("X", True), ["tutors"])

        vocabulary = {"list", "get", "create", "update", "replace", "delete", "by"}
        for segment in path.replace("{", "").replace("}", "").split("/"):
            vocabulary.update(segment.replace("-", "_").split("_"))

        assert set(name.split("_")) <= vocabulary, name


class TestDisambiguateMethodName:
    def test_uses_the_path_parameter_rather_than_a_counter(self):
        assert disambiguate_method_name(
            "get_artifacts_download", "/submissions/artifacts/{artifact_id}/download", {"get_artifacts_download"}
        ) == "get_artifacts_download_by_artifact_id"

    def test_falls_back_to_a_suffix_when_there_is_no_free_parameter(self):
        taken = {"get_thing", "get_thing_by_id"}
        assert disambiguate_method_name("get_thing", "/things/{id}", taken) == "get_thing_2"

    def test_is_independent_of_call_order(self):
        path = "/submissions/artifacts/{artifact_id}/download"
        taken = {"get_artifacts_download"}
        first = disambiguate_method_name("get_artifacts_download", path, set(taken))
        second = disambiguate_method_name("get_artifacts_download", path, set(taken))
        assert first == second


class TestGeneratedNamesAreOrderIndependent:
    OPERATIONS = [
        {"path": "/tutors/courses", "method": "GET",
         "operation": _op("CourseTutorList", True), "operation_id": "a"},
        {"path": "/tutors/courses/{course_id}", "method": "GET",
         "operation": _op("CourseTutorGet"), "operation_id": "b"},
        {"path": "/tutors/course-members", "method": "GET",
         "operation": _op("TutorCourseMemberList", True), "operation_id": "c"},
        {"path": "/tutors/course-members/{course_member_id}", "method": "GET",
         "operation": _op("TutorCourseMemberGet"), "operation_id": "d"},
        {"path": "/tutors/tests/{test_id}/artifacts/download", "method": "GET",
         "operation": _op(), "operation_id": "e"},
    ]

    def _names(self, operations):
        code, _, _ = generate_client_class("tutors", operations, {})
        return sorted(
            line.strip().removeprefix("async def ").split("(")[0]
            for line in code.splitlines()
            if line.strip().startswith("async def ")
        )

    def test_shuffling_the_route_order_does_not_change_any_name(self):
        expected = self._names(self.OPERATIONS)
        rng = random.Random(20260811)
        for _ in range(12):
            shuffled = list(self.OPERATIONS)
            rng.shuffle(shuffled)
            assert self._names(shuffled) == expected

    def test_names_are_unique_within_a_class(self):
        names = self._names(self.OPERATIONS)
        assert len(names) == len(set(names))

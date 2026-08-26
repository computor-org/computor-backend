"""Defensive strip of absolute paths from tester reports (#239).

The testers no longer write filesystem paths into ``report.properties``, but
``strip_path_properties`` guards the backend read side against any tester that
still does — the report lands verbatim in ``result_json`` and is returned to
the student.
"""

from computor_backend.tasks.temporal_base import strip_path_properties


def test_absolute_path_values_are_dropped():
    results = {
        "summary": {"passed": 3, "failed": 1, "total": 4},
        "properties": {
            "test": "/tmp/examples/by-version/abc/123/test.yaml",
            "specification": "/tmp/tmpXYZ.yaml",
            "pytestflags": "-v",
            "exitcode": "1",
        },
    }
    stripped = strip_path_properties(results)
    assert stripped is results
    assert stripped["properties"] == {"pytestflags": "-v", "exitcode": "1"}
    assert stripped["summary"] == {"passed": 3, "failed": 1, "total": 4}


def test_results_without_properties_pass_through():
    results = {"passed": 0, "failed": 1, "total": 1, "error": "boom"}
    assert strip_path_properties(results) == {
        "passed": 0,
        "failed": 1,
        "total": 1,
        "error": "boom",
    }


def test_non_dict_properties_are_left_alone():
    results = {"properties": ["/tmp/not-a-dict"]}
    assert strip_path_properties(results)["properties"] == ["/tmp/not-a-dict"]


def test_relative_and_non_string_values_survive():
    results = {"properties": {"exitcode": 0, "basename": "test.yaml"}}
    assert strip_path_properties(results)["properties"] == {
        "exitcode": 0,
        "basename": "test.yaml",
    }

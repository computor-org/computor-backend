"""Report properties must never disclose filesystem paths (#239).

The tester report is stored verbatim in ``result_json`` and returned to the
student. Before this, ``properties`` carried the absolute container paths of
``test.yaml`` and the generated spec file — the latter contains the reference
solution, so the paths fed the #240 read-the-reference attack.

``build_report_properties`` in ``testers.tests.conftest_base`` is now the one
place report properties are built (the Octave conftest shares it); these tests
pin that nothing path-shaped comes out of it.
"""

from __future__ import annotations

from testers.tests.conftest_base import build_report_properties  # type: ignore


def test_properties_keep_flags_and_exitcode():
    props = build_report_properties("-v --tb=short", 1)
    assert props["pytestflags"] == "-v --tb=short"
    assert props["exitcode"] == "1"


def test_properties_contain_no_absolute_paths():
    props = build_report_properties("-v", 0)
    for key, value in props.items():
        assert not str(value).startswith("/"), (
            f"report property {key!r} leaks an absolute path: {value!r}"
        )


def test_properties_have_no_path_keys():
    props = build_report_properties("-v", 0)
    assert "test" not in props
    assert "specification" not in props

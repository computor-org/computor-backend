"""Learner-facing runner messages follow the course language."""

import pytest

from ctcore.i18n import ENV_VAR, MESSAGES, tr
from testers.tests.test_base import check_occurrence_range


def _fail_text(monkeypatch, language, *args):
    if language is None:
        monkeypatch.delenv(ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(ENV_VAR, language)
    with pytest.raises(pytest.fail.Exception) as exc:
        check_occurrence_range(*args)
    return exc.value.msg


def test_german_message_and_placeholders(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "de")
    text = tr("variable_not_found", name="x_start")
    assert text == "Die Variable `x_start` wurde in deiner Lösung nicht gefunden"


@pytest.mark.parametrize("language", [None, "en", "fr", "", "xx-YY"])
def test_english_default_and_unknown_language_fallback(monkeypatch, language):
    if language is None:
        monkeypatch.delenv(ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(ENV_VAR, language)
    assert tr("variable_not_found", name="x_start") == (
        "Variable `x_start` not found in student namespace"
    )


def test_language_code_variants(monkeypatch):
    for value in ("de", "DE", "de-AT", "de_DE"):
        monkeypatch.setenv(ENV_VAR, value)
        assert tr("file_empty", file="a.py").startswith("Die Datei")


def test_every_entry_has_en_de_with_same_placeholders():
    import string

    def fields(t):
        return {f for _, f, _, _ in string.Formatter().parse(t) if f}

    for key, entry in MESSAGES.items():
        assert set(entry) == {"en", "de"}, key
        assert fields(entry["en"]) == fields(entry["de"]), key


@pytest.mark.parametrize("args", [
    (3, [0, 0], "`for`"),
    (1, [2, 0], "`for`"),
    (9, [2, 5], "`for`"),
    (9, [2, 5], "Words", "is"),
])
def test_same_outcome_in_en_and_de(monkeypatch, args):
    en = _fail_text(monkeypatch, "en", *args)
    de = _fail_text(monkeypatch, "de", *args)
    assert en != de
    assert "`for`" in de or "Words" in de
    # Within the allowed range both languages pass without a message.
    for language in ("en", "de"):
        monkeypatch.setenv(ENV_VAR, language)
        check_occurrence_range(3, [3, 3], "x")


def test_unknown_language_gives_english_failure(monkeypatch):
    en = _fail_text(monkeypatch, "en", 9, [2, 5], "`for`")
    assert _fail_text(monkeypatch, "zz", 9, [2, 5], "`for`") == en
    assert en == "`for` found 9 times, expected 2-5"


def _assertion_text(monkeypatch, language, actual, expected):
    from testers.tests.test_base import compare_values

    monkeypatch.setenv(ENV_VAR, language)
    with pytest.raises(AssertionError) as exc:
        compare_values(actual, expected, name="x")
    return str(exc.value)


def test_value_comparison_reads_german(monkeypatch):
    de = _assertion_text(monkeypatch, "de", 3.0, 5.5)
    assert de.splitlines()[:3] == [
        "Die Variable `x` weicht vom erwarteten Wert ab:",
        "  erwartet: 5.5",
        "  tatsächlich: 3",
    ]
    assert "expected" not in de and "actual" not in de


def test_array_and_string_comparisons_read_german(monkeypatch):
    import numpy as np

    array = _assertion_text(monkeypatch, "de", np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 5.5]))
    assert "abweichende Elemente (insgesamt 1):" in array
    assert "tatsächlich=3" in array and "erwartet=5.5" in array
    text = _assertion_text(monkeypatch, "de", "hallo", "hello")
    assert "erste Abweichung an Index 1:" in text


def test_default_summaries_follow_the_language_but_lecturer_text_stays(monkeypatch):
    from ctcore.i18n import tr_summary

    monkeypatch.setenv(ENV_VAR, "de")
    assert tr_summary("Congratulations! All tests passed") == "Glückwunsch! Alle Tests bestanden"
    assert tr_summary("Some or all tests failed") == "Einige oder alle Tests sind fehlgeschlagen"
    assert tr_summary("Gut gemacht, Lisa!") == "Gut gemacht, Lisa!"
    assert tr_summary(None) is None
    monkeypatch.setenv(ENV_VAR, "en")
    assert tr_summary("Some or all tests failed") == "Some or all tests failed"


@pytest.mark.parametrize("entry_point,language,expected", [
    ("pscript.py", "de", "Das Python-Skript `pscript.py` wurde in deiner Abgabe nicht gefunden"),
    ("pscript.py", "en", "Python script `pscript.py` not found in your submission"),
    (None, "de", "In deiner Abgabe wurde kein Python-Skript gefunden"),
    (None, "en", "No Python script found in your submission"),
])
def test_missing_student_script_names_file_not_temp_path(
    monkeypatch, tmp_path, entry_point, language, expected
):
    from types import SimpleNamespace
    from testers.tests.python.conftest import Solution, report_key
    from testers.tests.python.test_class import get_solution

    monkeypatch.setenv(ENV_VAR, language)
    main = SimpleNamespace(
        entryPoint=entry_point, timeout=None, inputAnswers=None, setUpCode=None,
        tearDownCode=None, successDependency=None, setUpCodeDependency=None, tests=[],
    )
    config = SimpleNamespace(stash={report_key: {
        "testsuite": SimpleNamespace(properties=SimpleNamespace(tests=[main])),
        "specification": SimpleNamespace(studentDirectory=str(tmp_path)),
        "report": None,
        "solutions": {},
    }})
    solution = get_solution(monkeypatch, config, 0, Solution.student)
    assert solution["errormsg"] == expected
    assert str(tmp_path) not in repr(solution)


pytest_plugins = ["pytester"]


@pytest.mark.parametrize("language,failed,skipped", [
    ("de", "Fehlgeschlagen: `x` = 3", "Übersprungen: `y`"),
    ("en", "Failed: `x` = 3", "Skipped: `y`"),
])
def test_fail_and_skip_label_follows_language(pytester, monkeypatch, language, failed, skipped):
    from testers.tests.conftest_base import learner_result_message

    pytester.makepyfile("""
        import pytest
        def test_fail():
            pytest.fail("`x` = 3")
        def test_skip():
            pytest.skip("`y`")
    """)
    reports = {
        r.nodeid.split("::")[-1]: r
        for r in pytester.inline_run().getreports("pytest_runtest_logreport")
        if r.when == "call" or r.skipped
    }
    monkeypatch.setenv(ENV_VAR, language)
    assert learner_result_message(reports["test_fail"]) == failed
    assert learner_result_message(reports["test_skip"]) == skipped


@pytest.fixture
def bilingual():
    from ctcore.i18n import enable_bilingual

    enable_bilingual()
    yield
    enable_bilingual(False)


def test_marked_messages_render_in_each_language(monkeypatch, bilingual):
    from ctcore.i18n import bilingual_report, tr_outcome

    monkeypatch.setenv(ENV_VAR, "de")
    nested = tr("execution_failed", errors=tr("security_check_failed", issue="Blocked import: os"))
    own = tr_outcome("AssertionError: " + tr("differs", name="x") + f"\n  {tr('label_expected')}: 5")
    report = bilingual_report({"tests": [{"tests": [
        {"resultMessage": tr_outcome("Failed: " + nested)},
        {"resultMessage": own},
        {"resultMessage": "AssertionError: lecturer or learner text"},
    ]}]})
    first, second, third = report["tests"][0]["tests"]
    assert first["resultMessageI18n"] == {
        "de": "Fehlgeschlagen: Die Ausführung ist fehlgeschlagen: "
              "Die Sicherheitsprüfung ist fehlgeschlagen: Blocked import: os",
        "en": "Failed: Execution failed: Security check failed: Blocked import: os",
    }
    assert first["resultMessage"] == first["resultMessageI18n"]["de"]
    assert second["resultMessageI18n"]["en"] == "Variable `x` differs from expected:\n  expected: 5"
    assert third == {"resultMessage": "AssertionError: lecturer or learner text"}


@pytest.mark.parametrize("language", ["de", "en"])
def test_tester_report_keeps_both_languages(tmp_path, language):
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    (tmp_path / "test.yaml").write_text(
        "type: python\nname: Files\nproperties:\n  tests:\n"
        "  - {type: exist, name: files, tests: [{name: notes.txt}]}\n"
    )
    env = {**os.environ, ENV_VAR: language, "MPLBACKEND": "Agg"}
    subprocess.run(
        [sys.executable, "-m", "testers.cli", "python", "local", "-d", str(tmp_path), "-v", "0"],
        cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, timeout=120,
    )
    report = json.loads((tmp_path / "output" / "testSummary.json").read_text())
    (sub,) = report["tests"][0]["tests"]
    assert sub["resultMessageI18n"] == {
        "de": "Fehlgeschlagen: Die Datei 'notes.txt' wurde in deinem Abgabeverzeichnis nicht gefunden",
        "en": "Failed: File 'notes.txt' not found in student directory",
    }
    assert sub["resultMessage"] == sub["resultMessageI18n"][language]
    assert report["resultMessageI18n"]["de"] == "Einige oder alle Tests sind fehlgeschlagen"
    assert report["resultMessage"] == report["resultMessageI18n"][language]
    assert "\u2061" not in json.dumps(report, ensure_ascii=False)


@pytest.mark.parametrize("language", ["de", "en"])
def test_syntax_error_is_named_once_with_file_and_line(tmp_path, language):
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    (tmp_path / "test.yaml").write_text(
        "type: python\nname: Syntax\nproperties:\n  tests:\n"
        "  - {type: variable, name: vars, entryPoint: basis2.py, tests: [{name: a}, {name: b}]}\n"
        "  - {type: variable, name: more, entryPoint: basis2.py, tests: [{name: c}]}\n"
    )
    (tmp_path / "basis2.py").write_text("a = 1\nb = (2\nc = 3\n")
    env = {**os.environ, ENV_VAR: language, "MPLBACKEND": "Agg"}
    subprocess.run(
        [sys.executable, "-m", "testers.cli", "python", "local", "-d", str(tmp_path), "-v", "0"],
        cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, timeout=120,
    )
    report = json.loads((tmp_path / "output" / "testSummary.json").read_text())
    subs = [sub for main in report["tests"] for sub in main["tests"]]
    # Still failed: skipped tests would leave the grade's denominator.
    assert [sub["result"] for sub in subs] == ["FAILED"] * 3
    texts = [sub["resultMessageI18n"] for sub in subs]
    assert texts[0] == {
        "de": "Fehlgeschlagen: Dein Skript `basis2.py` kann nicht ausgeführt werden: "
              "Syntaxfehler in Zeile 2: '(' was never closed\n  b = (2",
        "en": "Failed: Your script `basis2.py` cannot be run: "
              "syntax error in line 2: '(' was never closed\n  b = (2",
    }
    assert texts[1] == texts[2] == {
        "de": "Nicht ausgeführt: `basis2.py` hat einen Syntaxfehler in Zeile 2",
        "en": "Not run: `basis2.py` has a syntax error in line 2",
    }

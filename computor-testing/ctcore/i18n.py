"""
Learner-facing runner messages in the course language.

The worker passes the course language to the runner in the environment
variable ``COMPUTOR_TEST_LANGUAGE`` (a two-letter code such as ``de`` or
``en``). ``tr(key, **values)`` renders the message template for that
language. English is the template of record and the fallback for an unset or
unknown language and for a key without a translation, so a missing entry can
never change a test outcome or raise.

Only the message text is translated. Result keys, statuses and scores are
produced elsewhere and are not touched by this module.
"""

import os

ENV_VAR = "COMPUTOR_TEST_LANGUAGE"
DEFAULT_LANGUAGE = "en"

MESSAGES = {
    "variable_not_found": {
        "en": "Variable `{name}` not found in student namespace",
        "de": "Die Variable `{name}` wurde in deiner Lösung nicht gefunden",
    },
    "file_not_found": {
        "en": "File '{file}' not found in student directory",
        "de": "Die Datei '{file}' wurde in deinem Abgabeverzeichnis nicht gefunden",
    },
    "file_not_found_plain": {
        "en": "File `{file}` not found in student directory",
        "de": "Die Datei `{file}` wurde in deinem Abgabeverzeichnis nicht gefunden",
    },
    "file_empty": {
        "en": "File '{file}' is empty (0 bytes)",
        "de": "Die Datei '{file}' ist leer (0 Bytes)",
    },
    "execution_timed_out": {
        "en": "Execution timed out: {detail}",
        "de": "Zeitüberschreitung bei der Ausführung: {detail}",
    },
    "source_not_found": {
        "en": "Source file not found for structural test",
        "de": "Für den Strukturtest wurde keine Quelldatei gefunden",
    },
    "source_rejected": {
        "en": "Source file rejected for structural test: {detail}",
        "de": "Die Quelldatei wurde für den Strukturtest abgelehnt: {detail}",
    },
    "python_file_not_found_structural": {
        "en": "Python file not found for structural test",
        "de": "Für den Strukturtest wurde keine Python-Datei gefunden",
    },
    "python_file_not_found_linting": {
        "en": "Python file not found for linting",
        "de": "Für die Stilprüfung wurde keine Python-Datei gefunden",
    },
    "linting_errors": {
        "en": "{count} linting errors in `{file}`",
        "de": "{count} Stilfehler in `{file}`",
    },
    "pattern_timed_out": {
        "en": "Pattern `{pattern}` timed out (possible ReDoS)",
        "de": "Zeitüberschreitung beim Muster `{pattern}` (möglicherweise ReDoS)",
    },
    "occurrence_is_forbidden": {
        "en": "{subject} is {count}, but must be 0",
        "de": "{subject} ist {count}, muss aber 0 sein",
    },
    "occurrence_found_forbidden": {
        "en": "{subject} found {count} times, but must not occur",
        "de": "{subject} kommt {count}-mal vor, darf aber nicht vorkommen",
    },
    "occurrence_is_min": {
        "en": "{subject} is {count}, expected at least {min}",
        "de": "{subject} ist {count}, erwartet wird mindestens {min}",
    },
    "occurrence_found_min": {
        "en": "{subject} found {count} times, expected at least {min}",
        "de": "{subject} kommt {count}-mal vor, erwartet wird mindestens {min}",
    },
    "occurrence_is_range": {
        "en": "{subject} is {count}, expected {min}-{max}",
        "de": "{subject} ist {count}, erwartet wird {min} bis {max}",
    },
    "occurrence_found_range": {
        "en": "{subject} found {count} times, expected {min}-{max}",
        "de": "{subject} kommt {count}-mal vor, erwartet wird {min} bis {max}",
    },
    "occurrence_found_exact": {
        "en": "{subject} found {count} times, expected {expected}",
        "de": "{subject} kommt {count}-mal vor, erwartet wird {expected}",
    },
    "type_incorrect": {
        "en": "Variable `{name}` has incorrect type: {actual} vs {expected}",
        "de": "Die Variable `{name}` hat den falschen Typ: {actual} statt {expected}",
    },
    "shape_wrong": {
        "en": "Variable `{name}` has wrong shape:\n  expected: {expected}\n  actual:   {actual}",
        "de": "Die Variable `{name}` hat die falsche Form:\n  erwartet: {expected}\n  tatsächlich: {actual}",
    },
    "length_wrong": {
        "en": "Variable `{name}` has wrong length:\n  expected: {expected}\n  actual:   {actual}",
        "de": "Die Variable `{name}` hat die falsche Länge:\n  erwartet: {expected}\n  tatsächlich: {actual}",
    },
    "hint_transposed": {
        "en": "  hint: shapes look transposed — did you forget `.T` or transpose?",
        "de": "  Hinweis: Die Formen sehen vertauscht aus. Fehlt `.T` oder eine Transposition?",
    },
    "hint_reversed": {
        "en": "  hint: shapes are reversed — check axis order.",
        "de": "  Hinweis: Die Formen sind umgekehrt. Prüfe die Reihenfolge der Achsen.",
    },
    "hint_reshape": {
        "en": "  hint: total element count matches — try `.reshape({shape})`.",
        "de": "  Hinweis: Die Gesamtzahl der Elemente stimmt. Versuche `.reshape({shape})`.",
    },
    # Comparison reports. Labels stay short; values are never translated.
    "differs": {
        "en": "Variable `{name}` differs from expected:",
        "de": "Die Variable `{name}` weicht vom erwarteten Wert ab:",
    },
    "label_expected": {"en": "expected", "de": "erwartet"},
    "label_actual": {"en": "actual", "de": "tatsächlich"},
    "label_shape": {"en": "shape", "de": "Form"},
    "label_dtype": {"en": "dtype", "de": "Datentyp"},
    "label_tolerances": {"en": "tolerances", "de": "Toleranzen"},
    "label_lengths": {"en": "lengths", "de": "Längen"},
    "label_pattern": {"en": "pattern", "de": "Muster"},
    "label_abs_diff": {"en": "abs diff", "de": "abs. Abweichung"},
    "label_rel_diff": {"en": "rel diff", "de": "rel. Abweichung"},
    "label_missing": {"en": "missing", "de": "fehlt"},
    "label_extra": {"en": "extra", "de": "zusätzlich"},
    "label_in": {"en": "in", "de": "in"},
    "nan_disagreement": {
        "en": "NaN disagreement at {count}+ positions:",
        "de": "NaN stimmt an {count}+ Stellen nicht überein:",
    },
    "max_abs_diff": {
        "en": "max abs diff: {value} at index {index}",
        "de": "größte abs. Abweichung: {value} an Index {index}",
    },
    "max_rel_diff": {
        "en": "max rel diff: {value} at index {index}",
        "de": "größte rel. Abweichung: {value} an Index {index}",
    },
    "mismatching_elements": {
        "en": "mismatching elements ({count} total):",
        "de": "abweichende Elemente (insgesamt {count}):",
    },
    "unequal_elements": {
        "en": "unequal elements ({count} total):",
        "de": "ungleiche Elemente (insgesamt {count}):",
    },
    "and_more": {"en": "... and {count} more", "de": "... und {count} weitere"},
    "more_chars": {"en": "...<{count} more chars>", "de": "...<{count} weitere Zeichen>"},
    "first_diff": {"en": "first diff at index {index}:", "de": "erste Abweichung an Index {index}:"},
    "failed_check": {
        "en": "Variable `{name}` failed `{check}` check:",
        "de": "Die Variable `{name}` hat die Prüfung `{check}` nicht bestanden:",
    },
    "occurrences": {"en": "{count} occurrence(s)", "de": "{count}-mal"},
    "expected_none": {
        "en": "Expected None for '{name}', got {actual}",
        "de": "Für '{name}' wird None erwartet, erhalten: {actual}",
    },
    "is_none": {
        "en": "Variable '{name}' is None, expected {expected}",
        "de": "Die Variable '{name}' ist None, erwartet wird {expected}",
    },
    "type_mismatch": {
        "en": "Type mismatch for '{name}': {actual} vs {expected}",
        "de": "Falscher Typ für '{name}': {actual} statt {expected}",
    },
    "nan_mismatch": {
        "en": "NaN mismatch for '{name}': actual={actual}, expected={expected}",
        "de": "NaN stimmt für '{name}' nicht überein: tatsächlich={actual}, erwartet={expected}",
    },
    "wrong_type": {
        "en": "Variable `{name}` has wrong type:",
        "de": "Die Variable `{name}` hat den falschen Typ:",
    },
    "wrong_keys": {
        "en": "Variable `{name}` has wrong keys:",
        "de": "Die Variable `{name}` hat die falschen Schlüssel:",
    },
    # Dependencies, execution and output tests
    "dependency_invalid": {
        "en": "Success-Dependency `{dependency}` not valid",
        "de": "Die Erfolgsabhängigkeit `{dependency}` ist ungültig",
    },
    "dependency_not_satisfied": {
        "en": "Success-Dependency `{dependency}` not satisfied",
        "de": "Die vorausgesetzten Tests `{dependency}` sind nicht bestanden",
    },
    "setup_dependency_invalid": {
        "en": "SetupCode-Dependency `{dependency}` not valid",
        "de": "Die Setup-Abhängigkeit `{dependency}` ist ungültig",
    },
    "expected_error_not_found": {
        "en": "Expected error matching `{pattern}` not found",
        "de": "Es trat kein Fehler auf, der zu `{pattern}` passt",
    },
    "expected_error_none": {
        "en": "Expected an error but none occurred",
        "de": "Erwartet wurde ein Fehler, es trat aber keiner auf",
    },
    "expected_error_but_succeeded": {
        "en": "Expected an error but execution succeeded",
        "de": "Erwartet wurde ein Fehler, die Ausführung war aber erfolgreich",
    },
    "expected_warning_not_found": {
        "en": "Expected warning matching `{pattern}` not found",
        "de": "Es trat keine Warnung auf, die zu `{pattern}` passt",
    },
    "expected_warning_none": {
        "en": "Expected a warning but none occurred",
        "de": "Erwartet wurde eine Warnung, es trat aber keine auf",
    },
    "output_mismatch": {
        "en": "Output mismatch:\n  Actual: {actual}\n  Expected: {expected}",
        "de": "Die Ausgabe weicht ab:\n  Tatsächlich: {actual}\n  Erwartet: {expected}",
    },
    "output_not_contains": {
        "en": "Output does not contain '{pattern}'",
        "de": "Die Ausgabe enthält '{pattern}' nicht",
    },
    "output_not_matches": {
        "en": "Output does not match pattern '{pattern}'",
        "de": "Die Ausgabe passt nicht zum Muster '{pattern}'",
    },
    "file_not_found_short": {
        "en": "File '{file}' not found",
        "de": "Die Datei '{file}' wurde nicht gefunden",
    },
    "getting_solution_failed": {
        "en": "Getting solution failed: {error}",
        "de": "Die Lösung konnte nicht ausgeführt werden: {error}",
    },
    "execution_timed_out_plain": {
        "en": "Execution timed out",
        "de": "Zeitüberschreitung bei der Ausführung",
    },
    "exit_code_mismatch": {
        "en": "Exit code mismatch: got {actual}, expected {expected}",
        "de": "Falscher Exit-Code: erhalten {actual}, erwartet {expected}",
    },
    "execution_too_slow": {
        "en": "Execution took {duration}s, limit is {limit}s",
        "de": "Die Ausführung dauerte {duration} s, erlaubt sind {limit} s",
    },
    "execution_failed": {
        "en": "Execution failed: {errors}",
        "de": "Die Ausführung ist fehlgeschlagen: {errors}",
    },
    "language_execution_error": {
        "en": "{language} execution error: {error}",
        "de": "Fehler bei der Ausführung ({language}): {error}",
    },
    "unexpected_error": {
        "en": "Unexpected error: {error}",
        "de": "Unerwarteter Fehler: {error}",
    },
    "script_not_found_in": {
        "en": "No {language} script found in your submission",
        "de": "In deiner Abgabe wurde kein {language}-Skript gefunden",
    },
    "script_not_found": {
        "en": "{language} script `{file}` not found in your submission",
        "de": "Das {language}-Skript `{file}` wurde in deiner Abgabe nicht gefunden",
    },
    "variable_not_found_short": {
        "en": "Variable '{name}' not found in student solution",
        "de": "Die Variable '{name}' wurde in deiner Lösung nicht gefunden",
    },
    "evaluation_not_possible": {
        "en": "Evaluation of `{expression}` not possible",
        "de": "`{expression}` konnte nicht ausgewertet werden",
    },
    "broken_example": {
        "en": "BROKEN EXAMPLE: variable `{name}` is missing from the reference namespace — fix the example's test.yaml or reference solution, this is not a student error",
        "de": "FEHLER IM BEISPIEL: Die Variable `{name}` fehlt in der Referenzlösung. Das ist kein Fehler deiner Lösung; test.yaml oder die Referenzlösung des Beispiels muss korrigiert werden.",
    },
    "could_not_tokenize": {
        "en": "Could not tokenize student file: {error}",
        "de": "Deine Datei konnte nicht zerlegt werden: {error}",
    },
    "compilation_unavailable": {
        "en": "Compilation result not available",
        "de": "Es liegt kein Ergebnis der Kompilierung vor",
    },
    "compilation_failed": {
        "en": "Compilation should succeed but failed:\n{stderr}",
        "de": "Die Kompilierung sollte gelingen, ist aber fehlgeschlagen:\n{stderr}",
    },
    "compilation_should_fail": {
        "en": "Compilation should fail but succeeded",
        "de": "Die Kompilierung sollte fehlschlagen, ist aber gelungen",
    },
    "compiler_pattern_not_found": {
        "en": "Expected pattern not found in compiler output: {pattern}",
        "de": "Das erwartete Muster fehlt in der Ausgabe des Compilers: {pattern}",
    },
    "execution_result_unavailable": {
        "en": "No execution result available",
        "de": "Es liegt kein Ergebnis der Ausführung vor",
    },
    # Outcome labels pytest puts in front of a fail or skip message
    "outcome_failed": {"en": "Failed: {detail}", "de": "Fehlgeschlagen: {detail}"},
    "outcome_skipped": {"en": "Skipped: {detail}", "de": "Übersprungen: {detail}"},
    # Summaries
    "tests_skipped": {"en": "Tests skipped", "de": "Tests übersprungen"},
    "no_tests_specified": {"en": "No Tests specified", "de": "Keine Tests angegeben"},
    "all_tests_passed": {"en": "All tests passed", "de": "Alle Tests bestanden"},
    "some_tests_failed": {"en": "Some tests failed", "de": "Einige Tests sind fehlgeschlagen"},
    "default_success": {
        "en": "Congratulations! All tests passed",
        "de": "Glückwunsch! Alle Tests bestanden",
    },
    "default_failure": {
        "en": "Some or all tests failed",
        "de": "Einige oder alle Tests sind fehlgeschlagen",
    },
}

# The test.yaml defaults are ours to translate; a lecturer's own wording is not.
_DEFAULT_SUMMARIES = {
    MESSAGES["default_success"]["en"]: "default_success",
    MESSAGES["default_failure"]["en"]: "default_failure",
}


def tr_summary(text):
    """``text`` in the current language if it is one of our default summaries."""
    key = _DEFAULT_SUMMARIES.get(text) if isinstance(text, str) else None
    return tr(key) if key else text


_OUTCOME_LABELS = {"Failed: ": "outcome_failed", "Skipped: ": "outcome_skipped"}


def tr_outcome(text):
    """``text`` with pytest's English "Failed: "/"Skipped: " label in the current language."""
    if isinstance(text, str):
        for label, key in _OUTCOME_LABELS.items():
            if text.startswith(label):
                return tr(key, detail=text[len(label):])
    return text


def get_language() -> str:
    """Return the two-letter language code from the environment, or ``en``."""
    raw = os.environ.get(ENV_VAR, "").strip().lower()
    code = raw.replace("_", "-").split("-")[0]
    return code or DEFAULT_LANGUAGE


def tr(key: str, **values) -> str:
    """Render message ``key`` in the current language (English fallback)."""
    entry = MESSAGES[key]
    template = entry.get(get_language()) or entry[DEFAULT_LANGUAGE]
    return template.format(**values)

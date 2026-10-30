"""Texts the testing worker itself writes into a learner's result.

The job carries the reading language of the person who started the run
(``language``); the runner's own messages follow it through
``COMPUTOR_TEST_LANGUAGE``, these follow it here. English is the fallback.
"""

from typing import Optional

MESSAGES = {
    "timed_out": {
        "en": "Test execution timed out after {seconds} seconds",
        "de": "Der Test wurde nach {seconds} Sekunden wegen Zeitüberschreitung abgebrochen",
    },
    "matlab_timeout": {
        "en": "Execution timeout: Test exceeded {seconds} seconds. "
              "This usually indicates an infinite loop in the code.",
        "de": "Zeitüberschreitung: Der Test hat länger als {seconds} Sekunden gedauert. "
              "Meist steckt eine Endlosschleife im Code.",
    },
    "no_results": {
        "en": "No test results file found",
        "de": "Es wurde keine Datei mit Testergebnissen gefunden",
    },
    "report_rejected": {
        "en": "Test report rejected: {error}",
        "de": "Der Testbericht wurde abgelehnt: {error}",
    },
    "all_skipped": {
        "en": "All tests were skipped; run is inconclusive",
        "de": "Alle Tests wurden übersprungen, daher hat der Lauf kein Ergebnis",
    },
    "backend_error": {
        "en": "Backend error: {error}",
        "de": "Fehler im Testdienst: {error}",
    },
}


def runner_text(key: str, language: Optional[str], **values) -> str:
    entry = MESSAGES[key]
    code = (language or "").strip().lower().replace("_", "-").split("-")[0]
    return (entry.get(code) or entry["en"]).format(**values)


def runner_error(key: str, language: Optional[str], **values) -> dict:
    """``error`` in the run's language and ``error_i18n`` in every language.

    A result is read later by people in other languages (a tutor, a learner
    who switched); they read ``error_i18n``, older readers ``error``.
    """
    return {
        "error": runner_text(key, language, **values),
        "error_i18n": {code: runner_text(key, code, **values) for code in ("de", "en")},
    }

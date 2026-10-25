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
}


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

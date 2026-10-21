"""Rules behind the lecturer analytics (typical errors, timelines, flags).

Pure functions only — no database. All inputs are synthetic.
"""

from datetime import datetime, timedelta, timezone

from computor_backend.business_logic.course_analytics import (
    DEFAULT_THRESHOLDS,
    ReportedRun,
    Run,
    Submission,
    aggregate_typical_errors,
    build_timeline,
    evaluate_flags,
    extract_failures,
    flag_rules,
    normalize_message,
)

T0 = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def report(*collections):
    return {"result": "FAILED", "tests": list(collections)}


def collection(name, *subs, result="FAILED", message=None):
    return {"name": name, "result": result, "resultMessage": message, "tests": list(subs)}


def sub(name, result="FAILED", message=None):
    return {"name": name, "result": result, "resultMessage": message}


# --- normalization -----------------------------------------------------------


def test_numbers_and_values_collapse_into_one_group():
    a = normalize_message("AssertionError: assert 3 == 4")
    b = normalize_message("AssertionError: assert 17.5 == -2")
    assert a == b == "AssertionError: assert <n> == <n>"


def test_identifiers_in_quotes_are_kept_because_they_name_the_problem():
    assert normalize_message("NameError: name 'np' is not defined") == (
        "NameError: name 'np' is not defined"
    )
    assert normalize_message("Expected 'hello world' but got 'helo'") == (
        "Expected <str> but got 'helo'"
    )


def test_paths_and_addresses_are_replaced():
    msg = 'File "/tmp/run-81/student/main.py:12" object at 0x7f3a2b'
    assert normalize_message(msg) == 'File "<path>" object at <addr>'


def test_multiline_message_keeps_the_error_line():
    tb = "Traceback (most recent call last):\n  line 3\nE   ZeroDivisionError: division by zero\n"
    assert normalize_message(tb) == "ZeroDivisionError: division by zero"


def test_empty_message_has_a_placeholder():
    assert normalize_message(None) == "(no message)"
    assert normalize_message("   ") == "(no message)"


def test_long_messages_are_cut():
    assert len(normalize_message("x" * 1000)) == 300


# --- report parsing ----------------------------------------------------------


def test_extract_failures_walks_failing_subtests_only():
    r = report(
        collection("variables", sub("x", "PASSED"), sub("y", message="y wrong")),
        collection("plots", sub("figure", "PASSED"), result="PASSED"),
    )
    assert extract_failures(r) == [("variables / y", "y wrong")]


def test_crashed_collection_without_subtests_is_reported_as_itself():
    r = report({"name": "syntax", "status": "CRASHED", "statusMessage": "SyntaxError: invalid syntax"})
    assert extract_failures(r) == [("syntax", "SyntaxError: invalid syntax")]


def test_missing_or_malformed_report_yields_nothing():
    assert extract_failures(None) == []
    assert extract_failures({"tests": ["nonsense"]}) == []


# --- aggregation -------------------------------------------------------------


def _run(rid, member, rep, minutes, content="c1"):
    return ReportedRun(
        result_id=rid,
        course_member_id=member,
        course_content_id=content,
        created_at=at(minutes),
        report=rep,
        student_name=f"Student {member}",
        course_content_title="Loops",
    )


def test_typical_errors_count_students_and_occurrences():
    runs = [
        _run("r1", "a", report(collection("t", sub("sum", message="assert 1 == 2"))), 0),
        _run("r2", "a", report(collection("t", sub("sum", message="assert 5 == 2"))), 10),
        _run("r3", "b", report(collection("t", sub("sum", message="assert 9 == 3"))), 20),
        _run("r4", "c", report(collection("t", sub("mean", message="ZeroDivisionError: division by zero"))), 30),
        _run("r5", "c", None, 40),
    ]
    errors = aggregate_typical_errors(runs)
    assert [(e.test_name, e.affected_students, e.occurrences) for e in errors] == [
        ("t / sum", 2, 3),
        ("t / mean", 1, 1),
    ]
    top = errors[0]
    assert top.message == "assert <n> == <n>"
    assert top.first_seen_at == at(0) and top.last_seen_at == at(20)
    # One example per student, newest first, carrying the raw message.
    assert [(e.result_id, e.message) for e in top.examples] == [
        ("r3", "assert 9 == 3"),
        ("r2", "assert 5 == 2"),
    ]


def test_same_failure_twice_in_one_run_counts_once():
    rep = report(
        collection("t", sub("sum", message="assert 1 == 2")),
        collection("t", sub("sum", message="assert 3 == 4")),
    )
    (only,) = aggregate_typical_errors([_run("r1", "a", rep, 0)])
    assert only.occurrences == 1


def test_errors_are_kept_apart_per_assignment():
    rep = report(collection("t", sub("sum", message="boom")))
    errors = aggregate_typical_errors([_run("r1", "a", rep, 0, "c1"), _run("r2", "b", rep, 0, "c2")])
    assert sorted(e.course_content_id for e in errors) == ["c1", "c2"]


# --- timeline ----------------------------------------------------------------


def test_timeline_from_timestamps():
    runs = [
        Run("r1", "c1", at(0), 0.2, 0),
        Run("r2", "c1", at(10), 0.5, 0),
        Run("r3", "c1", at(25), 1.0, 0),
        Run("r4", "c1", at(24 * 60 + 25), 1.0, 0),  # next day, new session
    ]
    subs = [Submission("s1", "c1", at(30))]
    due = at(90)
    tl = build_timeline("c1", "Loops", runs, subs, due_at=due, session_gap_minutes=30)
    assert tl.test_runs == 4 and tl.submissions == 1
    assert tl.first_activity_at == at(0)
    assert tl.last_activity_at == at(24 * 60 + 25)
    assert tl.first_full_score_at == at(25)
    assert tl.best_grade == 1.0 and tl.latest_grade == 1.0
    assert tl.active_days == 2
    assert tl.median_gap_minutes == 15.0
    # 10 + 15 counted, the overnight gap is not.
    assert tl.estimated_active_minutes == 25.0
    assert tl.hours_before_due == 1.0


def test_timeline_without_runs_has_no_estimate():
    tl = build_timeline("c1", None, [], [Submission("s1", "c1", at(0))])
    assert tl.test_runs == 0
    assert tl.median_gap_minutes is None and tl.estimated_active_minutes is None
    assert tl.hours_before_due is None


# --- flags -------------------------------------------------------------------


def codes(flags):
    return sorted(f.code for f in flags)


def test_many_failed_attempts_without_full_score_is_a_warning():
    runs = {"c1": [Run(f"r{i}", "c1", at(i), 0.4, 0) for i in range(10)]}
    flags = evaluate_flags(runs, {}, {"c1": "Loops"}, now=at(60))
    (flag,) = [f for f in flags if f.code == "many_failed_attempts"]
    assert flag.severity == "warning"
    assert "10 test runs" in flag.reason and flag.course_content_title == "Loops"


def test_many_failed_attempts_then_success_is_info():
    runs = {"c1": [Run(f"r{i}", "c1", at(i), 0.4, 0) for i in range(12)] + [Run("ok", "c1", at(20), 1.0, 0)]}
    (flag,) = [f for f in evaluate_flags(runs, {}, {}, now=at(60)) if f.code == "many_failed_attempts"]
    assert flag.severity == "info" and "12 test runs" in flag.reason


def test_nine_failed_runs_do_not_flag():
    runs = {"c1": [Run(f"r{i}", "c1", at(i), 0.4, 0) for i in range(9)]}
    assert "many_failed_attempts" not in codes(evaluate_flags(runs, {}, {}, now=at(60)))


def test_sudden_jump_needs_consecutive_runs():
    jump = {"c1": [Run("a", "c1", at(0), 0.1, 0), Run("b", "c1", at(3), 1.0, 0)]}
    gradual = {"c1": [Run("a", "c1", at(0), 0.1, 0), Run("m", "c1", at(1), 0.6, 0), Run("b", "c1", at(3), 1.0, 0)]}
    (flag,) = [f for f in evaluate_flags(jump, {}, {}, now=at(10)) if f.code == "sudden_jump"]
    assert "From 10% to 100%" in flag.reason and "3 min" in flag.reason
    assert "sudden_jump" not in codes(evaluate_flags(gradual, {}, {}, now=at(10)))


def test_deadline_rules_only_with_a_due_date():
    subs = {"c1": [Submission("s", "c1", at(0))]}
    assert codes(evaluate_flags({}, subs, {}, now=at(1))) == []
    assert codes(evaluate_flags({}, subs, {}, now=at(1), due_at=at(30))) == ["last_minute"]
    assert codes(evaluate_flags({}, subs, {}, now=at(1), due_at=at(-90))) == ["late_submission"]
    assert codes(evaluate_flags({}, subs, {}, now=at(1), due_at=at(600))) == []


def test_inactivity_and_low_progress():
    now = at(0) + timedelta(days=20)
    runs = {"c1": [Run("r", "c1", at(0), 1.0, 0)]}
    flags = evaluate_flags(runs, {}, {}, now=now, submitted_assignments=1, submittable_assignments=10)
    assert codes(flags) == ["inactive", "low_progress"]
    by = {f.code: f for f in flags}
    assert "20 days ago" in by["inactive"].reason
    assert "1 of 10" in by["low_progress"].reason
    assert codes(evaluate_flags({}, {}, {}, now=now)) == ["inactive"]


def test_every_flag_code_has_a_rule_description():
    described = {r.code for r in flag_rules(DEFAULT_THRESHOLDS, None)}
    assert described == {
        "many_failed_attempts",
        "sudden_jump",
        "inactive",
        "low_progress",
        "last_minute",
        "late_submission",
    }

"""
Lecturer analytics: typical errors, attempt timelines and rule-based flags.

Everything is derived from rows the platform already stores — ``result``
(one per test run, with its test report in object storage),
``submission_artifact`` (``submit=True`` marks an official submission) and
``submission_grade`` (human gradings with feedback). Nothing new is tracked.

The pure functions at the top hold all the rules so they can be unit-tested
without a database; the loaders at the bottom only fetch rows and check
permissions.
"""

from __future__ import annotations

import asyncio
import logging
import re
import statistics
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import (
    Any,
)

from computor_types.course_analytics import (
    ActivityEvent,
    AttemptTimeline,
    CourseFlagsGet,
    FlagReason,
    FlagRule,
    StudentActivityGet,
    StudentFlags,
    TypicalError,
    TypicalErrorExample,
    TypicalErrorsGet,
)
from computor_types.grading import GradingStatus
from computor_types.tasks import ResultStatus, map_int_to_task_status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from computor_backend.exceptions import ForbiddenException, NotFoundException
from computor_backend.model.artifact import SubmissionArtifact, SubmissionGrade
from computor_backend.model.auth import User
from computor_backend.model.course import (
    CourseContent,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.result import Result
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.roles import CourseRole

logger = logging.getLogger(__name__)

# A test run at or above this grade counts as "full score".
FULL_SCORE = 0.999

# Stored run states that can carry a test report with failures: completed,
# failed and crashed (e.g. a syntax error before any test ran).
_REPORT_STATUSES = [
    int(ResultStatus.FINISHED),
    int(ResultStatus.FAILED),
    int(ResultStatus.CRASHED),
]


# ---------------------------------------------------------------------------
# Rule thresholds
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FlagThresholds:
    """Thresholds of the flag rules. Returned with every response so the UI
    can say exactly why a student was flagged."""

    failed_attempts: int = 10
    last_minute_hours: float = 2.0
    jump_from_grade: float = 0.3
    inactive_days: int = 14
    low_progress_percent: float = 25.0


DEFAULT_THRESHOLDS = FlagThresholds()
DEFAULT_SESSION_GAP_MINUTES = 30


def flag_rules(thresholds: FlagThresholds, due_at: datetime | None) -> list[FlagRule]:
    """Human-readable description of every rule, in the order they are applied."""
    t = thresholds
    rules = [
        FlagRule(
            code="many_failed_attempts",
            title="Many failed attempts",
            description=(
                f"At least {t.failed_attempts} test runs on one assignment without reaching "
                "the full score (counted up to the first full-score run)."
            ),
        ),
        FlagRule(
            code="sudden_jump",
            title="Sudden jump to full score",
            description=(
                f"A test run reached the full score directly after a run at or below "
                f"{round(t.jump_from_grade * 100)}% on the same assignment. Worth a look; "
                "not evidence of misconduct on its own."
            ),
        ),
        FlagRule(
            code="inactive",
            title="Inactive",
            description=f"No test run and no submission in the last {t.inactive_days} days.",
        ),
        FlagRule(
            code="low_progress",
            title="Low progress",
            description=(
                f"Submitted fewer than {round(t.low_progress_percent)}% of the submittable assignments."
            ),
        ),
    ]
    due_note = (
        "Uses the due date set on the page; the platform does not store per-assignment deadlines."
        if due_at
        else "Only evaluated when a due date is set on the page."
    )
    rules += [
        FlagRule(
            code="last_minute",
            title="Last-minute submission",
            description=f"Last submission less than {t.last_minute_hours:g} h before the due date. {due_note}",
        ),
        FlagRule(
            code="late_submission",
            title="Submission after the due date",
            description=f"At least one submission after the due date. {due_note}",
        ),
    ]
    return rules


# ---------------------------------------------------------------------------
# Typical errors: report parsing and message normalization
# ---------------------------------------------------------------------------

_ERROR_LINE = re.compile(r"^\s*(?:E\s+)?[A-Za-z_][\w.]*(?:Error|Exception|Failure)\b.*$")
_ADDR = re.compile(r"\b0x[0-9a-fA-F]+\b")
_PATH = re.compile(r"(?:[A-Za-z]:)?(?:[\\/][\w.\-]+){2,}(?::\d+)?")
_QUOTED = re.compile(r"'([^'\n]{0,200})'|\"([^\"\n]{0,200})\"")
# Plain identifiers, and placeholders already substituted (a quoted path).
_IDENT = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]{0,40}|<[a-z]+>)$")
_NUMBER = re.compile(r"(?<![\w<])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w>])")
_SPACE = re.compile(r"\s+")
MAX_MESSAGE_LENGTH = 300


def _pick_line(message: str) -> str:
    """The most telling line of a (possibly multi-line) message: the first
    line that names an error/exception, else the first non-empty line."""
    lines = [line for line in message.splitlines() if line.strip()]
    if not lines:
        return ""
    for line in lines:
        if _ERROR_LINE.match(line):
            return line.strip().removeprefix("E ").strip()
    return lines[0].strip()


def normalize_message(message: str | None) -> str:
    """Normalize an error message so that runs failing for the same reason group together.

    Rules, applied in order (each one is visible in the result):
    1. keep the first line that names an error/exception, else the first non-empty line;
    2. memory addresses -> ``<addr>``, file paths -> ``<path>``;
    3. quoted values -> ``<str>``, except plain identifiers such as ``'np'``,
       which usually name the actual problem;
    4. numbers -> ``<n>``;
    5. collapse whitespace and cut to 300 characters.
    """
    if not message or not message.strip():
        return "(no message)"
    text = _pick_line(message)
    text = _ADDR.sub("<addr>", text)
    text = _PATH.sub("<path>", text)

    def _quoted(match: re.Match) -> str:
        value = match.group(1) if match.group(1) is not None else match.group(2)
        return match.group(0) if _IDENT.match(value or "") else "<str>"

    text = _QUOTED.sub(_quoted, text)
    text = _NUMBER.sub("<n>", text)
    text = _SPACE.sub(" ", text).strip()
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[: MAX_MESSAGE_LENGTH - 1] + "…"
    return text or "(no message)"


def _node_message(node: dict[str, Any]) -> str | None:
    for key in ("resultMessage", "statusMessage", "details"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _is_failed(node: dict[str, Any]) -> bool:
    result = str(node.get("result") or "").upper()
    status = str(node.get("status") or "").upper()
    return result == "FAILED" or status in {"FAILED", "CRASHED", "TIMEDOUT"}


def extract_failures(report: dict[str, Any] | None) -> list[tuple[str, str]]:
    """Failing leaves of a test report as ``(test name, raw message)``.

    A collection whose own result is FAILED but that lists no failing test
    (a crash, a timeout, a syntax error before any test ran) is reported as
    a failure of the collection itself; so is a whole report that failed
    without any collection.
    """
    if not isinstance(report, dict):
        return []
    failures: list[tuple[str, str]] = []
    collections = report.get("tests") or []
    for idx, main in enumerate(collections):
        if not isinstance(main, dict):
            continue
        main_name = str(main.get("name") or f"Test {idx + 1}")
        failing_subs = [
            sub for sub in (main.get("tests") or []) if isinstance(sub, dict) and _is_failed(sub)
        ]
        for sub_idx, sub in enumerate(failing_subs):
            sub_name = str(sub.get("name") or f"#{sub_idx + 1}")
            failures.append((f"{main_name} / {sub_name}", _node_message(sub) or ""))
        if not failing_subs and _is_failed(main):
            failures.append((main_name, _node_message(main) or ""))
    if not failures and not collections and _is_failed(report):
        failures.append(("(whole test run)", _node_message(report) or ""))
    return failures


@dataclass
class ReportedRun:
    """A failing test run together with its stored report."""

    result_id: str
    course_member_id: str
    course_content_id: str
    created_at: datetime | None
    report: dict[str, Any] | None
    student_name: str | None = None
    course_content_title: str | None = None


def aggregate_typical_errors(runs: Iterable[ReportedRun], max_examples: int = 3) -> list[TypicalError]:
    """Group failing tests by (assignment, test, normalized message).

    A run that fails the same test twice in one report counts once. Groups
    are ordered by affected students, then occurrences.
    """
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for run in runs:
        seen_in_run = set()
        for test_name, raw in extract_failures(run.report):
            normalized = normalize_message(raw)
            key = (run.course_content_id, test_name, normalized)
            if key in seen_in_run:
                continue
            seen_in_run.add(key)
            g = groups.setdefault(
                key,
                {
                    "title": run.course_content_title,
                    "occurrences": 0,
                    "students": set(),
                    "first": None,
                    "last": None,
                    "examples": [],
                },
            )
            g["occurrences"] += 1
            g["students"].add(run.course_member_id)
            if run.created_at is not None:
                g["first"] = run.created_at if g["first"] is None else min(g["first"], run.created_at)
                g["last"] = run.created_at if g["last"] is None else max(g["last"], run.created_at)
            g["examples"].append(
                TypicalErrorExample(
                    result_id=run.result_id,
                    course_member_id=run.course_member_id,
                    student_name=run.student_name,
                    created_at=run.created_at,
                    message=(raw.strip()[:2000] or None),
                )
            )

    _epoch = datetime.min.replace(tzinfo=timezone.utc)
    out: list[TypicalError] = []
    for (content_id, test_name, normalized), g in groups.items():
        examples = sorted(g["examples"], key=lambda e: e.created_at or _epoch, reverse=True)
        # One example per student first, so the examples show the spread.
        picked: list[TypicalErrorExample] = []
        seen_students = set()
        for e in examples:
            if e.course_member_id not in seen_students:
                picked.append(e)
                seen_students.add(e.course_member_id)
            if len(picked) >= max_examples:
                break
        out.append(
            TypicalError(
                course_content_id=content_id,
                course_content_title=g["title"],
                test_name=test_name,
                message=normalized,
                occurrences=g["occurrences"],
                affected_students=len(g["students"]),
                first_seen_at=g["first"],
                last_seen_at=g["last"],
                examples=picked,
            )
        )
    out.sort(key=lambda e: (-e.affected_students, -e.occurrences, e.test_name, e.message))
    return out


# ---------------------------------------------------------------------------
# Attempt timelines and flags
# ---------------------------------------------------------------------------


@dataclass
class Run:
    result_id: str
    course_content_id: str
    at: datetime
    grade: float | None
    status: int | None
    artifact_id: str | None = None


@dataclass
class Submission:
    artifact_id: str
    course_content_id: str
    at: datetime


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def build_timeline(
    course_content_id: str,
    title: str | None,
    runs: Sequence[Run],
    submissions: Sequence[Submission],
    due_at: datetime | None = None,
    session_gap_minutes: int = DEFAULT_SESSION_GAP_MINUTES,
) -> AttemptTimeline:
    """Attempt timeline of one student on one assignment, from timestamps only."""
    runs = sorted(runs, key=lambda r: r.at)
    subs = sorted(submissions, key=lambda s: s.at)
    times = sorted([r.at for r in runs] + [s.at for s in subs])

    gaps = [(b.at - a.at).total_seconds() / 60.0 for a, b in zip(runs, runs[1:])]
    median_gap = round(statistics.median(gaps), 1) if gaps else None
    active = None
    if gaps:
        active = round(sum(g for g in gaps if g <= session_gap_minutes), 1)

    graded = [r.grade for r in runs if r.grade is not None]
    first_full = next((r.at for r in runs if r.grade is not None and r.grade >= FULL_SCORE), None)
    latest_grade = next((r.grade for r in reversed(runs) if r.grade is not None), None)

    hours_before_due = None
    if due_at is not None and subs:
        hours_before_due = round((due_at - subs[-1].at).total_seconds() / 3600.0, 2)

    return AttemptTimeline(
        course_content_id=course_content_id,
        course_content_title=title,
        test_runs=len(runs),
        submissions=len(subs),
        first_activity_at=times[0] if times else None,
        last_activity_at=times[-1] if times else None,
        first_submission_at=subs[0].at if subs else None,
        last_submission_at=subs[-1].at if subs else None,
        first_full_score_at=first_full,
        best_grade=max(graded) if graded else None,
        latest_grade=latest_grade,
        active_days=len({t.astimezone(timezone.utc).date() for t in times}),
        median_gap_minutes=median_gap,
        estimated_active_minutes=active,
        hours_before_due=hours_before_due,
    )


def _pct(value: float) -> str:
    return f"{round(value * 100)}%"


def evaluate_flags(
    runs_by_content: dict[str, Sequence[Run]],
    submissions_by_content: dict[str, Sequence[Submission]],
    titles: dict[str, str | None],
    now: datetime,
    due_at: datetime | None = None,
    submitted_assignments: int | None = None,
    submittable_assignments: int | None = None,
    thresholds: FlagThresholds = DEFAULT_THRESHOLDS,
) -> list[FlagReason]:
    """Apply every rule to one student. Each flag carries its reason."""
    t = thresholds
    flags: list[FlagReason] = []

    for content_id in sorted(runs_by_content, key=lambda c: titles.get(c) or c):
        runs = sorted(runs_by_content[content_id], key=lambda r: r.at)
        title = titles.get(content_id)

        failed_before_full = 0
        reached_full = False
        for r in runs:
            if r.grade is not None and r.grade >= FULL_SCORE:
                reached_full = True
                break
            failed_before_full += 1
        if failed_before_full >= t.failed_attempts:
            flags.append(
                FlagReason(
                    code="many_failed_attempts",
                    severity="info" if reached_full else "warning",
                    title="Many failed attempts",
                    reason=(
                        f"{failed_before_full} test runs without full score"
                        + (" before reaching it." if reached_full else "; full score not reached yet.")
                    ),
                    course_content_id=content_id,
                    course_content_title=title,
                )
            )

        for prev, cur in zip(runs, runs[1:]):
            if (
                prev.grade is not None
                and cur.grade is not None
                and prev.grade <= t.jump_from_grade
                and cur.grade >= FULL_SCORE
            ):
                minutes = (cur.at - prev.at).total_seconds() / 60.0
                flags.append(
                    FlagReason(
                        code="sudden_jump",
                        severity="info",
                        title="Sudden jump to full score",
                        reason=(
                            f"From {_pct(prev.grade)} to {_pct(cur.grade)} between two consecutive "
                            f"test runs {minutes:.0f} min apart."
                        ),
                        course_content_id=content_id,
                        course_content_title=title,
                    )
                )
                break

    if due_at is not None:
        for content_id in sorted(submissions_by_content, key=lambda c: titles.get(c) or c):
            subs = sorted(submissions_by_content[content_id], key=lambda s: s.at)
            if not subs:
                continue
            title = titles.get(content_id)
            late = [s for s in subs if s.at > due_at]
            if late:
                hours = (late[0].at - due_at).total_seconds() / 3600.0
                flags.append(
                    FlagReason(
                        code="late_submission",
                        severity="warning",
                        title="Submission after the due date",
                        reason=f"{len(late)} submission(s) after the due date; the first {hours:.1f} h late.",
                        course_content_id=content_id,
                        course_content_title=title,
                    )
                )
                continue
            hours_before = (due_at - subs[-1].at).total_seconds() / 3600.0
            if hours_before < t.last_minute_hours:
                flags.append(
                    FlagReason(
                        code="last_minute",
                        severity="info",
                        title="Last-minute submission",
                        reason=f"Last submission {hours_before * 60:.0f} min before the due date.",
                        course_content_id=content_id,
                        course_content_title=title,
                    )
                )

    all_times = [r.at for rs in runs_by_content.values() for r in rs] + [
        s.at for ss in submissions_by_content.values() for s in ss
    ]
    last = max(all_times) if all_times else None
    if last is None:
        flags.append(
            FlagReason(
                code="inactive",
                severity="warning",
                title="Inactive",
                reason="No test run and no submission so far.",
            )
        )
    elif now - last > timedelta(days=t.inactive_days):
        flags.append(
            FlagReason(
                code="inactive",
                severity="warning",
                title="Inactive",
                reason=f"Last test run or submission {(now - last).days} days ago.",
            )
        )

    if submittable_assignments and submitted_assignments is not None:
        percent = 100.0 * submitted_assignments / submittable_assignments
        if percent < t.low_progress_percent:
            flags.append(
                FlagReason(
                    code="low_progress",
                    severity="warning",
                    title="Low progress",
                    reason=(
                        f"Submitted {submitted_assignments} of {submittable_assignments} "
                        f"assignments ({percent:.0f}%)."
                    ),
                )
            )

    return flags


# ---------------------------------------------------------------------------
# Loaders (database + object storage)
# ---------------------------------------------------------------------------


def _require_course_role(permissions: Principal, course_id: str, role: str, db: Session) -> None:
    if permissions.is_admin:
        return
    allowed = (
        check_course_permissions(permissions, CourseMember, role, db)
        .filter(
            CourseMember.course_id == course_id,
            CourseMember.user_id == permissions.get_user_id(),
        )
        .first()
    )
    if not allowed:
        raise ForbiddenException(
            detail="Course analytics require the lecturer role or higher in this course."
        )


def _display_name(given: str | None, family: str | None, email: str | None = None) -> str | None:
    name = f"{given or ''} {family or ''}".strip()
    return name or email or None


def _grade(result_grade: float | None, legacy: float | None) -> float | None:
    return result_grade if result_grade is not None else legacy


def _status_slug(status: int | None) -> str | None:
    if status is None:
        return None
    try:
        return map_int_to_task_status(status).value
    except Exception:  # pragma: no cover - unknown legacy values
        return str(status)


def _grading_slug(status: int | None) -> str | None:
    try:
        return GradingStatus(status).name.lower() if status is not None else None
    except ValueError:
        return None


def _student_rows(db: Session, course_id: str) -> dict[str, dict[str, Any]]:
    from computor_backend.repositories.course_member_gradings import (
        CourseMemberGradingsRepository,
    )

    rows = CourseMemberGradingsRepository(db).get_all_course_members_with_students_role(course_id)
    return {r["course_member_id"]: r for r in rows}


def _content_titles(db: Session, course_id: str) -> dict[str, str | None]:
    rows = db.query(CourseContent.id, CourseContent.title, CourseContent.path).filter(
        CourseContent.course_id == course_id
    )
    return {str(r.id): (r.title or str(r.path)) for r in rows}


ReportFetcher = Callable[[str], Awaitable[dict[str, Any] | None]]


def _fetch_blocking(result_id: str) -> dict[str, Any] | None:
    from computor_backend.services.result_storage import retrieve_result_json

    return asyncio.run(retrieve_result_json(result_id))


async def _default_fetch(result_id: str) -> dict[str, Any] | None:
    # The MinIO client is synchronous: awaiting it directly would run every
    # download of a large scan on the event loop and stall all other requests.
    return await asyncio.to_thread(_fetch_blocking, result_id)


async def get_typical_errors(
    course_id: str,
    permissions: Principal,
    db: Session,
    course_content_id: str | None = None,
    max_results: int = 300,
    fetch_report: ReportFetcher | None = None,
) -> TypicalErrorsGet:
    """Typical errors over the newest ``max_results`` imperfect student test runs."""
    _require_course_role(permissions, course_id, CourseRole.LECTURER, db)
    students = _student_rows(db, course_id)
    titles = _content_titles(db, course_id)
    if course_content_id and course_content_id not in titles:
        raise NotFoundException(detail="Assignment not found in this course")

    query = (
        db.query(
            Result.id,
            Result.course_member_id,
            Result.course_content_id,
            Result.created_at,
        )
        .join(CourseContent, CourseContent.id == Result.course_content_id)
        .filter(
            CourseContent.course_id == course_id,
            Result.course_member_id.in_(list(students) or [None]),
            Result.status.in_(_REPORT_STATUSES),
            or_(Result.grade.is_(None), Result.grade < FULL_SCORE),
        )
    )
    if course_content_id:
        query = query.filter(Result.course_content_id == course_content_id)
    rows = query.order_by(Result.created_at.desc()).limit(max_results + 1).all()
    truncated = len(rows) > max_results
    rows = rows[:max_results]

    fetch = fetch_report or _default_fetch
    # Below the MinIO client's default connection pool size (10).
    semaphore = asyncio.Semaphore(8)

    async def _load(row) -> ReportedRun:
        async with semaphore:
            report = await fetch(str(row.id))
        student = students.get(str(row.course_member_id), {})
        return ReportedRun(
            result_id=str(row.id),
            course_member_id=str(row.course_member_id),
            course_content_id=str(row.course_content_id),
            created_at=_utc(row.created_at),
            report=report,
            student_name=_display_name(
                student.get("given_name"), student.get("family_name"), student.get("username")
            ),
            course_content_title=titles.get(str(row.course_content_id)),
        )

    runs = await asyncio.gather(*(_load(r) for r in rows))
    return TypicalErrorsGet(
        course_id=str(course_id),
        course_content_id=str(course_content_id) if course_content_id else None,
        results_scanned=len(runs),
        results_without_report=sum(1 for r in runs if r.report is None),
        truncated=truncated,
        errors=aggregate_typical_errors(runs),
    )


def _member_activity(
    db: Session, course_id: str, member_ids: Sequence[str]
) -> tuple[dict[str, list[Run]], dict[str, list[Submission]], dict[str, set]]:
    """Runs and official submissions of the given members, keyed by member.

    A run counts for every member of the submission group it ran in (team
    work), and for its own member when it has no group.
    """
    runs: dict[str, list[Run]] = defaultdict(list)
    subs: dict[str, list[Submission]] = defaultdict(list)
    submit_artifacts: dict[str, set] = defaultdict(set)
    if not member_ids:
        return runs, subs, submit_artifacts

    group_rows = (
        db.query(SubmissionGroupMember.submission_group_id, SubmissionGroupMember.course_member_id)
        .join(SubmissionGroup, SubmissionGroup.id == SubmissionGroupMember.submission_group_id)
        .filter(
            SubmissionGroup.course_id == course_id,
            SubmissionGroupMember.course_member_id.in_(member_ids),
        )
        .all()
    )
    members_of_group: dict[str, list[str]] = defaultdict(list)
    for g in group_rows:
        members_of_group[str(g.submission_group_id)].append(str(g.course_member_id))

    result_rows = (
        db.query(
            Result.id,
            Result.course_member_id,
            Result.submission_group_id,
            Result.course_content_id,
            Result.created_at,
            Result.grade,
            Result.result,
            Result.status,
            Result.submission_artifact_id,
        )
        .join(CourseContent, CourseContent.id == Result.course_content_id)
        .filter(
            CourseContent.course_id == course_id,
            or_(
                Result.course_member_id.in_(member_ids),
                Result.submission_group_id.in_(list(members_of_group) or [None]),
            ),
        )
        .all()
    )
    for r in result_rows:
        owners = members_of_group.get(str(r.submission_group_id)) if r.submission_group_id else None
        if not owners:
            owners = [str(r.course_member_id)] if str(r.course_member_id) in member_ids else []
        run = Run(
            result_id=str(r.id),
            course_content_id=str(r.course_content_id),
            at=_utc(r.created_at),
            grade=_grade(r.grade, r.result),
            status=r.status,
            artifact_id=str(r.submission_artifact_id) if r.submission_artifact_id else None,
        )
        for m in owners:
            runs[m].append(run)

    if members_of_group:
        artifact_rows = (
            db.query(
                SubmissionArtifact.id,
                SubmissionArtifact.submission_group_id,
                SubmissionArtifact.created_at,
                SubmissionGroup.course_content_id,
            )
            .join(SubmissionGroup, SubmissionGroup.id == SubmissionArtifact.submission_group_id)
            .filter(
                SubmissionArtifact.submission_group_id.in_(list(members_of_group)),
                SubmissionArtifact.submit.is_(True),
            )
            .all()
        )
        for a in artifact_rows:
            sub = Submission(
                artifact_id=str(a.id),
                course_content_id=str(a.course_content_id),
                at=_utc(a.created_at),
            )
            for m in members_of_group[str(a.submission_group_id)]:
                subs[m].append(sub)
                submit_artifacts[m].add(str(a.id))
    return runs, subs, submit_artifacts


def _by_content(items: Iterable[Any]) -> dict[str, list[Any]]:
    out: dict[str, list[Any]] = defaultdict(list)
    for item in items:
        out[item.course_content_id].append(item)
    return out


def _submittable_ids(db: Session, course_id: str) -> set:
    from computor_backend.repositories.course_member_gradings import (
        CourseMemberGradingsRepository,
    )

    return {
        c["course_content_id"]
        for c in CourseMemberGradingsRepository(db).get_submittable_contents(course_id)
    }


async def get_student_activity(
    course_member_id: str,
    permissions: Principal,
    db: Session,
    due_at: datetime | None = None,
    session_gap_minutes: int = DEFAULT_SESSION_GAP_MINUTES,
    now: datetime | None = None,
) -> StudentActivityGet:
    """Chronological history, attempt timelines and flags of one student."""
    member = db.query(CourseMember).filter(CourseMember.id == course_member_id).first()
    if member is None:
        raise NotFoundException(detail="Course member not found")
    course_id = str(member.course_id)
    _require_course_role(permissions, course_id, CourseRole.LECTURER, db)

    due_at = _utc(due_at)
    now = _utc(now) or datetime.now(timezone.utc)
    member_id = str(member.id)
    titles = _content_titles(db, course_id)
    runs_all, subs_all, submit_artifacts = _member_activity(db, course_id, [member_id])
    runs = runs_all.get(member_id, [])
    subs = subs_all.get(member_id, [])
    runs_by_content = _by_content(runs)
    subs_by_content = _by_content(subs)
    submitted_ids = submit_artifacts.get(member_id, set())

    events: list[ActivityEvent] = [
        ActivityEvent(
            kind="test_run",
            at=r.at,
            course_content_id=r.course_content_id,
            course_content_title=titles.get(r.course_content_id),
            result_id=r.result_id,
            artifact_id=r.artifact_id,
            grade=r.grade,
            status=_status_slug(r.status),
            is_submission=bool(r.artifact_id and r.artifact_id in submitted_ids),
        )
        for r in runs
    ]
    events += [
        ActivityEvent(
            kind="submission",
            at=s.at,
            course_content_id=s.course_content_id,
            course_content_title=titles.get(s.course_content_id),
            artifact_id=s.artifact_id,
            is_submission=True,
        )
        for s in subs
    ]

    if submitted_ids or subs:
        group_artifacts = {s.artifact_id: s.course_content_id for s in subs}
        grade_rows = (
            db.query(
                SubmissionGrade.id,
                SubmissionGrade.artifact_id,
                SubmissionGrade.graded_at,
                SubmissionGrade.grade,
                SubmissionGrade.status,
                SubmissionGrade.comment,
                User.given_name,
                User.family_name,
            )
            .outerjoin(CourseMember, CourseMember.id == SubmissionGrade.graded_by_course_member_id)
            .outerjoin(User, User.id == CourseMember.user_id)
            .filter(SubmissionGrade.artifact_id.in_(list(group_artifacts)))
            .all()
        )
        for g in grade_rows:
            content_id = group_artifacts.get(str(g.artifact_id))
            if content_id is None:
                continue
            events.append(
                ActivityEvent(
                    kind="grading",
                    at=_utc(g.graded_at),
                    course_content_id=content_id,
                    course_content_title=titles.get(content_id),
                    artifact_id=str(g.artifact_id),
                    grade=g.grade,
                    status=_grading_slug(g.status),
                    is_submission=True,
                    feedback=g.comment,
                    graded_by=_display_name(g.given_name, g.family_name),
                )
            )
    events.sort(key=lambda e: e.at, reverse=True)

    content_ids = sorted(set(runs_by_content) | set(subs_by_content), key=lambda c: titles.get(c) or c)
    timelines = [
        build_timeline(
            c,
            titles.get(c),
            runs_by_content.get(c, []),
            subs_by_content.get(c, []),
            due_at=due_at,
            session_gap_minutes=session_gap_minutes,
        )
        for c in content_ids
    ]

    is_student = member.course_role_id == CourseRole.STUDENT.value
    submittable = _submittable_ids(db, course_id) if is_student else set()
    flags = evaluate_flags(
        runs_by_content,
        subs_by_content,
        titles,
        now=now,
        due_at=due_at,
        submitted_assignments=len(submittable & set(subs_by_content)) if is_student else None,
        submittable_assignments=len(submittable) if is_student else None,
    )
    return StudentActivityGet(
        course_member_id=member_id,
        course_id=course_id,
        due_at=due_at,
        session_gap_minutes=session_gap_minutes,
        events=events,
        timelines=timelines,
        flags=flags,
        rules=flag_rules(DEFAULT_THRESHOLDS, due_at),
    )


async def get_course_flags(
    course_id: str,
    permissions: Principal,
    db: Session,
    due_at: datetime | None = None,
    now: datetime | None = None,
) -> CourseFlagsGet:
    """Flags for every student of the course; students without flags are omitted."""
    _require_course_role(permissions, course_id, CourseRole.LECTURER, db)
    due_at = _utc(due_at)
    now = _utc(now) or datetime.now(timezone.utc)
    students = _student_rows(db, course_id)
    titles = _content_titles(db, course_id)
    member_ids = list(students)
    runs_all, subs_all, _ = _member_activity(db, course_id, member_ids)
    submittable = _submittable_ids(db, course_id)

    out: list[StudentFlags] = []
    for member_id in member_ids:
        subs_by_content = _by_content(subs_all.get(member_id, []))
        flags = evaluate_flags(
            _by_content(runs_all.get(member_id, [])),
            subs_by_content,
            titles,
            now=now,
            due_at=due_at,
            submitted_assignments=len(submittable & set(subs_by_content)),
            submittable_assignments=len(submittable),
        )
        if flags:
            s = students[member_id]
            out.append(
                StudentFlags(
                    course_member_id=member_id,
                    student_name=_display_name(s.get("given_name"), s.get("family_name"), s.get("username")),
                    student_id=s.get("student_id"),
                    flags=flags,
                )
            )
    return CourseFlagsGet(
        course_id=str(course_id),
        due_at=due_at,
        rules=flag_rules(DEFAULT_THRESHOLDS, due_at),
        students=out,
    )

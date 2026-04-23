"""Markdown test-report generator for the computor-backend common tests.

Mirrors ``integration-tests/reporting.py`` in structure: hooks into
pytest's lifecycle, accumulates test outcomes, then renders a
human-readable markdown doc at session end. The permission-matrix table
is absent here because these tests are unit-level and don't emit
``matrix_observation`` properties — it's gracefully omitted when no
observations are collected.

Report lands at ``computor-backend/reports/latest.md``.

Loaded via ``pytest_plugins`` in ``conftest.py``.
"""

from __future__ import annotations

import datetime
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

REPORT_TITLE = "Computor Backend Test Report"

# Walk up from this file to the package root: .../tests/reporting.py →
# computor-backend/. That's where we colocate reports/.
_PACKAGE_ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = _PACKAGE_ROOT / "reports"
REPORT_FILE = REPORT_DIR / "latest.md"

OUTCOME_GLYPH = {
    "passed": "✓ PASS",
    "failed": "✗ FAIL",
    "skipped": "⊘ SKIP",
    "error": "⚠ ERROR",
}


@dataclass
class TestRecord:
    nodeid: str
    suite: str
    test_file: str
    test_name: str
    outcome: str
    duration: float
    longrepr: str = ""
    skip_reason: str = ""


@dataclass
class _Accumulator:
    records: list[TestRecord] = field(default_factory=list)
    session_start: float = 0.0


_acc = _Accumulator()


# ---- hooks --------------------------------------------------------------


def pytest_sessionstart(session: pytest.Session) -> None:
    import time

    _acc.records.clear()
    _acc.session_start = time.monotonic()


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.when == "call" or report.outcome in ("failed", "error"):
        for existing in _acc.records:
            if existing.nodeid == report.nodeid:
                if report.outcome in ("failed", "error"):
                    existing.outcome = report.outcome
                    existing.longrepr = str(report.longrepr or "")
                return

        nodeid = report.nodeid
        file_part, _, name_part = nodeid.partition("::")
        file_path = Path(file_part)
        suite = str(file_path.parent) if file_path.parent != Path(".") else ""
        skip_reason = ""
        if report.outcome == "skipped" and isinstance(report.longrepr, tuple) and len(report.longrepr) >= 3:
            skip_reason = str(report.longrepr[2])
        _acc.records.append(
            TestRecord(
                nodeid=nodeid,
                suite=suite,
                test_file=file_path.name,
                test_name=name_part or file_part,
                outcome=report.outcome,
                duration=float(getattr(report, "duration", 0.0)),
                longrepr=str(report.longrepr or "") if report.outcome in ("failed", "error") else "",
                skip_reason=skip_reason,
            )
        )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    import time

    total_duration = time.monotonic() - _acc.session_start
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    content = _render(_acc.records, total_duration)
    REPORT_FILE.write_text(content, encoding="utf-8")
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(f"📝 Backend test report → {REPORT_FILE}")


# ---- rendering ----------------------------------------------------------


def _render(records: list[TestRecord], duration: float) -> str:
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    git_info = _git_info()

    counts: dict[str, int] = defaultdict(int)
    for r in records:
        counts[r.outcome] += 1
    total = len(records)

    lines: list[str] = []
    lines.append(f"# {REPORT_TITLE}")
    lines.append("")
    lines.append(f"**Generated:** {now} · **Duration:** {duration:.2f}s")
    if git_info:
        lines.append(f"**Branch:** `{git_info['branch']}` · **Commit:** `{git_info['short']}` — {git_info['subject']}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Outcome | Count |")
    lines.append("|---|---:|")
    for name in ("passed", "failed", "skipped", "error"):
        if counts.get(name):
            lines.append(f"| {OUTCOME_GLYPH[name]} | {counts[name]} |")
    lines.append(f"| **Total** | **{total}** |")
    lines.append("")

    # Per-suite tables (grouped by file).
    by_suite: dict[str, list[TestRecord]] = defaultdict(list)
    for r in records:
        by_suite[r.suite or "(root)"].append(r)
    for suite_name in sorted(by_suite):
        suite_records = by_suite[suite_name]
        lines.append(f"## {suite_name}")
        lines.append("")
        lines.append("| Test | Result | Duration |")
        lines.append("|---|---|---:|")
        for r in sorted(suite_records, key=lambda x: x.nodeid):
            glyph = OUTCOME_GLYPH.get(r.outcome, r.outcome)
            safe_name = r.test_name.replace("|", "\\|")
            lines.append(f"| `{safe_name}` | {glyph} | {r.duration:.2f}s |")
        lines.append("")

    failing = [r for r in records if r.outcome in ("failed", "error")]
    if failing:
        lines.append("## Failures")
        lines.append("")
        for r in failing:
            lines.append(f"### `{r.nodeid}`")
            lines.append("")
            lines.append("```")
            lines.append(r.longrepr.strip() or "(no traceback)")
            lines.append("```")
            lines.append("")

    skipped = [r for r in records if r.outcome == "skipped"]
    if skipped:
        lines.append("## Skipped")
        lines.append("")
        lines.append("| Test | Reason |")
        lines.append("|---|---|")
        for r in sorted(skipped, key=lambda x: x.nodeid):
            reason = r.skip_reason.replace("\n", " ").replace("|", "\\|")
            lines.append(f"| `{r.nodeid}` | {reason or '—'} |")
        lines.append("")

    return "\n".join(lines) + "\n"


def _git_info() -> dict[str, str]:
    try:
        cwd = Path(__file__).resolve().parent
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd, stderr=subprocess.DEVNULL,
        ).decode().strip()
        short = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=cwd, stderr=subprocess.DEVNULL,
        ).decode().strip()
        subject = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%s"],
            cwd=cwd, stderr=subprocess.DEVNULL,
        ).decode().strip()
        return {"branch": branch, "short": short, "subject": subject}
    except Exception:
        return {}

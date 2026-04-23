"""Markdown test-report generator for the integration suite.

Hooks into pytest's lifecycle, accumulates test outcomes, then at session
end renders a human-readable markdown doc to ``reports/latest.md``. The
permission-matrix suite also stamps a ``matrix_observation`` on each test
via ``record_property``; those observations are cross-tabulated as an
endpoint × role table in the report.

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

REPORT_DIR = Path(__file__).resolve().parent / "reports"
REPORT_FILE = REPORT_DIR / "latest.md"

ROLE_COLUMNS = ("admin", "owner", "maintainer", "lecturer", "tutor", "student", "anon")

OUTCOME_GLYPH = {
    "passed": "✓ PASS",
    "failed": "✗ FAIL",
    "skipped": "⊘ SKIP",
    "error": "⚠ ERROR",
}


@dataclass
class TestRecord:
    nodeid: str
    suite: str  # e.g. "suites/03_permissions"
    test_file: str
    test_name: str  # test_foo[paramid]
    outcome: str
    duration: float
    longrepr: str = ""
    skip_reason: str = ""
    matrix_observations: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class _Accumulator:
    records: list[TestRecord] = field(default_factory=list)
    session_start: float = 0.0


# pytest instantiates hooks at module level; keep one accumulator per run.
_acc = _Accumulator()


# ---- hooks --------------------------------------------------------------


def pytest_sessionstart(session: pytest.Session) -> None:
    import time

    _acc.records.clear()
    _acc.session_start = time.monotonic()


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    # Only record once per test; the "call" phase is the definitive one for
    # passed tests. Failures and errors can come from setup/teardown too, so
    # we keep any failing phase.
    if report.when == "call" or report.outcome in ("failed", "error"):
        # Avoid duplicates if both setup and call report.
        for existing in _acc.records:
            if existing.nodeid == report.nodeid:
                # Upgrade the outcome if the later phase failed.
                if report.outcome in ("failed", "error"):
                    existing.outcome = report.outcome
                    existing.longrepr = str(report.longrepr or "")
                return

        nodeid = report.nodeid
        file_part, _, name_part = nodeid.partition("::")
        file_path = Path(file_part)
        suite = str(file_path.parent) if file_path.parent != Path(".") else ""
        obs = [
            value
            for (name, value) in getattr(report, "user_properties", [])
            if name == "matrix_observation"
        ]
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
                matrix_observations=obs,
            )
        )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    import time

    total_duration = time.monotonic() - _acc.session_start
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    content = _render(_acc.records, total_duration)
    REPORT_FILE.write_text(content, encoding="utf-8")
    # Surface the path so a human running pytest sees where the report went.
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(f"📝 Integration test report → {REPORT_FILE}")


# ---- rendering ----------------------------------------------------------


def _render(records: list[TestRecord], duration: float) -> str:
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    git_info = _git_info()

    counts: dict[str, int] = defaultdict(int)
    for r in records:
        counts[r.outcome] += 1
    total = len(records)

    lines: list[str] = []
    lines.append("# Integration Test Report")
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

    # Permission matrix cross-tab, if any observations present.
    observations = [
        obs for r in records for obs in r.matrix_observations
    ]
    if observations:
        lines.append("## Permission Matrix")
        lines.append("")
        lines.append(
            "Rows = endpoint, columns = role. Each cell is the observed HTTP "
            "status code. ✓ = matches expected, ✗ = mismatch. Missing cells "
            "are not asserted by the current matrix."
        )
        lines.append("")
        lines.append(_render_matrix_table(observations))
        lines.append("")

    # Per-suite tables. Matrix tests are already represented in the cross
    # tab above — excluding them keeps this section focused on the
    # one-off assertions (smoke, auth).
    non_matrix = [r for r in records if not r.matrix_observations]
    by_suite: dict[str, list[TestRecord]] = defaultdict(list)
    for r in non_matrix:
        by_suite[r.suite or "(root)"].append(r)
    for suite_name in sorted(by_suite):
        suite_records = by_suite[suite_name]
        lines.append(f"## {suite_name}")
        lines.append("")
        lines.append("| Test | Result | Duration |")
        lines.append("|---|---|---:|")
        for r in sorted(suite_records, key=lambda x: x.nodeid):
            glyph = OUTCOME_GLYPH.get(r.outcome, r.outcome)
            # Escape pipes in test names so they don't break the table.
            safe_name = r.test_name.replace("|", "\\|")
            lines.append(f"| `{safe_name}` | {glyph} | {r.duration:.2f}s |")
        lines.append("")

    # Failures + errors detail.
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

    # Skipped detail.
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


def _render_matrix_table(observations: list[dict[str, Any]]) -> str:
    # Group observations by (method, path) → {role: (expected, observed)}
    rows: dict[tuple[str, str], dict[str, tuple[int, int]]] = defaultdict(dict)
    for obs in observations:
        key = (obs["method"], obs["path"])
        rows[key][obs["role"]] = (obs["expected"], obs["observed"])

    header = "| Endpoint | " + " | ".join(ROLE_COLUMNS) + " |"
    separator = "|---|" + "|".join(":---:" for _ in ROLE_COLUMNS) + "|"

    body_lines = []
    for (method, path) in sorted(rows.keys()):
        cells = []
        for role in ROLE_COLUMNS:
            pair = rows[(method, path)].get(role)
            if pair is None:
                cells.append("—")
            else:
                expected, observed = pair
                if expected == observed:
                    cells.append(f"✓ {observed}")
                else:
                    cells.append(f"✗ {observed}≠{expected}")
        label = f"`{method} {path}`"
        body_lines.append(f"| {label} | " + " | ".join(cells) + " |")

    return "\n".join([header, separator, *body_lines])


def _git_info() -> dict[str, str]:
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        short = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        subject = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%s"],
            cwd=Path(__file__).resolve().parent,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return {"branch": branch, "short": short, "subject": subject}
    except Exception:
        return {}

"""Optional external plot judge for graphics tests.

A graphics subtest with ``qualification: plotJudge`` whose ``name`` evaluates
to a figure (for example ``figure(1)``) sends the student's and the
reference's figure to the judge service at ``$PLOT_JUDGE_URL`` and passes or
fails with the judge's verdict. The judge decides whether the plot shows the
same content as the reference while tolerating style and wording
(plot-grader, ``plot_grader.judge_server``).

The judge is advisory infrastructure: without ``PLOT_JUDGE_URL``, or when the
service does not answer within ``PLOT_JUDGE_TIMEOUT`` seconds (default 120),
or answers without a verdict, the subtest is SKIPPED, never failed.

Request: POST JSON {"student_png", "reference_png": base64 PNG,
"student_data", "reference_data": {"axes": [...]}}.
Response: JSON {"verdict": "PASS"|"FAIL"|"ERROR", "criteria", "problems",
"differences": [str], "hint": str}.
"""

import base64
import io
import json
import os
import urllib.error
import urllib.request

import pytest

ENV_URL = "PLOT_JUDGE_URL"
ENV_TIMEOUT = "PLOT_JUDGE_TIMEOUT"
DEFAULT_TIMEOUT = 120.0


def figure_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    return buf.getvalue()


def _list(values):
    try:
        return [float(v) for v in values]
    except (TypeError, ValueError):
        return []


def figure_data(fig) -> dict:
    """Axes, labels, limits and line data in plot-grader's extract format."""
    axes = []
    for k, ax in enumerate(fig.axes):
        axes.append({
            "index": k,
            "xlabel": ax.get_xlabel(),
            "ylabel": ax.get_ylabel(),
            "title": ax.get_title(),
            "xlim": list(ax.get_xlim()),
            "ylim": list(ax.get_ylim()),
            "lines": [{"index": j, "xdata": _list(line.get_xdata()),
                       "ydata": _list(line.get_ydata()), "label": line.get_label()}
                      for j, line in enumerate(ax.lines)],
        })
    return {"axes": axes}


def request_verdict(student_fig, reference_fig, url: str, timeout: float) -> dict:
    body = {
        "student_png": base64.b64encode(figure_png(student_fig)).decode(),
        "reference_png": base64.b64encode(figure_png(reference_fig)).decode(),
        "student_data": figure_data(student_fig),
        "reference_data": figure_data(reference_fig),
    }
    req = urllib.request.Request(url, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def failure_message(verdict: dict) -> str:
    parts = ["The plot does not show the same content as the reference."]
    findings = list(verdict.get("problems") or []) + list(verdict.get("differences") or [])
    if findings:
        parts.append("Findings: " + "; ".join(str(f) for f in findings))
    if verdict.get("hint"):
        parts.append("Hint: " + str(verdict["hint"]))
    return " ".join(parts)


def check_plot_judge(val_student, val_reference, name: str) -> None:
    """Pass, fail or skip the current subtest with the judge's verdict."""
    for which, fig in (("student", val_student), ("reference", val_reference)):
        if not hasattr(fig, "savefig"):
            if which == "student":
                pytest.fail(f"`{name}` is not a figure in the student's solution")
            pytest.fail(f"BROKEN EXAMPLE: plotJudge test `{name}` must evaluate to "
                        f"a figure in the reference, e.g. `figure(1)`")
    url = os.environ.get(ENV_URL)
    if not url:
        pytest.skip(f"plot judge not configured (${ENV_URL})")
    try:
        timeout = float(os.environ.get(ENV_TIMEOUT) or DEFAULT_TIMEOUT)
        verdict = request_verdict(val_student, val_reference, url, timeout)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        pytest.skip(f"plot judge unavailable: {exc}")
    result = str(verdict.get("verdict", "")).upper()
    if result == "FAIL":
        pytest.fail(failure_message(verdict))
    if result != "PASS":
        pytest.skip("plot judge gave no verdict")

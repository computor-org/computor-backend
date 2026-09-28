"""End-to-end: `qualification: plotJudge` in a graphics collection.

Runs the real harness (computor-test python run) on a trivial synthetic
example against a stub judge service. The stub is the oracle for what the
judge sees: it answers FAIL exactly when the student's line data differs from
the reference's, so a PASS/FAIL in testSummary.json proves that both figures
and their data reached the judge and that the verdict came back as the
subtest result. Without a reachable judge the subtest must be SKIPPED.
"""

import base64
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REFERENCE = "import matplotlib.pyplot as plt\nplt.plot([1, 2], [1, 4], 'r-')\n" \
            "plt.xlabel('x')\n"
TEST_YAML = """type: python
name: plot judge example
properties:
  tests:
    - type: graphics
      name: figure
      entryPoint: plot.py
      tests:
        - name: figure(1).axes[0].get_xlabel()
        - name: figure(1)
          qualification: plotJudge
"""


class StubJudge(BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        StubJudge.requests.append(body)
        lines = [[(line["xdata"], line["ydata"]) for ax in body[k]["axes"]
                  for line in ax["lines"]] for k in ("student_data", "reference_data")]
        same = lines[0] == lines[1]
        pngs_ok = all(base64.b64decode(body[k])[:4] == b"\x89PNG"
                      for k in ("student_png", "reference_png"))
        reply = {"verdict": "PASS" if same and pngs_ok else "FAIL",
                 "differences": [] if same else ["M2: the curve is steeper"],
                 "hint": "" if same else "check the y values"}
        data = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def judge_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), StubJudge)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/judge"
    server.shutdown()


def run_harness(tmp_path: Path, student_code: str, env_url) -> dict:
    """Run the harness; return {subtest name: (result, resultMessage)}."""
    student, reference = tmp_path / "student", tmp_path / "reference"
    student.mkdir()
    reference.mkdir()
    (student / "plot.py").write_text(student_code)
    (reference / "plot.py").write_text(REFERENCE)
    (tmp_path / "test.yaml").write_text(TEST_YAML)
    spec = tmp_path / "specification.yaml"
    spec.write_text(
        f"executionDirectory: {student}\nstudentDirectory: {student}\n"
        f"referenceDirectory: {reference}\ntestDirectory: {tmp_path}/tp\n"
        f"outputDirectory: {tmp_path}/output\nartifactDirectory: {tmp_path}/art\n"
        "testVersion: v1\nisLocalUsage: true\nstoreGraphicsArtifacts: false\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("PLOT_JUDGE")}
    if env_url:
        env.update(PLOT_JUDGE_URL=env_url, PLOT_JUDGE_TIMEOUT="5")
    cli = Path(sys.executable).parent / "computor-test"
    subprocess.run([str(cli), "python", "run", "-t", str(student), "-T",
                    str(tmp_path / "test.yaml"), "-s", str(spec)],
                   env=env, capture_output=True, text=True, timeout=120)
    summary = json.loads((tmp_path / "output" / "testSummary.json").read_text())
    return {t["name"]: (t["result"], t.get("resultMessage") or "")
            for t in summary["tests"][0]["tests"]}


def test_same_content_passes(tmp_path, judge_url):
    code = REFERENCE.replace("'r-'", "'g--'")  # style differs, data the same
    res = run_harness(tmp_path, code, judge_url)
    assert res["figure(1)"][0] == "PASSED"
    assert res["figure(1).axes[0].get_xlabel()"][0] == "PASSED"


def test_different_data_fails_with_judge_feedback(tmp_path, judge_url):
    res = run_harness(tmp_path, REFERENCE.replace("[1, 4]", "[1, 6]"), judge_url)
    result, message = res["figure(1)"]
    assert result == "FAILED"
    assert "M2: the curve is steeper" in message and "check the y values" in message


def test_without_judge_the_subtest_is_skipped(tmp_path):
    res = run_harness(tmp_path, REFERENCE.replace("[1, 4]", "[1, 6]"), None)
    assert res["figure(1)"][0] == "SKIPPED"


def test_unreachable_judge_is_skipped(tmp_path):
    res = run_harness(tmp_path, REFERENCE, "http://127.0.0.1:9/judge")
    assert res["figure(1)"][0] == "SKIPPED"

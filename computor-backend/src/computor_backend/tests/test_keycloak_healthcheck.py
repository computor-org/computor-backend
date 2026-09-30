"""Behavioral tests for the Keycloak compose readiness probes.

The probes must report healthy only on HTTP 200 from ``<rel>/health/ready``.
During startup/migration Keycloak answers 503 with overall ``DOWN`` while some
individual checks are already ``UP``; a body grep for "UP" wrongly passes that.
"""

import http.server
import os
import shutil
import subprocess
import threading
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[4]
PROBE = REPO / "ops/keycloak/healthcheck.sh"
PREVIEW_COMPOSE = REPO / "ops/docker/docker-compose.preview-state.yaml"
MAIN_COMPOSE = REPO / "ops/docker/docker-compose.keycloak.yaml"

MIXED_503 = (
    '{"status":"DOWN","checks":[{"name":"Graceful Shutdown","status":"UP"},'
    '{"name":"Keycloak Initialized","status":"DOWN"}]}'
)
READY_200 = '{"status":"UP","checks":[{"name":"Keycloak Initialized","status":"UP"}]}'

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


class _Server:
    def __init__(self, status, body):
        self.paths = []
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                outer.paths.append(self.path)
                data = body.encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), H)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def server(request):
    status, body = request.param
    s = _Server(status, body)
    yield s
    s.close()


def _run_probe(port, rel):
    env = dict(os.environ, KC_HEALTH_PROBE_HOST="127.0.0.1",
               KC_HEALTH_PROBE_PORT=str(port), KC_HTTP_RELATIVE_PATH=rel)
    return subprocess.run(["bash", str(PROBE)], env=env, timeout=15).returncode


@pytest.mark.parametrize("server", [(503, MIXED_503)], indirect=True)
def test_probe_rejects_mixed_status_503(server):
    assert _run_probe(server.port, "/auth") != 0


@pytest.mark.parametrize("server", [(200, READY_200)], indirect=True)
@pytest.mark.parametrize("rel,expected", [("/auth", "/auth/health/ready"),
                                          ("/", "/health/ready")])
def test_probe_accepts_200_on_relative_path(server, rel, expected):
    assert _run_probe(server.port, rel) == 0
    assert server.paths == [expected]


def test_probe_fails_when_nothing_listens():
    s = _Server(200, READY_200)
    port = s.port
    s.close()
    assert _run_probe(port, "/auth") != 0


def test_main_compose_uses_the_probe_script():
    svc = yaml.safe_load(MAIN_COMPOSE.read_text())["services"]["keycloak"]
    assert svc["healthcheck"]["test"] == ["CMD", "bash", "/opt/keycloak/healthcheck.sh"]
    assert "../keycloak/healthcheck.sh:/opt/keycloak/healthcheck.sh:ro" in svc["volumes"]


def _preview_probe(port):
    test = yaml.safe_load(PREVIEW_COMPOSE.read_text())["services"]["keycloak"]["healthcheck"]["test"]
    assert test[0] == "CMD-SHELL"
    cmd = test[1].replace("$$", "$").replace("/dev/tcp/127.0.0.1/9000", f"/dev/tcp/127.0.0.1/{port}")
    return subprocess.run(["bash", "-c", cmd], timeout=15).returncode


@pytest.mark.parametrize("server", [(503, MIXED_503)], indirect=True)
def test_preview_probe_rejects_mixed_status_503(server):
    assert _preview_probe(server.port) != 0


@pytest.mark.parametrize("server", [(200, READY_200)], indirect=True)
def test_preview_probe_accepts_200(server):
    assert _preview_probe(server.port) == 0
    assert server.paths == ["/auth/health/ready"]

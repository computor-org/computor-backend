"""The one-shot IdP setup must wait for Keycloak instead of exiting on the
first failed admin authentication (Keycloak may still be starting)."""

import http.server
import importlib.util
import json
import threading
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location(
    "setup_identity_providers", REPO / "ops/keycloak/setup_identity_providers.py")
idp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(idp)


class FlakyKeycloak:
    """Token endpoint answering the given statuses in order, then 200."""

    def __init__(self, failures):
        self.failures = list(failures)
        self.calls = 0
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                outer.calls += 1
                if outer.failures:
                    code, body = outer.failures.pop(0), {"error": "not ready"}
                else:
                    code, body = 200, {"access_token": "tok-123"}
                data = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), H)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class FakeClock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def test_retries_until_keycloak_accepts_admin_auth():
    kc = FlakyKeycloak([503, 404, 401])
    clk = FakeClock()
    try:
        tok = idp.get_admin_token(kc.base, "admin", "pw", timeout_s=300,
                                  sleep=clk.sleep, clock=clk.now)
    finally:
        kc.close()
    assert tok == "tok-123"
    assert kc.calls == 4
    assert clk.sleeps == [2.0, 4.0, 8.0]  # exponential backoff


def test_retries_through_connection_refused():
    kc = FlakyKeycloak([])
    base = kc.base
    kc.close()  # nothing listens yet
    clk = FakeClock()
    calls = {"n": 0}
    real = idp._request

    def fake_request(*a, **k):
        calls["n"] += 1
        if calls["n"] < 3:
            return real(*a, **k)  # real connection refused
        return 200, {"access_token": "late"}

    idp._request, saved = fake_request, real
    try:
        tok = idp.get_admin_token(base, "admin", "pw", timeout_s=300,
                                  sleep=clk.sleep, clock=clk.now)
    finally:
        idp._request = saved
    assert tok == "late" and calls["n"] == 3


def test_gives_up_after_timeout_without_leaking_password():
    kc = FlakyKeycloak([401] * 100)
    clk = FakeClock()
    try:
        with pytest.raises(SystemExit) as ei:
            idp.get_admin_token(kc.base, "admin", "s3cret-pw", timeout_s=60,
                                sleep=clk.sleep, clock=clk.now)
    finally:
        kc.close()
    assert "401" in str(ei.value) and "s3cret-pw" not in str(ei.value)
    assert sum(clk.sleeps) == pytest.approx(60)
    assert max(clk.sleeps) <= 30

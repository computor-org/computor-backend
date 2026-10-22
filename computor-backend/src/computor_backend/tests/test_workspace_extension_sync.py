"""Run the workspace extension sync script against a fake registry and code-server.

The script (ops/coder/templates/*/extension-sync.mjs) runs inside the workspace
with code-server's bundled node. Here it runs with any node >= 18 against a
local HTTP registry and a stub ``code-server`` that records installs, so the
decisions that matter are checked end to end: install only a newer approved
version, verify the sha256, and leave the extension alone on any failure.
"""

import hashlib
import json
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")
TOKEN = "ctp_test-token"


def _templates_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "ops" / "coder" / "templates"
        if candidate.is_dir():
            return candidate
    raise AssertionError("could not locate ops/coder/templates")


SCRIPT = _templates_dir() / "vscode" / "extension-sync.mjs"

FAKE_CODE_SERVER = """#!/bin/sh
# --extensions-dir DIR (--list-extensions --show-versions | --install-extension FILE --force)
state="$FAKE_STATE"
case "$3" in
  --list-extensions) [ -s "$state" ] && echo "computor-org.computor@$(cat "$state")"; echo "ms-python.python@2026.1.0" ;;
  --install-extension)
    echo "$4" >> "$FAKE_INSTALLS"
    v=${4##*-}; echo "${v%.vsix}" > "$state" ;;
esac
"""


class Registry:
    def __init__(self, versions, payloads, status=200):
        self.versions, self.payloads, self.status = versions, payloads, status
        self.requests = []


@pytest.fixture
def registry():
    holder = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            reg = holder["registry"]
            reg.requests.append((self.path, self.headers.get("X-API-Token")))
            if self.headers.get("X-API-Token") != TOKEN:
                self.send_response(401); self.end_headers(); return
            if reg.status != 200:
                self.send_response(reg.status); self.end_headers(); return
            if self.path.startswith("/extensions/computor-org.computor/versions"):
                body = json.dumps({"items": reg.versions, "next_cursor": None}).encode()
            elif self.path.startswith("/extensions/computor-org.computor/download?version=%3D%3D"):
                body = reg.payloads[self.path.rsplit("%3D%3D", 1)[1]]
            else:
                self.send_response(404); self.end_headers(); return
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def configure(versions, payloads=None, status=200):
        holder["registry"] = Registry(versions, payloads or {}, status)
        return holder["registry"], f"http://127.0.0.1:{server.server_port}"

    yield configure
    server.shutdown()


@pytest.fixture
def workspace(tmp_path):
    stub = tmp_path / "code-server"
    stub.write_text(FAKE_CODE_SERVER)
    stub.chmod(0o755)
    state, installs, marker = tmp_path / "state", tmp_path / "installs", tmp_path / "marker.json"

    def sync(backend, installed):
        state.write_text(installed + "\n" if installed else "")
        result = subprocess.run(
            [NODE, str(SCRIPT)],
            env={**os.environ, "COMPUTOR_BACKEND_URL": backend + "/", "COMPUTOR_AUTH_TOKEN": TOKEN,
                 "CODE_SERVER_BIN": str(stub), "FAKE_STATE": str(state), "FAKE_INSTALLS": str(installs),
                 "COMPUTOR_EXTENSION_UPDATE_MARKER": str(marker)},
            capture_output=True, text=True, timeout=60, check=True,
        )
        installed_now = state.read_text().strip()
        return result.stdout, installs.read_text().splitlines() if installs.exists() else [], installed_now, marker

    return sync


def _item(version, payload, yanked=False, sha=None):
    return {"version": version, "yanked": yanked, "sha256": sha or hashlib.sha256(payload).hexdigest()}


def test_newer_approved_version_is_installed_and_announced(registry, workspace):
    new, old = b"vsix 2027.3.4", b"vsix 2026.10.5"
    reg, url = registry([_item("2027.3.4", new), _item("2026.10.5", old), _item("2027.4.0", b"x", yanked=True),
                         _item("2027.5.0-rc.1", b"y")], {"2027.3.4": new})
    out, installs, installed, marker = workspace(url, "2026.10.5")
    assert installed == "2027.3.4"
    assert len(installs) == 1 and installs[0].endswith("-2027.3.4.vsix")
    assert not Path(installs[0]).exists(), "the downloaded VSIX must not be left behind"
    assert json.loads(marker.read_text())["version"] == "2027.3.4"
    assert json.loads(marker.read_text())["previous"] == "2026.10.5"
    assert "installed 2027.3.4 (was 2026.10.5" in out


@pytest.mark.parametrize("installed", ["2027.3.4", "2027.3.5"])
def test_same_or_newer_installed_version_is_kept(registry, workspace, installed):
    reg, url = registry([_item("2027.3.4", b"vsix")], {"2027.3.4": b"vsix"})
    out, installs, now, marker = workspace(url, installed)
    assert installs == [] and now == installed and not marker.exists()
    assert not any("download" in path for path, _ in reg.requests)


def test_checksum_mismatch_keeps_the_installed_extension(registry, workspace):
    reg, url = registry([_item("2027.3.4", b"approved bytes")], {"2027.3.4": b"tampered bytes"})
    out, installs, now, marker = workspace(url, "2026.10.5")
    assert installs == [] and now == "2026.10.5" and not marker.exists()
    assert "WARN sha256 mismatch" in out


@pytest.mark.parametrize("status", [404, 500])
def test_unavailable_registry_keeps_the_installed_extension(registry, workspace, status):
    reg, url = registry([], status=status)
    out, installs, now, _ = workspace(url, "2026.10.5")
    assert installs == [] and now == "2026.10.5"


def test_unreachable_backend_keeps_the_installed_extension(workspace):
    out, installs, now, _ = workspace("http://127.0.0.1:9", "2026.10.5")
    assert installs == [] and now == "2026.10.5" and "WARN" in out


@pytest.mark.parametrize("installed, approved, installs", [
    ("2026.10.5", "2027.3.4", True),    # a newer line
    ("2027.3.9", "2027.3.10", True),    # numeric, not lexical
    ("2027.3.4", "2027.3.4", False),    # same version: the image's copy stays
    ("2027.3.5", "2027.3.4", False),    # an image rebuilt from a newer commit is not shadowed
    ("2027.3.10", "2027.3.9", False),
    ("", "2027.3.4", True),             # extension missing from the image
])
def test_version_order(registry, workspace, installed, approved, installs):
    reg, url = registry([_item(approved, b"vsix")], {approved: b"vsix"})
    _, done, now, _ = workspace(url, installed)
    assert (len(done) == 1) is installs
    assert now == (approved if installs else installed)


def _extension_templates():
    """Every template whose image ships the Computor extension."""
    found = []
    for manifest in sorted(_templates_dir().glob("*/template.json")):
        template = manifest.parent
        sources = json.loads(manifest.read_text()).get("source_repos", [])
        dockerfile = template / "Dockerfile"
        if any("computor-vscode" in s.get("url", "") for s in sources) or (
            dockerfile.is_file() and "computor-vscode" in dockerfile.read_text()
        ):
            found.append(template)
    return found


def test_extension_templates_are_discovered():
    names = {t.name for t in _extension_templates()}
    assert {"vscode", "matlab-vscode"} <= names


@pytest.mark.parametrize("template", _extension_templates(), ids=lambda p: p.name)
def test_every_extension_template_ships_the_in_place_update(template):
    """A template that ships the extension must also keep it up to date in place
    (README.md "Extension updates"): same script, copied into the image, run
    before code-server starts and again periodically."""
    assert (template / "extension-sync.mjs").read_bytes() == SCRIPT.read_bytes()
    assert "COPY extension-sync.mjs /opt/computor/extension-sync.mjs" in (template / "Dockerfile").read_text()
    startup = (template / "startup.sh.tftpl").read_text()
    assert "/usr/lib/code-server/lib/node /opt/computor/extension-sync.mjs" in startup
    assert "export COMPUTOR_EXTENSION_UPDATE_MARKER=" in startup
    # Installed before code-server launches, so a start needs no reload.
    assert startup.index("computor_extension_sync 120") < startup.index("\ncode-server \\")
    assert "while sleep 1800; do" in startup and "computor_extension_sync 600" in startup

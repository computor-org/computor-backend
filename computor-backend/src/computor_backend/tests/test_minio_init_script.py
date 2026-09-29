"""The minio-init one-shot (both compose files) must abort on any chown
failure and mark /data as migrated only after every child succeeded."""

import os
import shutil
import subprocess

import pytest
import yaml

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 4))
COMPOSE_FILES = [
    os.path.join(REPO, "ops", "docker", "docker-compose.base.yaml"),
    os.path.join(REPO, "integration-tests", "docker-compose.integration.yaml"),
]

pytestmark = pytest.mark.skipif(shutil.which("sh") is None, reason="sh required")

# chown/stat stubs: ownership lives in <path>.owner files next to the tree.
CHOWN = r"""#!/bin/sh
[ "$1" = "-R" ] && shift
owner=$1; shift
for p in "$@"; do
  case "$p" in *fail*) echo "chown: $p: Operation not permitted" >&2; exit 1 ;; esac
  echo "$p" >> "$STUB_LOG"; echo "$owner" > "$p.owner.stub" 2>/dev/null || true
done
"""
STAT = r"""#!/bin/sh
p="${@: -1}"
[ -f "$p.owner.stub" ] && cat "$p.owner.stub" || echo "0:0"
"""


def _script(path):
    with open(path, encoding="utf-8") as f:
        service = yaml.safe_load(f)["services"]["minio-init"]
    assert service["entrypoint"] == ["sh", "-c"]
    assert service["user"] == "0:0"
    return service["command"][0].replace("$$", "$")


def _run(tmp_path, script, children):
    data = tmp_path / "data"
    data.mkdir()
    for child in children:
        (data / child).mkdir()
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name, body in (("chown", CHOWN), ("stat", STAT.replace("${@: -1}", "$3"))):
        (bindir / name).write_text(body)
        (bindir / name).chmod(0o755)
    log = tmp_path / "chown.log"
    log.write_text("")
    proc = subprocess.run(
        ["sh", "-c", script.replace("/data", str(data))],
        env={"PATH": f"{bindir}:/usr/bin:/bin", "STUB_LOG": str(log)},
        capture_output=True, text=True,
    )
    return proc, log.read_text().split(), str(data)


@pytest.mark.parametrize("compose", COMPOSE_FILES)
def test_success_marks_parent_last(tmp_path, compose):
    proc, chowned, data = _run(tmp_path, _script(compose), ["bucket", ".minio.sys"])
    assert proc.returncode == 0, proc.stderr
    assert chowned[-1] == data
    assert {os.path.basename(p) for p in chowned[:-1]} == {"bucket", ".minio.sys"}


@pytest.mark.parametrize("compose", COMPOSE_FILES)
def test_chown_failure_aborts_and_leaves_parent_unmarked(tmp_path, compose):
    proc, chowned, data = _run(tmp_path, _script(compose), ["a-fail", "z-bucket"])
    assert proc.returncode != 0
    assert data not in chowned
    assert "left unmarked" in proc.stderr


@pytest.mark.parametrize("compose", COMPOSE_FILES)
def test_already_migrated_is_a_noop(tmp_path, compose):
    (tmp_path / "data.owner.stub").write_text("65532:65532\n")
    proc, chowned, _ = _run(tmp_path, _script(compose), ["bucket"])
    assert proc.returncode == 0
    assert chowned == []
    assert "ownership ok" in proc.stdout

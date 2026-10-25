"""The worker <-> host spool for operations the worker's Docker proxy refuses.

Drives the real host script (ops/coder/hostops/computor-coder-hostops.sh)
against the real worker-side client (tasks/coder_hostops.py), with a fake
`docker` that records its arguments. The script runs as root in production
and reads files the worker wrote, so the refusals matter as much as the
happy paths.
"""

import fcntl
import os
import shutil
import subprocess
import threading
import time

import pytest

from computor_backend.tasks import coder_hostops
from computor_backend.tasks.worker_settings import get_worker_settings

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 4))
SCRIPT = os.path.join(REPO, "ops", "coder", "hostops", "computor-coder-hostops.sh")


@pytest.fixture(autouse=True)
def _fresh_worker_settings():
    """Settings are cached per process; these tests change the env."""
    get_worker_settings.cache_clear()
    yield
    get_worker_settings.cache_clear()

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("flock") is None,
    reason="needs bash and flock",
)

FAKE_DOCKER = r"""#!/usr/bin/env bash
printf '%s\n' "$*" >> "$FAKE_LOG"
[ "$1" = -H ] && shift 2
case "$1 $2" in
  "ps -aq") printf '%s' "${FAKE_PS:-}" ;;
  "volume rm") exit 0 ;;
  "volume inspect")
    case "$4" in
      '{{.Driver}}') echo "${FAKE_DRIVER:-local}" ;;
      '{{json .Options}}') echo "${FAKE_VOLUME_OPTS:-null}" ;;
    esac ;;
  "run --rm") exit 0 ;;
  "exec computor-coder-registry")
    case "$3" in
      ls) printf 'latest\nv20260710-185325\nv20260713-092229\nv20260714-223158\nv20260714-225625\n' ;;
      rm) exit 0 ;;
      registry) echo "marking blobs"; echo "blob eligible for deletion"; exit 0 ;;
    esac ;;
esac
"""


@pytest.fixture
def spool(tmp_path, monkeypatch):
    base = tmp_path / "hostops"
    for d in ("staging", "requests", "results", ".work"):
        (base / d).mkdir(parents=True)
    (base / "registry.lock").write_text("")
    fake = tmp_path / "docker"
    fake.write_text(FAKE_DOCKER)
    fake.chmod(0o755)
    log = tmp_path / "docker.log"
    log.write_text("")
    monkeypatch.setenv("COMPUTOR_HOSTOPS_DIR", str(base))
    env = dict(os.environ, COMPUTOR_HOSTOPS_DIR=str(base), DOCKER=str(fake),
               FAKE_LOG=str(log), COMPUTOR_REGISTRY_LOCK_WAIT="2")
    return base, env, log


def _host(env):
    return subprocess.run(["bash", SCRIPT], env=env, capture_output=True, text=True, timeout=30)


def _serve_once(base, env):
    """Run the host script as soon as a request is queued (the path unit)."""
    def loop():
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if os.listdir(base / "requests"):
                _host(env)
                return
            time.sleep(0.05)
    thread = threading.Thread(target=loop)
    thread.start()
    return thread


def test_chown_volume_round_trip(spool):
    base, env, log = spool
    thread = _serve_once(base, env)
    answer = coder_hostops.submit("chown-volume", [("volume", "coder-home-abc")], timeout=20)
    thread.join()
    assert answer["status"] == "ok", answer
    run = [line for line in log.read_text().splitlines() if line.startswith("run ")]
    assert len(run) == 1
    args = run[0].split()
    assert "coder-home-abc:/vol" in args and args[-4:] == ["chown", "-R", "1000:1000", "/vol"]
    assert "--network none" in run[0] and "--cap-drop ALL" in run[0]
    assert "--privileged" not in run[0]
    # Request and answer are consumed; nothing is left to re-trigger the unit.
    assert not os.listdir(base / "requests") and not os.listdir(base / "results")


def test_registry_gc_round_trip(spool):
    base, env, log = spool
    thread = _serve_once(base, env)
    answer = coder_hostops.submit(
        "registry-gc", [("keep", "2"), ("repo", "computor-workspace-vscode")], timeout=20
    )
    thread.join()
    assert answer["status"] == "ok", answer
    assert answer["removed"] == [
        "computor-workspace-vscode:v20260713-092229",
        "computor-workspace-vscode:v20260710-185325",
    ]
    assert answer["gc"].startswith("exit=0")
    calls = log.read_text().splitlines()
    rm = next(c for c in calls if " rm -rf " in c)
    assert "/computor-workspace-vscode/_manifests/tags/v20260710-185325" in rm
    assert "latest" not in rm and "v20260714" not in rm
    assert any("garbage-collect --delete-untagged" in c for c in calls)


def _queue_raw(base, body, request_id="0" * 32):
    (base / "requests" / f"{request_id}.req").write_text(body)
    return base / "results" / request_id


@pytest.mark.parametrize(
    "body",
    [
        "action=chown-volume\nvolume=computor_postgres-data\n",
        "action=chown-volume\nvolume=coder-home-x;touch /tmp/pwned\n",
        "action=chown-volume\nvolume=coder-home-../../etc\n",
        "action=registry-gc\nkeep=2\nrepo=../../etc\n",
        "action=registry-gc\nkeep=0\nrepo=computor-workspace-vscode\n",
        "action=run\nimage=alpine\n",
    ],
)
def test_host_refuses_malformed_requests(spool, body):
    """The worker validates too, but the host must not trust it."""
    base, env, log = spool
    result = _queue_raw(base, body)
    _host(env)
    text = result.read_text()
    assert "status=error" in text
    assert "pwned" not in text and "etc" not in text  # invalid values not echoed
    assert not any(c.startswith(("run ", "exec ")) for c in log.read_text().splitlines())


def test_host_refuses_a_bind_mount_volume(spool):
    base, env, log = spool
    env["FAKE_VOLUME_OPTS"] = '{"device":"/","o":"bind","type":"none"}'
    result = _queue_raw(base, "action=chown-volume\nvolume=coder-home-abc\n")
    _host(env)
    assert "not a plain local volume" in result.read_text()
    assert not any(c.startswith("run ") for c in log.read_text().splitlines())


def test_host_does_not_follow_a_symlinked_request(spool, tmp_path):
    base, env, _ = spool
    secret = tmp_path / "secret"
    secret.write_text("action=chown-volume\nvolume=coder-home-abc\n")
    os.symlink(secret, base / "requests" / f"{'1' * 32}.req")
    _host(env)
    assert "not a regular file" in (base / "results" / ("1" * 32)).read_text()


def test_stray_files_are_dropped_and_pending_requests_kept(spool):
    base, env, _ = spool
    (base / "requests" / "junk").write_text("x")
    (base / "requests" / "subdir").mkdir()
    _host(env)
    assert not os.listdir(base / "requests")


def test_gc_waits_for_a_running_push(spool):
    base, env, log = spool
    fd = os.open(base / "registry.lock", os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_SH)  # what registry_push_lock() holds
        result = _queue_raw(base, "action=registry-gc\nkeep=2\nrepo=computor-workspace-vscode\n")
        _host(env)
    finally:
        os.close(fd)
    assert "held the lock" in result.read_text()
    assert not any(" rm " in c or "garbage-collect" in c for c in log.read_text().splitlines())


def test_push_lock_is_shared_and_skipped_without_spool(spool, monkeypatch, tmp_path):
    with coder_hostops.registry_push_lock(), coder_hostops.registry_push_lock():
        pass  # two concurrent pushes do not block each other
    monkeypatch.setenv("COMPUTOR_HOSTOPS_DIR", str(tmp_path / "absent"))
    with coder_hostops.registry_push_lock():
        pass


def test_push_waits_for_a_running_collection(spool):
    base, _, _ = spool
    beats = []
    holder = subprocess.Popen(
        ["flock", "-x", str(base / "registry.lock"), "sleep", "1.5"]
    )
    try:
        time.sleep(0.3)
        start = time.monotonic()
        with coder_hostops.registry_push_lock(heartbeat=lambda: beats.append(1)):
            waited = time.monotonic() - start
    finally:
        holder.wait()
    assert waited > 0.5 and beats  # blocked, and kept the activity alive


def test_unanswered_request_is_withdrawn(spool, monkeypatch):
    base, _, _ = spool
    monkeypatch.setattr(coder_hostops, "POLL_SECONDS", 0.05)
    answer = coder_hostops.submit("chown-volume", [("volume", "coder-home-abc")], timeout=0.3)
    assert answer["status"] == "error" and "withdrawn" in answer["message"]
    assert not os.listdir(base / "requests")


def test_missing_spool_is_reported(monkeypatch, tmp_path):
    monkeypatch.setenv("COMPUTOR_HOSTOPS_DIR", str(tmp_path / "absent"))
    answer = coder_hostops.submit("chown-volume", [("volume", "coder-home-abc")], timeout=1)
    assert answer["status"] == "error" and "not set up" in answer["message"]


# --- workspace daemon (image-backed homes, ops/coder/ws-daemon) -----------------

HOME = "coder-home-0b1c2d3e-0000-4000-8000-00000000abcd"


@pytest.fixture
def ws_spool(spool, tmp_path):
    base, env, log = spool
    homes, mnt = tmp_path / "homes", tmp_path / "mnt"
    homes.mkdir()
    mnt.mkdir()
    env = dict(env, COMPUTOR_WORKSPACE_DOCKER="unix:///ws.sock",
               COMPUTOR_WS_HOMES_DIR=str(homes), COMPUTOR_WS_MOUNT_DIR=str(mnt))
    return base, env, log, homes


def test_chown_runs_on_the_workspace_daemon_for_an_image_home(ws_spool):
    base, env, log, _ = ws_spool
    env["FAKE_DRIVER"] = "computor-home"
    thread = _serve_once(base, env)
    answer = coder_hostops.submit("chown-volume", [("volume", HOME)], timeout=20)
    thread.join()
    assert answer["status"] == "ok", answer
    run = [line for line in log.read_text().splitlines() if " run --rm " in line]
    assert len(run) == 1 and run[0].startswith("-H unix:///ws.sock run --rm ")


def test_a_plugin_volume_is_refused_without_the_workspace_daemon(spool):
    base, env, log = spool
    env["FAKE_DRIVER"] = "computor-home"
    thread = _serve_once(base, env)
    answer = coder_hostops.submit("chown-volume", [("volume", HOME)], timeout=20)
    thread.join()
    assert answer["status"] == "error" and "not a plain local volume" in answer["message"]
    assert not any(" run " in f" {c} " for c in log.read_text().splitlines())


@pytest.mark.skipif(shutil.which("mkfs.ext4") is None or shutil.which("dumpe2fs") is None,
                    reason="needs e2fsprogs")
def test_list_volumes_reports_used_bytes_of_unmounted_images(ws_spool):
    base, env, _, homes = ws_spool
    img = homes / f"{HOME}.img"
    subprocess.run(["truncate", "-s", "64M", str(img)], check=True)
    subprocess.run(["mkfs.ext4", "-q", "-F", "-m", "0", str(img)], check=True)
    (homes / "not-a-volume.img").write_text("")
    thread = _serve_once(base, env)
    answer = coder_hostops.submit("list-volumes", [], timeout=20)
    thread.join()
    assert answer["status"] == "ok", answer
    assert len(answer["volume"]) == 1
    name, used, capacity, mounted, created = answer["volume"][0].split(",")
    assert name == HOME and mounted == "0" and capacity == str(64 * 1024 * 1024)
    # An empty ext4: some metadata, far below the capacity.
    assert 0 < int(used) < 8 * 1024 * 1024 and created.endswith("Z")


def test_delete_volume_is_refused_while_a_container_references_it(ws_spool):
    base, env, _, homes = ws_spool
    (homes / f"{HOME}.img").write_text("x")
    env["FAKE_PS"] = "c0ffee\n"
    thread = _serve_once(base, env)
    answer = coder_hostops.submit("delete-volume", [("volume", HOME)], timeout=20)
    thread.join()
    assert answer["status"] == "error" and "in use" in answer["message"]
    assert (homes / f"{HOME}.img").exists()


def test_delete_volume_removes_the_image(ws_spool):
    base, env, log, homes = ws_spool
    (homes / f"{HOME}.img").write_text("x")
    thread = _serve_once(base, env)
    answer = coder_hostops.submit("delete-volume", [("volume", HOME)], timeout=20)
    thread.join()
    assert answer["status"] == "ok", answer
    assert not os.listdir(homes)
    assert f"-H unix:///ws.sock volume rm -- {HOME}" in log.read_text()


@pytest.mark.parametrize("name", ["coder-home-abc", "coder-home-../x", "computor_postgres-data"])
def test_delete_volume_refuses_other_names(ws_spool, name):
    base, env, _, homes = ws_spool
    thread = _serve_once(base, env)
    answer = coder_hostops.submit("delete-volume", [("volume", name)], timeout=20)
    thread.join()
    assert answer["status"] == "error"


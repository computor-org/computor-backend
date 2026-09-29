"""Behaviour of ops/coder/home-watchdog/computor-home-watchdog.sh with stubbed
docker/du/logger: per-object error isolation, writable-layer limits, exit status."""

import os
import shutil
import subprocess

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 4))
SCRIPT = os.path.join(REPO, "ops", "coder", "home-watchdog", "computor-home-watchdog.sh")
GIB = 1024 ** 3

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")

DOCKER_STUB = r"""#!/usr/bin/env bash
S="$WATCHDOG_STATE"
case "$1 $2" in
  "volume ls") [ -f "$S/volume_ls_fail" ] && exit 1; cat "$S/volumes" ;;
  "volume inspect")
    name="${@: -1}"; [ -f "$S/inspect_fail_$name" ] && { echo "boom" >&2; exit 1; }
    echo "$S/mnt/$name" ;;
  "ps -q")
    f="${4#volume=}"; f="${f#label=}"
    [ -f "$S/ps_fail_$f" ] && exit 1; cat "$S/ps_$f" 2>/dev/null ;;
  "inspect --size") id="${@: -1}"; cat "$S/sizerw_$id" ;;
  "stop --time") id="${@: -1}"; [ -f "$S/stopfail_$id" ] && exit 1; echo "$id" >> "$S/stopped" ;;
  *) echo "unexpected docker $*" >&2; exit 99 ;;
esac
"""

DU_STUB = r"""#!/usr/bin/env bash
dir="${@: -1}"; [ -f "$dir/.fail" ] && exit 1; printf '%s\t%s\n' "$(cat "$dir/.size")" "$dir"
"""


@pytest.fixture
def env(tmp_path):
    bindir, state = tmp_path / "bin", tmp_path / "state"
    bindir.mkdir()
    (state / "mnt").mkdir(parents=True)
    for name, body in (("docker", DOCKER_STUB), ("du", DU_STUB), ("logger", "#!/bin/sh\n")):
        (bindir / name).write_text(body)
        (bindir / name).chmod(0o755)
    (state / "volumes").write_text("")
    (state / "ps_coder.workspace_id").write_text("")

    def volume(name, size, containers=""):
        (state / "mnt" / name).mkdir()
        (state / "mnt" / name / ".size").write_text(str(size))
        with open(state / "volumes", "a") as f:
            f.write(name + "\n")
        (state / f"ps_{name}").write_text(containers)

    def run(**extra):
        environ = {
            "PATH": f"{bindir}:/usr/bin:/bin",
            "WATCHDOG_STATE": str(state),
            "COMPUTOR_HOME_LIMIT_GIB": "1",
            "COMPUTOR_LAYER_LIMIT_GIB": "1",
            **extra,
        }
        proc = subprocess.run(["bash", SCRIPT], env=environ, capture_output=True, text=True)
        stopped_file = state / "stopped"
        stopped = stopped_file.read_text().split() if stopped_file.exists() else []
        return proc, stopped

    return {"state": state, "volume": volume, "run": run}


def test_over_limit_volume_is_stopped_small_one_untouched(env):
    env["volume"]("coder-home-big", 2 * GIB, "c-big\n")
    env["volume"]("coder-home-small", GIB // 2, "c-small\n")
    env["volume"]("other-volume", 5 * GIB, "c-other\n")
    proc, stopped = env["run"]()
    assert proc.returncode == 0, proc.stderr
    assert stopped == ["c-big"]


@pytest.mark.parametrize("breakage", ["inspect", "du"])
def test_error_on_one_volume_does_not_stop_the_scan(env, breakage):
    env["volume"]("coder-home-aaa-broken", 5 * GIB, "c-broken\n")
    env["volume"]("coder-home-zzz-big", 2 * GIB, "c-big\n")
    if breakage == "inspect":
        (env["state"] / "inspect_fail_coder-home-aaa-broken").write_text("")
    else:
        (env["state"] / "mnt" / "coder-home-aaa-broken" / ".fail").write_text("")
    proc, stopped = env["run"]()
    assert stopped == ["c-big"]
    assert proc.returncode == 2
    assert "INCOMPLETE" in proc.stderr


def test_failed_stop_is_reported_and_others_still_stopped(env):
    env["volume"]("coder-home-a", 2 * GIB, "c-1\nc-2\n")
    env["volume"]("coder-home-b", 2 * GIB, "c-3\n")
    (env["state"] / "stopfail_c-1").write_text("")
    proc, stopped = env["run"]()
    assert sorted(stopped) == ["c-2", "c-3"]
    assert proc.returncode == 2
    assert "could not stop c-1" in proc.stderr


def test_writable_layer_over_limit_is_stopped(env):
    (env["state"] / "ps_coder.workspace_id").write_text("w-big\nw-small\n")
    (env["state"] / "sizerw_w-big").write_text(str(2 * GIB))
    (env["state"] / "sizerw_w-small").write_text("1024")
    proc, stopped = env["run"]()
    assert proc.returncode == 0, proc.stderr
    assert stopped == ["w-big"]


def test_dry_run_never_stops(env):
    env["volume"]("coder-home-big", 2 * GIB, "c-big\n")
    proc, stopped = env["run"](COMPUTOR_HOME_DRY_RUN="true")
    assert proc.returncode == 0
    assert stopped == []
    assert "not stopped" in proc.stderr

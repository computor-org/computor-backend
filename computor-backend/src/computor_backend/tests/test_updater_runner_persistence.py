"""The updater's detached --rm runner must write Keycloak dumps to the HOST.

Launches the real ``launch_runner`` from docker/updater/watch.sh with a real
docker daemon, runs update.sh's real ``keycloak_predump`` inside the runner
(only the ``compose`` call is stubbed to emit a dump), and checks the file on
the host after the container is gone.
"""

import os
import shutil
import subprocess
import textwrap
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
WATCH_SH = REPO / "docker/updater/watch.sh"
IMAGE = "python:3.13-slim@sha256:7c61056e61ac89e852de05f3dc6fa51a6dd2181797bceed46aa725dd7cb2cd3b"


def _docker_ok():
    if shutil.which("docker") is None:
        return False
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        return False
    return subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode == 0 \
        or subprocess.run(["docker", "pull", "-q", IMAGE], capture_output=True).returncode == 0


pytestmark = [pytest.mark.docker,
              pytest.mark.skipif(not _docker_ok(), reason="needs a docker daemon and the python image")]

RUNNER_SCRIPT = textwrap.dedent("""
    set -u
    SYSTEM_DEPLOYMENT_PATH='{deploy}'
    source '{repo}/ops/lib/update.sh'
    ulog() {{ echo "$*"; }}
    compose() {{
        case "$*" in *pg_dumpall*)
            printf '%b' 'CREATE DATABASE keycloak WITH TEMPLATE = template0;\\n-- PostgreSQL database cluster dump complete\\n';;
        esac
    }}
    keycloak_predump "$(updater_state_dir)/backups/keycloak/test.sql.gz"
""")


def _launch(tmp_path, deploy, pass_deploy_path):
    name = f"kc26-runner-test-{uuid.uuid4().hex[:8]}"
    env = dict(os.environ, UPDATER_WATCH_SOURCE_ONLY="1",
               COMPUTOR_REPO_DIR=str(REPO), DOCKER_GID=str(os.getgid()),
               RUNNER_NETWORK="bridge", SELF_IMAGE=IMAGE, REDIS_PASSWORD="x")
    if pass_deploy_path:
        env["SYSTEM_DEPLOYMENT_PATH"] = str(deploy)
    else:
        env.pop("SYSTEM_DEPLOYMENT_PATH", None)
    env["RUNNER_CMD"] = RUNNER_SCRIPT.format(deploy=deploy, repo=REPO)
    script = f'source "{WATCH_SH}"; RUNNER_NAME="{name}"; launch_runner'
    p = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    subprocess.run(["docker", "wait", name], capture_output=True, text=True, timeout=120)
    # The runner is --rm: once it has exited it must be gone.
    for _ in range(50):
        if subprocess.run(["docker", "inspect", name], capture_output=True).returncode != 0:
            break
        subprocess.run(["sleep", "0.2"])
    else:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        pytest.fail("runner container was not removed")


def test_dump_written_by_runner_persists_on_host(tmp_path):
    deploy = tmp_path / "deploy"
    (deploy / "updater").mkdir(parents=True)
    (deploy / "updater/.host-persistent").touch()
    _launch(tmp_path, deploy, pass_deploy_path=True)
    dump = deploy / "updater/backups/keycloak/test.sql.gz"
    assert dump.is_file() and dump.stat().st_size > 0
    out = subprocess.run(["bash", "-c", f"gzip -dc '{dump}'"], capture_output=True, text=True).stdout
    assert "dump complete" in out


def test_runner_without_state_mount_refuses_instead_of_writing_ephemerally(tmp_path):
    deploy = tmp_path / "deploy"
    (deploy / "updater").mkdir(parents=True)
    (deploy / "updater/.host-persistent").touch()
    _launch(tmp_path, deploy, pass_deploy_path=False)   # no state mount
    assert not (deploy / "updater/backups").exists()

"""Rendered production compose passes the Coder settings the API reads.

Renders ops/docker (base + prod + coder) with `docker compose config` and
checks the uvicorn service environment. Skipped without the docker CLI.
"""

import json
import os
import shutil
import subprocess

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 4))
COMPOSE_DIR = os.path.join(REPO, "ops", "docker")

pytestmark = pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI not available")


def _render(tmp_path, extra_env):
    env_lines = []
    for name in _required_variables():
        env_lines.append(f"{name}=x")
    env_lines += [
        "SYSTEM_DEPLOYMENT_PATH=/tmp/x",
        "DOCKER_GID=999",
        "CODER_WORKER_DB_PASSWORD=workerpw",
    ]
    env_lines += [f"{k}={v}" for k, v in extra_env.items()]
    env_file = tmp_path / "compose.env"
    env_file.write_text("\n".join(env_lines) + "\n")
    files = []
    for name in ("base", "prod", "coder"):
        files += ["-f", os.path.join(COMPOSE_DIR, f"docker-compose.{name}.yaml")]
    result = subprocess.run(
        ["docker", "compose", "--env-file", str(env_file), *files, "config", "--format", "json"],
        capture_output=True, text=True, timeout=60,
        env={k: v for k, v in os.environ.items() if not k.startswith(("CODER_", "COMPUTOR_"))},
    )
    if result.returncode != 0 and "unknown flag" in result.stderr:
        pytest.skip("docker compose plugin not available")
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["services"]["uvicorn"]["environment"]


def _required_variables():
    import re

    names = set()
    for fn in os.listdir(COMPOSE_DIR):
        if fn.endswith(".yaml"):
            with open(os.path.join(COMPOSE_DIR, fn), encoding="utf-8") as f:
                names.update(re.findall(r"\$\{([A-Z0-9_]+):\?", f.read()))
    names.discard("CODER_WORKER_DB_PASSWORD")
    return sorted(names)


def test_api_receives_custom_coder_admin_username(tmp_path):
    env = _render(tmp_path, {"CODER_ADMIN_USERNAME": "svc", "COMPUTOR_PUBLIC_DEPLOYMENT": "true",
                             "CODER_WORKSPACE_CGROUP_PARENT": "computor-workspaces.slice"})
    assert env["CODER_ADMIN_USERNAME"] == "svc"
    assert env["COMPUTOR_PUBLIC_DEPLOYMENT"] == "true"
    assert env["CODER_WORKSPACE_CGROUP_PARENT"] == "computor-workspaces.slice"
    assert env["CODER_WORKER_DB_PASSWORD"] == "workerpw"


def test_api_coder_admin_username_defaults_to_admin(tmp_path):
    assert _render(tmp_path, {})["CODER_ADMIN_USERNAME"] == "admin"

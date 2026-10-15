"""temporal-worker-coder reaches Docker only through its allowlist proxy.

Renders ops/docker (base + prod + coder, and the split worker-host overlay)
with `docker compose config`. Skipped without the docker CLI.
"""

import json
import os
import shutil
import subprocess

import pytest

from computor_backend.tests.test_prod_compose_api_env import COMPOSE_DIR, _required_variables

pytestmark = pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI not available")


def _render(tmp_path, overlays):
    env_file = tmp_path / "compose.env"
    addresses = {"WORKERHOST_CONTROL_ADDR": "10.88.0.1", "WORKERHOST_BIND_ADDRESS": "10.88.0.2",
                 "PREVIEW_BIND_ADDRESS": "10.88.0.2"}
    env_file.write_text("\n".join(
        [f"{name}=x" for name in _required_variables() if name not in addresses]
        + [f"{k}={v}" for k, v in addresses.items()]
        + ["SYSTEM_DEPLOYMENT_PATH=/tmp/x", "DOCKER_GID=999", "CODER_WORKER_DB_PASSWORD=x"]
    ) + "\n")
    files = []
    for name in overlays:
        files += ["-f", os.path.join(COMPOSE_DIR, f"docker-compose.{name}.yaml")]
    result = subprocess.run(
        ["docker", "compose", "--env-file", str(env_file), *files, "config", "--format", "json"],
        capture_output=True, text=True, timeout=60,
        env={k: v for k, v in os.environ.items()
             if not k.startswith(("CODER_", "COMPUTOR_", "DOCKER_"))},
    )
    if result.returncode != 0 and "unknown flag" in result.stderr:
        pytest.skip("docker compose plugin not available")
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture(params=[("base", "prod", "coder"), ("base", "prod", "coder", "workerhost")])
def config(request, tmp_path):
    return _render(tmp_path, request.param)


def test_worker_has_no_docker_socket(config):
    worker = config["services"]["temporal-worker-coder"]
    targets = {v["target"]: v for v in worker["volumes"]}
    assert not any("docker.sock" in (v.get("source") or "") for v in worker["volumes"])
    assert "group_add" not in worker
    assert worker["environment"]["DOCKER_HOST"] == "tcp://coder-worker-socket-proxy:2375"
    assert "coder-worker-socket-proxy" in worker["depends_on"]
    # Slice limits come from the host cgroup tree, read-only.
    assert targets["/host/sys/fs/cgroup"]["read_only"] is True
    assert targets["/hostops"]["source"] == "/var/lib/computor/coder-hostops"


def test_proxy_uses_the_allowlist_and_is_private(config):
    proxy = config["services"]["coder-worker-socket-proxy"]
    targets = {v["target"]: v for v in proxy["volumes"]}
    assert targets["/var/run/docker.sock"]["read_only"] is True
    template = targets["/usr/local/etc/haproxy/haproxy.cfg.template"]
    assert template["source"].endswith("ops/docker/coder-worker-socket-proxy/haproxy.cfg.template")
    assert list(proxy["networks"]) == ["coder-worker-docker"]
    assert config["networks"]["coder-worker-docker"]["internal"] is True
    assert "ports" not in proxy


def test_allowlist_has_no_container_or_exec_route():
    path = os.path.join(COMPOSE_DIR, "coder-worker-socket-proxy", "haproxy.cfg.template")
    rules = [
        line.strip() for line in open(path, encoding="utf-8")
        if line.strip().startswith(("acl ", "http-request"))
    ]
    assert rules[-1] == "http-request deny"  # default deny
    joined = "\n".join(rules)
    for section in ("containers", "exec", "networks", "plugins", "swarm", "session", "grpc"):
        assert f"/{section}" not in joined
    assert "env(" not in joined  # not switchable by the upstream env flags

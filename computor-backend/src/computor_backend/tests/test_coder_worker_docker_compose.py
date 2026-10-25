"""Coder and temporal-worker-coder reach Docker only through allowlist proxies.

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
    # The proxy admits image names only under the registry the worker pushes to.
    worker = config["services"]["temporal-worker-coder"]
    assert proxy["environment"]["CODER_REGISTRY_HOST"] == worker["environment"]["CODER_REGISTRY_HOST"]


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


def test_coder_server_has_no_docker_socket(config):
    coder = config["services"]["coder"]
    assert not any("docker.sock" in (v.get("source") or "") for v in coder["volumes"])
    assert "group_add" not in coder
    assert coder["environment"]["DOCKER_HOST"] == "tcp://coder-provisioner-socket-proxy:2375"
    assert "coder-provisioner-socket-proxy" in coder["depends_on"]
    assert "coder-provisioner-docker" in coder["networks"]


def test_provisioner_proxy_uses_the_allowlist_and_is_private(config):
    proxy = config["services"]["coder-provisioner-socket-proxy"]
    targets = {v["target"]: v for v in proxy["volumes"]}
    # The daemon socket is mounted read-only at a fixed target: by default the
    # main socket, on the worker the workspace daemon's socket directory.
    assert targets["/var/run/workspace-docker"]["read_only"] is True
    assert proxy["environment"]["SOCKET_PATH"] == "/var/run/workspace-docker"
    template = targets["/usr/local/etc/haproxy/haproxy.cfg.template"]
    assert template["source"].endswith(
        "ops/docker/coder-provisioner-socket-proxy/haproxy.cfg.template")
    assert list(proxy["networks"]) == ["coder-provisioner-docker"]
    assert config["networks"]["coder-provisioner-docker"]["internal"] is True
    assert "ports" not in proxy
    # Only coder shares the proxy's network.
    on_net = [name for name, svc in config["services"].items()
              if "coder-provisioner-docker" in (svc.get("networks") or {})]
    assert sorted(on_net) == ["coder", "coder-provisioner-socket-proxy"]
    # Pulls only from the registry the worker pushes to; connects only to the
    # networks the compose stack gives workspaces.
    worker = config["services"]["temporal-worker-coder"]
    assert proxy["environment"]["CODER_REGISTRY_HOST"] == worker["environment"]["CODER_REGISTRY_HOST"]
    nets = config["networks"]
    assert proxy["environment"]["CODER_WORKSPACE_NETWORK"] == nets["computor-coder-workspaces"]["name"]
    assert (proxy["environment"]["CODER_WORKSPACE_NETWORK_OFFLINE"]
            == nets["computor-coder-workspaces-offline"]["name"])


def test_provisioner_allowlist_has_no_exec_or_build_route():
    path = os.path.join(COMPOSE_DIR, "coder-provisioner-socket-proxy", "haproxy.cfg.template")
    rules = [
        line.strip() for line in open(path, encoding="utf-8")
        if line.strip().startswith(("acl ", "http-request"))
    ]
    assert rules[-1] == "http-request deny"  # default deny
    joined = "\n".join(rules)
    for section in ("exec", "attach", "archive", "update", "build", "plugins", "swarm",
                    "session", "grpc", "secrets", "commit"):
        assert section not in joined, section
    assert "env(" not in joined  # not switchable by the upstream env flags
    assert "option http-buffer-request" in open(path, encoding="utf-8").read()

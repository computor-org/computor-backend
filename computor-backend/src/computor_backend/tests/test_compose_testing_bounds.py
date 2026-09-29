"""Testing-worker container bounds are identical in dev and prod and leave
headroom for the worker itself (#237)."""
import re
from pathlib import Path

import pytest
import yaml

DOCKER = Path(__file__).resolve().parents[4] / "ops" / "docker"
BOUND_KEYS = ("mem_limit", "cpus", "pids_limit", "init", "user")
SHARED_ENV_PREFIXES = ("COMPUTOR_JOB_", "TEMPORAL_MAX_CONCURRENT_ACTIVITIES",
                       "COMPUTOR_SANDBOX_ENABLE")
GIB = 1024 ** 3


def _service(name):
    path = DOCKER / f"docker-compose.{name}.yaml"
    if not path.exists():
        pytest.skip(f"{path} not in this checkout")
    return yaml.safe_load(path.read_text())["services"]["temporal-worker-testing"]


def _shared_env(service):
    return sorted(e for e in service["environment"]
                  if e.startswith(SHARED_ENV_PREFIXES))


def _default(value):
    """'${VAR:-default}' -> 'default'."""
    m = re.fullmatch(r"\$\{\w+:-([^}]*)\}", str(value))
    return m.group(1) if m else str(value)


def _bytes(text):
    m = re.fullmatch(r"(\d+)([kmg]?)", text.lower())
    return int(m.group(1)) * {"": 1, "k": 1024, "m": 1024 ** 2, "g": GIB}[m.group(2)]


def test_dev_and_prod_share_the_testing_worker_bounds():
    dev, prod = _service("dev"), _service("prod")
    for key in BOUND_KEYS:
        assert dev.get(key) == prod.get(key), key
        assert prod.get(key) is not None, key
    assert _shared_env(dev) == _shared_env(prod)


def test_memory_leaves_headroom_for_the_worker():
    prod = _service("prod")
    env = dict(e.split("=", 1) for e in prod["environment"] if "=" in e)
    jobs = int(_default(env["TEMPORAL_MAX_CONCURRENT_ACTIVITIES"]))
    per_job = int(_default(env["COMPUTOR_JOB_MEMORY_BYTES"]))
    container = _bytes(_default(prod["mem_limit"]))
    assert container - jobs * per_job >= 2 * GIB

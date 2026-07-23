from pathlib import Path

import pytest
import yaml


@pytest.mark.unit
def test_critical_services_restart_after_host_reboot() -> None:
    repository_root = Path(__file__).resolve().parents[4]
    compose_path = repository_root / "ops/docker/docker-compose.base.yaml"
    services = yaml.safe_load(compose_path.read_text())["services"]

    for service_name in ("postgres", "traefik"):
        assert services[service_name]["restart"] == "unless-stopped"

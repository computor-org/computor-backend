"""The QA stack (ops/qa, computor-org/issues#529) stays isolated on a shared host.

qactl.sh runs the production compose files plus ops/qa/docker-compose.qa.yaml
beside other stacks and CI containers. A compose change elsewhere must not
silently give a QA container a production name, a public port or no limits.
"""
import importlib.util
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
QA = ROOT / "ops" / "qa"
DOCKER = ROOT / "ops" / "docker"


def _compose_set():
    """The files qactl.sh passes to docker compose, in its order."""
    script = (QA / "qactl.sh").read_text()
    names = re.findall(r'"\$d/(docker-compose\.[\w.-]+\.yaml)"', script)
    assert names, "qactl.sh lists no compose files"
    return [DOCKER / name for name in names] + [QA / "docker-compose.qa.yaml"]


def _merge(base, override):
    """Compose's override rule for mappings: merge keys, later files win."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def _merged_services():
    merged = {}
    for path in _compose_set():
        assert path.exists(), path
        for name, service in (yaml.safe_load(path.read_text()).get("services") or {}).items():
            _merge(merged.setdefault(name, {}), service or {})
    return merged


def _runs(service):
    return "profiles" not in service and service.get("restart") != "no" \
        and "image" in service


def test_every_container_name_is_prefixed():
    for name, service in _merged_services().items():
        container = service.get("container_name")
        if container is None:
            continue  # auto-named from the "qa" project
        assert container.startswith("${CONTAINER_NAME_PREFIX"), (name, container)


def _bind_default(host):
    """'${A:-${B:-127.0.0.1}}' -> '127.0.0.1'; a bare '${A}' has no default."""
    while True:
        m = re.fullmatch(r"\$\{\w+(?::[-?](.*))?\}", host)
        if not m:
            return host
        host = m.group(1) or ""


def test_every_published_port_is_loopback():
    for name, service in _merged_services().items():
        for port in service.get("ports") or []:
            m = re.fullmatch(r"(.*):(\$\{\w+(?::-\d+)?:?\??\}|\d+):\d+", str(port))
            assert m, (name, port)
            assert _bind_default(m.group(1)) == "127.0.0.1", (name, port)


def test_long_running_services_are_limited():
    for name, service in _merged_services().items():
        if not _runs(service) or name == "temporal-worker-testing":
            continue  # the testing worker's limits come from TESTING_WORKER_*
        assert "cpus" in service and "mem_limit" in service, name


def test_qa_images_build_from_qa_base_tags():
    """Every FROM computor-<base> of a built service is mapped to a QA tag, so a
    QA build never reads or retags the host's shared computor-* base images."""
    overlay = yaml.safe_load((QA / "docker-compose.qa.yaml").read_text())["services"]
    for name, service in _merged_services().items():
        if "build" not in service:
            continue
        dockerfile = (DOCKER / service["build"]["context"] / service["build"]["dockerfile"]).resolve()
        bases = set(re.findall(r"^FROM (computor-[\w-]+)", dockerfile.read_text(), re.M))
        contexts = (overlay.get(name, {}).get("build") or {}).get("additional_contexts", {})
        for base in bases:
            assert contexts.get(base, "").startswith("docker-image://${QA_"), (name, base)


def _render_realm():
    spec = importlib.util.spec_from_file_location("render_realm", QA / "render_realm.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render


def test_realm_has_email_first_signup_and_mailpit():
    source = json.loads((ROOT / "data" / "keycloak" / "computor-realm.json").read_text())
    personas = [{"keycloak_id": "11111111-1111-5111-8111-111111111111", "username": "qa-x",
                 "email": "qa-x@example.com", "given_name": "Q", "family_name": "A",
                 "password": "pw", "groups": ["/administrators"]}]
    realm = _render_realm()(source, personas, client_secret="c" * 64,
                            forgejo_secret="f" * 64, origin="http://localhost:18480",
                            mail_from="noreply@example.com")
    for key in ("registrationAllowed", "verifyEmail", "resetPasswordAllowed"):
        assert realm[key] is True, key
    assert realm["smtpServer"]["host"] == "mailpit"
    assert "PLACEHOLDER" not in json.dumps(realm)
    backend = next(c for c in realm["clients"] if c["clientId"] == "computor-backend")
    assert "http://localhost:18480/api/auth/keycloak/callback" in backend["redirectUris"]
    (user,) = realm["users"]
    assert user["emailVerified"] is True and user["requiredActions"] == []

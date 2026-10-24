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


def _qa_seed(tmp_path, monkeypatch):
    personas = tmp_path / "personas.json"
    personas.write_text("[]")
    monkeypatch.setenv("QA_PERSONAS_FILE", str(personas))
    spec = importlib.util.spec_from_file_location("qa_seed", QA / "qa_seed.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(root, files):
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)


def test_examples_package_is_preferred_and_uploaded_dependencies_first(tmp_path, monkeypatch):
    """The runnable GitLab examples package wins over the text-only mirror,
    and an example is uploaded after the ones its testDependencies name (the
    upload of an example with a missing dependency is rejected)."""
    seed = _qa_seed(tmp_path, monkeypatch)
    package, mirror = tmp_path / "examples", tmp_path / "content"
    _write(mirror, {"examples/python/x.a/meta.yaml": "slug: x.a\n"})
    monkeypatch.setattr(seed, "CONTENT", mirror)
    monkeypatch.setattr(seed, "EXAMPLES", package)
    assert seed.example_directories() == ([mirror / "examples/python/x.a"], False)

    _write(package, {
        "x.a_test/meta.yaml": "slug: x.a_test\nproperties:\n  testDependencies: [x.b, x.a]\n",
        "x.a/meta.yaml": "slug: x.a\n",
        "x.b/meta.yaml": "slug: x.b\ntestDependencies:\n  - slug: x.a\n",
    })
    directories, runnable = seed.example_directories()
    assert runnable and [d.name for d in directories] == ["x.a", "x.a_test", "x.b"]
    entries = [(d, yaml.safe_load((d / "meta.yaml").read_text())) for d in directories]
    assert [m["slug"] for _, m in seed.upload_order(entries)] == ["x.a", "x.b", "x.a_test"]


def test_learner_submissions_come_from_the_examples(tmp_path, monkeypatch):
    """Seeded learners submit real files that the testing worker grades."""
    seed = _qa_seed(tmp_path, monkeypatch)
    example = tmp_path / "x.mathc"
    _write(example, {
        "meta.yaml": "slug: x.mathc\nproperties:\n  studentSubmissionFiles: [mathc.py]\n",
        "localTests/correctSolution/mathc.py": '"""\nName: A\n"""\n\np = 3.14159\n',
    })
    assert seed.submission_files(example, "correct")["mathc.py"].startswith(b'"""')
    assert seed.submission_files(example, "nodoc") == {"mathc.py": b"p = 3.14159\n"}
    assert b"=" not in seed.submission_files(example, "empty")["mathc.py"]


def test_support_welcome_mail_is_isolated_to_mailpit():
    services = _merged_services()
    assert services['uvicorn']['environment']['SUPPORT_WELCOME_MAIL_ENABLED'] == 'true'
    worker = services['temporal-worker-support']
    assert worker['command'][-1] == '--queues=support'
    env = worker['environment']
    assert env['SUPPORT_MAIL_ENABLED'] == 'true'
    assert env['SUPPORT_WELCOME_MAIL_ENABLED'] == 'true'
    assert env['SUPPORT_MAIL_IMPORT_ENABLED'] == 'false'
    assert env['SUPPORT_SMTP_HOST'] == 'mailpit'
    assert env['SUPPORT_SMTP_PORT'] == '1025'
    assert env['SUPPORT_SMTP_STARTTLS'] == 'false'
    assert env['SUPPORT_SMTP_USER'] == env['SUPPORT_SMTP_PASSWORD'] == ''
    assert env['SUPPORT_SITE_URL'] == 'http://localhost:18480'

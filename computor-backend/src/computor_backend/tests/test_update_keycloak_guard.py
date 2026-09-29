"""Behavioral tests for the self-updater's Keycloak version-change guard.

Keycloak does not support DB downgrades, and an old Keycloak reports ready on a
newer schema. So when an update changes the Keycloak image, ops/lib/update.sh
must dump the Keycloak DB (verified) before starting the new version and, if the
update fails afterwards, keep maintenance up and NOT roll the code back.

cmd_update_exec runs for real against throwaway git repos; only docker/redis
side effects are stubbed and recorded.
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
UPDATE_SH = REPO / "ops/lib/update.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None or shutil.which("git") is None,
                                reason="needs bash and git")

COMPLETE_DUMP = ("--\\n-- PostgreSQL database cluster dump\\n--\\n"
                 "CREATE DATABASE keycloak WITH TEMPLATE = template0;\\n"
                 "-- data\\n--\\n-- PostgreSQL database cluster dump complete\\n--\\n")
TRUNCATED_DUMP = "--\\nCREATE DATABASE keycloak WITH TEMPLATE = template0;\\n-- data\\n"


def _git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def _compose_yaml(tag):
    return f"services:\n  keycloak:\n    image: quay.io/keycloak/keycloak:{tag}@sha256:abc\n"


def _make_repos(tmp_path, from_tag, to_tag):
    origin = tmp_path / "origin"
    (origin / "ops/docker").mkdir(parents=True)
    _git(tmp_path, "init", "-q", "-b", "main", str(origin))
    _git(origin, "config", "user.email", "t@example.invalid")
    _git(origin, "config", "user.name", "t")
    (origin / "ops/docker/docker-compose.keycloak.yaml").write_text(_compose_yaml(from_tag))
    _git(origin, "add", "-A"); _git(origin, "commit", "-qm", "A")
    a = _git(origin, "rev-parse", "HEAD")
    deploy = tmp_path / "deploy"
    _git(tmp_path, "clone", "-q", str(origin), str(deploy))
    (origin / "ops/docker/docker-compose.keycloak.yaml").write_text(_compose_yaml(to_tag))
    (origin / "CHANGE").write_text("b\n")
    _git(origin, "add", "-A"); _git(origin, "commit", "-qm", "B")
    b = _git(origin, "rev-parse", "HEAD")
    return origin, deploy, a, b


def _run_update(tmp_path, origin, deploy, a, dump_body, keycloak_enabled="true",
                kc_state="exited", stop_fails=False, docker_ps_fails=False):
    calls = tmp_path / "calls.log"
    script = textwrap.dedent(f"""
        set -u
        REPO_ROOT={deploy}
        SYSTEM_REPO_URL={origin}
        SYSTEM_REPO_BRANCH=main
        SYSTEM_DEPLOYMENT_PATH={tmp_path}/deploypath
        KEYCLOAK_ENABLED={keycloak_enabled}
        CALLS={calls}
        source {UPDATE_SH}
        update_env_init() {{ :; }}
        log() {{ echo "$*"; }}
        redis_cli() {{ echo "redis $*" >> "$CALLS"; [ "$1" = SET ] && echo OK; return 0; }}
        build_images() {{ echo "build $(git -C "$REPO_ROOT" rev-parse HEAD)" >> "$CALLS"; }}
        get_stoppable_services() {{ echo keycloak; echo uvicorn; }}
        set_redis_maintenance() {{ echo "maintenance $1" >> "$CALLS"; }}
        ensure_maintenance_page() {{ :; }}
        activate_traefik_maintenance() {{ echo "traefik-maintenance on" >> "$CALLS"; }}
        deactivate_traefik_maintenance() {{ echo "traefik-maintenance off" >> "$CALLS"; }}
        sleep() {{ :; }}
        compose() {{
            echo "compose $*" >> "$CALLS"
            case "$*" in
                *pg_dumpall*) printf '%b' '{dump_body}';;
                "stop keycloak") [ "{int(stop_fails)}" = 1 ] && return 1;;
            esac
            return 0
        }}
        docker() {{
            echo "docker $*" >> "$CALLS"
            case "$1" in
                ps) [ "{int(docker_ps_fails)}" = 1 ] && return 1; echo "{kc_state}";;
            esac
            return 0
        }}
        # The API only comes up healthy on the OLD commit.
        wait_for_api() {{ [ "$(git -C "$REPO_ROOT" rev-parse HEAD)" = "{a}" ]; }}
        wait_for_frontend() {{ return 0; }}
        cmd_update_exec prod
    """)
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60)
    return p, calls.read_text() if calls.exists() else ""


def test_keycloak_change_failed_update_keeps_maintenance_and_code(tmp_path):
    origin, deploy, a, b = _make_repos(tmp_path, "25.0.6", "26.7.4")
    p, calls = _run_update(tmp_path, origin, deploy, a, COMPLETE_DUMP)
    out = p.stdout + p.stderr
    assert p.returncode != 0
    assert _git(deploy, "rev-parse", "HEAD") == b          # no code rollback
    assert "traefik-maintenance off" not in calls            # maintenance kept
    assert "maintenance 0" not in calls
    assert "compose up -d\n" in calls
    # verified dump taken before the new Keycloak was started
    assert calls.index("pg_dumpall") < calls.index("compose up -d\n")
    dumps = list((tmp_path / "deploypath/backups/keycloak").glob("keycloak-pre-25.0.6-to-26.7.4-*.sql.gz"))
    assert len(dumps) == 1 and not list(dumps[0].parent.glob("*.partial"))
    assert "rolling_back" not in calls
    for needle in ("DROP DATABASE keycloak", str(dumps[0]), a, "Keycloak 25.0.6"):
        assert needle in out
    assert "automatic rollback refused" in calls


def test_keycloak_change_with_incomplete_dump_rolls_back_safely(tmp_path):
    origin, deploy, a, b = _make_repos(tmp_path, "25.0.6", "26.7.4")
    p, calls = _run_update(tmp_path, origin, deploy, a, TRUNCATED_DUMP)
    assert p.returncode == 0, p.stdout + p.stderr           # rolled_back is a clean exit
    assert _git(deploy, "rev-parse", "HEAD") == a            # new Keycloak never started
    assert "compose up -d\n" in calls                         # only the rollback start
    assert calls.count("compose up -d\n") == 1
    assert "status rolled_back" in calls
    assert "traefik-maintenance off" in calls
    assert not list((tmp_path / "deploypath/backups/keycloak").glob("*"))


@pytest.mark.parametrize("tags,enabled", [(("26.7.4", "26.7.4"), "true"),
                                          (("25.0.6", "26.7.4"), "false")])
def test_no_keycloak_change_keeps_ordinary_rollback(tmp_path, tags, enabled):
    origin, deploy, a, b = _make_repos(tmp_path, *tags)
    p, calls = _run_update(tmp_path, origin, deploy, a, COMPLETE_DUMP, keycloak_enabled=enabled)
    assert p.returncode == 0, p.stdout + p.stderr
    assert _git(deploy, "rev-parse", "HEAD") == a
    assert "pg_dumpall" not in calls
    assert "status rolled_back" in calls


@pytest.mark.parametrize("from_tag,to_tag,enabled,expected", [
    ("25.0.6", "26.7.4", "true", "guard"),
    ("26.7.3", "26.7.4", "true", "guard"),   # patch releases migrate too
    ("26.7.4", "26.7.4", "true", "none"),
    ("25.0.6", "26.7.4", "", "none"),
    ("", "26.7.4", "true", "none"),           # Keycloak newly added: nothing to protect
    ("26.7.4", "25.0.6", "true", "downgrade"),
    ("26.7.4", "26.7.3", "true", "downgrade"),
    ("26.10.0", "26.9.1", "true", "downgrade"),  # version order, not string order
    ("26.9.1", "26.10.0", "true", "guard"),
])
def test_decision_table(from_tag, to_tag, enabled, expected):
    out = subprocess.run(["bash", "-c", f'source {UPDATE_SH}; keycloak_update_decision "$1" "$2" "$3"',
                          "_", from_tag, to_tag, enabled], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == expected


@pytest.mark.parametrize("kw", [dict(kc_state="running"), dict(stop_fails=True),
                                dict(docker_ps_fails=True), dict(kc_state="restarting")])
def test_unverified_keycloak_shutdown_aborts_before_dump_and_new_start(tmp_path, kw):
    origin, deploy, a, b = _make_repos(tmp_path, "25.0.6", "26.7.4")
    p, calls = _run_update(tmp_path, origin, deploy, a, COMPLETE_DUMP, **kw)
    assert p.returncode == 0, p.stdout + p.stderr          # ordinary safe rollback
    assert "pg_dumpall" not in calls                         # no dump of a live DB
    assert calls.count("compose up -d\n") == 1              # only the rollback start
    assert _git(deploy, "rev-parse", "HEAD") == a
    assert "did not stop cleanly" in calls


@pytest.mark.parametrize("state", ["exited", ""])
def test_verified_shutdown_precedes_dump(tmp_path, state):
    origin, deploy, a, b = _make_repos(tmp_path, "25.0.6", "26.7.4")
    p, calls = _run_update(tmp_path, origin, deploy, a, COMPLETE_DUMP, kc_state=state)
    assert calls.index("compose stop keycloak") < calls.index("docker ps -a") < calls.index("pg_dumpall")


def test_keycloak_downgrade_is_refused_without_touching_anything(tmp_path):
    origin, deploy, a, b = _make_repos(tmp_path, "26.7.4", "25.0.6")
    p, calls = _run_update(tmp_path, origin, deploy, a, COMPLETE_DUMP)
    assert p.returncode != 0
    assert _git(deploy, "rev-parse", "HEAD") == a
    assert "build " not in calls and "maintenance 1" not in calls
    assert "pg_dumpall" not in calls and "compose up" not in calls
    assert "Refusing automated Keycloak downgrade 26.7.4 -> 25.0.6" in calls

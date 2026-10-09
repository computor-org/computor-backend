"""Behavioral tests for the self-updater's Keycloak version-change guard.

Keycloak does not support DB downgrades, and an old Keycloak reports ready on a
newer schema. So when an update changes the Keycloak image, ops/lib/update.sh
must dump the Keycloak DB (verified) before starting the new version and, if the
update fails afterwards, keep maintenance up and NOT roll the code back.

cmd_update_exec runs for real against throwaway git repos; only docker/redis
side effects are stubbed and recorded.
"""

import gzip
import shlex
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
UPDATE_SH = REPO / "ops/lib/update.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None or shutil.which("git") is None,
                                reason="needs bash and git")

COMPLETE_DUMP = ("--\\n-- PostgreSQL database dump\\n--\\n"
                 "CREATE DATABASE keycloak WITH TEMPLATE = template0;\\n"
                 "-- data\\n--\\n-- PostgreSQL database dump complete\\n--\\n")
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
                kc_state="exited", stop_fails=False, docker_ps_fails=False,
                persistent=True, api_healthy=False):
    calls = tmp_path / "calls.log"
    state = tmp_path / "deploypath/updater"
    state.mkdir(parents=True, exist_ok=True)
    if persistent:
        (state / ".host-persistent").touch()
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
                *"select version from migration_model"*) keycloak_image_tag_at HEAD;;
                *pg_dump*) printf '%b' '{dump_body}';;
                "stop keycloak") [ "{int(stop_fails)}" = 1 ] && return 1;;
                "up -d")
                    if [ -f "$(recovery_marker_file)" ]; then
                        echo migration-protected >> "$CALLS"
                    fi;;
            esac
            return 0
        }}
        docker() {{
            echo "docker $*" >> "$CALLS"
            case "$1" in
                ps) [ "{int(docker_ps_fails)}" = 1 ] && return 1; echo "{kc_state}";;
                inspect) echo healthy;;
            esac
            return 0
        }}
        # By default the API only comes up healthy on the OLD commit.
        wait_for_api() {{ [ "{int(api_healthy)}" = 1 ] || [ "$(git -C "$REPO_ROOT" rev-parse HEAD)" = "{a}" ]; }}
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
    assert calls.index("pg_dump") < calls.index("compose up -d\n")
    assert "migration-protected" in calls
    dumps = list((tmp_path / "deploypath/updater/backups/keycloak").glob("keycloak-pre-25.0.6-to-26.7.4-*.sql.gz"))
    assert len(dumps) == 1 and not list(dumps[0].parent.glob("*.partial"))
    assert "rolling_back" not in calls
    for needle in ("update recover prod restore", "update recover prod keep-new", str(dumps[0]), a, "Keycloak 25.0.6"):
        assert needle in out
    assert "automatic rollback refused" in calls


def test_successful_upgrade_clears_provisional_recovery_marker(tmp_path):
    origin, deploy, a, b = _make_repos(tmp_path, "25.0.6", "26.7.4")
    result, calls = _run_update(tmp_path, origin, deploy, a, COMPLETE_DUMP, api_healthy=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _git(deploy, "rev-parse", "HEAD") == b
    assert "migration-protected" in calls
    assert not (tmp_path / "deploypath/updater/recovery-required").exists()
    assert "redis DEL update:recovery" in calls
    assert "traefik-maintenance off" in calls and "maintenance 0" in calls


def test_keycloak_change_with_incomplete_dump_rolls_back_safely(tmp_path):
    origin, deploy, a, b = _make_repos(tmp_path, "25.0.6", "26.7.4")
    p, calls = _run_update(tmp_path, origin, deploy, a, TRUNCATED_DUMP)
    assert p.returncode == 0, p.stdout + p.stderr           # rolled_back is a clean exit
    assert _git(deploy, "rev-parse", "HEAD") == a            # new Keycloak never started
    assert "compose up -d\n" in calls                         # only the rollback start
    assert calls.count("compose up -d\n") == 1
    assert "status rolled_back" in calls
    assert "traefik-maintenance off" in calls
    assert not list((tmp_path / "deploypath/updater/backups/keycloak").glob("*"))


@pytest.mark.parametrize("tags,enabled", [(("26.7.4", "26.7.4"), "true"),
                                          (("25.0.6", "26.7.4"), "false")])
def test_no_keycloak_change_keeps_ordinary_rollback(tmp_path, tags, enabled):
    origin, deploy, a, b = _make_repos(tmp_path, *tags)
    p, calls = _run_update(tmp_path, origin, deploy, a, COMPLETE_DUMP, keycloak_enabled=enabled)
    assert p.returncode == 0, p.stdout + p.stderr
    assert _git(deploy, "rev-parse", "HEAD") == a
    assert "pg_dump" not in calls
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
    assert "pg_dump" not in calls                         # no dump of a live DB
    assert calls.count("compose up -d\n") == 1              # only the rollback start
    assert _git(deploy, "rev-parse", "HEAD") == a
    assert "did not stop cleanly" in calls


@pytest.mark.parametrize("state", ["exited", ""])
def test_verified_shutdown_precedes_dump(tmp_path, state):
    origin, deploy, a, b = _make_repos(tmp_path, "25.0.6", "26.7.4")
    p, calls = _run_update(tmp_path, origin, deploy, a, COMPLETE_DUMP, kc_state=state)
    assert calls.index("compose stop keycloak") < calls.index("docker ps -a") < calls.index("pg_dump")


def test_keycloak_downgrade_is_refused_without_touching_anything(tmp_path):
    origin, deploy, a, b = _make_repos(tmp_path, "26.7.4", "25.0.6")
    p, calls = _run_update(tmp_path, origin, deploy, a, COMPLETE_DUMP)
    assert p.returncode != 0
    assert _git(deploy, "rev-parse", "HEAD") == a
    assert "build " not in calls and "maintenance 1" not in calls
    assert "pg_dump" not in calls and "compose up" not in calls
    assert "Refusing automated Keycloak downgrade 26.7.4 -> 25.0.6" in calls


def test_missing_host_persistent_state_dir_fails_safe(tmp_path):
    origin, deploy, a, b = _make_repos(tmp_path, "25.0.6", "26.7.4")
    p, calls = _run_update(tmp_path, origin, deploy, a, COMPLETE_DUMP, persistent=False)
    assert p.returncode == 0, p.stdout + p.stderr          # ordinary rollback, 25 kept
    assert _git(deploy, "rev-parse", "HEAD") == a
    assert "pg_dump" not in calls and calls.count("compose up -d\n") == 1
    assert not (tmp_path / "deploypath/updater/backups").exists()


@pytest.fixture
def failed_upgrade(tmp_path):
    origin, deploy, a, b = _make_repos(tmp_path, "25.0.6", "26.7.4")
    result, _ = _run_update(tmp_path, origin, deploy, a, COMPLETE_DUMP)
    assert result.returncode != 0, result.stdout + result.stderr
    marker = tmp_path / "deploypath/updater/recovery-required"
    assert marker.is_file()
    dump = next((marker.parent / "backups/keycloak").glob("*.sql.gz"))
    return origin, deploy, a, b, marker, dump


def _run_recovery(tmp_path, deploy, mode, *, unhealthy="", sql_error=False,
                  schema=None):
    """Run actual recovery; Docker emits the observed schema and SQL exit status."""
    calls = tmp_path / "recovery.log"
    expected_schema = schema or ("25.0.6" if mode == "restore" else "26.7.4")
    script = textwrap.dedent(f"""
        set -u
        REPO_ROOT={shlex.quote(str(deploy))}
        SYSTEM_REPO_BRANCH=main
        SYSTEM_DEPLOYMENT_PATH={shlex.quote(str(tmp_path / "deploypath"))}
        CALLS={shlex.quote(str(calls))}
        source {shlex.quote(str(UPDATE_SH))}
        update_env_init() {{ :; }}
        log() {{ echo "$*"; }}
        die() {{ echo "$*" >&2; exit 1; }}
        redis_cli() {{ echo "redis $*" >> "$CALLS"; [ "$1" = SET ] && echo OK; return 0; }}
        build_images() {{ echo "build $(git -C "$REPO_ROOT" rev-parse HEAD)" >> "$CALLS"; }}
        set_redis_maintenance() {{ echo "maintenance $1" >> "$CALLS"; }}
        ensure_maintenance_page() {{ :; }}
        activate_traefik_maintenance() {{ echo "traefik-maintenance on" >> "$CALLS"; }}
        deactivate_traefik_maintenance() {{ echo "traefik-maintenance off" >> "$CALLS"; }}
        sleep() {{ :; }}
        compose() {{
            echo "compose $*" >> "$CALLS"
            case "$*" in
                *"select version from migration_model"*) echo {shlex.quote(expected_schema)};;
                *"DROP DATABASE"*)
                    # The irreversible step must be fenced before it starts.
                    echo "restore-state $(recovery_marker_get restore_started)" >> "$CALLS";;
                *psql*)
                    cat > {shlex.quote(str(tmp_path / "restored.sql"))}
                    # psql ignores SQL errors unless ON_ERROR_STOP is enabled.
                    if [ {int(sql_error)} = 1 ] && [[ "$*" = *ON_ERROR_STOP=1* ]]; then
                        return 1
                    fi;;
            esac
            return 0
        }}
        docker() {{
            echo "docker $*" >> "$CALLS"
            case "$1" in
                ps) echo exited;;
                inspect) echo healthy;;
            esac
        }}
        wait_for_keycloak() {{ echo health-keycloak >> "$CALLS"; [ "{unhealthy}" != keycloak ]; }}
        wait_for_api() {{ echo health-api >> "$CALLS"; [ "{unhealthy}" != api ]; }}
        wait_for_frontend() {{ echo health-frontend >> "$CALLS"; [ "{unhealthy}" != frontend ]; }}
        cmd_update_recover prod {shlex.quote(mode)}
    """)
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60)
    return result, calls.read_text() if calls.exists() else ""


def _assert_stays_closed(result, calls, marker):
    assert result.returncode != 0, result.stdout + result.stderr
    assert marker.is_file()
    assert "traefik-maintenance off" not in calls
    assert "maintenance 0" not in calls
    assert "redis DEL update:recovery" not in calls


def test_retry_at_same_commit_cannot_bypass_recovery_gate(tmp_path, failed_upgrade):
    origin, deploy, a, b, marker, dump = failed_upgrade
    (tmp_path / "calls.log").unlink()
    # A fresh shell models a replacement updater with no Redis recovery mirror.
    result, calls = _run_update(tmp_path, origin, deploy, a, COMPLETE_DUMP)
    _assert_stays_closed(result, calls, marker)
    assert _git(deploy, "rev-parse", "HEAD") == b
    assert "Already up to date" not in result.stdout
    assert "build " not in calls and "compose " not in calls
    assert dump.is_file()


@pytest.mark.parametrize("mode", ["restore", "keep-new"])
def test_recovery_reopens_only_after_every_health_check(tmp_path, failed_upgrade, mode):
    _, deploy, a, b, marker, dump = failed_upgrade
    result, calls = _run_recovery(tmp_path, deploy, mode)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not marker.exists()
    assert "redis HSET update:state status success" in calls
    assert dump.is_file()  # recovery does not discard the only pre-upgrade backup
    assert _git(deploy, "rev-parse", "HEAD") == (a if mode == "restore" else b)
    assert calls.index("health-keycloak") < calls.index("health-api") < calls.index("health-frontend")
    assert calls.index("health-frontend") < calls.index("redis DEL update:recovery")
    assert calls.index("health-frontend") < calls.index("traefik-maintenance off") < calls.index("maintenance 0")
    if mode == "restore":
        assert "restore-state 1" in calls
        assert calls.index("DROP DATABASE") < calls.index("health-keycloak")
        assert (tmp_path / "restored.sql").read_bytes() == gzip.decompress(dump.read_bytes())
    else:
        assert "DROP DATABASE" not in calls and not (tmp_path / "restored.sql").exists()


@pytest.mark.parametrize("mode", ["restore", "keep-new"])
@pytest.mark.parametrize("unhealthy", ["keycloak", "api", "frontend"])
def test_recovery_health_failure_preserves_fence(tmp_path, failed_upgrade, mode, unhealthy):
    _, deploy, _, _, marker, _ = failed_upgrade
    result, calls = _run_recovery(tmp_path, deploy, mode, unhealthy=unhealthy)
    _assert_stays_closed(result, calls, marker)
    assert f"health-{unhealthy}" in calls
    assert "redis HSET update:state status failed" in calls


@pytest.mark.parametrize("invalid", ["corrupt", "incomplete", "missing"])
def test_invalid_backup_is_rejected_before_database_drop(tmp_path, failed_upgrade, invalid):
    _, deploy, _, _, marker, dump = failed_upgrade
    if invalid == "corrupt":
        dump.write_bytes(b"not a gzip file")
    elif invalid == "incomplete":
        dump.write_bytes(gzip.compress(b"CREATE DATABASE keycloak WITH TEMPLATE = template0;\n"))
    else:
        dump.unlink()
    result, calls = _run_recovery(tmp_path, deploy, "restore")
    _assert_stays_closed(result, calls, marker)
    assert "DROP DATABASE" not in calls


def test_sql_failure_cannot_be_ignored_or_reopened_with_keep_new(tmp_path, failed_upgrade):
    _, deploy, _, b, marker, _ = failed_upgrade
    result, calls = _run_recovery(tmp_path, deploy, "restore", sql_error=True)
    _assert_stays_closed(result, calls, marker)
    assert "restore-state 1" in calls
    assert "health-keycloak" not in calls
    # Even putting the new code back must not reopen a partially restored DB.
    _git(deploy, "checkout", "-q", "-B", "main", b)
    (tmp_path / "recovery.log").unlink()
    result, calls = _run_recovery(tmp_path, deploy, "keep-new")
    _assert_stays_closed(result, calls, marker)
    assert "compose up" not in calls


@pytest.mark.parametrize("mode", ["restore", "keep-new"])
def test_healthy_service_with_wrong_schema_cannot_reopen(tmp_path, failed_upgrade, mode):
    _, deploy, _, _, marker, _ = failed_upgrade
    result, calls = _run_recovery(tmp_path, deploy, mode, schema="24.0.5")
    _assert_stays_closed(result, calls, marker)


def test_keep_new_rejects_old_keycloak_checkout(tmp_path, failed_upgrade):
    _, deploy, a, _, marker, _ = failed_upgrade
    _git(deploy, "checkout", "-q", "-B", "main", a)
    result, calls = _run_recovery(tmp_path, deploy, "keep-new")
    _assert_stays_closed(result, calls, marker)
    assert "compose " not in calls


def test_restore_preserves_dirty_tracked_checkout(tmp_path, failed_upgrade):
    _, deploy, _, b, marker, _ = failed_upgrade
    changed = deploy / "ops/docker/docker-compose.keycloak.yaml"
    changed.write_text(_compose_yaml("26.7.4") + "# local operational change\n")
    result, calls = _run_recovery(tmp_path, deploy, "restore")
    _assert_stays_closed(result, calls, marker)
    assert _git(deploy, "rev-parse", "HEAD") == b
    assert "# local operational change" in changed.read_text()
    assert "compose " not in calls


def test_restore_rejects_incomplete_marker_before_stopping_services(tmp_path, failed_upgrade):
    _, deploy, _, _, marker, _ = failed_upgrade
    marker.write_text("reason=failed upgrade\n")
    result, calls = _run_recovery(tmp_path, deploy, "restore")
    _assert_stays_closed(result, calls, marker)
    assert "compose " not in calls

"""Exercise the real up/deploy lifecycle with isolated Compose/health doubles."""
import os
from pathlib import Path
import subprocess

import pytest


SCRIPT = Path(os.environ.get("QA_LIFECYCLE_SCRIPT", Path(__file__).resolve().parents[4] / "ops/qa/qactl.sh"))


@pytest.fixture
def lifecycle(tmp_path):
    source = SCRIPT.read_text().rsplit('\nmain "$@"; exit', 1)[0]
    controller = tmp_path / "controller.sh"
    controller.write_text(source)
    themes = tmp_path / "src/data/keycloak/themes/computor/login"
    themes.mkdir(parents=True)
    (themes / "theme.properties").write_text("styles=css/login-current.css\n")
    css = themes / "css/login-current.css"
    css.parent.mkdir()
    css.write_text("body { color: navy; }\n")
    (tmp_path / ".seeded").touch()
    events = tmp_path / "events"
    marker = tmp_path / "keycloak-theme.sha256"

    def run(command, before="existing", after="existing", fail=""):
        (tmp_path / "container").write_text(before)
        events.write_text("")
        env = {**os.environ, "QA_HOME": str(tmp_path), "QA_BACKEND_REPO": str(tmp_path),
               "AFTER_CID": after, "FAIL": fail}
        result = subprocess.run(["bash", "-c", '''
source "$1"
SRC="$QA_HOME/src"
ensure_state() { :; }
ensure_source() { :; }
load_env() { :; }
stage_runtime_files() { :; }
images_present() { return 0; }
keycloak_setup() { :; }
cmd_status() { :; }
qa_compose() {
    case "$*" in
        'ps -q keycloak') cat "$QA_HOME/container" ;;
        'up -d --remove-orphans')
            echo up >> "$QA_HOME/events"
            printf '%s' "$AFTER_CID" > "$QA_HOME/container" ;;
        'restart --no-deps keycloak')
            echo restart-keycloak >> "$QA_HOME/events"
            [ "$FAIL" != restart ] ;;
        *) echo "Unexpected Compose operation" >&2; return 2 ;;
    esac
}
wait_healthy() {
    echo "healthy-$1" >> "$QA_HOME/events"
    [ "$FAIL" != health ] || [ "$1" != keycloak ]
}
"$2"
''', "qa-lifecycle", str(controller), command], env=env, text=True,
                                capture_output=True, timeout=10)
        return result, events.read_text().splitlines()

    return run, marker, css


@pytest.mark.parametrize("command", ["cmd_up", "cmd_deploy"])
@pytest.mark.parametrize("previous", [None, "old-theme"])
def test_existing_unknown_or_changed_theme_refreshes_only_keycloak(lifecycle, command, previous):
    run, marker, _ = lifecycle
    if previous is not None:
        marker.write_text(previous)
    result, events = run(command)
    assert result.returncode == 0, result.stderr
    assert events == ["up", "restart-keycloak", "healthy-keycloak", "healthy-uvicorn"]
    assert marker.read_text().strip() != previous
    assert len(marker.read_text().strip()) == 64


@pytest.mark.parametrize("command", ["cmd_up", "cmd_deploy"])
@pytest.mark.parametrize("before", ["", "replaced-container"])
def test_fresh_process_records_theme_without_redundant_restart(lifecycle, command, before):
    run, marker, _ = lifecycle
    result, events = run(command, before=before, after="fresh-container")
    assert result.returncode == 0, result.stderr
    assert events == ["up", "healthy-keycloak", "healthy-uvicorn"]
    assert len(marker.read_text().strip()) == 64


@pytest.mark.parametrize("command", ["cmd_up", "cmd_deploy"])
def test_unchanged_theme_ignores_metadata_but_refreshes_changed_bytes_and_paths(lifecycle, command):
    run, marker, css = lifecycle
    assert run(command, before="", after="existing")[0].returncode == 0
    acknowledged = marker.read_text()
    css.touch()
    result, events = run(command)
    assert result.returncode == 0, result.stderr
    assert "restart-keycloak" not in events
    assert marker.read_text() == acknowledged
    css.write_text("body { color: teal; }\n")
    result, events = run(command)
    assert result.returncode == 0, result.stderr
    assert "restart-keycloak" in events
    assert marker.read_text() != acknowledged
    acknowledged = marker.read_text()
    css.rename(css.with_name("login-renamed.css"))
    result, events = run(command)
    assert result.returncode == 0, result.stderr
    assert "restart-keycloak" in events
    assert marker.read_text() != acknowledged


@pytest.mark.parametrize("command", ["cmd_up", "cmd_deploy"])
@pytest.mark.parametrize("failure", ["restart", "health"])
def test_failed_refresh_never_acknowledges_new_theme(lifecycle, command, failure):
    run, marker, _ = lifecycle
    marker.write_text("previous-healthy-theme\n")
    result, events = run(command, fail=failure)
    assert result.returncode != 0
    assert "restart-keycloak" in events
    assert "healthy-uvicorn" not in events
    assert marker.read_text() == "previous-healthy-theme\n"

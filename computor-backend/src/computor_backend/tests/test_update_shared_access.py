"""Exercise the CLI with real Git repositories and filesystem permissions."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


@pytest.fixture
def checkout(tmp_path):
    repo = tmp_path / "deploy"
    repo.mkdir()
    shutil.copy(ROOT / "computor.sh", repo)
    shutil.copytree(ROOT / "ops/lib", repo / "ops/lib")
    (repo / ".gitignore").write_text(".env\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "fixture")
    (repo / ".env").write_text(f"SYSTEM_REPO_URL={repo}\nSYSTEM_REPO_BRANCH=main\n")
    return repo


def test_check_reads_a_shared_checkout_without_global_git_trust(checkout):
    env = os.environ | {"GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"}
    raw = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                         env=env, capture_output=True, text=True)
    assert raw.returncode != 0 and "dubious ownership" in raw.stderr
    before = (checkout / ".git/config").read_bytes()
    result = subprocess.run(["bash", str(checkout / "computor.sh"), "update", "check"],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert git(checkout, "rev-parse", "HEAD") in result.stdout
    assert "Up to date" in result.stdout
    assert (checkout / ".git/config").read_bytes() == before
    assert not (checkout / ".git/FETCH_HEAD").exists()


@pytest.mark.skipif(os.getuid() == 0, reason="root bypasses DAC read restrictions")
def test_unreadable_env_explains_deployment_access(checkout):
    secret = checkout / ".env"
    secret.chmod(0)
    try:
        result = subprocess.run(["bash", str(checkout / "computor.sh"), "update", "check"],
                                capture_output=True, text=True)
    finally:
        secret.chmod(0o600)
    assert result.returncode != 0
    assert "Cannot read" in result.stderr
    assert "deployment group" in result.stderr
    assert "Run updates from your own account" in result.stderr


@pytest.mark.skipif(os.getuid() == 0, reason="root bypasses DAC write restrictions")
def test_readonly_checkout_fails_before_an_update_lock_or_docker_call(checkout, tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "docker-called"
    stub = bin_dir / "docker"
    stub.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 99\n")
    stub.chmod(0o755)
    checkout.chmod(0o555)
    try:
        result = subprocess.run(["bash", str(checkout / "computor.sh"), "update", "run"],
                                env=os.environ | {"PATH": str(bin_dir) + ":" + os.environ["PATH"]},
                                capture_output=True, text=True)
    finally:
        checkout.chmod(0o755)
    assert result.returncode != 0
    assert "Cannot update" in result.stderr
    assert "no sudo to another user" in result.stderr
    assert not marker.exists()


def test_detached_runner_can_read_another_operators_private_config():
    """Docker driver substitutes a real UID/GID transition for its container."""
    if not all(shutil.which(x) for x in ["sudo", "setpriv", "setfacl"]):
        pytest.skip("requires local test identities and ACL tools")
    if subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode:
        pytest.skip("local test identities unavailable")
    with tempfile.TemporaryDirectory(prefix="computor-runner-access.") as tmp:
        repo = Path(tmp)
        repo.chmod(0o755)
        (repo / "ops/lib").mkdir(parents=True)
        (repo / "ops/lib/common.sh").write_text(f"REPO_ROOT={repo}\n")
        (repo / "ops/lib/update.sh").write_text(
            'cmd_update_exec() { cat "$REPO_ROOT/.env" > "$REPO_ROOT/result"; }\n')
        secret = repo / ".env"
        secret.write_text("other-operator-config\n")
        secret.chmod(0o600)
        subprocess.run(["setfacl", "-m", f"g:{os.getgid()}:r", str(secret)], check=True)
        subprocess.run(["sudo", "-n", "chown", "65534:65534", str(secret)], check=True)
        driver = r'''
            set -e
            redis-cli() {
                case "$*" in *BLPOP*) printf 'update:queue\nfixture\n';; esac
            }
            id() { case "$1" in -u) echo "$TEST_UID";; -g) echo 30001;; esac; }
            docker() {
                case "$1" in
                    inspect)
                        if [ "$2" = --format ]; then echo fixture-image; return; fi
                        [ ! -f "$COMPUTOR_REPO_DIR/result" ] || exit 0
                        return 1;;
                    run)
                        local command="${!#}" identity="" groups=""
                        while [ "$#" -gt 0 ]; do
                            case "$1" in
                                --user) identity="$2"; shift;;
                                --group-add) groups="${groups:+$groups,}$2"; shift;;
                            esac
                            shift
                        done
                        sudo -n setpriv --reuid="${identity%:*}" --regid="${identity#*:}" \
                            --groups="$groups" bash -c "$command";;
                esac
            }
            source "$WATCHER"
        '''
        env = os.environ | dict(COMPUTOR_REPO_DIR=str(repo), COMPUTOR_DEPLOY_GID=str(os.getgid()),
                                DOCKER_GID="30000", REDIS_PASSWORD="fixture", TEST_UID=str(os.getuid()),
                                WATCHER=str(ROOT / "docker/updater/watch.sh"))
        result = subprocess.run(["bash", "-c", driver], env=env,
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stdout + result.stderr
        assert (repo / "result").read_text() == "other-operator-config\n"

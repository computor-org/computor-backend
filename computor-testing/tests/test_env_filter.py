"""Environment scrubbing keeps worker secrets out of student code (#241)."""

from ctexec.environment import filter_env, is_blocked_var, get_safe_env


def test_api_token_is_blocked():
    assert is_blocked_var("API_TOKEN")
    assert is_blocked_var("TESTING_WORKER_TOKEN")


def test_computor_prefix_is_blocked():
    assert is_blocked_var("COMPUTOR_BACKEND_URL")
    assert is_blocked_var("computor_secret")  # case-insensitive


def test_filter_env_removes_secrets_keeps_the_rest():
    env = {
        "API_TOKEN": "s3cr3t",
        "TESTING_WORKER_TOKEN": "s3cr3t",
        "COMPUTOR_BACKEND_URL": "http://api",
        "PATH": "/usr/bin",
        "R_LIBS_USER": "/home/worker/.local/lib/R/library",
    }
    filtered = filter_env(env)
    assert "API_TOKEN" not in filtered
    assert "TESTING_WORKER_TOKEN" not in filtered
    assert "COMPUTOR_BACKEND_URL" not in filtered
    assert filtered["PATH"] == "/usr/bin"
    assert filtered["R_LIBS_USER"].endswith("R/library")


def test_safe_env_drops_blocked_extra_vars():
    env = get_safe_env("python", extra_vars={"API_TOKEN": "x", "MY_FLAG": "1"})
    assert "API_TOKEN" not in env
    assert env["MY_FLAG"] == "1"

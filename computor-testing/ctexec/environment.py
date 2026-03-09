"""
Unified safe environment handling for all executors.

Provides consistent, secure environment configuration to prevent
leaking secrets to student code during execution.
"""

import os
from typing import Dict, Set, Optional


# Environment variables that should NEVER be passed to student code
BLOCKED_ENV_VARS: Set[str] = {
    # Cloud credentials
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_SECURITY_TOKEN",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
    "AZURE_TENANT_ID",
    "AZURE_SUBSCRIPTION_ID",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_PROJECT",
    "GCP_SERVICE_ACCOUNT",
    "CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE",
    # Database credentials
    "DATABASE_URL",
    "DB_PASSWORD",
    "DB_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_USER",
    "MYSQL_PASSWORD",
    "MYSQL_ROOT_PASSWORD",
    "MONGO_PASSWORD",
    "REDIS_PASSWORD",
    # API keys and tokens
    "API_KEY",
    "API_SECRET",
    "SECRET_KEY",
    "AUTH_TOKEN",
    "ACCESS_TOKEN",
    "REFRESH_TOKEN",
    "BEARER_TOKEN",
    "JWT_SECRET",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GITHUB_TOKEN",
    "GITLAB_TOKEN",
    "NPM_TOKEN",
    "PYPI_TOKEN",
    # Generic secrets
    "PASSWORD",
    "PASSWD",
    "TOKEN",
    "SECRET",
    "PRIVATE_KEY",
    "ENCRYPTION_KEY",
    "SIGNING_KEY",
    # SSH
    "SSH_AUTH_SOCK",
    "SSH_AGENT_PID",
    "SSH_PRIVATE_KEY",
    # CI/CD
    "CI_JOB_TOKEN",
    "CI_REGISTRY_PASSWORD",
    "DOCKER_PASSWORD",
    "DOCKER_AUTH_CONFIG",
}


# Minimal safe environment for subprocess execution
DEFAULT_SAFE_ENV: Dict[str, str] = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/tmp",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "TERM": "dumb",
}


# Language-specific environment additions
_LANGUAGE_ENV: Dict[str, Dict[str, str]] = {
    "python": {
        "PYTHONHASHSEED": "0",  # Reproducible hashing
        "PYTHONDONTWRITEBYTECODE": "1",  # Don't create .pyc files
        "PYTHONUNBUFFERED": "1",  # Unbuffered output
    },
    "octave": {
        "OCTAVE_HISTFILE": "/dev/null",  # No history file
    },
    "julia": {
        "JULIA_DEPOT_PATH": "/tmp/.julia",
    },
    "r": {
        # R needs real HOME, handled specially in get_safe_env
    },
    "c": {},
    "cpp": {},
    "fortran": {},
}


# Environment variables to pass through from host (if set)
_PASSTHROUGH_VARS: Dict[str, Set[str]] = {
    "python": {"PYTHONPATH", "VIRTUAL_ENV"},
    "r": {"R_LIBS_USER", "R_LIBS", "R_HOME"},
    "julia": {"JULIA_LOAD_PATH", "JULIA_PROJECT"},
    "octave": {"OCTAVE_PATH"},
    "c": {"CC", "CFLAGS", "LDFLAGS"},
    "cpp": {"CXX", "CXXFLAGS", "LDFLAGS"},
    "fortran": {"FC", "FFLAGS", "LDFLAGS"},
}


def get_safe_env(
    language: str,
    working_dir: Optional[str] = None,
    extra_vars: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Get a safe environment for executing code in the given language.

    Args:
        language: Language key (python, r, julia, octave, c, cpp, fortran)
        working_dir: Working directory to set appropriate paths
        extra_vars: Additional environment variables to include

    Returns:
        Dictionary of safe environment variables
    """
    env = DEFAULT_SAFE_ENV.copy()

    # Add language-specific variables
    lang_lower = language.lower()
    if lang_lower in _LANGUAGE_ENV:
        env.update(_LANGUAGE_ENV[lang_lower])

    # Pass through allowed variables from host
    if lang_lower in _PASSTHROUGH_VARS:
        for var in _PASSTHROUGH_VARS[lang_lower]:
            if var in os.environ:
                env[var] = os.environ[var]

    # R needs real HOME for library loading
    if lang_lower == "r":
        env["HOME"] = os.path.expanduser("~")

    # Set working directory in PYTHONPATH for Python
    if lang_lower == "python" and working_dir:
        existing = env.get("PYTHONPATH", "")
        if existing:
            env["PYTHONPATH"] = f"{working_dir}:{existing}"
        else:
            env["PYTHONPATH"] = working_dir

    # Add extra variables (after filtering blocked ones)
    if extra_vars:
        for key, value in extra_vars.items():
            if key.upper() not in BLOCKED_ENV_VARS:
                env[key] = value

    return env


def filter_env(env: Dict[str, str]) -> Dict[str, str]:
    """
    Remove blocked environment variables from a dictionary.

    Args:
        env: Environment dictionary to filter

    Returns:
        Filtered environment dictionary
    """
    return {k: v for k, v in env.items() if k.upper() not in BLOCKED_ENV_VARS}


def is_blocked_var(name: str) -> bool:
    """Check if an environment variable name is blocked."""
    return name.upper() in BLOCKED_ENV_VARS

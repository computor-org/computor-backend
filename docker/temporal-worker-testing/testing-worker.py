#!/usr/bin/env python3
"""
Unified Testing Worker Startup Script

This script:
1. Fetches service configuration from the Computor API
2. Clones/updates the computor-testing repository from GitLab
3. Installs the computor-testing framework
4. Sets up language-specific test execution environments
5. Starts the Temporal worker for unified multi-language testing

Supports: Python, Octave, R, Julia, C/C++, Fortran, Document analysis
"""

import asyncio
import os
import sys
import subprocess
from typing import Any, Dict, List, Optional

from computor_types.repositories import Repository
from computor_types.services import ServiceGet
from computor_client.http import AsyncHTTPClient


# =============================================================================
# Configuration Fetching
# =============================================================================

async def fetch_service_config(
    max_retries: int = 60,
    retry_interval: int = 5
) -> Optional[ServiceGet]:
    """
    Fetch service configuration from the Computor API.

    Uses the API_TOKEN environment variable to authenticate.
    Retries with configurable interval if the backend is not yet available.
    Returns None if the API call fails after all retries or token is not set.

    Args:
        max_retries: Maximum number of retry attempts (default: 60 = 5 minutes with 5s interval)
        retry_interval: Seconds to wait between retries (default: 5)
    """
    api_token = os.getenv("API_TOKEN")
    api_base_url = os.getenv("API_URL")

    if not api_token:
        print("  ⚠ API_TOKEN not set, skipping API config fetch")
        return None

    if not api_base_url:
        print("  ⚠ API_URL not set, skipping API config fetch")
        return None

    print(f"  Fetching config from: {api_base_url}/service-accounts/me")
    print(f"  Token prefix: {api_token[:12]}..." if len(api_token) > 12 else "  Token: (short)")

    for attempt in range(1, max_retries + 1):
        try:
            async with AsyncHTTPClient(base_url=api_base_url, headers={"X-API-Token": api_token}) as client:
                print(f"  Making API request (attempt {attempt}/{max_retries})...")
                response = await client.get("/service-accounts/me")
                print(f"  Response status: {response.status_code}")
                data = response.json()
                print(f"  Response data keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                return ServiceGet.model_validate(data)
        except Exception as e:
            if attempt < max_retries:
                print(f"  ⚠ Attempt {attempt}/{max_retries} failed: {e}")
                print(f"  Retrying in {retry_interval} seconds...")
                await asyncio.sleep(retry_interval)
            else:
                print(f"  ⚠ Failed to fetch config from API after {max_retries} attempts: {e}")
                import traceback
                traceback.print_exc()
                return None

    return None


def get_service_language(service_config: Optional[ServiceGet], config: Dict[str, Any]) -> str:
    """
    Determine the primary language for this service.

    Priority:
    1. Explicit 'language' field in config
    2. Inferred from service slug (e.g., itpcp.exec.py -> python)
    3. Default to 'python'
    """
    # Check explicit language in config
    if "language" in config:
        return config["language"]

    # Infer from service slug
    if service_config and service_config.slug:
        slug = service_config.slug.lower()
        if slug.endswith(".py"):
            return "python"
        elif slug.endswith(".oct"):
            return "octave"
        elif slug.endswith(".r"):
            return "r"
        elif slug.endswith(".julia"):
            return "julia"
        elif slug.endswith(".mat"):
            return "matlab"
        elif slug.endswith(".c"):
            return "c"
        elif slug.endswith(".fortran"):
            return "fortran"

    return "python"


# =============================================================================
# Language-specific Environment Setup
# =============================================================================

def setup_python_environment(config: Dict[str, Any], framework_package_path: str) -> None:
    """
    Set up Python test execution environment.

    Creates a virtual environment with the specified Python version
    and installs required packages.
    """
    python_config = config.get("python", {})
    python_version = python_config.get("version", "3.13")
    requirements = python_config.get("requirements", [])
    pip_index_url = python_config.get("pip_index_url")
    environment = python_config.get("environment", {})

    # Environment variables override API config if set
    env_python_version = os.getenv("PYTHON_TEST_VERSION")
    env_requirements = os.getenv("PYTHON_TEST_REQUIREMENTS", "")

    if env_python_version:
        python_version = env_python_version

    # Merge requirements
    if isinstance(requirements, str):
        requirements = [r.strip() for r in requirements.split(",") if r.strip()]
    requirements_list = list(requirements)
    if env_requirements:
        requirements_list.extend([r.strip() for r in env_requirements.split(",") if r.strip()])

    test_venv_path = "/home/worker/test-venv"

    print(f"  Python version: {python_version}")
    print(f"  Additional requirements: {requirements_list if requirements_list else '(none)'}")

    # Create venv with specified Python version
    python_executable = f"python{python_version}"
    venv_create = subprocess.run(
        f"{python_executable} -m venv {test_venv_path}",
        shell=True,
        capture_output=True,
        text=True
    )

    if venv_create.returncode != 0:
        print(f"  ⚠ Failed to create test venv: {venv_create.stderr}")
        print(f"  Tests will run in worker Python (3.10) instead")
        return

    print(f"  ✓ Created venv at {test_venv_path} (Python {python_version})")

    # Install base testing dependencies from computor-testing requirements.txt
    print("  Installing base test dependencies (numpy, scipy, matplotlib, etc.)...")
    requirements_path = os.path.join(framework_package_path, "requirements.txt")

    pip_cmd_base = f"{test_venv_path}/bin/pip"
    if pip_index_url:
        pip_cmd_base += f" --index-url {pip_index_url}"

    if os.path.exists(requirements_path):
        pip_install = subprocess.run(
            f"{pip_cmd_base} install -r {requirements_path}",
            shell=True
        )
        if pip_install.returncode == 0:
            print("  ✓ Base dependencies installed")
        else:
            print("  ⚠ Failed to install base dependencies")
    else:
        print("  ⚠ requirements.txt not found, skipping base dependencies")

    # Install additional requirements if specified
    if requirements_list:
        print(f"  Installing additional requirements: {requirements_list}")
        pip_install_extra = subprocess.run(
            f"{pip_cmd_base} install {' '.join(requirements_list)}",
            shell=True
        )
        if pip_install_extra.returncode == 0:
            print("  ✓ Additional requirements installed")
        else:
            print("  ⚠ Failed to install some additional requirements")

    # Verify numpy in test venv
    numpy_check = subprocess.run(
        f"{test_venv_path}/bin/python -c 'import numpy; print(numpy.__version__)'",
        shell=True,
        capture_output=True,
        text=True
    )
    if numpy_check.returncode == 0:
        print(f"  ✓ numpy available in test venv: {numpy_check.stdout.strip()}")

    # Verify Python version in test venv
    version_check = subprocess.run(
        f"{test_venv_path}/bin/python --version",
        shell=True,
        capture_output=True,
        text=True
    )
    if version_check.returncode == 0:
        print(f"  ✓ Test venv Python: {version_check.stdout.strip()}")

    # Set environment variable for PyExecutor to use test venv Python
    os.environ["PYTHON_TEST_EXECUTABLE"] = f"{test_venv_path}/bin/python"
    print(f"  ✓ Set PYTHON_TEST_EXECUTABLE={test_venv_path}/bin/python")

    # Set additional environment variables from config
    for key, value in environment.items():
        os.environ[key] = str(value)
        print(f"  ✓ Set {key}={value}")


def setup_octave_environment(config: Dict[str, Any]) -> None:
    """
    Set up Octave test execution environment.

    Installs Octave packages if specified.
    """
    octave_config = config.get("octave", {})
    packages = octave_config.get("packages", [])

    print(f"  Octave packages to install: {packages if packages else '(none)'}")

    if packages:
        for package in packages:
            print(f"  Installing Octave package: {package}")
            result = subprocess.run(
                f"octave --eval \"pkg install -forge {package}\"",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"  ✓ Installed {package}")
            else:
                print(f"  ⚠ Failed to install {package}: {result.stderr}")

    # Verify Octave is available
    octave_check = subprocess.run(
        "octave --version",
        shell=True,
        capture_output=True,
        text=True
    )
    if octave_check.returncode == 0:
        version_line = octave_check.stdout.split('\n')[0]
        print(f"  ✓ Octave available: {version_line}")


def setup_r_environment(config: Dict[str, Any]) -> None:
    """
    Set up R test execution environment.

    Installs R packages to R_LIBS_USER if specified.
    """
    r_config = config.get("r", {})
    packages = r_config.get("packages", [])
    cran_mirror = r_config.get("cran_mirror", "https://cloud.r-project.org")

    print(f"  R packages to install: {packages if packages else '(none)'}")

    if packages:
        # Ensure R library directory exists
        r_libs = os.environ.get("R_LIBS_USER", "/home/worker/.local/lib/R/library")
        os.makedirs(r_libs, exist_ok=True)

        for package in packages:
            print(f"  Installing R package: {package}")
            result = subprocess.run(
                f"Rscript -e \"install.packages('{package}', repos='{cran_mirror}', lib='{r_libs}')\"",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"  ✓ Installed {package}")
            else:
                print(f"  ⚠ Failed to install {package}: {result.stderr[:200]}")

    # Verify R is available
    r_check = subprocess.run(
        "R --version",
        shell=True,
        capture_output=True,
        text=True
    )
    if r_check.returncode == 0:
        version_line = r_check.stdout.split('\n')[0]
        print(f"  ✓ R available: {version_line}")


def setup_julia_environment(config: Dict[str, Any]) -> None:
    """
    Set up Julia test execution environment.

    Installs Julia packages if specified.
    """
    julia_config = config.get("julia", {})
    packages = julia_config.get("packages", [])

    print(f"  Julia packages to install: {packages if packages else '(none)'}")

    if packages:
        for package in packages:
            print(f"  Installing Julia package: {package}")
            result = subprocess.run(
                f"julia -e 'using Pkg; Pkg.add(\"{package}\")'",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"  ✓ Installed {package}")
            else:
                print(f"  ⚠ Failed to install {package}: {result.stderr[:200]}")

    # Verify Julia is available
    julia_check = subprocess.run(
        "julia --version",
        shell=True,
        capture_output=True,
        text=True
    )
    if julia_check.returncode == 0:
        print(f"  ✓ Julia available: {julia_check.stdout.strip()}")


def setup_compiled_languages(config: Dict[str, Any]) -> None:
    """
    Verify C/C++/Fortran compilers are available.

    These are typically installed in the Dockerfile, so we just verify.
    """
    compilers = [
        ("gcc", "GCC (C compiler)"),
        ("g++", "G++ (C++ compiler)"),
        ("gfortran", "GFortran (Fortran compiler)"),
    ]

    for cmd, name in compilers:
        result = subprocess.run(
            f"{cmd} --version",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"  ✓ {name}: {version_line}")
        else:
            print(f"  ⚠ {name}: not available")


def setup_language_environment(
    language: str,
    config: Dict[str, Any],
    framework_package_path: str
) -> None:
    """
    Set up the test execution environment for the specified language.
    """
    print(f"\n  Setting up {language} environment...")

    if language == "python":
        setup_python_environment(config, framework_package_path)
    elif language == "octave":
        setup_octave_environment(config)
    elif language == "r":
        setup_r_environment(config)
    elif language == "julia":
        setup_julia_environment(config)
    elif language in ("c", "cpp", "fortran"):
        setup_compiled_languages(config)
    elif language == "matlab":
        print("  MATLAB environment is handled by separate matlab-server container")
    else:
        print(f"  ⚠ Unknown language: {language}, skipping environment setup")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    print("=" * 80)
    print("Starting Unified Testing Worker")
    print("=" * 80)

    # Step 0: Fetch configuration from API
    print("\n[0/4] Fetching service configuration...")
    service_config = asyncio.run(fetch_service_config())

    if service_config:
        print(f"  ✓ Service: {service_config.slug} ({service_config.name})")
        print(f"  ✓ Service type: {service_config.service_type_path or 'not set'}")
        config = service_config.config or {}
    else:
        print("  Using environment variables as fallback")
        config = {}

    # Determine primary language
    language = get_service_language(service_config, config)
    print(f"  Primary language: {language}")

    # Get environment configuration (with API config as override)
    TESTING_FRAMEWORK_URL = os.getenv("TESTING_FRAMEWORK_URL")
    TESTING_FRAMEWORK_TOKEN = os.getenv("TESTING_FRAMEWORK_TOKEN")
    TESTING_FRAMEWORK_VERSION = os.getenv("TESTING_FRAMEWORK_VERSION") or "main"

    if not TESTING_FRAMEWORK_URL:
        print("WARNING: TESTING_FRAMEWORK_URL not set, using default")
        TESTING_FRAMEWORK_URL = "https://gitlab.tugraz.at/codeability/testing-frameworks/computor-testing"

    if TESTING_FRAMEWORK_TOKEN is None:
        print("WARNING: No TESTING_FRAMEWORK_TOKEN available.")
        print("         Public repository access only.")

    framework_repo_path = os.path.abspath("/home/worker/computor-testing")
    # The actual package is in a subdirectory (monorepo structure)
    framework_package_path = os.path.join(framework_repo_path, "computor-testing")

    # Step 1: Clone or update computor-testing repository
    print("\n[1/4] Fetching computor-testing framework...")
    print(f"  URL: {TESTING_FRAMEWORK_URL}")
    print(f"  Version: {TESTING_FRAMEWORK_VERSION}")
    print(f"  Target: {framework_repo_path}")

    try:
        result = Repository(
            url=TESTING_FRAMEWORK_URL,
            token=TESTING_FRAMEWORK_TOKEN,
            branch=TESTING_FRAMEWORK_VERSION
        ).clone_or_fetch(framework_repo_path)
        print(f"  ✓ {result}")
    except Exception as e:
        print(f"  ✗ FAILED: git clone/fetch failed [{str(e)}]")
        print("\nContinuing without computor-testing framework...")
        print("Worker will only support legacy testing backends.")

    # Step 2: Install computor-testing framework
    if os.path.exists(framework_package_path) and os.path.exists(os.path.join(framework_package_path, "pyproject.toml")):
        print("\n[2/4] Installing computor-testing framework...")
        print(f"  Package path: {framework_package_path}")

        # Install computor-testing framework in worker Python (3.10)
        cmd = f"pip install --user {framework_package_path}"
        print(f"  Command: {cmd}")
        result = subprocess.run(cmd, cwd=framework_package_path, shell=True)

        if result.returncode == 0:
            print("\n  ✓ computor-testing installed successfully (worker environment)")

            # Verify installation
            verify_cmd = "computor-test --version"
            verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
            if verify_result.returncode == 0:
                print(f"  ✓ computor-test CLI available: {verify_result.stdout.strip()}")
            else:
                print("  ⚠ computor-test CLI not found in PATH")
        else:
            print(f"\n  ✗ Installation failed (exit code: {result.returncode})")
            print("\nContinuing without computor-testing framework...")
    else:
        print("\n[2/4] Skipping computor-testing installation (not available)")
        print(f"  Checked path: {framework_package_path}")
        print(f"  Path exists: {os.path.exists(framework_package_path)}")
        if os.path.exists(framework_package_path):
            print(f"  Contents: {os.listdir(framework_package_path)}")

    # Step 3: Set up language-specific environment
    print(f"\n[3/4] Setting up test execution environment for {language}...")
    setup_language_environment(language, config, framework_package_path)

    # Also set up any additional languages specified in config
    for lang_key in ["python", "octave", "r", "julia", "c", "fortran"]:
        if lang_key in config and lang_key != language:
            print(f"\n  Also setting up {lang_key} (found in config)...")
            setup_language_environment(lang_key, config, framework_package_path)

    # Step 4: Start Temporal worker
    print("\n[4/4] Starting Temporal worker...")

    # Pass command line arguments to the temporal worker
    # This allows docker-compose to specify --queues=testing
    args = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else ''
    cmd = f"python -m computor_backend.tasks.temporal_worker {args}"
    print(f"  Command: {cmd}")

    print("\n" + "=" * 80)
    print("Worker Starting - Logs will follow")
    print("=" * 80 + "\n")

    # Use Popen to allow logs to flow through
    # Forward stdout/stderr so we can see worker activity in Docker logs
    subprocess.Popen(
        cmd,
        cwd=os.path.abspath(os.path.expanduser("~")),
        shell=True,
        stdout=sys.stdout,
        stderr=sys.stderr,
    ).wait()  # Wait for worker to finish (blocks forever)


if __name__ == '__main__':
    main()
